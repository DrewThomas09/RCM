"""Golden test for NEW-02 price-volume-mix bridge.

Hand-computed 3-product two-period fixture:

    FY24: A 100@10=1000, B 200@5=1000, C 50@20=1000  -> R1=3000, Q1=350
    FY25: A 120@11=1320, B 180@5=900,  C 60@22=1320  -> R2=3540, Q2=360
    total change = 540

    price  = sum dp_i * qa_i
           = (1)*(110) + (0)*(190) + (2)*(55) = 110 + 0 + 110 = 220
    quantity (volume+mix) = 540 - 220 = 320
      volume = dQ * sum pa_i*s_avg_i = 10 * 9.178571... = 91.785714...
      mix    = Qavg * sum pa_i*ds_i  = 355 * 0.642857... = 228.214286...
      volume + mix = 320

Invariants: volume+price+mix == total (1e-6); reversal negates each component.
"""
import unittest

from rcm_mc.cdd.pvm_bridge import pvm_bridge

ROWS = [
    {"period": "FY24", "line": "A", "volume": 100, "price": 10.0},
    {"period": "FY24", "line": "B", "volume": 200, "price": 5.0},
    {"period": "FY24", "line": "C", "volume": 50, "price": 20.0},
    {"period": "FY25", "line": "A", "volume": 120, "price": 11.0},
    {"period": "FY25", "line": "B", "volume": 180, "price": 5.0},
    {"period": "FY25", "line": "C", "volume": 60, "price": 22.0},
]
TOL = 1e-6


class TestPvmBridge(unittest.TestCase):
    def _build(self, p1="FY24", p2="FY25"):
        return pvm_bridge(ROWS, period1=p1, period2=p2, source="Golden", vintage="2026")

    def test_hand_components(self):
        m = self._build().meta
        self.assertAlmostEqual(m["total_change"], 540.0, delta=TOL)
        self.assertAlmostEqual(m["price"], 220.0, delta=TOL,
                               msg=f"price expected 220 got {m['price']}")
        self.assertAlmostEqual(m["volume"], 91.78571428571429, delta=1e-5,
                               msg=f"volume expected 91.7857 got {m['volume']}")
        self.assertAlmostEqual(m["mix"], 228.21428571428572, delta=1e-5,
                               msg=f"mix expected 228.2143 got {m['mix']}")
        self.assertAlmostEqual(m["new_lost"], 0.0, delta=TOL)

    def test_additive(self):
        m = self._build().meta
        recomposed = m["volume"] + m["price"] + m["mix"] + m["new_lost"]
        gap = recomposed - m["total_change"]
        self.assertLessEqual(abs(gap), TOL,
                             msg=f"additivity gap {gap}: {recomposed} vs {m['total_change']}")
        self.assertTrue(self._build().reconciled)

    def test_reversal_consistent(self):
        fwd = self._build("FY24", "FY25").meta
        rev = self._build("FY25", "FY24").meta
        for k in ("volume", "price", "mix", "total_change"):
            self.assertAlmostEqual(rev[k], -fwd[k], delta=TOL,
                                   msg=f"reversal of {k}: {rev[k]} != -{fwd[k]}")

    def test_waterfall_ordered_by_magnitude(self):
        ex = self._build()
        pts = ex.render()["series"][0]["points"]
        deltas = [p for p in pts if p["kind"] == "delta"]
        mags = [abs(p["value"]) for p in deltas]
        self.assertEqual(mags, sorted(mags, reverse=True),
                         msg="waterfall deltas must be ordered by magnitude")
        # Largest driver is mix (228.2), then price (220), then volume (91.8).
        self.assertEqual([d["label"] for d in deltas], ["Mix", "Price", "Volume"])

    def test_color_convention(self):
        pts = self._build().render()["series"][0]["points"]
        for p in pts:
            if p["kind"] == "delta":
                self.assertEqual(p["color"], "green" if p["value"] >= 0 else "red")
            else:
                self.assertEqual(p["color"], "blue")

    def test_new_and_lost_line_bucket(self):
        rows = [
            {"period": "P1", "line": "A", "volume": 10, "price": 10.0},  # continuing
            {"period": "P1", "line": "L", "volume": 5, "price": 4.0},    # lost (-20)
            {"period": "P2", "line": "A", "volume": 10, "price": 10.0},
            {"period": "P2", "line": "N", "volume": 3, "price": 7.0},    # new (+21)
        ]
        ex = pvm_bridge(rows, period1="P1", period2="P2", source="Golden", vintage="2026")
        m = ex.meta
        self.assertAlmostEqual(m["new_lost"], 21.0 - 20.0, delta=TOL)
        self.assertAlmostEqual(m["total_change"], m["r2"] - m["r1"], delta=TOL)
        recomposed = m["volume"] + m["price"] + m["mix"] + m["new_lost"]
        self.assertAlmostEqual(recomposed, m["total_change"], delta=TOL)

    def test_footnote_populated(self):
        fn = self._build().render()["footnote"]
        self.assertTrue(fn["source"] and fn["vintage"] and fn["assumptions"])

    def test_degenerate_single_line_no_change(self):
        rows = [
            {"period": "P1", "line": "A", "volume": 10, "price": 5.0},
            {"period": "P2", "line": "A", "volume": 10, "price": 5.0},
        ]
        m = pvm_bridge(rows, period1="P1", period2="P2", source="G", vintage="2026").meta
        self.assertAlmostEqual(m["total_change"], 0.0, delta=TOL)
        self.assertAlmostEqual(m["volume"] + m["price"] + m["mix"], 0.0, delta=TOL)


if __name__ == "__main__":
    unittest.main()
