"""End-of-day prices and volume from Yahoo Finance."""
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from finn.cache import cached

logger = logging.getLogger(__name__)

PRICE_TTL = 3600
IST = timezone(timedelta(hours=5, minutes=30))


def _summarise(frame: pd.DataFrame) -> Optional[Dict]:
    frame = frame.dropna(subset=["Close", "Volume"])
    # During market hours Yahoo includes today's unfinished session; keep only completed days
    now_ist = datetime.now(IST)
    if len(frame) and frame.index[-1].date() == now_ist.date() and now_ist.time() < time(16, 0):
        frame = frame.iloc[:-1]
    if len(frame) < 3:
        return None
    latest, previous = frame.iloc[-1], frame.iloc[-2]
    # Average volume over up to 20 sessions before the latest one
    history = frame.iloc[-21:-1]
    avg_volume = float(history["Volume"].mean()) if len(history) else 0.0
    close, prev_close = float(latest["Close"]), float(previous["Close"])
    return {
        "date": latest.name.strftime("%Y-%m-%d"),
        "close": round(close, 2),
        "change_pct": round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0,
        "volume": int(latest["Volume"]),
        "avg_volume_20d": int(avg_volume),
        "volume_multiple": round(float(latest["Volume"]) / avg_volume, 2) if avg_volume else None,
        "closes": [round(float(c), 2) for c in frame["Close"].iloc[-30:]],
    }


def eod(tickers: List[str]) -> Dict[str, Optional[Dict]]:
    """Latest end-of-day figures per NSE ticker; None where Yahoo has no data."""
    def fetch():
        symbols = [f"{t}.NS" for t in tickers]
        data = yf.download(symbols, period="2mo", interval="1d", group_by="ticker", progress=False, threads=True, auto_adjust=False)
        result = {}
        for ticker, symbol in zip(tickers, symbols):
            try:
                frame = data[symbol] if isinstance(data.columns, pd.MultiIndex) else data
                result[ticker] = _summarise(frame)
            except Exception as e:
                logger.info(f"No price data for {symbol}: {e}")
                result[ticker] = None
        return result

    return cached(f"eod:{','.join(sorted(tickers))}", PRICE_TTL, fetch) or {}
