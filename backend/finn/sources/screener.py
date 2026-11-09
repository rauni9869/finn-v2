"""Company data from screener.in: financial tables, ratios, document links and recent BSE announcements."""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

from finn.cache import cached

logger = logging.getLogger(__name__)

BASE = "https://www.screener.in"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
PAGE_TTL = 6 * 3600


class CompanyNotFound(Exception):
    pass


def _number(text: str) -> Optional[float]:
    try:
        return float(text.replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def search(query: str) -> List[Dict[str, str]]:
    """Company suggestions for a ticker or name."""
    def fetch():
        resp = requests.get(f"{BASE}/api/company/search/", params={"q": query}, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        results = []
        for item in resp.json()[:8]:
            match = re.search(r"/company/([^/]+)/", item.get("url", ""))
            if match:
                results.append({"ticker": unquote(match.group(1)), "name": item.get("name", "")})
        return results
    return cached(f"search:{query.lower()}", 24 * 3600, fetch) or []


def _fetch_page(query: str) -> requests.Response:
    """Tries the query as a ticker (consolidated, then standalone), then as a name via search."""
    slug = quote(query, safe="")
    for url in (f"{BASE}/company/{slug}/consolidated/", f"{BASE}/company/{slug}/"):
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 404:
            break
    if resp.status_code == 404:
        matches = search(query)
        if not matches:
            raise CompanyNotFound(query)
        resp = requests.get(f"{BASE}/company/{quote(matches[0]['ticker'], safe='')}/consolidated/", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp


def _table(soup, section_id: str) -> Dict[str, Any]:
    """A financial table as {'periods': [...], 'rows': {label: [values...]}}."""
    section = soup.select_one(f"#{section_id}")
    if not section or not section.select_one("table"):
        return {"periods": [], "rows": {}}
    periods = [th.get_text(strip=True) for th in section.select("thead th")][1:]
    rows = {}
    for tr in section.select("tbody tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        label_el = cells[0]
        # Screener appends a help tooltip to some labels
        for extra in label_el.select("span.tooltip, .tooltip"):
            extra.decompose()
        label = label_el.get_text(" ", strip=True).rstrip(" +").strip()
        if label and label not in rows:
            rows[label] = [_number(td.get_text()) for td in cells[1:]]
    return {"periods": periods, "rows": rows}


def _growth(soup, title: str) -> Dict[str, Optional[float]]:
    for table in soup.select("table.ranges-table"):
        if title in table.get_text():
            out = {}
            for match in re.finditer(r"(10 Years|5 Years|3 Years|TTM|1 Year|Last Year):\s*(-?[\d.,]+)\s*%", table.get_text(" ", strip=True)):
                out[match.group(1)] = _number(match.group(2))
            return out
    return {}


def _announcements(soup) -> List[Dict[str, Any]]:
    items = []
    for box in soup.select("#documents div.documents"):
        heading = box.find("h3")
        if not heading or "Announcements" not in heading.get_text():
            continue
        for li in box.select("ul.list-links li"):
            link = li.find("a", href=True)
            when = li.find("time")
            if not link or not when or not when.get("datetime"):
                continue
            detail = link.find("div")
            summary = ""
            if detail:
                # Text is "<date> - <summary>", and the summary may be missing
                parts = detail.get_text(" ", strip=True).split(" - ", 1)
                summary = parts[1].strip() if len(parts) == 2 else ""
                detail.extract()
            subject = " ".join(link.get_text(" ", strip=True).split())
            # Without a summary the date can end up in the link text
            subject = re.sub(r"\s+\d{1,2} [A-Z][a-z]{2}( \d{4})?$", "", subject)
            items.append({
                "subject": subject,
                "summary": summary,
                "url": link["href"],
                "published_at": datetime.fromisoformat(when["datetime"]).isoformat(),
            })
    return items


def _documents(soup) -> Dict[str, List[Dict[str, str]]]:
    annual_reports, transcripts, presentations = [], [], []
    for box in soup.select("#documents div.documents"):
        heading = (box.find("h3").get_text(strip=True) if box.find("h3") else "")
        if heading == "Annual reports":
            for a in box.select("ul.list-links a[href]"):
                title = " ".join(a.get_text(" ", strip=True).split()).replace(" AI Summary", "")
                annual_reports.append({"title": title, "url": a["href"]})
        elif heading == "Concalls":
            for li in box.select("ul.list-links li"):
                period_el = li.find("div")
                period = " ".join(period_el.get_text(" ", strip=True).split()) if period_el else ""
                for a in li.find_all("a", href=True):
                    kind = a.get_text(strip=True)
                    if kind == "Transcript":
                        transcripts.append({"title": f"{period} transcript", "period": period, "url": a["href"]})
                    elif kind == "PPT":
                        presentations.append({"title": f"{period} presentation", "period": period, "url": a["href"]})
    return {"annual_reports": annual_reports[:5], "transcripts": transcripts[:8], "presentations": presentations[:4]}


def _parse(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    ticker_match = re.search(r"/company/([^/]+)/", url)
    ratios = {}
    for li in soup.select("#top-ratios li"):
        name, value = li.select_one(".name"), li.select_one(".value .number") or li.select_one(".value")
        if name and value:
            ratios[name.get_text(strip=True).lower()] = _number(value.get_text())
    about = soup.select_one(".company-profile .about") or soup.select_one(".about")
    company_id = soup.select_one("[data-company-id]")
    name = soup.find("h1")
    return {
        "ticker": unquote(ticker_match.group(1)) if ticker_match else "",
        "name": name.get_text(strip=True) if name else "",
        "company_id": company_id["data-company-id"] if company_id else None,
        "consolidated": "/consolidated/" in url,
        "url": url,
        "about": re.sub(r"\s*\[\d+\]", "", about.get_text(" ", strip=True)) if about else "",
        "ratios": ratios,
        "quarters": _table(soup, "quarters"),
        "profit_loss": _table(soup, "profit-loss"),
        "balance_sheet": _table(soup, "balance-sheet"),
        "cash_flow": _table(soup, "cash-flow"),
        "efficiency": _table(soup, "ratios"),
        "sales_growth": _growth(soup, "Compounded Sales Growth"),
        "profit_growth": _growth(soup, "Compounded Profit Growth"),
        "announcements": _announcements(soup),
        "documents": _documents(soup),
    }


def company(query: str) -> Dict[str, Any]:
    """All screener data for a ticker or company name. Raises CompanyNotFound."""
    key = query.upper().replace(".NS", "").replace(".BO", "").strip()

    def fetch():
        resp = _fetch_page(key)
        data = _parse(resp.text, resp.url)
        # Companies without consolidated accounts have a consolidated page with row names but no periods
        if data["consolidated"] and not data["profit_loss"]["periods"]:
            standalone = requests.get(resp.url.replace("consolidated/", ""), headers=HEADERS, timeout=15)
            if standalone.ok:
                data = _parse(standalone.text, standalone.url)
        return data

    return cached(f"company:{key}", PAGE_TTL, fetch)


def latest(table: Dict[str, Any], *labels: str) -> Optional[float]:
    """Latest non-empty value of the first matching row."""
    for label in labels:
        values = table["rows"].get(label)
        if values:
            for value in reversed(values):
                if value is not None:
                    return value
    return None
