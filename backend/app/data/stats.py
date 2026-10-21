"""Turn a daily close history into the numbers the scoring needs."""

from __future__ import annotations

from dataclasses import dataclass

# Trading days, approximately.
DAYS_1M = 21
DAYS_3M = 63
DAYS_1Y = 250


@dataclass
class HistoryStats:
    ch1m: float | None = None
    ch3m: float | None = None
    ch1y: float | None = None
    dma50: float | None = None
    dma200: float | None = None
    high52: float | None = None
    low52: float | None = None


def _pct_change(closes: list[float], days: int) -> float | None:
    if len(closes) <= days or not closes[-days - 1]:
        return None
    return round((closes[-1] / closes[-days - 1] - 1) * 100, 2)


def _sma(closes: list[float], days: int) -> float | None:
    if len(closes) < days:
        return None
    return round(sum(closes[-days:]) / days, 2)


def stats_from_closes(closes: list[float], highs: list[float] | None = None, lows: list[float] | None = None) -> HistoryStats:
    """`closes` is oldest first and ends at the latest session."""
    if not closes:
        return HistoryStats()
    year_highs = (highs or closes)[-DAYS_1Y:]
    year_lows = (lows or closes)[-DAYS_1Y:]
    return HistoryStats(
        ch1m=_pct_change(closes, DAYS_1M),
        ch3m=_pct_change(closes, DAYS_3M),
        ch1y=_pct_change(closes, DAYS_1Y),
        dma50=_sma(closes, 50),
        dma200=_sma(closes, 200),
        high52=max(year_highs),
        low52=min(year_lows),
    )
