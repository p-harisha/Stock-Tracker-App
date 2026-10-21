"""Combine tickers, quotes and scores into the dashboard payload."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from sqlmodel import Session, select

from .models import Quote, Ticker
from .scoring import SectorMember, TickerInput, score_ticker, sector_call


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def build_overview(session: Session) -> dict:
    tickers = session.exec(select(Ticker)).all()
    quotes = {q.ticker_id: q for q in session.exec(select(Quote)).all()}

    by_sector: dict[str, list[Ticker]] = defaultdict(list)
    for t in tickers:
        by_sector[t.sector or "Unassigned"].append(t)

    sector_pe = {
        s: _avg([quotes[t.id].pe for t in ts if t.id in quotes and quotes[t.id].pe and quotes[t.id].pe > 0])
        for s, ts in by_sector.items()
    }

    rows = []
    for t in tickers:
        q = quotes.get(t.id)
        sector = t.sector or "Unassigned"
        result = score_ticker(
            TickerInput(
                price=q.price if q else None,
                target=t.target,
                stop_loss=t.stop_loss,
                ch1m=q.ch1m if q else None,
                ch3m=q.ch3m if q else None,
                dma50=q.dma50 if q else None,
                dma200=q.dma200 if q else None,
                high52=q.high52 if q else None,
                low52=q.low52 if q else None,
                pe=q.pe if q else None,
                sector_pe=sector_pe.get(sector),
                horizon_override=t.horizon_override,  # type: ignore[arg-type]
            )
        )
        invested = t.quantity * t.avg_price if t.quantity and t.avg_price else None
        value = t.quantity * q.price if t.quantity and q and q.price else None
        rows.append(
            {
                "ticker": t.model_dump(),
                "quote": q.model_dump() if q else None,
                "analysis": asdict(result),
                "invested": invested,
                "value": value,
                "pnl": (value - invested) if value is not None and invested is not None else None,
            }
        )

    sectors = []
    for s, ts in by_sector.items():
        members = [r for r in rows if (r["ticker"]["sector"] or "Unassigned") == s]
        avg_score, call = sector_call(
            [SectorMember(r["analysis"]["score"], r["invested"]) for r in members]
        )
        invested = sum(r["invested"] or 0 for r in members)
        value = sum(r["value"] or 0 for r in members)
        sectors.append(
            {
                "sector": s,
                "count": len(members),
                "score": avg_score,
                "call": call,
                "avg_pe": sector_pe.get(s),
                "avg_ch1m": _avg([r["quote"]["ch1m"] for r in members if r["quote"] and r["quote"]["ch1m"] is not None]),
                "invested": invested or None,
                "value": value or None,
                "pnl": (value - invested) if invested else None,
                "signals": {
                    k: sum(1 for r in members if r["analysis"]["signal"] == k) for k in ("buy", "hold", "sell")
                },
            }
        )
    sectors.sort(key=lambda x: (x["score"] is None, -(x["score"] or 0)))
    return {"tickers": rows, "sectors": sectors}
