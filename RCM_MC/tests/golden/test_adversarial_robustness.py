"""Adversarial / degenerate-input robustness sweep (Part 6 refute protocol).

Feeds each CDD feature a degenerate or adversarial input and confirms it either
degrades gracefully with a clear flag, computes a defensible value, or raises a
clean ValueError. The contract: never crash with an unexpected error, and never
emit a silent wrong number for a degenerate case.
"""
import unittest

import numpy as np

from rcm_mc.cdd.tam_sam_som import tam_sam_som
from rcm_mc.cdd.pvm_bridge import pvm_bridge
from rcm_mc.cdd.payer_mix import payer_mix
from rcm_mc.cdd.pct_medicare import BASIS_MEDICAL, pct_of_medicare
from rcm_mc.cdd.retention_survival import retention_curves
from rcm_mc.cdd.ltv_cac import ltv_cac
from rcm_mc.cdd.provider_density import provider_density
from rcm_mc.cdd.market_saturation import market_saturation
from rcm_mc.cdd.site_of_care import site_of_care_shift
from rcm_mc.cdd.concentration import customer_concentration
from rcm_mc.cdd.monte_carlo_overlay import monte_carlo_overlay
from rcm_mc.cdd.hcc_raf import compute_raf
from rcm_mc.cdd.ffs_correction import ffs_to_all_population
from rcm_mc.cdd.quality_benchmark import quality_benchmark
from rcm_mc.cdd.positioning_map import positioning_map
from rcm_mc.cdd.pricing_cm_bridge import pricing_cm_bridge
from rcm_mc.cdd.regulatory_flags import regulatory_flags
from rcm_mc.cdd.forecast import ridge_conformal_forecast
from rcm_mc.cdd.anomaly import detect_anomalies
from rcm_mc.cdd.changepoint import detect_changepoints
from rcm_mc.cdd.ingestion import ingestion_reconciliation

G = dict(source="Golden", vintage="2026")


