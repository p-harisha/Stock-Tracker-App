"""Pull fresh market data for every ticker and store it in the Quote table."""

from __future__ import annotations

from sqlmodel import Session, select

from .data import kite as kite_src
from .data import yahoo
from .models import Quote, Ticker, utcnow


def refresh_all(session: Session) -> dict:
    tickers = session.exec(select(Ticker)).all()
    kite = kite_src.client(session)
    live: dict[str, dict] = {}
    if kite and tickers:
        live = kite_src.quotes(kite, [f"{t.exchange}:{t.symbol}" for t in tickers])

    updated, failed = 0, []
    for t in tickers:
        q = session.get(Quote, t.id) or Quote(ticker_id=t.id)
        k = live.get(f"{t.exchange}:{t.symbol}")
        if k and k.get("price"):
            q.price, q.prev_close = k["price"], k["prev_close"]
            stats = kite_src.history(kite, k["instrument_token"]) if k.get("instrument_token") else None
            q.source = "kite"
        else:
            q.price, q.prev_close, stats = yahoo.price_and_history(t.exchange, t.symbol)
            q.source = "yahoo"
        if stats:
            for field in ("ch1m", "ch3m", "ch1y", "dma50", "dma200", "high52", "low52"):
                setattr(q, field, getattr(stats, field))

        f = yahoo.fundamentals(t.exchange, t.symbol)
        q.pe, q.market_cap, q.dividend_yield = f.pe, f.market_cap, f.dividend_yield
        if not t.name and f.name:
            t.name = f.name
        if not t.sector and f.sector:
            t.sector = f.sector
        q.updated_at = utcnow()

        if q.price is None:
            failed.append(f"{t.exchange}:{t.symbol}")
        else:
            updated += 1
        session.add(q)
        session.add(t)
    session.commit()
    return {"updated": updated, "failed": failed, "source": "kite" if kite else "yahoo"}
