import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from alerts import AlertEngine, sma


def run(engine, symbol, prices):
    out, hist = [], []
    for p in prices:
        hist.append(p)
        out += engine.on_price(symbol, hist)
    return out


class AlertTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 2), 3.5)
        self.assertEqual(sma([1, 2, 3, 4], 2, offset=1), 2.5)
        self.assertIsNone(sma([1], 2))

    def test_bullish_crossover(self):
        prices = [100] * 30 + [90] * 30 + [130] * 10
        msgs = [a.message for a in run(AlertEngine(), "X", prices)]
        self.assertTrue(any("Bullish" in m for m in msgs))

    def test_bearish_crossover(self):
        prices = [100] * 30 + [110] * 30 + [70] * 10
        msgs = [a.message for a in run(AlertEngine(), "X", prices)]
        self.assertTrue(any("Bearish" in m for m in msgs))

    def test_surge_and_cooldown(self):
        prices = [100] * 30 + [102, 103, 104]
        surges = [a for a in run(AlertEngine(), "X", prices) if "Surge" in a.message]
        self.assertEqual(len(surges), 1)  # cooldown suppresses repeats

    def test_price_rule_fires_once_then_is_removed(self):
        e = AlertEngine()
        rule = e.add_rule("x", "above", 105)
        fired = [a for a in run(e, "X", [100, 104, 106, 107]) if a.rule_id == rule.id]
        self.assertEqual(len(fired), 1)
        self.assertEqual(e.rules, [])

    def test_invalid_rule(self):
        with self.assertRaises(ValueError):
            AlertEngine().add_rule("X", "sideways", 10)


if __name__ == "__main__":
    unittest.main()