class TestAdversarialRobustness(unittest.TestCase):
    def test_tam_empty_raises_clean(self):
        with self.assertRaises(ValueError):
            tam_sam_som([], sales_capacity_units=1, win_rate=0.5)

    def test_tam_all_unreachable(self):
        ex = tam_sam_som(
            [{"segment": "x", "unit_count": 100, "price": 1.0, "penetration_rate": 0.5, "reachable": False}],
            sales_capacity_units=10, win_rate=0.5, **G)
        self.assertEqual(ex.meta["sam"], 0.0)
        self.assertEqual(ex.meta["som"], 0.0)  # no reachable demand

    def test_pvm_identical_periods_zero_change(self):
        rows = [{"period": "A", "line": "x", "volume": 10, "price": 5.0},
                {"period": "B", "line": "x", "volume": 10, "price": 5.0}]
        ex = pvm_bridge(rows, period1="A", period2="B", **G)
        self.assertAlmostEqual(ex.meta["total_change"], 0.0, delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_payer_mix_all_medicaid(self):
        ex = payer_mix({"Medicaid": 1000}, **G)
        self.assertAlmostEqual(ex.meta["shares_1"]["Medicaid"], 100.0, delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_pct_medicare_all_codes_missing(self):
        ex = pct_of_medicare([{"code": "ZZZ", "allowed": 100.0}], {"AAA": 50.0},
                             basis=BASIS_MEDICAL, **G)
        self.assertIn("codes_missing_from_schedule", ex.flag_codes())
        self.assertEqual(ex.meta["blended_pct"], 0.0)  # no silent wrong number

    def test_retention_single_member_flagged(self):
        ex = retention_curves([{"entity_id": "a", "cohort": "c", "duration_months": 3, "churned": True}],
                              times=(1, 3), **G)
        self.assertIn("small_cohort", ex.flag_codes())

    def test_ltv_zero_revenue_never_pays_back(self):
        ex = ltv_cac([{"cohort": "c", "n_customers": 10, "cac": 100.0,
                       "revenue_by_age": {1: 0, 2: 0}}], **G)
        self.assertIn("never_pays_back", ex.flag_codes())

    def test_provider_density_single_provider(self):
        ex = provider_density([{"npi": "1", "fips": "06037"}], by="fips", suppress=False, **G)
        self.assertEqual(ex.meta["total"], 1)
        self.assertTrue(ex.reconciled)

    def test_market_saturation_zero_beneficiaries(self):
        ex = market_saturation([{"area": "x", "providers": 5, "beneficiaries": 0}], **G)
        self.assertEqual(ex.meta["rows"][0]["saturation_per_n"], 0.0)  # safe div, no crash

    def test_site_of_care_zero_counts(self):
        ex = site_of_care_shift({"IP": 0}, {"IP": 0}, **G)
        self.assertAlmostEqual(ex.meta["deltas"]["IP"], 0.0, delta=1e-9)

    def test_concentration_single_account_flags(self):
        ex = customer_concentration([{"account": "solo", "revenue": 1.0}], **G)
        self.assertIn("single_account_over_40pct", ex.flag_codes())

    def test_monte_carlo_degenerate_zero_variance(self):
        drivers = [{"name": "d", "dist": "normal", "params": {"mean": 0.0, "sd": 0.0}}]
        ex = monte_carlo_overlay(1000.0, drivers, seed=1, **G)
        self.assertAlmostEqual(ex.meta["p5"], ex.meta["p95"], delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_monte_carlo_too_few_sims_raises(self):
        with self.assertRaises(ValueError):
            monte_carlo_overlay(1.0, [{"name": "d", "dist": "normal",
                                       "params": {"mean": 0, "sd": 1}}], n_sims=100)

    def test_hcc_no_diagnoses(self):
        ex = compute_raf({"age": 70, "sex": "F", "icd10": []}, **G)
        self.assertAlmostEqual(ex.meta["hcc_sum"], 0.0, delta=1e-12)
        self.assertTrue(ex.reconciled)

    def test_ffs_100pct_ma_uncomputable(self):
        ex = ffs_to_all_population([{"fips": "x", "ffs_activity": 10, "ma_penetration": 1.0}], **G)
        self.assertIn("ma_penetration_at_100pct", ex.flag_codes())
        self.assertIsNone(ex.meta["rows"][0]["corrected_activity"])

    def test_quality_all_suppressed(self):
        ex = quality_benchmark("1", [{"measure": "m", "direction": "lower", "suppressed": True}], **G)
        self.assertIn("measures_suppressed", ex.flag_codes())

    def test_positioning_single_player(self):
        ex = positioning_map([{"name": "solo", "share": 0.5, "attractiveness": 0.5, "revenue": 10}], **G)
        self.assertTrue(ex.reconciled)

    def test_pricing_zero_volume(self):
        ex = pricing_cm_bridge(gross_price=10.0, volume=0, **G)
        self.assertEqual(ex.meta["revenue"], 0.0)
        self.assertTrue(ex.reconciled)

    def test_regulatory_empty_target(self):
        ex = regulatory_flags({}, **G)
        self.assertEqual(ex.flag_codes(), [])
        self.assertTrue(ex.reconciled)

    def test_forecast_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            ridge_conformal_forecast([[1.0]] * 5, [1.0] * 5)

    def test_forecast_constant_series_no_crash(self):
        X = np.arange(40, dtype=float).reshape(-1, 1)
        y = np.full(40, 7.0)
        ex = ridge_conformal_forecast(X, y, seed=1, **G)
        self.assertIn("80", ex.meta["coverage"])  # produced intervals, no crash

    def test_anomaly_identical_records(self):
        recs = [{"id": f"r{i}", "x": 1.0, "y": 2.0} for i in range(20)]
        ex = detect_anomalies(recs, ["x", "y"], **G)
        self.assertTrue(ex.reconciled)  # no crash on zero-variance features

    def test_changepoint_two_points(self):
        ex = detect_changepoints([1.0, 2.0], **G)
        self.assertIn("changepoints", ex.meta)

    def test_ingestion_empty_raises(self):
        with self.assertRaises(ValueError):
            ingestion_reconciliation({}, [])


if __name__ == "__main__":
    unittest.main()
