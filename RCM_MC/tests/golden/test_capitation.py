"""Golden test for NEW-20 Capitation / lives and shared-savings model.

Hand-computed base case (1,000 lives, 12 months, $1,000 base PMPM, RAF 1.0):
    member-months      = 12,000
    risk-adjusted PMPM = 1,000
    revenue            = 12,000,000

MLR (clinical spend 10,000,000 against 12,000,000 premium):
    MLR        = 10,000,000 / 12,000,000 = 0.83333...  (below the 0.85 floor)
    remittance = (0.85 - 0.83333...) * 12,000,000 = 200,000

Shared savings (benchmark 12,000,000; actual 10,000,000; MSR 2%; sharing 50%):
    gross savings = 2,000,000 (16.67%, clears MSR)
    earned        = 2,000,000 * 0.50 * 1.0 = 1,000,000
"""
import unittest

from rcm_mc.cdd.capitation import (
    capitation_model,
    capitation_revenue,
    mlr_test,
    shared_savings_waterfall,
)

TOL = 1e-6


class TestCapitation(unittest.TestCase):
    def test_revenue_identity(self):
        r = capitation_revenue(1000, 12, 1000.0, 1.0)
        self.assertAlmostEqual(r["member_months"], 12_000.0, delta=TOL)
        self.assertAlmostEqual(r["risk_adjusted_pmpm"], 1000.0, delta=TOL)
        self.assertAlmostEqual(r["revenue"], 12_000_000.0, delta=TOL)

    def test_raf_scales_pmpm(self):
        r = capitation_revenue(1000, 12, 800.0, 1.045)
        self.assertAlmostEqual(r["risk_adjusted_pmpm"], 836.0, delta=TOL)

    def test_mlr_below_floor_owes_remittance(self):
        t = mlr_test(10_000_000.0, 0.0, 12_000_000.0)
        self.assertAlmostEqual(t["mlr"], 10.0 / 12.0, delta=TOL)
        self.assertTrue(t["below_floor"])
        self.assertAlmostEqual(t["remittance"], 200_000.0, delta=1e-3)

    def test_mlr_above_floor_no_remittance(self):
        t = mlr_test(11_000_000.0, 0.0, 12_000_000.0)
        self.assertFalse(t["below_floor"])
        self.assertAlmostEqual(t["remittance"], 0.0, delta=TOL)

    def test_waterfall_savings_earned(self):
        w = shared_savings_waterfall(
            12_000_000.0, 10_000_000.0, msr=0.02, sharing_rate=0.50
        )
        self.assertEqual(w["status"], "savings_earned")
        self.assertAlmostEqual(w["settlement"], 1_000_000.0, delta=TOL)

    def test_waterfall_below_msr_keeps_nothing(self):
        # 1% gross savings does not clear a 2% MSR.
        w = shared_savings_waterfall(
            12_000_000.0, 11_880_000.0, msr=0.02, sharing_rate=0.50
        )
        self.assertEqual(w["status"], "below_msr")
        self.assertAlmostEqual(w["settlement"], 0.0, delta=TOL)

    def test_waterfall_one_sided_no_downside(self):
        w = shared_savings_waterfall(
            12_000_000.0, 13_000_000.0, msr=0.02, sharing_rate=0.50
        )
        self.assertEqual(w["status"], "one_sided_no_downside")
        self.assertAlmostEqual(w["settlement"], 0.0, delta=TOL)

    def test_waterfall_two_sided_loss_owed(self):
        # 10% loss past the threshold; loss-sharing rate = 1 - 0.5 = 0.5.
        w = shared_savings_waterfall(
            100.0, 110.0, msr=0.02, sharing_rate=0.50, two_sided=True
        )
        self.assertEqual(w["status"], "loss_owed")
        self.assertAlmostEqual(w["settlement"], -5.0, delta=TOL)

    def test_model_reconciles_and_flags(self):
        ex = capitation_model(
            attributed_lives=1000,
            months=12,
            base_pmpm=1000.0,
            raf=1.0,
            clinical_spend=10_000_000.0,
            msr=0.02,
            sharing_rate=0.50,
            source="Golden fixture",
            vintage="2026",
        )
        self.assertTrue(ex.reconciled)
        self.assertIn("mlr_below_floor", ex.flag_codes())
        self.assertAlmostEqual(ex.meta["revenue"], 12_000_000.0, delta=TOL)
        self.assertAlmostEqual(ex.meta["settlement"], 1_000_000.0, delta=TOL)


if __name__ == "__main__":
    unittest.main()
