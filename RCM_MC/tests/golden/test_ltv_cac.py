"""Golden test for NEW-06 cohort LTV/CAC.

Hand-computed cohort (n=100, CAC per customer = 50, gross margin = 1.0):

    month:        1     2     3     4     5     6
    revenue:    2000  2000  1500  1500  1000  1000
    cumulative: 2000  4000  5500  7000  8000  9000
    LTV/cust:     20    40    55    70    80    90

    payback month = first age where LTV/cust >= 50  -> month 3 (55 >= 50)
    final LTV/cust = 90
    LTV:CAC = 90 / 50 = 1.8   (below 3:1)
    total cohort revenue = 9000; vs total 9100 -> gap 1.1% (within 2%)
"""
import unittest

from rcm_mc.cdd.ltv_cac import ltv_cac

COHORT = {
    "cohort": "2024",
    "n_customers": 100,
    "cac": 50.0,
    "revenue_by_age": {1: 2000, 2: 2000, 3: 1500, 4: 1500, 5: 1000, 6: 1000},
}


class TestLtvCac(unittest.TestCase):
    def _build(self, total_revenue=9100.0, gross_margin=1.0):
        return ltv_cac([COHORT], total_revenue=total_revenue,
                       gross_margin=gross_margin, source="Golden", vintage="2026")

    def test_ltv_payback_ratio(self):
        c = self._build().meta["cohorts"]["2024"]
        self.assertAlmostEqual(c["final_ltv_per_customer"], 90.0, delta=1e-9)
        self.assertEqual(c["payback_month"], 3)
        self.assertAlmostEqual(c["ltv_cac_ratio"], 1.8, delta=1e-9)

    def test_below_3to1_flag(self):
        self.assertIn("below_3to1", self._build().flag_codes())

    def test_revenue_reconciles_within_2pct(self):
        ex = self._build(total_revenue=9100.0)
        self.assertTrue(ex.reconciled)
        self.assertNotIn("revenue_reconciliation_gap", ex.flag_codes())

    def test_revenue_reconciliation_gap_flags(self):
        ex = self._build(total_revenue=12000.0)  # 9000 vs 12000 -> 25% gap
        self.assertIn("revenue_reconciliation_gap", ex.flag_codes())
        self.assertFalse(ex.reconciled)

    def test_gross_margin_scales_ltv(self):
        c = self._build(gross_margin=0.5).meta["cohorts"]["2024"]
        self.assertAlmostEqual(c["final_ltv_per_customer"], 45.0, delta=1e-9)
        # 45/50 = 0.9
        self.assertAlmostEqual(c["ltv_cac_ratio"], 0.9, delta=1e-9)

    def test_healthy_cohort_no_flag(self):
        healthy = {
            "cohort": "win",
            "n_customers": 10,
            "cac": 10.0,
            "revenue_by_age": {1: 200, 2: 200},  # LTV/cust = 40, ratio 4.0
        }
        ex = ltv_cac([healthy], source="Golden", vintage="2026")
        c = ex.meta["cohorts"]["win"]
        self.assertAlmostEqual(c["ltv_cac_ratio"], 4.0, delta=1e-9)
        self.assertEqual(c["payback_month"], 1)
        self.assertNotIn("below_3to1", ex.flag_codes())

    def test_never_pays_back_flag(self):
        slow = {
            "cohort": "slow",
            "n_customers": 100,
            "cac": 1000.0,
            "revenue_by_age": {1: 100, 2: 100},  # LTV/cust max 2 < 1000
        }
        ex = ltv_cac([slow], source="Golden", vintage="2026")
        self.assertIn("never_pays_back", ex.flag_codes())
        self.assertIsNone(ex.meta["cohorts"]["slow"]["payback_month"])

    def test_reference_line_in_meta(self):
        self.assertEqual(self._build().meta["ltv_cac_reference"], 3.0)


if __name__ == "__main__":
    unittest.main()
