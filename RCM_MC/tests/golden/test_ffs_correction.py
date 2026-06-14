"""Golden test for NEW-13 FFS-to-all-population correction.

Hand-computed:
    County X: FFS 1000, MA 0.50 -> weight 1/0.5 = 2.0   -> corrected 2000
    County Y: FFS 1000, MA 0.20 -> weight 1/0.8 = 1.25  -> corrected 1250
High-MA threshold 0.40: X (0.50) flags, Y (0.20) does not.
"""
import unittest

from rcm_mc.cdd.ffs_correction import (
    NATIONAL_MA_PENETRATION_2026,
    ffs_to_all_population,
)

COUNTIES = [
    {"fips": "X", "ffs_activity": 1000, "ma_penetration": 0.50},
    {"fips": "Y", "ffs_activity": 1000, "ma_penetration": 0.20},
]


class TestFfsCorrection(unittest.TestCase):
    def _build(self, counties=None):
        return ffs_to_all_population(counties or COUNTIES, source="Golden", vintage="2026")

    def test_correction_values(self):
        rows = {r["fips"]: r for r in self._build().meta["rows"]}
        self.assertAlmostEqual(rows["X"]["weight"], 2.0, delta=1e-12)
        self.assertAlmostEqual(rows["X"]["corrected_activity"], 2000.0, delta=1e-9)
        self.assertAlmostEqual(rows["Y"]["weight"], 1.25, delta=1e-12)
        self.assertAlmostEqual(rows["Y"]["corrected_activity"], 1250.0, delta=1e-9)

    def test_high_ma_flag(self):
        ex = self._build()
        self.assertIn("high_ma_understatement", ex.flag_codes())
        self.assertEqual(ex.meta["high_ma_counties"], ["X"])

    def test_low_ma_only_no_flag(self):
        ex = self._build([{"fips": "Z", "ffs_activity": 500, "ma_penetration": 0.10}])
        self.assertNotIn("high_ma_understatement", ex.flag_codes())

    def test_totals_reconcile(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["total_corrected"], 3250.0, delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_national_anchor_in_metadata(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["national_ma_anchor"], NATIONAL_MA_PENETRATION_2026, delta=1e-12)
        fn = ex.render()["footnote"]
        self.assertTrue(any("MA penetration" in a for a in fn["assumptions"]))

    def test_100pct_ma_uncomputable(self):
        ex = self._build([{"fips": "full", "ffs_activity": 100, "ma_penetration": 1.0}])
        self.assertIn("ma_penetration_at_100pct", ex.flag_codes())
        self.assertIsNone(ex.meta["rows"][0]["corrected_activity"])

    def test_partner_hides_weight_series(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Per-county correction weight", partner)

    def test_invalid_ma_raises(self):
        with self.assertRaises(ValueError):
            self._build([{"fips": "bad", "ffs_activity": 1, "ma_penetration": -0.1}])


if __name__ == "__main__":
    unittest.main()
