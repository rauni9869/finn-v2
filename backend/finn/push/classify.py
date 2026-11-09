"""Sorts exchange filings into the 17 categories from the challenge reference, with a priority."""
import re
from typing import List, Optional, Tuple

from pydantic import BaseModel

from finn import llm
from finn.cache import cached
from finn.config import FAST_MODELS

CATEGORIES = [
    "results", "M&A", "fund_raise", "management_change", "litigation", "insider_trading",
    "earnings_call", "investor_meetings", "credit_rating", "dividend", "bonus_split", "capex",
    "press_release", "postal_ballot", "agm_egm", "pledging", "unclassified",
]

# How much each category usually matters to an investor
DEFAULT_PRIORITY = {
    "results": "HIGH", "M&A": "HIGH", "fund_raise": "HIGH", "management_change": "HIGH",
    "litigation": "HIGH", "capex": "HIGH",
    "insider_trading": "MEDIUM", "credit_rating": "MEDIUM", "dividend": "MEDIUM", "bonus_split": "MEDIUM",
    "press_release": "MEDIUM", "pledging": "MEDIUM", "earnings_call": "MEDIUM",
    "investor_meetings": "LOW", "postal_ballot": "LOW", "agm_egm": "LOW", "unclassified": "LOW",
}

# Checked in order: the first match wins, and a rule may lower the default priority
RULES: List[Tuple[str, Optional[str], List[str]]] = [
    ("unclassified", None, [
        r"reg(ulation)?\.?\s*74\s*\(5\)", r"trading window", r"loss of share certificate", r"duplicate share",
        r"esop|esos|esps|employee stock", r"secretarial compliance", r"business responsibility", r"\besg\b",
        r"appointment of (statutory|secretarial|internal|cost) auditor", r"certificate under reg", r"regulation 7\(3\)",
        r"regulation 40\(9\)", r"investor complaints", r"related party transactions? disclosure",
        r"monitoring agency", r"repayment", r"interest payment", r"credit of interest", r"redemption",
    ]),
    ("postal_ballot", None, [r"postal.?ballot", r"e-?voting", r"scrutini[sz]er"]),
    ("agm_egm", None, [r"\bagm\b", r"\begm\b", r"annual general meeting", r"extra-?ordinary general meeting", r"shareholders? meeting"]),
    ("results", "LOW", [r"newspaper publication.*result", r"result.*newspaper", r"board meeting intimation.*result", r"intimation of board meeting.*result"]),
    ("results", "MEDIUM", [r"investor presentation", r"results? presentation", r"shareholder'?s? letter", r"media statement"]),
    ("results", "HIGH", [r"financial results?", r"^result\b", r"unaudited", r"audited .*results?", r"quarterly results?"]),
    ("earnings_call", None, [r"earnings? call", r"conference call", r"con-?call", r"audio recording", r"transcript", r"video recording"]),
    ("investor_meetings", None, [r"analyst\(?s?\)?\s*/\s*investor\(?s?\)?\s*meet", r"investor meet", r"analysts? meet", r"investor conference", r"one-on-one"]),
    ("management_change", None, [
        r"change in (directorate|management|kmp|key managerial)", r"resignation", r"appointment", r"retire", r"cessation",
        r"chief (executive|financial|operating)", r"\b(ceo|cfo|coo|md)\b", r"managing director", r"key managerial", r"re-?designation",
    ]),
    ("M&A", None, [r"acquisition", r"acquire", r"merger", r"amalgamation", r"demerger", r"scheme of arrangement", r"joint venture", r"stake sale", r"divest", r"slump sale"]),
    ("fund_raise", None, [r"\bqip\b", r"qualified institution", r"rights issue", r"preferential (issue|allotment)", r"buy-?back", r"commercial paper", r"debentures?|\bncds?\b", r"fund rais", r"issue of securities", r"warrants"]),
    ("litigation", None, [r"litigation", r"dispute", r"regulatory action", r"penalt", r"show cause", r"\bsebi order", r"tax demand", r"\bgst\b.*(demand|order)", r"insolvency", r"nclt", r"warning letter", r"form 483", r"import alert", r"\busfda\b|\bus fda\b", r"court"]),
    ("pledging", None, [r"pledge", r"encumbrance", r"31\s*\(1\)"]),
    ("insider_trading", None, [r"insider trading", r"\bpit\b", r"regulation 7\s*\(2\)", r"disclosure under sebi takeover", r"\bsast\b", r"29\s*\(2\)"]),
    ("credit_rating", None, [r"credit rating", r"\bcrisil\b", r"\bicra\b", r"care ratings?", r"india ratings", r"rating (upgrade|downgrade|reaffirm)"]),
    ("bonus_split", None, [r"bonus", r"sub-?division", r"stock split", r"split of"]),
    ("dividend", None, [r"dividend", r"record date"]),
    ("capex", None, [r"capex", r"capital expenditure", r"capacity expansion", r"new (plant|facility|unit)", r"greenfield", r"brownfield", r"commissioning", r"commencement of (commercial )?production"]),
    ("press_release", None, [r"press release", r"media release", r"\border\b", r"contract", r"award", r"launch", r"partnership", r"collaboration", r"clarification", r"spurt in volume"]),
    ("unclassified", None, [r"newspaper publication", r"board meeting intimation", r"intimation of board meeting", r"compliance"]),
]

