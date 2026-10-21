import os

os.environ["SW_DATABASE_URL"] = "sqlite:///./test_api.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Quote  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c
    SQLModel.metadata.drop_all(engine)


def test_add_edit_delete_and_overview(client):
    r = client.post("/api/tickers", json={"exchange": "NSE", "symbol": "infy", "sector": "IT Services", "target": 1800, "quantity": 10, "avg_price": 1400, "tag": "holding"})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert r.json()["symbol"] == "INFY"

    assert client.post("/api/tickers", json={"exchange": "NSE", "symbol": "INFY"}).status_code == 409
    assert client.post("/api/tickers", json={"exchange": "NYSE", "symbol": "X"}).status_code == 422

    with Session(engine) as s:
        s.add(Quote(ticker_id=tid, price=1500, ch1m=3, ch3m=5, pe=22))
        s.commit()

    ov = client.get("/api/overview").json()
    row = ov["tickers"][0]
    assert row["pnl"] == 1000
    assert row["analysis"]["signal"] in {"buy", "hold", "sell"}
    assert ov["sectors"][0]["sector"] == "IT Services"

    assert client.patch(f"/api/tickers/{tid}", json={"stop_loss": 1550}).status_code == 200
    assert client.get("/api/overview").json()["tickers"][0]["analysis"]["signal"] == "sell"

    assert client.post(f"/api/tickers/{tid}/alerts", params={"kind": "price_above", "value": 1700}).status_code == 201
    assert client.delete(f"/api/tickers/{tid}").status_code == 204
    assert client.get("/api/overview").json()["tickers"] == []


def test_kite_status_without_keys(client):
    assert client.get("/api/kite/status").json() == {"configured": False, "logged_in": False}
