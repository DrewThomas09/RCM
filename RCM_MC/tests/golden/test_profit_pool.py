"""Golden test for NEW-18 profit-pool stacked column.

Hand-computed two-column EBITDA by segment:
    segment:   Payers  Providers  HST   Pharmacy   total
    2022:        60       254       49     220       583
    2027:        78       366       86     289       819

    total CAGR 2022->2027 = (819/583)^(1/5) - 1 = 0.07037...  (about 7 percent)
    HST CAGR   2022->2027 = (86/49)^(1/5)  - 1 = 0.11908...   (about 12 percent)

NHE framing: 583/4464 = 13.06 percent, 819/6215 = 13.18 percent.
"""
import unittest

from rcm_mc.cdd.profit_pool import profit_pool

COLUMNS = [
    {"year": 2022, "segments": {"Payers": 60, "Providers": 254, "HST": 49, "Pharmacy": 220}},
    {"year": 2027, "segments": {"Payers": 78, "Providers": 366, "HST": 86, "Pharmacy": 289}},
]


class TestProfitPool(unittest.TestCase):
    def _build(self):
        return profit_pool(COLUMNS, nhe_by_year={2022: 4464, 2027: 6215},
                           projected_from_year=2027, source="Golden", vintage="2024")

    def test_totals(self):
        m = self._build().meta
        self.assertEqual(m["totals"][2022], 583)
        self.assertEqual(m["totals"][2027], 819)

    def test_total_cagr(self):
        b = self._build().meta["brackets"][-1]
        self.assertEqual(b["from_year"], 2022)
        self.assertEqual(b["to_year"], 2027)
        self.assertAlmostEqual(b["total_cagr"], 0.07034324, delta=1e-7)

    def test_segment_cagr_hst(self):
        b = self._build().meta["brackets"][-1]
        self.assertAlmostEqual(b["segment_cagrs"]["HST"], 0.11907830, delta=1e-7)

    def test_nhe_framing(self):
        pts = {p["year"]: p["value"] for p in self._build().meta["nhe_points"]}
        self.assertAlmostEqual(pts[2022], 583 / 4464 * 100, delta=1e-9)
        self.assertAlmostEqual(pts[2027], 819 / 6215 * 100, delta=1e-9)

    def test_projection_ghosting_and_flag(self):
        ex = self._build()
        total_series = next(s for s in ex.series if s.name == "Total EBITDA")
        ghosted = {p["year"]: p["projected"] for p in total_series.points}
        self.assertFalse(ghosted[2022])
        self.assertTrue(ghosted[2027])
        self.assertIn("contains_projection", ex.flag_codes())

    def test_declining_pool_flag(self):
        cols = [
            {"year": 2022, "segments": {"Payers": 60, "HST": 49}},
            {"year": 2027, "segments": {"Payers": 40, "HST": 86}},
        ]
        ex = profit_pool(cols, source="Golden", vintage="2024")
        self.assertIn("declining_pool", ex.flag_codes())

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_requires_two_columns(self):
        with self.assertRaises(ValueError):
            profit_pool([COLUMNS[0]], source="Golden", vintage="2024")


if __name__ == "__main__":
    unittest.main()
