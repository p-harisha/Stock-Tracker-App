"""Yahoo Finance via yfinance: fundamentals always, prices when Kite is not connected.

yfinance is unofficial and can break when Yahoo changes its site, so every call
here fails soft and returns what it could get.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import yfinance as yf

from .stats import HistoryStats, stats_from_closes

log = logging.getLogger(__name__)

SUFFIX = {"NSE": ".NS", "BSE": ".BO"}


def yahoo_symbol(exchange: str, symbol: str) -> str:
    return symbol.upper() + SUFFIX.get(exchange.upper(), ".NS")


@dataclass
class Fundamentals:
    name: str | None = None
    sector: str | None = None
    pe: float | None = None
    market_cap: float | None = None
    dividend_yield: float | None = None  # percent


def fundamentals(exchange: str, symbol: str) -> Fundamentals:
    try:
        info = yf.Ticker(yahoo_symbol(exchange, symbol)).info or {}
    except Exception:  # network errors, Yahoo format changes
        log.warning("yfinance info failed for %s:%s", exchange, symbol, exc_info=True)
        return Fundamentals()
    dy = info.get("dividendYield")
    return Fundamentals(
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        pe=info.get("trailingPE"),
        market_cap=info.get("marketCap"),
        # yfinance has returned this both as a fraction and as a percent across versions.
        dividend_yield=(dy * 100 if dy is not None and dy < 1 else dy),
    )


def price_and_history(exchange: str, symbol: str) -> tuple[float | None, float | None, HistoryStats]:
    """Returns (last price, previous close, stats from one year of daily history)."""
    try:
        df = yf.Ticker(yahoo_symbol(exchange, symbol)).history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        log.warning("yfinance history failed for %s:%s", exchange, symbol, exc_info=True)
        return None, None, HistoryStats()
    if df is None or df.empty:
        return None, None, HistoryStats()
    closes = [float(c) for c in df["Close"].tolist()]
    stats = stats_from_closes(closes, [float(h) for h in df["High"].tolist()], [float(low) for low in df["Low"].tolist()])
    prev = closes[-2] if len(closes) > 1 else None
    return closes[-1], prev, stats
