"""Triggered alerts: unusual end-of-day moves and material filings, against thresholds the user sets."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from finn.config import PORTFOLIO
from finn.push.digest import all_filings
from finn.sources import prices


class AlertSettings(BaseModel):
    volume_multiple: float = Field(2.0, ge=1.0, le=20)
    price_move_pct: float = Field(4.0, ge=0.5, le=50)
    categories: List[str] = ["results", "M&A", "management_change", "fund_raise", "litigation", "capex"]
    filing_window_hours: int = Field(24, ge=1, le=168)


def evaluate(settings: AlertSettings) -> List[Dict[str, Any]]:
    alerts = []
    eod = prices.eod([p["ticker"] for p in PORTFOLIO])
    names = {p["ticker"]: p["name"] for p in PORTFOLIO}

    for ticker, data in eod.items():
        if not data:
            continue
        reasons = []
        if data["volume_multiple"] is not None and data["volume_multiple"] >= settings.volume_multiple:
            reasons.append(f"Volume {data['volume_multiple']}x its 20-day average")
        if abs(data["change_pct"]) >= settings.price_move_pct:
            reasons.append(f"Price {data['change_pct']:+.2f}% on the day")
        if reasons:
            alerts.append({
                "kind": "market",
                "ticker": ticker,
                "company": names[ticker],
                "headline": " · ".join(reasons),
                "at": data["date"],
                "eod": {k: v for k, v in data.items() if k != "closes"},
            })

    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.filing_window_hours)
    for filing in all_filings():
        if filing["category"] in settings.categories and datetime.fromisoformat(filing["published_at"]) >= cutoff:
            alerts.append({
                "kind": "filing",
                "ticker": filing["ticker"],
                "company": filing["company"],
                "headline": filing["title"],
                "at": filing["published_at"],
                "filing_id": filing["id"],
                "category": filing["category"],
            })

    # Market moves first (largest first), then filings newest first
    market = sorted((a for a in alerts if a["kind"] == "market"), key=lambda a: -abs(a["eod"]["change_pct"]))
    filings = sorted((a for a in alerts if a["kind"] == "filing"), key=lambda a: a["at"], reverse=True)
    return market + filings
