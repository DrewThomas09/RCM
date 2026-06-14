"""Golden test for NEW-19 marimekko profit-pool map.

Hand-computed EBITDA-share by EBITDA-share map (total industry EBITDA = 100):
    sector                          EBITDA  width   cumulative x
    Payers                            10    0.10    [0.00, 0.10]
    Delivery systems                  50    0.50    [0.10, 0.60]
    Service vendors                    5    0.05    [0.60, 0.65]
    Manufacturers and distributors    35    0.35    [0.65, 1.00]

    Payers heights: MA 6/10 = 0.6, Individual 4/10 = 0.4
    areas: MA 0.10*0.6 = 0.06, Individual 0.10*0.4 = 0.04; all areas sum to 1.0
"""
import unittest

from rcm_mc.cdd.marimekko import marimekko_profit_pool

SECTORS = [
    {"sector": "Payers", "subsegments": {"MA": 6, "Individual": 4}},
    {"sector": "Delivery systems", "subsegments": {"Acute": 30, "ASC": 20}},
    {"sector": "Service vendors", "subsegments": {"SW": 3, "Data": 2}},
    {"sector": "Manufacturers and distributors", "subsegments": {"Pharma": 25, "Distribution": 10}},
]


class TestMarimekko(unittest.TestCase):
    def _build(self):
        return marimekko_profit_pool(SECTORS, source="Golden", vintage="2018")

    def test_sector_widths(self):
        w = self._build().meta["sector_widths"]
        self.assertAlmostEqual(w["Payers"], 0.10, delta=1e-9)
        self.assertAlmostEqual(w["Delivery systems"], 0.50, delta=1e-9)
        self.assertAlmostEqual(w["Service vendors"], 0.05, delta=1e-9)
        self.assertAlmostEqual(w["Manufacturers and distributors"], 0.35, delta=1e-9)

    def test_cumulative_x_boundaries(self):
        rects = self._build().meta["rects"]
        payers = [r for r in rects if r["sector"] == "Payers"]
        self.assertAlmostEqual(payers[0]["x0"], 0.0, delta=1e-9)
        self.assertAlmostEqual(payers[0]["x1"], 0.10, delta=1e-9)
        delivery = [r for r in rects if r["sector"] == "Delivery systems"]
        self.assertAlmostEqual(delivery[0]["x0"], 0.10, delta=1e-9)
        self.assertAlmostEqual(delivery[0]["x1"], 0.60, delta=1e-9)

    def test_heights_and_areas(self):
        rects = self._build().meta["rects"]
        ma = next(r for r in rects if r["subsegment"] == "MA")
        self.assertAlmostEqual(ma["height"], 0.6, delta=1e-9)
        self.assertAlmostEqual(ma["area"], 0.06, delta=1e-9)

    def test_areas_sum_to_one(self):
        rects = self._build().meta["rects"]
        self.assertAlmostEqual(sum(r["area"] for r in rects), 1.0, delta=1e-9)

    def test_classic_alternate(self):
        sectors = [
            {"sector": "A", "subsegments": {"a1": 10}, "revenue": 100, "margin": 0.10},
            {"sector": "B", "subsegments": {"b1": 30}, "revenue": 300, "margin": 0.20},
        ]
        ex = marimekko_profit_pool(sectors, source="Golden", vintage="2024")
        alt = ex.meta["alt_rects"]
        self.assertEqual(len(alt), 2)
        a = next(r for r in alt if r["sector"] == "A")
        self.assertAlmostEqual(a["width"], 0.25, delta=1e-9)  # 100 / 400
        self.assertAlmostEqual(a["height"], 0.10, delta=1e-9)

    def test_clutter_flag(self):
        many = [{"sector": f"S{i}", "subsegments": {"x": 1}} for i in range(8)]
        ex = marimekko_profit_pool(many, source="Golden", vintage="2024")
        self.assertIn("too_many_columns", ex.flag_codes())

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_requires_sector(self):
        with self.assertRaises(ValueError):
            marimekko_profit_pool([], source="Golden", vintage="2024")


if __name__ == "__main__":
    unittest.main()
