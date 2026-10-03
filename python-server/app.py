"""Tickwatch server (standard library only). Run: python app.py"""
from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
from collections import deque
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from alerts import AlertEngine
from feeds import FinnhubFeed, SimulatedFeed

ROOT = Path(__file__).parent
MAX_HISTORY = 420


def load_env(path: Path) -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() and not k.strip().startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())


class State:
    """Shared market state. All access goes through a lock because HTTP handlers run in threads."""

    def __init__(self, feed, symbols, mode, poll_s):
        self.feed, self.symbols, self.mode, self.poll_s = feed, symbols, mode, poll_s
        self.history = {s: deque(maxlen=MAX_HISTORY) for s in symbols}
        self.engine = AlertEngine()
        self.lock = threading.Lock()
        self.clients: list[queue.Queue] = []

    def prime(self, prices=None, n=1):
        """Fill history before serving. Simulated feeds get n points, live feeds get the first quote."""
        for _ in range(n):
            for s, p in (prices or self.feed.fetch()).items():
                self.history[s].append(p)
        for s in list(self.symbols):
            if not self.history[s]:
                print(f"No data for {s}, dropping it")
                self.symbols.remove(s)
            else:
                self.engine.seed(s, list(self.history[s]))
        if self.mode == "simulated":
            self.feed.opens = {s: self.history[s][0] for s in self.symbols}

    def snapshot(self):
        return {
            "symbols": self.symbols,
            "history": {s: list(self.history[s]) for s in self.symbols},
            "open": {s: self.feed.opens.get(s, self.history[s][0]) for s in self.symbols},
            "rules": [asdict(r) for r in self.engine.rules],
            "mode": self.mode,
            "pollMs": int(self.poll_s * 1000),
        }

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            snap = self.snapshot()
            self.clients.append(q)
        return q, snap

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def _broadcast(self, event, data):
        for q in self.clients:
            q.put((event, data))

    def ingest(self, prices):
        with self.lock:
            fresh = {}
            alerts = []
            for s, p in prices.items():
                if s in self.history:
                    self.history[s].append(p)
                    fresh[s] = p
                    alerts += self.engine.on_price(s, list(self.history[s]))
            if fresh:
                self._broadcast("tick", fresh)
            for a in alerts:
                self._broadcast("alert", asdict(a))

    def poll_forever(self):
        while True:
            time.sleep(self.poll_s)
            try:
                self.ingest(self.feed.fetch())
            except Exception as exc:
                print("poll error:", exc)


def make_handler(state: State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _json(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/stream":
                return self._stream()
            if self.path == "/health":
                return self._json(200, {"ok": True, "mode": state.mode})
            if self.path in ("/", "/index.html"):
                page = (ROOT / "public" / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/rules":
                return self._json(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                symbol = str(body["symbol"]).upper()
                if symbol not in state.symbols:
                    raise ValueError("unknown symbol")
                with state.lock:
                    rule = state.engine.add_rule(symbol, body["direction"], float(body["price"]))
                self._json(201, asdict(rule))
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})

        def do_DELETE(self):
            prefix = "/api/rules/"
            if not self.path.startswith(prefix) or not self.path[len(prefix):].isdigit():
                return self._json(404, {"error": "not found"})
            with state.lock:
                ok = state.engine.remove_rule(int(self.path[len(prefix):]))
            self._json(200 if ok else 404, {"deleted": ok})

        def _send_event(self, event, data):
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
            self.wfile.flush()

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            q, snap = state.subscribe()
            try:
                self._send_event("init", snap)
                while True:
                    try:
                        event, data = q.get(timeout=15)
                        self._send_event(event, data)
                    except queue.Empty:
                        self.wfile.write(b":hb\n\n")
                        self.wfile.flush()
            except OSError:  # browser closed the tab
                pass
            finally:
                state.unsubscribe(q)

    return Handler


def main():
    load_env(ROOT / ".env")
    ap = argparse.ArgumentParser(description="Tickwatch live market monitor")
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", 3000)))
    ap.add_argument("--poll", type=float, default=float(os.getenv("POLL_S", 10)),
                    help="seconds between live quote refreshes (simulated mode ticks every second)")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL,META,AMD").split(",") if s.strip()]
    key = os.getenv("FINNHUB_API_KEY", "")
    if key:
        state = State(FinnhubFeed(symbols, key), symbols, "live", max(args.poll, 2))
        state.prime()
    else:
        state = State(SimulatedFeed(symbols), symbols, "simulated", 1.0)
        state.prime(n=200)
    if not state.symbols:
        raise SystemExit("No valid symbols. Check SYMBOLS and FINNHUB_API_KEY.")

    threading.Thread(target=state.poll_forever, daemon=True).start()
    server = ThreadingHTTPServer(("", args.port), make_handler(state))
    server.daemon_threads = True
    print(f"Tickwatch running at http://localhost:{args.port} ({state.mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
