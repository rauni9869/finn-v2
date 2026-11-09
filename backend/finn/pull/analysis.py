"""AI analysis grounded only in a company's own earnings call transcripts and reported results."""
import io
import logging
import re
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import BaseModel
from pypdf import PdfReader

from finn import llm
from finn.cache import cache_get, cache_set, cached
from finn.config import REASONING_MODELS
from finn.pull.research import report as research_report
from finn.sources import screener

logger = logging.getLogger(__name__)

MAX_TRANSCRIPTS = 4
MAX_CHARS_PER_TRANSCRIPT = 70000
MIN_PROMISES_FOR_SCORE = 3

SYSTEM = """You analyse an Indian listed company for an equity investor, using ONLY the transcripts and reported numbers provided.
Never use outside knowledge of the company, news, or broker views.

Return:
1. promises: up to 6 specific, checkable things management promised (growth, margins, capex, debt, launches, expansion),
   only where a LATER transcript or the reported numbers show the outcome. Prefer promises with numbers or dates.
   Verdicts: DELIVERED (met or beaten), PARTIAL (partly met), DELAYED (late but still on track), MISSED (not met),
   DIVERGED (outcome contradicts the story). If the evidence does not clearly support DELIVERED, do not use it.
   actual_delivered states the outcome with numbers and says where they came from.
2. guidance: up to 5 forward targets from the LATEST transcript (growth, margin, capex, debt), each as given by management.
3. bull and bear: exactly 3 points each, tight and specific, each backed by a transcript quote or the reported numbers.
4. summary: two sentences on management's credibility.

Every quote must be copied word for word from the cited transcript page, 8 to 30 words, with no edits.
"transcript" must exactly match a transcript label and "page" must be the page holding the quote.
For a bull or bear point backed only by reported numbers, leave quote empty and transcript "numbers"."""


class Promise(BaseModel):
    transcript: str
    page: int
    quote: str
    promised: str
    actual_delivered: str
    verdict: Literal["DELIVERED", "PARTIAL", "DELAYED", "MISSED", "DIVERGED"]
    reasoning: str


class Guidance(BaseModel):
    topic: str
    target: str
    transcript: str
    page: int
    quote: str


class Point(BaseModel):
    point: str
    transcript: str
    page: int
    quote: str


class AnalysisOutput(BaseModel):
    summary: str
    promises: List[Promise]
    guidance: List[Guidance]
    bull: List[Point]
    bear: List[Point]


