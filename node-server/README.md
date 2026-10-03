# Tickwatch

Real-time stock monitoring dashboard: watchlist, live chart with 10/30-tick moving averages, and alerts.
No npm dependencies. Requires Node 18 or newer.

## Run
    node server.js
    # open http://localhost:3000

With no API key it runs on simulated prices. For real quotes:
1. Get a free key at https://finnhub.io
2. `cp .env.example .env` and set `FINNHUB_API_KEY` (and `SYMBOLS` if you like)
3. `node server.js`

## Notes
- One "tick" is one quote refresh (every `POLL_MS`, default 10 s). Free Finnhub allows 60 calls/min, one per symbol, so keep `symbols x 60000 / POLL_MS` under 60.
- When the market is closed, prices stay flat and few alerts fire.
- Alerts: 10/30 average crossovers, 1.5%+ moves over 30 ticks, new session highs/lows, plus your own price levels.
- History lives in server memory and resets on restart. Your price alerts live in the browser tab.
- Quotes may be delayed depending on your data plan. This is not financial advice.

## Files
- `server.js`: quote polling or simulator, Server-Sent Events stream, static file serving
- `public/index.html`: dashboard UI (charts drawn on canvas, no libraries)
