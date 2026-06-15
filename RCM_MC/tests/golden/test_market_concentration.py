"""Golden test for NEW-25 market concentration overlay.

Seven verticals. Dialysis (77.1 percent, two firms) is the most concentrated;
drug distribution (95) and PBMs (80) also clear the 70 percent bar, so three
rows are highly concentrated. GPO and EHR shares are industry estimates.
Hospital systems sit at the open end (about 5 percent, top two).
"""
import unittest

from rcm_mc.cdd.market_concentration import ConcentrationRow, market_concentration


class TestMarketConcentration(unittest.TestCase):
    def test_counts(self):
        m = market_concentration().meta
        self.assertEqual(m["n_rows"], 7)
        # Distribution 95, PBM 80, dialysis 77.1, and GPO 75 all clear 70 percent.
        self.assertEqual(m["n_highly_concentrated"], 4)
        self.assertEqual(m["n_estimates"], 2)

    def test_top_share(self):
        ex = market_concentration()
        self.assertEqual(ex.meta["top_share_vertical"], "Drug wholesale distribution")
        self.assertAlmostEqual(ex.series[0].points[0]["value"], 95.0, delta=1e-9)

    def test_sorted_descending(self):
        vals = [p["value"] for p in market_concentration().series[0].points]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_flags(self):
        codes = market_concentration().flag_codes()
        self.assertIn("highly_concentrated", codes)
        self.assertIn("estimates_present", codes)

    def test_reconciles(self):
        self.assertTrue(market_concentration().reconciled)

    def test_share_bounds_validated(self):
        with self.assertRaises(ValueError):
            ConcentrationRow("Bad", 120.0, 1, "h", "s", "v").validate()
        with self.assertRaises(ValueError):
            ConcentrationRow("Bad", 50.0, 0, "h", "s", "v").validate()

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            market_concentration([])


if __name__ == "__main__":
    unittest.main()
