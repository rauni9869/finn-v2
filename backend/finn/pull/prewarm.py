"""Runs the transcript analysis ahead of time, so holdings open instantly instead of after a minute or two."""
import logging
import threading
import time
from typing import Any, Dict, List

from finn import llm
from finn.config import AD_HOC, PORTFOLIO
from finn.pull import analysis
from finn.push import digest, enrich
from finn.sources import screener

logger = logging.getLogger(__name__)

SPACING_SECONDS = 20       # gap between companies, to stay inside the free per-minute limit
REFRESH_SECONDS = 6 * 3600  # check again for new transcripts
BACKOFF_SECONDS = 30 * 60   # wait after the AI service refuses, e.g. when the daily limit is used up

_status: Dict[str, Any] = {"running": False, "done": [], "skipped": [], "waiting": [], "failed": [], "total": 0, "current": None}
_lock = threading.Lock()


def status() -> Dict[str, Any]:
    with _lock:
        return {**_status, **{k: list(_status[k]) for k in ("done", "skipped", "waiting", "failed")}}


def _tickers() -> List[str]:
    seen, out = set(), []
    for ticker in [p["ticker"] for p in PORTFOLIO] + AD_HOC:
        if ticker not in seen:
            seen.add(ticker)
            out.append(ticker)
    return out


def _prepare_people_briefs() -> None:
    """People briefs first: there are only a few, and someone clicking one shouldn't have to wait."""
    for filing in digest.all_filings():
        if filing["category"] != "management_change" or filing.get("people"):
            continue
        try:
            enrich.management_brief(filing["company"], filing["title"], filing["summary"], quick=True)
            logger.info(f"Prepared people brief for {filing['ticker']}: {filing['title']}")
        except Exception as e:
            logger.warning(f"People brief failed for {filing['ticker']}: {e}")
        time.sleep(5)


def _run_pass() -> bool:
    """One pass over every company. Returns False if the AI service refused, so the caller backs off."""
    with _lock:
        _status.update(running=True, current="people briefs")
    try:
        _prepare_people_briefs()
    except Exception as e:
        logger.warning(f"People briefs skipped: {e}")
    tickers = _tickers()
    with _lock:
        _status.update(running=True, done=[], skipped=[], failed=[], waiting=[], total=len(tickers), current=None)
    # Once the AI quota is refused, keep going through the list without calling the AI:
    # saved companies still count as done, and the rest wait for the next pass
    quota_out = False
    try:
        for ticker in tickers:
            with _lock:
                _status["current"] = ticker
            try:
                if analysis.is_ready(ticker):
                    with _lock:
                        _status["done"].append(ticker)
                    continue
                if not analysis.has_transcripts(ticker):
                    with _lock:
                        _status["skipped"].append(ticker)
                    continue
            except screener.CompanyNotFound:
                with _lock:
                    _status["skipped"].append(ticker)
                continue
            if quota_out:
                with _lock:
                    _status["waiting"].append(ticker)
                continue
            started = time.time()
            try:
                analysis.analyse(ticker)
                with _lock:
                    _status["done"].append(ticker)
                logger.info(f"Pre-ran analysis for {ticker} in {time.time() - started:.0f}s")
            except analysis.AnalysisUnavailable as e:
                message = str(e)
                if "busy" in message or "limit" in message:
                    logger.warning(f"AI quota refused at {ticker}; the rest wait for the next pass: {message}")
                    quota_out = True
                    with _lock:
                        _status["waiting"].append(ticker)
                else:
                    with _lock:
                        _status["skipped"].append(ticker)
            except Exception as e:
                logger.warning(f"Pre-run failed for {ticker}: {e}")
                with _lock:
                    _status["failed"].append(ticker)
            time.sleep(SPACING_SECONDS)
        return not quota_out
    finally:
        with _lock:
            _status.update(running=False, current=None)


def _loop():
    # Let the server finish starting before the first pass
    time.sleep(10)
    while True:
        ok = _run_pass()
        time.sleep(REFRESH_SECONDS if ok else BACKOFF_SECONDS)


def start() -> None:
    if not llm.is_available():
        logger.info("Pre-run is off because AI is not configured.")
        return
    threading.Thread(target=_loop, name="finn-prewarm", daemon=True).start()
