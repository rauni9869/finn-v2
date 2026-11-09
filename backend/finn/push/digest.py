"""The push digest: live filings across the portfolio, classified, prioritised and enriched."""
import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from finn.config import PORTFOLIO
from finn.push import classify
from finn.cache import cache_get
from finn.push.enrich import brief_key, results_scorecard
from finn.sources import screener

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _clean_subject(subject: str) -> str:
    subject = re.sub(r"^Announcement under Regulation 30 \(LODR\)\s*-\s*", "", subject, flags=re.I)
    return subject.strip(" -") or "Filing"


def portfolio_companies() -> Dict[str, Optional[Dict[str, Any]]]:
    """Screener data for every portfolio company, fetched in parallel; None where it failed."""
    def load(ticker):
        try:
            return ticker, screener.company(ticker)
        except Exception as e:
            logger.warning(f"Could not load {ticker}: {e}")
            return ticker, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(pool.map(load, [p["ticker"] for p in PORTFOLIO]))


def all_filings() -> List[Dict[str, Any]]:
    """Every recent filing for the portfolio, classified, newest first."""
    companies = portfolio_companies()
    filings, unmatched = [], []
    for stock in PORTFOLIO:
        data = companies.get(stock["ticker"])
        if not data:
            continue
        for ann in data["announcements"]:
            rule = classify.classify_by_rules(ann["subject"], ann["summary"])
            filing = {
                "id": hashlib.sha1(ann["url"].encode()).hexdigest()[:12],
                "ticker": stock["ticker"],
                "company": data["name"] or stock["name"],
                "published_at": ann["published_at"],
                "title": _clean_subject(ann["subject"]),
                "summary": ann["summary"],
                "url": ann["url"],
                "category": rule[0] if rule else "unclassified",
                "priority": rule[1] if rule else "LOW",
                "classified_by": "rules" if rule else "model",
                "results": None,
            }
            if not rule:
                unmatched.append(filing)
            filings.append(filing)

    labels = classify.classify_with_model([(f["url"], f["title"], f["summary"]) for f in unmatched])
    for filing in unmatched:
        category = labels.get(filing["url"])
        if category:
            filing["category"] = category
            filing["priority"] = classify.DEFAULT_PRIORITY[category]
        else:
            filing["classified_by"] = "default"

    for filing in filings:
        # Prepared people briefs ship with the filing, so the card can show them straight away
        if filing["category"] == "management_change":
            filing["people"] = cache_get(brief_key(filing["company"], filing["title"], filing["summary"]))
        if filing["category"] == "results" and filing["priority"] == "HIGH":
            filing["results"] = results_scorecard(companies[filing["ticker"]], filing["published_at"])

    filings.sort(key=lambda f: f["published_at"], reverse=True)
    return filings


def digest(window_hours: int, ticker: Optional[str] = None) -> Dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    filings = [
        f for f in all_filings()
        if datetime.fromisoformat(f["published_at"]) >= cutoff and (not ticker or f["ticker"] == ticker.upper())
    ]
    filings.sort(key=lambda f: PRIORITY_ORDER[f["priority"]])  # stable, so newest first within each priority
    return {
        "window_hours": window_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {p: sum(1 for f in filings if f["priority"] == p) for p in PRIORITY_ORDER},
        "material": [f for f in filings if f["priority"] != "LOW"],
        "routine": [f for f in filings if f["priority"] == "LOW"],
    }
