"""Zerodha Kite Connect: login, holdings, live quotes and daily history.

Kite access tokens expire every morning, so the user logs in once a day from the app.
The token is kept in the settings table.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from kiteconnect import KiteConnect
from sqlmodel import Session

from ..config import settings
from ..models import Setting
from .stats import HistoryStats, stats_from_closes

log = logging.getLogger(__name__)

TOKEN_KEY = "kite_access_token"
TOKEN_DATE_KEY = "kite_token_date"


def configured() -> bool:
    return bool(settings.kite_api_key and settings.kite_api_secret)


def login_url() -> str:
    return KiteConnect(api_key=settings.kite_api_key).login_url()


def complete_login(session: Session, request_token: str) -> None:
    kite = KiteConnect(api_key=settings.kite_api_key)
    data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
    session.merge(Setting(key=TOKEN_KEY, value=data["access_token"]))
    session.merge(Setting(key=TOKEN_DATE_KEY, value=date.today().isoformat()))
    session.commit()


def client(session: Session) -> KiteConnect | None:
    """A logged-in client, or None when Kite is not set up or today's login is missing."""
    if not configured():
        return None
    token = session.get(Setting, TOKEN_KEY)
    token_date = session.get(Setting, TOKEN_DATE_KEY)
    if not token or not token_date or token_date.value != date.today().isoformat():
        return None
    kite = KiteConnect(api_key=settings.kite_api_key)
    kite.set_access_token(token.value)
    return kite


def holdings(kite: KiteConnect) -> list[dict]:
    """Each item: exchange, symbol, quantity, avg_price."""
    out = []
    for h in kite.holdings():
        qty = (h.get("quantity") or 0) + (h.get("t1_quantity") or 0)
        if qty <= 0:
            continue
        out.append(
            {
                "exchange": h["exchange"],
                "symbol": h["tradingsymbol"],
                "quantity": qty,
                "avg_price": h.get("average_price"),
            }
        )
    return out


def quotes(kite: KiteConnect, keys: list[str]) -> dict[str, dict]:
    """keys look like 'NSE:INFY'. Returns last price, previous close and instrument token per key."""
    out: dict[str, dict] = {}
    for i in range(0, len(keys), 200):  # stay well under Kite's per-request instrument limit
        for key, q in kite.quote(keys[i : i + 200]).items():
            out[key] = {
                "price": q.get("last_price"),
                "prev_close": (q.get("ohlc") or {}).get("close"),
                "instrument_token": q.get("instrument_token"),
            }
    return out


def history(kite: KiteConnect, instrument_token: int) -> HistoryStats:
    to = date.today()
    try:
        candles = kite.historical_data(instrument_token, to - timedelta(days=380), to, "day")
    except Exception:
        log.warning("Kite history failed for %s", instrument_token, exc_info=True)
        return HistoryStats()
    return stats_from_closes(
        [c["close"] for c in candles], [c["high"] for c in candles], [c["low"] for c in candles]
    )
