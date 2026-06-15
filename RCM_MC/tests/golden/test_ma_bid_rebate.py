"""Golden test for NEW-27 MA bid / benchmark / rebate waterfall.

KFF worked example (apply_qbp off so the benchmark matches the published figure):
    FFS 1000, quartile 1 (115 percent) -> benchmark 1150
    bid 830, 4.5 stars -> 70 percent retention
    spread 1150 - 830 = 320; rebate 0.70 * 320 = 224
    CMS retained 320 - 224 = 96; plan payment 830 + 224 = 1054
With the quality bonus applied (4+ stars, +5 percent):
    benchmark 1000 * 1.20 = 1200; spread 370; rebate 0.70 * 370 = 259
"""
import unittest

from rcm_mc.cdd.ma_bid_rebate import (
    compute_components,
    ma_bid_rebate,
    rebate_pct_for_stars,
)


class TestMaBidRebate(unittest.TestCase):
    def test_kff_worked_example(self):
        c = compute_components(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=830.0, apply_qbp=False
        )
        self.assertAlmostEqual(c["benchmark"], 1150.0, delta=1e-9)
        self.assertAlmostEqual(c["rebate_pct"], 0.70, delta=1e-12)
        self.assertAlmostEqual(c["spread"], 320.0, delta=1e-9)
        self.assertAlmostEqual(c["rebate"], 224.0, delta=1e-9)
        self.assertAlmostEqual(c["cms_retained"], 96.0, delta=1e-9)
        self.assertAlmostEqual(c["plan_payment"], 1054.0, delta=1e-9)
        self.assertAlmostEqual(c["program_vs_ffs"], 54.0, delta=1e-9)

    def test_quality_bonus_adds_to_benchmark(self):
        c = compute_components(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=830.0, apply_qbp=True
        )
        self.assertAlmostEqual(c["benchmark"], 1200.0, delta=1e-9)
        self.assertAlmostEqual(c["rebate"], 259.0, delta=1e-9)
        self.assertAlmostEqual(c["plan_payment"], 1089.0, delta=1e-9)

    def test_double_bonus(self):
        c = compute_components(
            ffs_percapita=1000.0, quartile=3, stars=4.0, bid=900.0,
            double_bonus=True, apply_qbp=True,
        )
        # quartile 3 = 100 percent + 10 percent double bonus = 1100
        self.assertAlmostEqual(c["benchmark"], 1100.0, delta=1e-9)

    def test_rebate_tiers(self):
        self.assertEqual(rebate_pct_for_stars(5.0), 0.70)
        self.assertEqual(rebate_pct_for_stars(4.5), 0.70)
        self.assertEqual(rebate_pct_for_stars(4.0), 0.65)
        self.assertEqual(rebate_pct_for_stars(3.5), 0.65)
        self.assertEqual(rebate_pct_for_stars(3.0), 0.50)

    def test_reconciliations_tie_out(self):
        ex = ma_bid_rebate(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=830.0,
            apply_qbp=False, source="Golden", vintage="2024",
        )
        self.assertTrue(ex.reconciled)

    def test_bid_above_benchmark_flags_enrollee_premium(self):
        ex = ma_bid_rebate(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=1300.0,
            apply_qbp=False, source="Golden", vintage="2024",
        )
        self.assertIn("bid_above_benchmark", ex.flag_codes())
        self.assertAlmostEqual(ex.meta["enrollee_premium"], 150.0, delta=1e-9)
        self.assertAlmostEqual(ex.meta["rebate"], 0.0, delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_low_star_flag(self):
        ex = ma_bid_rebate(
            ffs_percapita=1000.0, quartile=2, stars=3.0, bid=900.0,
            source="Golden", vintage="2024",
        )
        self.assertIn("low_star_rebate", ex.flag_codes())
        self.assertAlmostEqual(ex.meta["rebate_pct"], 0.50, delta=1e-12)

    def test_risk_adjustment_scales_final(self):
        c = compute_components(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=830.0,
            apply_qbp=False, raf=1.1,
        )
        self.assertAlmostEqual(c["final_payment"], 1054.0 * 1.1, delta=1e-9)

    def test_partner_hides_rebate_detail_series(self):
        ex = ma_bid_rebate(
            ffs_percapita=1000.0, quartile=1, stars=4.5, bid=830.0,
            apply_qbp=False, source="Golden", vintage="2024",
        )
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Rebate retention detail", partner)

    def test_bad_quartile_raises(self):
        with self.assertRaises(ValueError):
            compute_components(ffs_percapita=1000.0, quartile=5, stars=4.0, bid=800.0)


if __name__ == "__main__":
    unittest.main()