# Subjects too vague to classify alone, so the summary decides
GENERIC_SUBJECTS = re.compile(r"^(general |meeting |other )?updates?$|^allotment$|^intimation$|^disclosure$|^announcement$|^clarification$")

_EARNINGS_CALL = re.compile(r"earnings? (conference )?call|con-?call|audio recording|transcript|recording of")

_COMPILED = [(cat, prio, [re.compile(p) for p in pats]) for cat, prio, pats in RULES]


def _match(text: str) -> Optional[Tuple[str, str]]:
    for category, priority, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return category, priority or DEFAULT_PRIORITY[category]
    return None


def classify_by_rules(subject: str, summary: str) -> Optional[Tuple[str, str]]:
    """(category, priority) from keyword rules, or None when no rule matches.

    The exchange subject is the filer's own label, so it decides first; the summary
    is used only when the subject is too vague."""
    subject = re.sub(r"announcement under regulation 30 \(lodr\)\s*-?", "", subject.lower()).strip(" -")
    if subject and not GENERIC_SUBJECTS.search(subject):
        found = _match(subject)
        # Companies often file call recordings and transcripts as an investor meet outcome
        if found and found[0] == "investor_meetings" and _EARNINGS_CALL.search(summary.lower()):
            return "earnings_call", DEFAULT_PRIORITY["earnings_call"]
        if found:
            return found
    return _match(f"{subject} | {summary.lower()}")


class _Label(BaseModel):
    index: int
    category: str


class _Labels(BaseModel):
    labels: List[_Label]


def classify_with_model(items: List[Tuple[str, str, str]]) -> dict:
    """Labels the filings the rules missed, in one cheap batched call. Keyed by filing URL."""
    if not items or not llm.is_available():
        return {}
    key = "classify:" + "|".join(sorted(url for url, _, _ in items))

    def ask():
        listing = "\n".join(f"{i}. {subject} | {summary}" for i, (_, subject, summary) in enumerate(items))
        result = llm.generate_json(
            FAST_MODELS,
            "Classify Indian exchange filings. Use exactly one of these categories: " + ", ".join(CATEGORIES)
            + ". Use 'unclassified' for routine paperwork that would not move the stock.",
            listing,
            _Labels,
        )
        return {items[l.index][0]: l.category for l in result.labels if 0 <= l.index < len(items) and l.category in CATEGORIES}

    try:
        return cached(key, 7 * 24 * 3600, ask) or {}
    except llm.LLMUnavailable:
        return {}
