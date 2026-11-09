"""Enrichments for pushed filings: a results first cut and a management bio."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from finn import llm
from finn.cache import cached
from finn.config import REASONING_MODELS

logger = logging.getLogger(__name__)

# Screener row labels: banks report Revenue and Financing Profit instead of Sales and Operating Profit
METRICS = [
    ("revenue", "Revenue", ("Sales", "Revenue")),
    ("ebitda", "EBITDA", ("Operating Profit", "Financing Profit")),
    ("pbt", "PBT", ("Profit before tax",)),
    ("pat", "PAT", ("Net Profit",)),
]


def _change(now: Optional[float], before: Optional[float]) -> Optional[float]:
    if now is None or before is None or before == 0:
        return None
    return round((now - before) / abs(before) * 100, 1)


def _quarter_end(label: str) -> Optional[datetime]:
    try:
        start = datetime.strptime(label, "%b %Y")
    except ValueError:
        return None
    # Last day of that month
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def results_scorecard(company: Dict[str, Any], published_at: str) -> Optional[Dict[str, Any]]:
    """Revenue, EBITDA, PBT and PAT for the latest quarter, QoQ and YoY, if it matches this filing."""
    quarters = company["quarters"]
    periods = quarters["periods"]
    if len(periods) < 2:
        return None
    latest_end = _quarter_end(periods[-1])
    filed = datetime.fromisoformat(published_at).replace(tzinfo=None)
    # Results are filed within about 60 days of quarter end; otherwise the table hasn't caught up yet
    if not latest_end or not (latest_end <= filed <= latest_end + timedelta(days=75)):
        return None

    rows = []
    for key, label, row_names in METRICS:
        values = next((quarters["rows"][n] for n in row_names if n in quarters["rows"]), None)
        if not values:
            continue
        now = values[-1]
        rows.append({
            "key": key,
            "label": label,
            "value_cr": now,
            "qoq_pct": _change(now, values[-2] if len(values) >= 2 else None),
            "yoy_pct": _change(now, values[-5] if len(values) >= 5 else None),
        })
    margin_row = quarters["rows"].get("OPM %") or quarters["rows"].get("Financing Margin %")
    return {
        "quarter": periods[-1],
        "metrics": rows,
        "margin_pct": margin_row[-1] if margin_row else None,
        "margin_yoy_bps": round((margin_row[-1] - margin_row[-5]) * 100) if margin_row and len(margin_row) >= 5 and None not in (margin_row[-1], margin_row[-5]) else None,
        "consolidated": company["consolidated"],
        "source": company["url"],
    }


class Person(BaseModel):
    name: str
    role: str
    change: str  # joining, leaving, retiring or redesignated
    known: bool
    background: List[str]


class PeopleBrief(BaseModel):
    people: List[Person]
    why_it_matters: str


def brief_key(company: str, title: str, summary: str) -> str:
    return f"bio:v3:{company}:{title}:{summary}"


def management_brief(company: str, title: str, summary: str, quick: bool = False) -> Dict[str, Any]:
    """Who is joining or leaving, with a background found by searching the web, and its sources."""
    system = (
        "You brief an equity investor on a management change at an Indian listed company. "
        "List each person named as joining, leaving, retiring or changing role. For each, give up to 3 short "
        "background points: prior roles, employers, education. Set known=false and leave background empty "
        "if you cannot clearly identify this person: never guess or invent. why_it_matters is one sentence "
        "on what the change could mean, without speculation presented as fact."
    )
    prompt = f"Company: {company}\nFiling: {title}\nSummary: {summary}"

    def ask():
        # Groq first: fast, with web search, and it leaves Gemini's small daily limit for the transcript analysis
        if llm.groq_available():
            try:
                brief, sources = llm.groq_search_json(system + " Search the web first.", prompt, PeopleBrief, 45 if quick else 90)
                return {**brief.model_dump(), "sources": sources, "searched": True}
            except llm.LLMUnavailable:
                pass
        try:
            brief, sources = llm.generate_grounded_json(REASONING_MODELS, system + " Search the web first.", prompt, PeopleBrief, quick)
            return {**brief.model_dump(), "sources": sources, "searched": True}
        except llm.LLMUnavailable:
            # Search grounding has its own, smaller free quota; fall back to the model's knowledge, labelled as such
            brief = llm.generate_json(REASONING_MODELS, system, prompt, PeopleBrief, quick)
            return {**brief.model_dump(), "sources": [], "searched": False}

    return cached(brief_key(company, title, summary), 30 * 24 * 3600, ask)
