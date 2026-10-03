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