class AnalysisUnavailable(Exception):
    """Analysis couldn't be produced; the message is safe to show."""


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _load_transcripts(links: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    transcripts = []
    for link in links[:MAX_TRANSCRIPTS]:
        try:
            resp = requests.get(link["url"], headers=screener.HEADERS, timeout=30)
            resp.raise_for_status()
            reader = PdfReader(io.BytesIO(resp.content))
            pages = {n: page.extract_text() or "" for n, page in enumerate(reader.pages, start=1)}
            if sum(len(t) for t in pages.values()) > 1000:
                transcripts.append({"label": link["period"], "url": link["url"], "pages": pages})
        except Exception as e:
            logger.warning(f"Could not read transcript {link['period']}: {e}")
    return list(reversed(transcripts))  # oldest first


def _quote_found(transcripts: Dict[str, Dict[str, Any]], label: str, page: int, quote: str) -> bool:
    transcript = transcripts.get(label)
    if not transcript or len(_normalise(quote)) < 20:
        return False
    # Allow the next page for a quote that runs across a page break
    text = transcript["pages"].get(page, "") + transcript["pages"].get(page + 1, "")
    return _normalise(quote) in _normalise(text)


def _numbers_text(rep: Dict[str, Any]) -> str:
    lines = []
    for title, series in (("QUARTERLY (Rs crore)", rep["quarters"]), ("ANNUAL (Rs crore)", rep["trajectory"])):
        lines.append(f"{title}: periods " + " | ".join(series["periods"]))
        for label, values in series.items():
            if label != "periods":
                lines.append(f"  {label}: " + " | ".join("-" if v is None else f"{v:g}" for v in values))
    return "\n".join(lines)


def _run(ticker: str, rep: Dict[str, Any], links: List[Dict[str, str]]) -> Dict[str, Any]:
    transcripts = _load_transcripts(links)
    if len(transcripts) < 2:
        raise AnalysisUnavailable("Fewer than two earnings call transcripts could be read, so promises can't be checked.")

    sections = []
    for t in transcripts:
        text = "\n".join(f"[{t['label']} | page {n}]\n{body}" for n, body in sorted(t["pages"].items()))
        sections.append(text[:MAX_CHARS_PER_TRANSCRIPT])
    prompt = (
        f"Company: {rep['name']} ({ticker})\n"
        f"Transcript labels, oldest first: {', '.join(t['label'] for t in transcripts)}\n\n"
        f"REPORTED NUMBERS\n{_numbers_text(rep)}\n\nTRANSCRIPTS\n" + "\n\n".join(sections)
    )
    try:
        out = llm.generate_json(REASONING_MODELS, SYSTEM, prompt, AnalysisOutput)
    except llm.LLMUnavailable as e:
        raise AnalysisUnavailable(str(e))

    by_label = {t["label"]: t for t in transcripts}

    def cite(label: str, page: int) -> Dict[str, Any]:
        return {"transcript": label, "page": page, "url": by_label[label]["url"]}

    promises = [
        {**p.model_dump(), **cite(p.transcript, p.page)}
        for p in out.promises if _quote_found(by_label, p.transcript, p.page, p.quote)
    ]
    guidance = [
        {**g.model_dump(), **cite(g.transcript, g.page)}
        for g in out.guidance if _quote_found(by_label, g.transcript, g.page, g.quote)
    ]

    def points(items: List[Point]) -> List[Dict[str, Any]]:
        kept = []
        for p in items:
            if p.transcript == "numbers" and not p.quote:
                kept.append({"point": p.point, "transcript": "numbers", "page": None, "quote": "", "url": None})
            elif _quote_found(by_label, p.transcript, p.page, p.quote):
                kept.append({**p.model_dump(), **cite(p.transcript, p.page)})
        return kept

    checked = len(out.promises) + len(out.guidance) + len(out.bull) + len(out.bear)
    bull, bear = points(out.bull), points(out.bear)
    kept = len(promises) + len(guidance) + len(bull) + len(bear)
    logger.info(f"{ticker}: kept {kept} of {checked} items after quote checks")

    delivered = sum(1 for p in promises if p["verdict"] == "DELIVERED")
    return {
        "ticker": ticker,
        "summary": out.summary,
        "coverage": f"{transcripts[0]['label']} to {transcripts[-1]['label']}",
        "transcripts_read": [{"label": t["label"], "url": t["url"], "pages": len(t["pages"])} for t in transcripts],
        "promises": promises,
        "delivered": delivered,
        # A percentage from one or two promises would look more certain than it is
        "credibility_pct": round(delivered / len(promises) * 100) if len(promises) >= MIN_PROMISES_FOR_SCORE else None,
        "guidance": guidance,
        "bull": bull,
        "bear": bear,
        "dropped_unverified": checked - kept,
        "models_tried": REASONING_MODELS,
    }


def _key(ticker: str, links: List[Dict[str, str]]) -> str:
    # A new transcript changes the key, so the analysis refreshes after each call
    return f"analysis:v2:{ticker}:{links[0]['url']}"


def is_ready(query: str) -> bool:
    """True when this company's latest analysis is already cached."""
    rep = research_report(query)
    links = rep["documents"]["transcripts"]
    return bool(links) and cache_get(_key(rep["ticker"], links)) is not None


def analyse(query: str) -> Dict[str, Any]:
    if not llm.is_available():
        raise AnalysisUnavailable("AI analysis is not configured on this server. Add GEMINI_API_KEY to enable it.")
    rep = research_report(query)
    links = rep["documents"]["transcripts"]
    if not links:
        raise AnalysisUnavailable("No earnings call transcripts are available for this company on screener.in.")
    key = _key(rep["ticker"], links)
    result = cached(key, 14 * 24 * 3600, lambda: _run(rep["ticker"], rep, links))
    # Keep a thin result only briefly, so a later run can do better
    if len(result["promises"]) < MIN_PROMISES_FOR_SCORE:
        cache_set(key, result, 6 * 3600)
    return result
