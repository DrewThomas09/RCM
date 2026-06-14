"""Golden test for NEW-14 quality/outcomes benchmarking.

Hand-computed percentile ranks (100 = best):
    Readmission (lower better): target 15, peers [10,12,14,16,18]
        peers worse (higher) than 15: 16,18 -> 2/5 = 40th percentile
    Mortality (lower better): target 20, peers [5,8,10,12,15]
        peers worse than 20: none -> 0th percentile -> bottom quartile
    HCAHPS (higher better): target 90, peers [70,75,80,85,88]
        peers worse (lower) than 90: all 5 -> 100th percentile
    PSI-90: suppressed -> excluded
"""
import unittest

from rcm_mc.cdd.quality_benchmark import quality_benchmark

MEASURES = [
    {"measure": "Readmission", "direction": "lower", "target": 15, "peers": [10, 12, 14, 16, 18], "national": 14},
    {"measure": "Mortality", "direction": "lower", "target": 20, "peers": [5, 8, 10, 12, 15], "national": 10},
    {"measure": "HCAHPS", "direction": "higher", "target": 90, "peers": [70, 75, 80, 85, 88], "national": 82},
    {"measure": "PSI-90", "direction": "lower", "suppressed": True},
]


class TestQualityBenchmark(unittest.TestCase):
    def _build(self):
        return quality_benchmark("123456", MEASURES, source="Golden", vintage="2026")

    def test_percentiles(self):
        rows = {r["measure"]: r for r in self._build().meta["rows"]}
        self.assertAlmostEqual(rows["Readmission"]["percentile"], 40.0, delta=1e-9)
        self.assertAlmostEqual(rows["Mortality"]["percentile"], 0.0, delta=1e-9)
        self.assertAlmostEqual(rows["HCAHPS"]["percentile"], 100.0, delta=1e-9)

    def test_bottom_quartile_flag(self):
        ex = self._build()
        self.assertIn("bottom_quartile_measure", ex.flag_codes())
        self.assertIn("Mortality", ex.meta["bottom_quartile_measures"])
        self.assertNotIn("Readmission", ex.meta["bottom_quartile_measures"])

    def test_suppression_handled(self):
        ex = self._build()
        self.assertIn("measures_suppressed", ex.flag_codes())
        self.assertIn("PSI-90", ex.meta["suppressed_measures"])
        rows = {r["measure"]: r for r in ex.meta["rows"]}
        self.assertTrue(rows["PSI-90"]["suppressed"])
        self.assertIsNone(rows["PSI-90"]["percentile"])

    def test_vs_national(self):
        rows = {r["measure"]: r for r in self._build().meta["rows"]}
        # Readmission 15 vs national 14 (lower better) -> above national means worse
        self.assertEqual(rows["Readmission"]["vs_national"], "below")
        # HCAHPS 90 vs 82 (higher better) -> above
        self.assertEqual(rows["HCAHPS"]["vs_national"], "above")

    def test_percentiles_in_range_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_partner_hides_national_detail(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Target vs national detail", partner)

    def test_invalid_direction_raises(self):
        with self.assertRaises(ValueError):
            quality_benchmark("1", [{"measure": "x", "direction": "sideways",
                                     "target": 1, "peers": [1, 2]}])


if __name__ == "__main__":
    unittest.main()
