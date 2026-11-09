"""The research view for any NSE company, built from its reported financials."""
from typing import Any, Dict, List, Optional

from finn.sources import prices, screener
from finn.sources.screener import latest


def _series(table: Dict[str, Any], labels: List[str], drop_ttm: bool = True, limit: int = 8) -> Dict[str, Any]:
    periods = table["periods"]
    keep = [i for i, p in enumerate(periods) if not (drop_ttm and p == "TTM")][-limit:]
    out = {"periods": [periods[i] for i in keep]}
    for label in labels:
        values = table["rows"].get(label)
        out[label] = [values[i] if values and i < len(values) else None for i in keep]
    return out


def _ratio(numerator: Optional[float], denominator: Optional[float], digits: int = 2) -> Optional[float]:
    if numerator is None or not denominator:
        return None
    return round(numerator / denominator, digits)


def report(query: str) -> Dict[str, Any]:
    data = screener.company(query)
    pl, bs, cf, eff, q = data["profit_loss"], data["balance_sheet"], data["cash_flow"], data["efficiency"], data["quarters"]
    revenue_label = "Sales" if "Sales" in pl["rows"] else "Revenue"
    ebitda_label = "Operating Profit" if "Operating Profit" in pl["rows"] else "Financing Profit"
    margin_label = "OPM %" if "OPM %" in pl["rows"] else "Financing Margin %"

    equity = None
    if latest(bs, "Equity Capital") is not None and latest(bs, "Reserves") is not None:
        equity = latest(bs, "Equity Capital") + latest(bs, "Reserves")
    borrowings = latest(bs, "Borrowings", "Borrowing")

    # Cash quality over the last three reported years
    years = [i for i, p in enumerate(cf["periods"])][-3:]
    cfo = cf["rows"].get("Cash from Operating Activity") or []
    profit_by_year = dict(zip(pl["periods"], pl["rows"].get("Net Profit") or []))
    cfo_3y = sum(cfo[i] for i in years if i < len(cfo) and cfo[i] is not None) if cfo else None
    pat_3y_values = [profit_by_year.get(cf["periods"][i]) for i in years]
    pat_3y = sum(v for v in pat_3y_values if v is not None) if any(v is not None for v in pat_3y_values) else None

    eod = prices.eod([data["ticker"]]).get(data["ticker"])
    ratios = data["ratios"]
    return {
        "ticker": data["ticker"],
        "name": data["name"],
        "about": data["about"],
        "source_url": data["url"],
        "consolidated": data["consolidated"],
        "is_bank": revenue_label == "Revenue",
        "price": {k: v for k, v in eod.items()} if eod else None,
        "snapshot": {
            "market_cap_cr": ratios.get("market cap"),
            "pe": ratios.get("stock p/e"),
            "roce_pct": ratios.get("roce"),
            "roe_pct": ratios.get("roe"),
            "revenue_ttm_cr": latest(pl, revenue_label),
            "ebitda_margin_pct": latest(pl, margin_label),
            "pat_ttm_cr": latest(pl, "Net Profit"),
            "debt_to_equity": _ratio(borrowings, equity),
            "sales_growth": data["sales_growth"],
            "profit_growth": data["profit_growth"],
        },
        "trajectory": _series(pl, [revenue_label, margin_label, "Net Profit"], limit=8),
        "quarters": _series(q, [revenue_label, margin_label, "Net Profit"], drop_ttm=False, limit=8),
        "labels": {"revenue": revenue_label, "margin": margin_label, "ebitda": ebitda_label},
        "balance_sheet": {
            "period": bs["periods"][-1] if bs["periods"] else None,
            "borrowings_cr": borrowings,
            "equity_cr": equity,
            "debt_to_equity": _ratio(borrowings, equity),
            "working_capital_days": latest(eff, "Working Capital Days"),
            "cash_conversion_cycle_days": latest(eff, "Cash Conversion Cycle"),
            "history": _series(bs, ["Borrowings", "Borrowing", "Reserves"], drop_ttm=False, limit=6),
        },
        "cash_quality": {
            "cfo_3y_cr": cfo_3y,
            "pat_3y_cr": pat_3y,
            "cfo_to_pat_3y": _ratio(cfo_3y, pat_3y),
            "free_cash_flow_cr": latest(cf, "Free Cash Flow"),
            "cfo_to_ebitda_pct": latest(cf, "CFO/EBITDA"),
            "history": _series(cf, ["Cash from Operating Activity", "Free Cash Flow"], drop_ttm=False, limit=6),
            "profit_history": [profit_by_year.get(p) for p in cf["periods"][-6:]],
        },
        "documents": data["documents"],
    }
