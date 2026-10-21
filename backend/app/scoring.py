"""Ticker scores, signals and sector calls.

Pure functions with no I/O, so the rules can be tested and tuned in one place.
Every component score runs 0-100, where 50 is neutral.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Horizon = Literal["short", "long"]
Signal = Literal["buy", "hold", "sell"]
SectorCall = Literal["overweight", "neutral", "underweight"]

# Weights per horizon. Short-term leans on momentum, long-term on valuation and upside.
WEIGHTS: dict[Horizon, dict[str, float]] = {
    "short": {"upside": 0.20, "momentum": 0.50, "valuation": 0.10, "risk": 0.20},
    "long": {"upside": 0.35, "momentum": 0.15, "valuation": 0.35, "risk": 0.15},
}

BUY_AT = 65
HOLD_AT = 40
OVERWEIGHT_AT = 60
UNDERWEIGHT_BELOW = 45


@dataclass
class TickerInput:
    price: float | None
    target: float | None = None
    stop_loss: float | None = None
    ch1m: float | None = None  # percent
    ch3m: float | None = None  # percent
    dma50: float | None = None
    dma200: float | None = None
    high52: float | None = None
    low52: float | None = None
    pe: float | None = None
    sector_pe: float | None = None
    horizon_override: Horizon | None = None


@dataclass
class TickerScore:
    score: float | None
    signal: Signal | None
    horizon: Horizon
    horizon_suggested: Horizon
    components: dict[str, float | None]
    reasons: list[str] = field(default_factory=list)


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def upside_score(t: TickerInput) -> float | None:
    if not t.price or not t.target:
        return None
    # +25% upside scores 100, -25% scores 0.
    return _clamp(50 + (t.target / t.price - 1) * 200)


def momentum_score(t: TickerInput) -> float | None:
    parts: list[float | None] = []
    if t.ch1m is not None:
        parts.append(_clamp(50 + t.ch1m * 5))  # +10% in a month = 100
    if t.ch3m is not None:
        parts.append(_clamp(50 + t.ch3m * 2.5))  # +20% in three months = 100
    if t.price and t.dma50 and t.dma200:
        parts.append((t.price > t.dma50) * 50.0 + (t.price > t.dma200) * 50.0)
    return _mean(parts)


def valuation_score(t: TickerInput) -> float | None:
    if not t.pe or t.pe <= 0 or not t.sector_pe or t.sector_pe <= 0:
        return None
    # P/E half the sector's scores 100, double the sector's scores 0.
    return _clamp(50 + (1 - t.pe / t.sector_pe) * 100)


def risk_score(t: TickerInput) -> float | None:
    """Higher is safer: room above the stop-loss, else position in the 52-week range."""
    if t.price and t.stop_loss:
        return _clamp((t.price / t.stop_loss - 1) * 500)  # 20% above stop = 100
    if t.price and t.high52 and t.low52 and t.high52 > t.low52:
        return _clamp(100 * (t.price - t.low52) / (t.high52 - t.low52))
    return None


def suggest_horizon(momentum: float | None, valuation: float | None) -> Horizon:
    """Strong trend on a rich valuation is a trade; cheap with a weak trend is a hold."""
    if momentum is not None and momentum >= 60 and (valuation is None or valuation < 45):
        return "short"
    return "long"


REASON_TEXT = {
    "upside": ("upside to target", "little upside to target"),
    "momentum": ("strong momentum", "weak momentum"),
    "valuation": ("cheap vs sector", "expensive vs sector"),
    "risk": ("well above stop-loss", "close to stop-loss"),
}


def score_ticker(t: TickerInput) -> TickerScore:
    comps = {
        "upside": upside_score(t),
        "momentum": momentum_score(t),
        "valuation": valuation_score(t),
        "risk": risk_score(t),
    }
    suggested = suggest_horizon(comps["momentum"], comps["valuation"])
    horizon = t.horizon_override or suggested
    weights = WEIGHTS[horizon]

    used = {k: v for k, v in comps.items() if v is not None}
    if not used:
        return TickerScore(None, None, horizon, suggested, comps)
    total_w = sum(weights[k] for k in used)
    score = sum(weights[k] * v for k, v in used.items()) / total_w

    if t.price and t.stop_loss and t.price <= t.stop_loss:
        signal: Signal = "sell"
    elif score >= BUY_AT:
        signal = "buy"
    elif score >= HOLD_AT:
        signal = "hold"
    else:
        signal = "sell"

    # The two components that pulled the score furthest from neutral.
    pulls = sorted(used.items(), key=lambda kv: abs(weights[kv[0]] * (kv[1] - 50)), reverse=True)
    reasons = [REASON_TEXT[k][0 if v >= 50 else 1] for k, v in pulls[:2]]
    if signal == "sell" and t.price and t.stop_loss and t.price <= t.stop_loss:
        reasons = ["at or below stop-loss"]

    return TickerScore(round(score, 1), signal, horizon, suggested, comps, reasons)


@dataclass
class SectorMember:
    score: float | None
    weight: float | None = None  # money invested; None means equal weight


def sector_call(members: list[SectorMember]) -> tuple[float | None, SectorCall | None]:
    scored = [m for m in members if m.score is not None]
    if not scored:
        return None, None
    weighted = [m for m in scored if m.weight]
    if weighted and len(weighted) == len(scored):
        total = sum(m.weight for m in weighted)  # type: ignore[misc]
        avg = sum(m.score * m.weight for m in weighted) / total  # type: ignore[operator]
    else:
        avg = sum(m.score for m in scored) / len(scored)  # type: ignore[misc]
    if avg >= OVERWEIGHT_AT:
        call: SectorCall = "overweight"
    elif avg < UNDERWEIGHT_BELOW:
        call = "underweight"
    else:
        call = "neutral"
    return round(avg, 1), call
