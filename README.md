<<<<<<< HEAD
# Tickwatch: complete project

A real-time stock monitoring dashboard with live charts, moving averages and trend alerts.
Four ways to run it, all sharing the same dashboard design.

| Folder | What it is | Needs | Best for |
|---|---|---|---|
| `python-server/` | Python backend (`app.py`, `alerts.py`, `feeds.py`, `tests/`) | Python 3.9+ | Learning, VS Code, hosting on Render/Docker |
| `vercel/` | Static page + Python function (`api/quotes.py`) | Vercel account | Free public website |
| `node-server/` | Same idea as python-server, written in Node | Node 18+ | Alternative backend |
| `demo/` | Single HTML file, simulated prices | A browser | Quick look, no setup |

## Quick start (recommended: Python)
    cd python-server
    python app.py                          # open http://localhost:3000
    python -m unittest discover tests -v   # run the tests

Runs on simulated prices. For real quotes, get a free key at https://finnhub.io, copy `.env.example` to `.env`,
and set `FINNHUB_API_KEY`.

## Open in VS Code
File > Open Folder > `tickwatch-complete`. Open a terminal, `cd python-server`, then `python app.py`.

## Deploy
- Vercel: see `vercel/README.md`
- Render or Docker: see the "Put it online" section in `python-server/README.md`

Quotes may be delayed. This is not financial advice.
=======
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
>>>>>>> 375e8ed1076848cdfa374123e7a59e412d2ed61c
