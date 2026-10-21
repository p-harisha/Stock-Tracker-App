from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from .config import settings
from .data import kite as kite_src
from .db import get_session, init_db
from .models import AlertTrigger, Quote, Ticker, TickerCreate, TickerUpdate
from .overview import build_overview
from .refresh import refresh_all

EXCHANGES = {"NSE", "BSE"}
TAGS = {"holding", "watching"}
HORIZONS = {None, "short", "long"}
ALERT_KINDS = {"price_above", "price_below", "pct_move", "signal_change", "near_52w_high", "near_52w_low"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sector Watchlist", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate(data: dict) -> None:
    if "exchange" in data and data["exchange"] not in EXCHANGES:
        raise HTTPException(422, "Exchange must be NSE or BSE.")
    if "tag" in data and data["tag"] not in TAGS:
        raise HTTPException(422, "Tag must be holding or watching.")
    if "horizon_override" in data and data["horizon_override"] not in HORIZONS:
        raise HTTPException(422, "Horizon must be short, long or empty.")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/overview")
def overview(session: Session = Depends(get_session)) -> dict:
    return build_overview(session)


@app.post("/api/tickers", status_code=201)
def create_ticker(body: TickerCreate, session: Session = Depends(get_session)) -> Ticker:
    data = body.model_dump()
    data["exchange"] = data["exchange"].upper()
    data["symbol"] = data["symbol"].strip().upper()
    _validate(data)
    exists = session.exec(
        select(Ticker).where(Ticker.exchange == data["exchange"], Ticker.symbol == data["symbol"])
    ).first()
    if exists:
        raise HTTPException(409, f"{data['exchange']}:{data['symbol']} is already on your list.")
    ticker = Ticker(**data)
    session.add(ticker)
    session.commit()
    session.refresh(ticker)
    return ticker


@app.patch("/api/tickers/{ticker_id}")
def update_ticker(ticker_id: int, body: TickerUpdate, session: Session = Depends(get_session)) -> Ticker:
    ticker = session.get(Ticker, ticker_id)
    if not ticker:
        raise HTTPException(404, "Ticker not found.")
    data = body.model_dump(exclude_unset=True)
    _validate(data)
    for k, v in data.items():
        setattr(ticker, k, v)
    session.add(ticker)
    session.commit()
    session.refresh(ticker)
    return ticker


@app.delete("/api/tickers/{ticker_id}", status_code=204)
def delete_ticker(ticker_id: int, session: Session = Depends(get_session)) -> None:
    ticker = session.get(Ticker, ticker_id)
    if not ticker:
        raise HTTPException(404, "Ticker not found.")
    for a in session.exec(select(AlertTrigger).where(AlertTrigger.ticker_id == ticker_id)).all():
        session.delete(a)
    if q := session.get(Quote, ticker_id):
        session.delete(q)
    session.delete(ticker)
    session.commit()


@app.post("/api/refresh")
def refresh(session: Session = Depends(get_session)) -> dict:
    return refresh_all(session)


# ---- Kite ----


@app.get("/api/kite/status")
def kite_status(session: Session = Depends(get_session)) -> dict:
    return {"configured": kite_src.configured(), "logged_in": kite_src.client(session) is not None}


@app.get("/api/kite/login")
def kite_login() -> RedirectResponse:
    if not kite_src.configured():
        raise HTTPException(400, "Add SW_KITE_API_KEY and SW_KITE_API_SECRET to backend/.env first.")
    return RedirectResponse(kite_src.login_url())


@app.get("/api/kite/callback")
def kite_callback(request_token: str = "", status: str = "", session: Session = Depends(get_session)) -> RedirectResponse:
    """Set this URL as the redirect URL in your Kite developer app."""
    if status != "success" or not request_token:
        return RedirectResponse(f"{settings.frontend_url}/?kite=failed")
    kite_src.complete_login(session, request_token)
    return RedirectResponse(f"{settings.frontend_url}/?kite=connected")


@app.post("/api/kite/import-holdings")
def import_holdings(session: Session = Depends(get_session)) -> dict:
    kite = kite_src.client(session)
    if not kite:
        raise HTTPException(401, "Log in to Kite first.")
    added = updated = 0
    for h in kite_src.holdings(kite):
        t = session.exec(
            select(Ticker).where(Ticker.exchange == h["exchange"], Ticker.symbol == h["symbol"])
        ).first()
        if t:
            t.quantity, t.avg_price, t.tag = h["quantity"], h["avg_price"], "holding"
            updated += 1
        else:
            t = Ticker(exchange=h["exchange"], symbol=h["symbol"], quantity=h["quantity"], avg_price=h["avg_price"], tag="holding")
            added += 1
        session.add(t)
    session.commit()
    return {"added": added, "updated": updated}


# ---- Alert triggers (stored now, sent in a later phase) ----


@app.get("/api/tickers/{ticker_id}/alerts")
def list_alerts(ticker_id: int, session: Session = Depends(get_session)) -> list[AlertTrigger]:
    return list(session.exec(select(AlertTrigger).where(AlertTrigger.ticker_id == ticker_id)).all())


@app.post("/api/tickers/{ticker_id}/alerts", status_code=201)
def add_alert(ticker_id: int, kind: str, value: float | None = None, session: Session = Depends(get_session)) -> AlertTrigger:
    if not session.get(Ticker, ticker_id):
        raise HTTPException(404, "Ticker not found.")
    if kind not in ALERT_KINDS:
        raise HTTPException(422, f"Alert kind must be one of: {', '.join(sorted(ALERT_KINDS))}.")
    alert = AlertTrigger(ticker_id=ticker_id, kind=kind, value=value)
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


@app.delete("/api/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: int, session: Session = Depends(get_session)) -> None:
    alert = session.get(AlertTrigger, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found.")
    session.delete(alert)
    session.commit()
