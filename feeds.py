"""Price feeds. Each feed has fetch() -> {symbol: price} and an `opens` dict."""
from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor


class SimulatedFeed:
    """Random-walk prices with a little momentum, so crossovers and surges happen."""

    def __init__(self, symbols: list[str]):
        self.state = {}
        self.opens: dict[str, float] = {}
        for s in symbols:
            h = sum(ord(c) * (i + 1) for i, c in enumerate(s)) % 997
            self.state[s] = {"p": 20 + h % 380, "drift": 0.0, "vol": 0.0008 + (h % 10) * 0.0001}

    def fetch(self) -> dict[str, float]:
        out = {}
        for s, x in self.state.items():
            x["drift"] = x["drift"] * 0.985 + random.gauss(0, 1) * x["vol"] * 0.35
            x["p"] = max(1.0, x["p"] * (1 + x["drift"] + random.gauss(0, 1) * x["vol"]))
            out[s] = round(x["p"], 2)
        return out


class FinnhubFeed:
    """Real quotes from https://finnhub.io (free API key). Uses only the standard library."""

    URL = "https://finnhub.io/api/v1/quote?symbol={sym}&token={key}"

    def __init__(self, symbols: list[str], api_key: str):
        self.symbols, self.key = symbols, api_key
        self.opens: dict[str, float] = {}

    def _one(self, sym: str):
        url = self.URL.format(sym=urllib.parse.quote(sym), key=self.key)
        try:
            with urllib.request.urlopen(url, timeout=6) as resp:
                q = json.load(resp)
            if sym not in self.opens and q.get("o", 0) > 0:
                self.opens[sym] = q["o"]
            return sym, q.get("c", 0)
        except Exception as exc:  # network errors, rate limits, bad JSON
            print(f"{sym}: fetch failed ({exc})")
            return sym, 0

    def fetch(self) -> dict[str, float]:
        with ThreadPoolExecutor(max_workers=min(8, len(self.symbols))) as pool:
            return {s: p for s, p in pool.map(self._one, self.symbols) if p and p > 0}
