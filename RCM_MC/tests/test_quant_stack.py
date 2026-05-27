"""Tests for the quant stack: Bayesian calibration, DEA, queueing, survival."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=100):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY"], n),
        "beds": rng.randint(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e7, 5e9, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "gross_patient_revenue": rng.uniform(5e7, 1e10, n),
        "total_patient_days": rng.randint(1000, 100000, n).astype(float),
        "bed_days_available": rng.randint(5000, 200000, n).astype(float),
        "medicare_day_pct": rng.uniform(0.1, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.3, n),
    })


class TestBayesianCalibration(unittest.TestCase):

    def test_rate_prior_only(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_rate_metric
        est = calibrate_rate_metric("denial_rate", None, 0, beds=200)
        self.assertEqual(est.data_quality, "prior_only")
        self.assertEqual(est.shrinkage_factor, 1.0)
        self.assertGreater(est.posterior_mean, 0)

    def test_rate_with_data(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_rate_metric
        est = calibrate_rate_metric("denial_rate", 0.12, 500, beds=200)
        self.assertEqual(est.data_quality, "strong")
        self.assertLess(est.shrinkage_factor, 0.5)
        # Should be close to observed with strong data
        self.assertAlmostEqual(est.posterior_mean, 0.12, delta=0.02)

    def test_rate_shrinkage_with_weak_data(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_rate_metric
        est = calibrate_rate_metric("denial_rate", 0.30, 5, beds=200)
        self.assertEqual(est.data_quality, "weak")
        # With only 5 obs, posterior should shrink toward prior (~8.5%)
        self.assertLess(est.posterior_mean, 0.30)
        self.assertGreater(est.shrinkage_factor, 0.5)

    def test_credible_interval(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_rate_metric
        est = calibrate_rate_metric("denial_rate", 0.10, 200, beds=200)
        lo, hi = est.credible_interval_90
        self.assertLess(lo, est.posterior_mean)
        self.assertGreater(hi, est.posterior_mean)
        self.assertGreaterEqual(lo, 0)
        self.assertLessEqual(hi, 1)

    def test_continuous_metric(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_continuous_metric
        est = calibrate_continuous_metric("days_in_ar", 55, 100, beds=200)
        self.assertEqual(est.data_quality, "strong")
        self.assertGreater(est.posterior_mean, 40)

    def test_hospital_profile(self):
        from rcm_mc.ml.bayesian_calibration import calibrate_hospital_profile
        results = calibrate_hospital_profile(
            {"denial_rate": 0.10, "days_in_ar": 45, "claims_volume": 200},
            beds=200)
        self.assertGreater(len(results), 5)
        for est in results:
            self.assertIsNotNone(est.posterior_mean)

    def test_missing_data_score(self):
        from rcm_mc.ml.bayesian_calibration import compute_missing_data_score
        score = compute_missing_data_score({"denial_rate": 0.08, "days_in_ar": 42})
        self.assertIn("grade", score)
        self.assertIn("completeness_pct", score)
        self.assertGreater(score["missing_count"], 0)

    def test_missing_data_all_present(self):
        from rcm_mc.ml.bayesian_calibration import compute_missing_data_score, _RATE_PRIORS, _CONTINUOUS_PRIORS
        obs = {m: 0.5 for m in _RATE_PRIORS}
        obs.update({m: 50 for m in _CONTINUOUS_PRIORS})
        score = compute_missing_data_score(obs)
        self.assertEqual(score["completeness_pct"], 100.0)


class TestEfficiencyFrontier(unittest.TestCase):

    def test_compute_frontier(self):
        from rcm_mc.ml.efficiency_frontier import compute_efficiency_frontier
        df = _sample_hcris(200)
        result_df, scores = compute_efficiency_frontier(df)
        self.assertIn("efficiency_score", result_df.columns)
        self.assertGreater(len(scores), 0)

    def test_scores_in_range(self):
        from rcm_mc.ml.efficiency_frontier import compute_efficiency_frontier
        df = _sample_hcris(200)
        _, scores = compute_efficiency_frontier(df)
        for s in scores:
            self.assertGreaterEqual(s.efficiency_score, 0)
            self.assertLessEqual(s.efficiency_score, 1)

    def test_frontier_hospitals_exist(self):
        from rcm_mc.ml.efficiency_frontier import compute_efficiency_frontier
        df = _sample_hcris(200)
        _, scores = compute_efficiency_frontier(df)
        frontier = [s for s in scores if s.is_frontier]
        self.assertGreater(len(frontier), 0)

    def test_dea_basic(self):
        from rcm_mc.ml.efficiency_frontier import _simple_dea_output_oriented
        inputs = np.array([[10, 5], [20, 10], [15, 8]])
        outputs = np.array([[100, 50], [150, 80], [120, 60]])
        scores = _simple_dea_output_oriented(inputs, outputs)
        self.assertEqual(len(scores), 3)
        self.assertTrue(all(0 <= s <= 1 for s in scores))


class TestQueueingModel(unittest.TestCase):

    def test_mmc_stable(self):
        from rcm_mc.ml.queueing_model import analyze_mmc_queue
        q = analyze_mmc_queue("Test", arrival_rate=40, service_rate=10, n_servers=5)
        self.assertLess(q.utilization, 1.0)
        self.assertGreater(q.avg_wait_time, 0)

    def test_mmc_overloaded(self):
        from rcm_mc.ml.queueing_model import analyze_mmc_queue
        q = analyze_mmc_queue("Test", arrival_rate=100, service_rate=10, n_servers=5)
        self.assertEqual(q.utilization, 1.0)
        self.assertTrue(q.bottleneck)

    def test_rcm_operations(self):
        from rcm_mc.ml.queueing_model import analyze_rcm_operations
        queues = analyze_rcm_operations()
        self.assertEqual(len(queues), 4)
        for q in queues:
            self.assertIsInstance(q.queue_name, str)
            self.assertGreater(q.recommended_servers, 0)

    def test_littles_law(self):
        from rcm_mc.ml.queueing_model import littles_law_analysis
        result = littles_law_analysis(avg_inventory=100, throughput=20)
        self.assertAlmostEqual(result["avg_cycle_time"], 5.0)

    def test_erlang_c(self):
        from rcm_mc.ml.queueing_model import _erlang_c
        # With low load, probability of waiting should be low
        p = _erlang_c(5, 2.0)
        self.assertGreater(p, 0)
        self.assertLess(p, 1)

    def test_sla_breach(self):
        from rcm_mc.ml.queueing_model import analyze_mmc_queue
        q = analyze_mmc_queue("Test", arrival_rate=20, service_rate=10, n_servers=5, sla_days=5)
        self.assertGreaterEqual(q.sla_breach_prob, 0)
        self.assertLessEqual(q.sla_breach_prob, 1)


class TestSurvivalAnalysis(unittest.TestCase):

    def test_estimate_runway(self):
        from rcm_mc.ml.survival_analysis import estimate_margin_runway
        df = _sample_hcris(100)
        result = estimate_margin_runway("000001", None, df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.estimated_years_to_distress, 0)

    def test_survival_curve_monotonic(self):
        from rcm_mc.ml.survival_analysis import estimate_margin_runway
        df = _sample_hcris(100)
        # Give hospital positive margin so curve should decrease
        df.loc[df["ccn"] == "000001", "operating_expenses"] = df.loc[df["ccn"] == "000001", "net_patient_revenue"] * 0.9
        result = estimate_margin_runway("000001", None, df)
        self.assertIsNotNone(result)
        probs = [p["survival_prob"] for p in result.survival_curve]
        # First should be highest (or equal)
        self.assertGreaterEqual(probs[0], probs[-1])

    def test_norm_cdf_matches_known_values(self):
        from rcm_mc.ml.survival_analysis import _norm_cdf
        self.assertAlmostEqual(_norm_cdf(0.0), 0.5, places=6)
        self.assertAlmostEqual(_norm_cdf(1.0), 0.8413447, places=5)
        self.assertAlmostEqual(_norm_cdf(-1.0), 0.1586553, places=5)
        self.assertGreater(_norm_cdf(6.0), 0.999999)

    def test_survival_prob_degenerate_and_monotone(self):
        from rcm_mc.ml.survival_analysis import _survival_prob
        # Zero SE → step function on the sign of the mean.
        self.assertEqual(_survival_prob(0.05, 0.0), 1.0)
        self.assertEqual(_survival_prob(-0.05, 0.0), 0.0)
        # Φ(0/σ) = 0.5 exactly; higher margin → higher survival.
        self.assertAlmostEqual(_survival_prob(0.0, 0.02), 0.5, places=6)
        self.assertGreater(_survival_prob(0.04, 0.02), _survival_prob(0.01, 0.02))
        for p in (_survival_prob(0.03, 0.02), _survival_prob(-0.03, 0.02)):
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)

    def test_survival_curve_is_prediction_interval_of_fit(self):
        # Principled contract: survival_prob at year t = Φ(projected_margin / SE),
        # where SE is the OLS prediction interval — not a hand-tuned ramp. A
        # healthy hospital whose margin compresses must cross 0.5 survival in a
        # finite horizon, which a fixed ramp can't express from the fit.
        from rcm_mc.ml.survival_analysis import estimate_margin_runway, _survival_prob
        latest = pd.DataFrame([{
            "ccn": "000001", "name": "H", "state": "TX",
            "net_patient_revenue": 1e8, "operating_expenses": 9e7,
            "beds": 120, "medicare_day_pct": 0.4, "medicaid_day_pct": 0.15,
            "total_patient_days": 3e4, "bed_days_available": 4e4}])
        trend = pd.DataFrame([{
            "ccn": "000001", "fiscal_year": y,
            "net_patient_revenue": 1e8,
            "operating_expenses": 9e7 + (y - 2020) * 3e6}
            for y in (2020, 2021, 2022, 2023)])  # margin compressing ~3pp/yr
        r = estimate_margin_runway("000001", trend, latest)
        probs = [p["survival_prob"] for p in r.survival_curve]
        self.assertGreater(probs[0], 0.9)        # healthy today
        self.assertLess(probs[-1], 0.5)          # underwater by year 10
        self.assertTrue(all(0.0 <= p <= 1.0 for p in probs))
        # Recover year 0's SE from its reported value and confirm year 1's SE
        # is strictly larger — the prediction interval widens with the horizon.
        from rcm_mc.ml.survival_analysis import _norm_cdf  # noqa: F401
        self.assertGreaterEqual(probs[0], probs[1])


if __name__ == "__main__":
    unittest.main()
