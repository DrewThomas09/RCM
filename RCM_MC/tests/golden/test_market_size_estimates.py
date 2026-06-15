"""Golden test for NEW-21 contested market-size triangulation.

Hand-computed fixture, US revenue-cycle management (report section 18):
    sources:  Market Data Forecast 56.8, Precedence 58.5, Arizton 141.6,
              Grand View 172.2  (USD billions)

    low    = 56.8
    high   = 172.2
    median = (58.5 + 141.6) / 2 = 100.05
    mean   = (56.8 + 58.5 + 141.6 + 172.2) / 4 = 429.1 / 4 = 107.275
    spread = (172.2 - 56.8) / 56.8 = 115.4 / 56.8 = 2.0316901...

The low two sources are software-led scope and the high two are
services-inclusive scope, so the basis-mismatch flag fires; the 203 percent
spread is well above the 25 percent line, so the divergence flag fires; the
default house is the median and lies inside the range, so it reconciles.
"""
import unittest

from rcm_mc.cdd.market_size_estimates import market_size_estimates

ESTIMATES = [
    {"source": "Market Data Forecast", "value": 56.8, "vintage": "2024",
     "basis": "software-led scope"},
    {"source": "Precedence", "value": 58.5, "vintage": "2024",
     "basis": "software-led scope"},
    {"source": "Arizton", "value": 141.6, "vintage": "2024",
     "basis": "services-inclusive scope"},
    {"source": "Grand View", "value": 172.2, "vintage": "2024",
     "basis": "services-inclusive scope"},
]


class TestMarketSizeEstimates(unittest.TestCase):
    def _build(self, **kw):
        return market_size_estimates(
            "US revenue-cycle management", ESTIMATES,
            source="Golden", vintage="2024", **kw)

    def test_range_and_central_tendency(self):
        m = self._build().meta
        self.assertAlmostEqual(m["low"], 56.8, delta=1e-9)
        self.assertAlmostEqual(m["high"], 172.2, delta=1e-9)
        self.assertAlmostEqual(m["median"], 100.05, delta=1e-9)
        self.assertAlmostEqual(m["mean"], 107.275, delta=1e-9)

    def test_spread(self):
        m = self._build().meta
        self.assertAlmostEqual(m["spread"], 115.4 / 56.8, delta=1e-12)

    def test_default_house_is_median(self):
        m = self._build().meta
        self.assertTrue(m["house_is_default"])
        self.assertAlmostEqual(m["house"], 100.05, delta=1e-9)
        self.assertEqual(m["house_basis"], "median of source estimates")
        self.assertTrue(m["house_in_range"])

    def test_divergence_and_basis_flags(self):
        codes = self._build().flag_codes()
        self.assertIn("wide_estimate_divergence", codes)
        self.assertIn("basis_mismatch", codes)

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_explicit_house_within_range_reconciles(self):
        ex = self._build(house=100.0, house_source="services-inclusive house view")
        self.assertFalse(ex.meta["house_is_default"])
        self.assertTrue(ex.meta["house_in_range"])
        self.assertTrue(ex.reconciled)
        self.assertNotIn("house_outside_range", ex.flag_codes())

    def test_house_outside_range_flags_and_breaks_reconciliation(self):
        ex = self._build(house=200.0)
        self.assertIn("house_outside_range", ex.flag_codes())
        self.assertFalse(ex.meta["house_in_range"])
        self.assertFalse(ex.reconciled)

    def test_deviation_from_house(self):
        sources = {s["source"]: s for s in self._build().meta["sources"]}
        # Grand View 172.2 vs median house 100.05 -> +72.11 percent.
        self.assertAlmostEqual(
            sources["Grand View"]["deviation_from_house"],
            (172.2 - 100.05) / 100.05, delta=1e-9)

    def test_tight_estimates_no_divergence_flag(self):
        # Two close sources: spread under 25 percent, no divergence flag.
        ex = market_size_estimates(
            "Tight market",
            [{"source": "A", "value": 100.0}, {"source": "B", "value": 110.0}],
            source="Golden", vintage="2024")
        self.assertNotIn("wide_estimate_divergence", ex.flag_codes())
        self.assertAlmostEqual(ex.meta["spread"], 0.10, delta=1e-9)

    def test_single_source_flag(self):
        ex = market_size_estimates(
            "Single market", [{"source": "Only", "value": 42.0}],
            source="Golden", vintage="2024")
        self.assertIn("single_source", ex.flag_codes())
        self.assertEqual(ex.meta["spread"], 0.0)
        self.assertTrue(ex.reconciled)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            market_size_estimates("Empty", [], source="Golden", vintage="2024")

    def test_nonpositive_value_raises(self):
        with self.assertRaises(ValueError):
            market_size_estimates(
                "Bad", [{"source": "A", "value": 0.0}],
                source="Golden", vintage="2024")

    def test_partner_render_strips_assumptions(self):
        partner = self._build().render(internal_mode=False)
        self.assertNotIn("assumptions", partner)
        # Flags and the source footnote still reach the partner surface.
        self.assertTrue(partner["footnote"]["source"])
        self.assertIn("wide_estimate_divergence",
                      [f["code"] for f in partner["flags"]])


if __name__ == "__main__":
    unittest.main()
