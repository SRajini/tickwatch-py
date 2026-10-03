"""Alert engine: pure Python, no I/O, easy to unit test."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import count


def sma(values: list[float], n: int, offset: int = 0):
    """Simple moving average of the n values ending `offset` items before the end."""
    end = len(values) - offset
    if n <= 0 or end < n:
        return None
    return sum(values[end - n:end]) / n


@dataclass
class Rule:
    """A user price alert. Field names match what the browser expects."""
    id: int
    s: str   # symbol
    d: str   # "above" or "below"
    v: float  # price level


@dataclass
class Alert:
    symbol: str
    kind: str  # "up", "dn" or "in" (used for colour in the UI)
    message: str
    rule_id: int | None = None


class AlertEngine:
    def __init__(self, short: int = 10, long: int = 30, move_pct: float = 1.5, move_window: int = 30):
        self.short, self.long = short, long
        self.move_pct, self.move_window = move_pct, move_window
        self.rules: list[Rule] = []
        self._next_id = count(1)
        self._ticks: dict[str, int] = defaultdict(int)
        self._last_fired: dict[tuple[str, str], int] = {}
        self.hi: dict[str, float] = {}
        self.lo: dict[str, float] = {}

    # --- user rules -------------------------------------------------
    def add_rule(self, symbol: str, direction: str, price: float) -> Rule:
        if direction not in ("above", "below") or price <= 0:
            raise ValueError("direction must be 'above' or 'below' and price must be positive")
        rule = Rule(next(self._next_id), symbol.upper(), direction, float(price))
        self.rules.append(rule)
        return rule

    def remove_rule(self, rule_id: int) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) < before

    # --- automatic alerts -------------------------------------------
    def seed(self, symbol: str, history: list[float]) -> None:
        """Set the session high/low from existing history without raising alerts."""
        if history:
            self.hi[symbol], self.lo[symbol] = max(history), min(history)

    def _cooled(self, symbol: str, kind: str, cooldown: int) -> bool:
        """True (and records the firing) if `kind` has not fired for `symbol` in `cooldown` ticks."""
        now = self._ticks[symbol]
        if now - self._last_fired.get((symbol, kind), -10**9) < cooldown:
            return False
        self._last_fired[(symbol, kind)] = now
        return True

    def on_price(self, symbol: str, history: list[float]) -> list[Alert]:
        """Call after appending the newest price to `history`. Returns any alerts raised."""
        self._ticks[symbol] += 1
        price = history[-1]
        out: list[Alert] = []

        if symbol not in self.hi:
            self.hi[symbol] = self.lo[symbol] = price
        else:
            if price > self.hi[symbol] and self._cooled(symbol, "hi", 60):
                out.append(Alert(symbol, "up", f"New session high at {price:.2f}"))
            if price < self.lo[symbol] and self._cooled(symbol, "lo", 60):
                out.append(Alert(symbol, "dn", f"New session low at {price:.2f}"))
            self.hi[symbol] = max(self.hi[symbol], price)
            self.lo[symbol] = min(self.lo[symbol], price)

        s_now, l_now = sma(history, self.short), sma(history, self.long)
        s_prev, l_prev = sma(history, self.short, 1), sma(history, self.long, 1)
        if None not in (s_now, l_now, s_prev, l_prev):
            if s_prev <= l_prev and s_now > l_now and self._cooled(symbol, "x", 25):
                out.append(Alert(symbol, "up", f"Bullish crossover: {self.short}-tick average moved above the {self.long}-tick average at {price:.2f}"))
            elif s_prev >= l_prev and s_now < l_now and self._cooled(symbol, "x", 25):
                out.append(Alert(symbol, "dn", f"Bearish crossover: {self.short}-tick average fell below the {self.long}-tick average at {price:.2f}"))

        if len(history) > self.move_window:
            move = (price / history[-1 - self.move_window] - 1) * 100
            if move >= self.move_pct and self._cooled(symbol, "m", 40):
                out.append(Alert(symbol, "up", f"Surge: +{move:.2f}% over the last {self.move_window} ticks"))
            elif move <= -self.move_pct and self._cooled(symbol, "m", 40):
                out.append(Alert(symbol, "dn", f"Drop: {move:.2f}% over the last {self.move_window} ticks"))

        for rule in [r for r in self.rules if r.s == symbol]:
            if (rule.d == "above" and price >= rule.v) or (rule.d == "below" and price <= rule.v):
                verb = "rose above" if rule.d == "above" else "fell below"
                out.append(Alert(symbol, "up" if rule.d == "above" else "dn",
                                 f"Your alert fired: {symbol} {verb} {rule.v:.2f} (now {price:.2f})", rule.id))
                self.rules.remove(rule)  # one-shot
        return out
