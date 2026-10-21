# Sector Watchlist

Track NSE and BSE tickers, group them by sector, and get Buy / Hold / Sell signals per ticker and Overweight / Neutral / Underweight calls per sector.

- **Backend:** FastAPI + SQLite (`backend/`). Prices come from Zerodha Kite when you're logged in, otherwise from Yahoo Finance via yfinance. Fundamentals (P/E, market cap, dividend yield) always come from yfinance, which is unofficial and can break.
- **Frontend:** React + TypeScript + Vite (`frontend/`).

## Run it

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # add your Kite API key and secret (optional)
uvicorn app.main:app --reload --port 8000

# Frontend, in a second terminal
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

### Kite setup (optional)

1. Create an app at https://developers.kite.trade (market data needs a paid Kite Connect subscription).
2. Set its redirect URL to `http://localhost:8000/api/kite/callback`.
3. Put the API key and secret in `backend/.env`.
4. In the app, click **Log in to Kite** once a day (Kite tokens expire every morning), then **Import Kite holdings**.

Without Kite, add tickers by hand; **Refresh prices** then uses Yahoo Finance.

## How scoring works

Each ticker gets a 0-100 score from four parts (`backend/app/scoring.py`):

| Part | Measures |
| --- | --- |
| Upside | Your target vs current price |
| Momentum | 1M and 3M return, price vs 50- and 200-day averages |
| Valuation | P/E vs the sector's average P/E |
| Risk | Room above your stop-loss, else position in the 52-week range |

The app suggests a horizon per ticker: strong momentum on a rich valuation is **short-term** (momentum weighs most); otherwise **long-term** (valuation and upside weigh most). You can override it per ticker.

- 65+ is Buy, 40-64 Hold, below 40 Sell. At or below the stop-loss is always Sell.
- Sector score = average of its tickers' scores, weighted by money invested when every ticker has a quantity. 60+ is Overweight, below 45 Underweight.

These are mechanical screens, not investment advice.

## API

| Method | Path | Does |
| --- | --- | --- |
| GET | `/api/overview` | Tickers with quotes, scores, P/L, and sector summaries |
| POST / PATCH / DELETE | `/api/tickers[/{id}]` | Manage the watchlist |
| POST | `/api/refresh` | Pull fresh prices and fundamentals |
| GET | `/api/kite/status`, `/api/kite/login`, `/api/kite/callback` | Kite login flow |
| POST | `/api/kite/import-holdings` | Add or update holdings from Kite |
| GET / POST / DELETE | `/api/tickers/{id}/alerts`, `/api/alerts/{id}` | Alert triggers (stored now, sent in a later phase) |

## Tests

```bash
cd backend && pytest
```
