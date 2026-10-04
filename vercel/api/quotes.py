"""Vercel serverless function: GET /api/quotes -> latest prices from Finnhub.

Without FINNHUB_API_KEY it returns {"mode": "simulated"} and the browser generates prices itself.
The API key stays on the server. Only symbols from the SYMBOLS env var can be requested.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler

DEFAULT_SYMBOLS = "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,AMD"


def get_symbols():
    raw = os.environ.get("SYMBOLS", DEFAULT_SYMBOLS)
    return [s.strip().upper() for s in raw.split(",") if s.strip()][:12]


def fetch_one(symbol, key):
    url = "https://finnhub.io/api/v1/quote?symbol=%s&token=%s" % (urllib.parse.quote(symbol), key)
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            q = json.load(resp)
        return symbol, q.get("c") or 0, q.get("o") or 0
    except Exception:
        return symbol, 0, 0


_status = {"t": 0.0, "open": None}


def market_open(key):
    """True/False from Finnhub's US market status, None if unknown. Cached for 60 s per warm instance."""
    now = time.time()
    if now - _status["t"] < 60:
        return _status["open"]
    try:
        url = "https://finnhub.io/api/v1/stock/market-status?exchange=US&token=%s" % key
        with urllib.request.urlopen(url, timeout=4) as resp:
            _status["open"] = bool(json.load(resp).get("isOpen"))
    except Exception:
        _status["open"] = None
    _status["t"] = now
    return _status["open"]


class handler(BaseHTTPRequestHandler):
    def _send(self, code, body, cache):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        symbols = get_symbols()
        key = os.environ.get("FINNHUB_API_KEY", "")
        if not key:
            return self._send(200, {"mode": "simulated", "symbols": symbols, "pollMs": 1000},
                              "public, s-maxage=60")
        with ThreadPoolExecutor(max_workers=len(symbols)) as pool:
            rows = list(pool.map(lambda s: fetch_one(s, key), symbols))
        prices = {s: c for s, c, _ in rows if c > 0}
        opens = {s: o for s, c, o in rows if c > 0 and o > 0}
        if not prices:
            return self._send(502, {"error": "no quotes returned"}, "no-store")
        # s-maxage lets Vercel's edge cache share one Finnhub fetch between all visitors
        self._send(200, {"mode": "live", "symbols": symbols, "prices": prices, "opens": opens,
                         "ts": int(time.time()), "pollMs": 10000,
                         "marketOpen": market_open(key)},
                   "public, s-maxage=10, stale-while-revalidate=10")