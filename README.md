# Tickwatch (Python)

Real-time stock monitoring dashboard: watchlist, live chart with moving averages, and trend alerts.
Backend is pure Python (standard library only, Python 3.9+). No `pip install` needed.

## Run
    python app.py            # then open http://localhost:3000
    python -m unittest discover tests -v

Runs on simulated prices by default. For real quotes get a free key at https://finnhub.io,
then `cp .env.example .env`, set `FINNHUB_API_KEY`, and restart.

## Layout
| File | Job |
|---|---|
| `feeds.py` | `SimulatedFeed` and `FinnhubFeed`, both with `fetch() -> {symbol: price}` |
| `alerts.py` | `AlertEngine`: crossovers, 30-tick moves, session highs/lows, user price rules (pure logic) |
| `app.py` | Polling thread, shared state with a lock, HTTP + Server-Sent Events |
| `public/index.html` | Dashboard UI (canvas charts, no libraries) |
| `tests/` | Unit tests for the alert engine |

## API
- `GET /stream` : SSE events `init`, `tick`, `alert`
- `POST /api/rules` : `{"symbol":"AAPL","direction":"above","price":200}`
- `DELETE /api/rules/<id>`

## Ideas to extend
Persist alerts to SQLite, send Telegram/email on alert, add RSI to `alerts.py`, swap in `yfinance` as a third feed.
Quotes may be delayed; this is not financial advice.
