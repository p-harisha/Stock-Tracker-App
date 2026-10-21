from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TickerBase(SQLModel):
    exchange: str = Field(default="NSE", description="NSE or BSE")
    symbol: str = Field(index=True, description="Trading symbol, e.g. INFY")
    name: str = ""
    sector: str = ""
    tag: str = Field(default="watching", description="holding or watching")
    quantity: Optional[float] = None
    avg_price: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    horizon_override: Optional[str] = Field(default=None, description="short, long or null")


class Ticker(TickerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class TickerCreate(TickerBase):
    pass


class TickerUpdate(SQLModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    tag: Optional[str] = None
    quantity: Optional[float] = None
    avg_price: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    horizon_override: Optional[str] = None


class Quote(SQLModel, table=True):
    """Latest market snapshot for one ticker, replaced on every refresh."""

    ticker_id: int = Field(foreign_key="ticker.id", primary_key=True)
    price: Optional[float] = None
    prev_close: Optional[float] = None
    ch1m: Optional[float] = None
    ch3m: Optional[float] = None
    ch1y: Optional[float] = None
    dma50: Optional[float] = None
    dma200: Optional[float] = None
    high52: Optional[float] = None
    low52: Optional[float] = None
    pe: Optional[float] = None
    market_cap: Optional[float] = None
    dividend_yield: Optional[float] = None
    source: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class AlertTrigger(SQLModel, table=True):
    """Stored now so alerts can be added later without a schema change.

    kind: price_above, price_below, pct_move, signal_change, near_52w_high, near_52w_low
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_id: int = Field(foreign_key="ticker.id", index=True)
    kind: str
    value: Optional[float] = None
    active: bool = True
    last_fired_at: Optional[datetime] = None


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
