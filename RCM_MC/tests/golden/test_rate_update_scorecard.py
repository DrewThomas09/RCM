"""Golden test for NEW-22 rate-update scorecard.

The default 2026 scorecard carries 12 settings. Home health (-1.3 percent) is the
only negative; the Physician Fee Schedule shows as two bars (QP +3.77, non-QP
+3.26). Where stated, components sum to the net:
    skilled nursing 3.3 + 0.6 - 0.7 = 3.2
    inpatient psych 3.2 - 0.7 = 2.5
    long-term acute care 3.4 - 0.7 = 2.7
"""
import unittest

from rcm_mc.cdd.rate_update_scorecard import RateUpdate, rate_update_scorecard


class TestRateUpdateScorecard(unittest.TestCase):
    def test_counts(self):
        m = rate_update_scorecard().meta
        self.assertEqual(m["n_settings"], 12)
        self.assertEqual(m["n_negative"], 1)

    def test_extremes_and_sort(self):
        ex = rate_update_scorecard()
        pts = ex.series[0].points
        self.assertEqual(pts[0]["label"], "Home health")
        self.assertAlmostEqual(pts[0]["value"], -1.3, delta=1e-9)
        self.assertAlmostEqual(pts[-1]["value"], 3.77, delta=1e-9)
        self.assertEqual(ex.meta["min_update"], -1.3)
        self.assertEqual(ex.meta["max_update"], 3.77)

    def test_flags(self):
        codes = rate_update_scorecard().flag_codes()
        self.assertIn("negative_update", codes)
        self.assertIn("pfs_dual_conversion_factor", codes)

    def test_negative_colored_red(self):
        pts = {p["label"]: p for p in rate_update_scorecard().series[0].points}
        self.assertEqual(pts["Home health"]["color"], "red")
        self.assertEqual(pts["Skilled nursing"]["color"], "green")

    def test_components_reconcile(self):
        self.assertTrue(rate_update_scorecard().reconciled)

    def test_bad_components_fail_reconciliation(self):
        bad = [RateUpdate("Bogus", 2.0, "X", [1.0, 0.5])]  # sums to 1.5, not 2.0
        self.assertFalse(rate_update_scorecard(bad).reconciled)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            rate_update_scorecard([])


if __name__ == "__main__":
    unittest.main()
