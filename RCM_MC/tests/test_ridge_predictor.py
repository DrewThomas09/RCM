"""Tests for the conformal-calibrated Ridge predictor.

Three concerns tested in this file:

1. **Conformal coverage** — when we fit on known-distribution data,
   the 90% intervals cover ~90% of held-out truth. If that property
   breaks, everything downstream (diligence-grade prediction quality
   claims) is marketing, not math.
2. **Fallback ladder** — the size-gated choice between Ridge /
   weighted-median / benchmark-fallback is the single most visible
   piece of logic the partner sees in the UI.
3. **Feature engineering** — the interaction features are deterministic
   and self-documenting; they either fire or they don't.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any, Dict, List

import numpy as np

from rcm_mc.ml.conformal import (
    ConformalPredictor,
    bootstrap_interval,
    percentile_interval,
    split_train_calibration,
)
from rcm_mc.ml.feature_engineering import (
    derive_features,
    derive_interaction_features,
    normalize_features,
    normalize_metrics,
)
from rcm_mc.ml.ridge_predictor import (
    PredictedMetric as RidgePredictedMetric,
    _RidgeModel,
    _grade,
    predict_missing_metrics,
    to_packet_predicted_metric,
)
from rcm_mc.ml.backtester import (
    PredictionBacktestResult,
    backtest_predictions,
)
from rcm_mc.analysis.completeness import RCM_METRIC_REGISTRY


# ── Synthetic comparable cohorts ─────────────────────────────────────

def _synthetic_cohort(n: int, seed: int = 7) -> List[Dict[str, Any]]:
    """Build a peer cohort with a known linear relationship so R² is
    high and Ridge actually learns something.

    target denial_rate ≈ 5 + 0.01 * days_in_ar + noise
    """
    rng = np.random.default_rng(seed)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        beds = float(100 + 10 * i + rng.normal(0, 5))
        dar = float(40 + 0.5 * i + rng.normal(0, 2))
        ccr = float(92 - 0.05 * i + rng.normal(0, 1))
        ncr = float(97 - 0.01 * i + rng.normal(0, 0.5))
        fpr = float(80 + 0.1 * i + rng.normal(0, 1))
        ctc = float(3.0 + rng.normal(0, 0.3))
        # Target metric: noisy linear function of days_in_ar.
        denial = float(5.0 + 0.1 * (dar - 40) + rng.normal(0, 0.5))
        out.append({
            "ccn": f"peer{i:03d}",
            "bed_count": beds,
            "region": "midwest",
            "similarity_score": 1.0 - abs(i - n / 2) / n,
            "denial_rate": max(0.1, denial),
            "days_in_ar": dar,
            "clean_claim_rate": ccr,
            "net_collection_rate": ncr,
            "first_pass_resolution_rate": fpr,
            "cost_to_collect": ctc,
        })
    return out


# ── ConformalPredictor ───────────────────────────────────────────────

class TestConformalPredictor(unittest.TestCase):
    def test_fit_computes_margin(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(60, 2))
        y = X @ [1.5, -2.0] + rng.normal(0, 0.3, size=60)
        X_tr, y_tr, X_cal, y_cal = split_train_calibration(X, y, cal_fraction=0.3)
        cp = ConformalPredictor(_RidgeModel(), coverage=0.90).fit(
            X_tr, y_tr, X_cal, y_cal,
        )
        self.assertGreater(cp.margin, 0.0)
        self.assertEqual(len(cp.residuals), len(X_cal))

    def test_predict_interval_returns_point_low_high(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(40, 1))
        y = X.squeeze() * 2.0 + rng.normal(0, 0.2, size=40)
        X_tr, y_tr, X_cal, y_cal = split_train_calibration(X, y)
        cp = ConformalPredictor(_RidgeModel(), coverage=0.90).fit(
            X_tr, y_tr, X_cal, y_cal,
        )
        point, low, high = cp.predict_interval(np.asarray([[0.5]]))
        self.assertEqual(point.shape, (1,))
        self.assertTrue(np.all(low <= point))
        self.assertTrue(np.all(point <= high))

    def test_invalid_coverage_raises(self):
        with self.assertRaises(ValueError):
            ConformalPredictor(_RidgeModel(), coverage=1.5)
        with self.assertRaises(ValueError):
            ConformalPredictor(_RidgeModel(), coverage=0.0)

    def test_empty_calibration_produces_zero_margin(self):
        cp = ConformalPredictor(_RidgeModel(), coverage=0.90).fit(
            np.asarray([[1.0], [2.0]]), np.asarray([1.0, 2.0]),
            np.zeros((0, 1)), np.zeros(0),
        )
        self.assertEqual(cp.margin, 0.0)

    def test_coverage_property_on_simulated_data(self):
        """The cornerstone test: on 1000 held-out samples, the 90%
        interval covers ~90% of the truth. Gives us confidence the
        conformal math is right.
        """
        rng = np.random.default_rng(42)
        # Generate a single ground-truth process
        X_all = rng.normal(size=(1200, 3))
        beta = np.asarray([2.0, -1.0, 0.5])
        y_all = X_all @ beta + rng.normal(0, 1.0, size=1200)
        # 100 train, 100 cal, 1000 test
        X_tr, y_tr = X_all[:100], y_all[:100]
        X_cal, y_cal = X_all[100:200], y_all[100:200]
        X_te, y_te = X_all[200:], y_all[200:]

        cp = ConformalPredictor(_RidgeModel(), coverage=0.90).fit(
            X_tr, y_tr, X_cal, y_cal,
        )
        point, low, high = cp.predict_interval(X_te)
        covered = np.mean((y_te >= low) & (y_te <= high))
        # Marginal coverage should be within ±5pp of 90% on n=1000.
        self.assertGreater(covered, 0.85)
        self.assertLess(covered, 0.96)


# ── Bootstrap interval ────────────────────────────────────────────────

class TestBootstrapInterval(unittest.TestCase):
    def test_weighted_median_matches_unweighted_for_uniform_weights(self):
        vals = np.arange(1.0, 11.0)
        point, low, high = bootstrap_interval(
            vals, None, coverage=0.90, n_bootstrap=500, random_state=0,
        )
        self.assertAlmostEqual(point, float(np.median(vals)), delta=1.0)
        self.assertLess(low, point)
        self.assertGreater(high, point)

    def test_weighted_median_heavier_weights_shift_point(self):
        vals = np.asarray([1.0, 2.0, 10.0])
        weights_low = np.asarray([5.0, 5.0, 1.0])
        point_low, _, _ = bootstrap_interval(
            vals, weights_low, coverage=0.90, n_bootstrap=300, random_state=0,
        )
        weights_high = np.asarray([1.0, 1.0, 10.0])
        point_high, _, _ = bootstrap_interval(
            vals, weights_high, coverage=0.90, n_bootstrap=300, random_state=0,
        )
        self.assertLess(point_low, point_high)

    def test_empty_values_returns_zero_tuple(self):
        self.assertEqual(bootstrap_interval(np.asarray([])), (0.0, 0.0, 0.0))


# ── Feature engineering ──────────────────────────────────────────────

class TestFeatureEngineering(unittest.TestCase):
    def test_derive_interaction_full_set(self):
        m = {
            "denial_rate": 5.0,
            "net_collection_rate": 96.0,
            "days_in_ar": 45.0,
            "clean_claim_rate": 92.0,
            "first_pass_resolution_rate": 85.0,
            "avoidable_denial_pct": 55.0,
            "payer_mix_commercial_pct": 40.0,
            "payer_mix_medicaid_pct": 10.0,
            "payer_mix_medicare_advantage_pct": 15.0,
            "net_revenue": 350_000_000,
            "bed_count": 420,
        }
        out = derive_interaction_features(m)
        self.assertIn("denial_to_collection_ratio", out)
        self.assertIn("ar_efficiency", out)
        self.assertIn("first_pass_gap", out)
        self.assertIn("avoidable_denial_burden", out)
        self.assertIn("payer_complexity_score", out)
        self.assertIn("revenue_per_bed", out)
        # Spot-check math
        self.assertAlmostEqual(out["first_pass_gap"], 7.0)
        self.assertAlmostEqual(out["revenue_per_bed"], 350_000_000 / 420)
        # Payer complexity = 0.4*40 + 0.35*10 + 0.25*15 = 23.25
        self.assertAlmostEqual(out["payer_complexity_score"], 23.25)

    def test_derive_interaction_handles_payer_mix_fraction_dict(self):
        m = {"payer_mix": {"commercial": 0.4, "medicaid": 0.1,
                           "medicare_advantage": 0.15}}
        out = derive_interaction_features(m)
        # Fractions are upscaled to pct → same result as the pct-keyed version.
        self.assertAlmostEqual(out["payer_complexity_score"], 23.25)

    def test_derive_interaction_missing_inputs_skip(self):
        out = derive_interaction_features({"denial_rate": 5.0})
        # No net_collection_rate → no denial_to_collection_ratio
        self.assertNotIn("denial_to_collection_ratio", out)

    def test_normalize_features_uses_mean_std(self):
        stats = {"denial_rate": {"mean": 6.0, "std": 2.0}}
        out = normalize_features({"denial_rate": 8.0}, stats)
        self.assertAlmostEqual(out["denial_rate"], 1.0)

    def test_normalize_features_passes_through_missing_stats(self):
        out = normalize_features({"foo": 3.14}, {})
        self.assertAlmostEqual(out["foo"], 3.14)

    def test_normalize_features_zero_std_fallback(self):
        stats = {"denial_rate": {"mean": 5.0, "std": 0.0}}
        out = normalize_features({"denial_rate": 8.0}, stats)
        # SD=0 → no division; returns raw value.
        self.assertAlmostEqual(out["denial_rate"], 8.0)

    def test_legacy_derive_features_still_works(self):
        # The older derive_features remains for back-compat with
        # rcm_predictor / backtester pathways.
        out = derive_features({
            "denial_rate": 5.0, "net_collection_rate": 96.0,
            "days_in_ar": 45.0, "clean_claim_rate": 92.0,
            "first_pass_resolution_rate": 85.0,
            "avoidable_denial_pct": 55.0,
        })
        self.assertIn("denial_to_collection_ratio", out)
        self.assertIn("ar_efficiency", out)


# ── Ridge / predict_missing_metrics ──────────────────────────────────

class TestPredictMissingMetrics(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "denial_rate": {
                "display_name": "Denial Rate", "category": "denials",
                "unit": "pct", "ebitda_sensitivity_rank": 1,
                "valid_range": (0.0, 100.0), "benchmark_p25": 3.0,
                "benchmark_p50": 5.2, "benchmark_p75": 9.8,
                "benchmark_p90": 14.5, "stale_after_days": 90,
                "required_for_bridge": True,
            },
        }

    def test_thick_cohort_uses_modern_predictor_branch(self):
        cohort = _synthetic_cohort(30, seed=11)
        known = {
            "days_in_ar": 50.0,
            "clean_claim_rate": 91.0,
            "net_collection_rate": 96.0,
            "first_pass_resolution_rate": 85.0,
            "cost_to_collect": 3.0,
            "bed_count": 400.0,
        }
        out = predict_missing_metrics(known, cohort, self.registry,
                                      coverage=0.90, seed=0)
        self.assertIn("denial_rate", out)
        pm = out["denial_rate"]
        self.assertIn(pm.method, (
            "ridge_regression", "knn", "weighted_median",
        ))
        self.assertGreaterEqual(pm.n_comparables_used, 15)
        self.assertGreater(pm.ci_high, pm.ci_low)
        self.assertGreater(pm.r_squared, 0.0)
        self.assertEqual(pm.coverage_target, 0.90)
        if pm.method == "ridge_regression":
            self.assertGreater(len(pm.feature_importances), 0)
        else:
            self.assertEqual(pm.feature_importances, {})

    def test_weighted_median_branch_used_in_middle_range(self):
        cohort = _synthetic_cohort(8, seed=3)
        # Hide enough known metrics that no Ridge features are usable.
        known = {"bed_count": 400.0}
        out = predict_missing_metrics(known, cohort, self.registry,
                                      coverage=0.90, seed=0)
        self.assertIn("denial_rate", out)
        pm = out["denial_rate"]
        self.assertEqual(pm.method, "weighted_median")
        self.assertGreaterEqual(pm.n_comparables_used, 5)
        self.assertLess(pm.n_comparables_used, 15)
        self.assertGreater(pm.ci_high, pm.ci_low)
        self.assertEqual(pm.r_squared, 0.0)

    def test_benchmark_fallback_when_no_comparables(self):
        out = predict_missing_metrics({}, [], self.registry,
                                      coverage=0.90, seed=0)
        self.assertIn("denial_rate", out)
        pm = out["denial_rate"]
        self.assertEqual(pm.method, "benchmark_fallback")
        self.assertEqual(pm.value, 5.2)        # P50
        self.assertEqual(pm.ci_low, 3.0)       # P25
        self.assertEqual(pm.ci_high, 9.8)      # P75
        self.assertEqual(pm.reliability_grade, "D")
        self.assertEqual(pm.n_comparables_used, 0)

    def test_benchmark_fallback_for_tiny_cohort(self):
        # 3 peers → below _MIN_FOR_MEDIAN=5, benchmark fallback kicks in.
        cohort = _synthetic_cohort(3, seed=2)
        out = predict_missing_metrics({}, cohort, self.registry,
                                      coverage=0.90, seed=0)
        pm = out["denial_rate"]
        self.assertEqual(pm.method, "benchmark_fallback")

    def test_already_observed_metric_is_skipped(self):
        cohort = _synthetic_cohort(20, seed=4)
        out = predict_missing_metrics(
            {"denial_rate": 7.5}, cohort, self.registry,
            coverage=0.90, seed=0,
        )
        self.assertNotIn("denial_rate", out)

    def test_dollar_valued_metrics_not_predicted(self):
        # Financial inputs should never be synthesized from comparables.
        registry = dict(self.registry)
        registry["net_revenue"] = {
            "display_name": "NPSR", "category": "financial",
            "unit": "dollars", "ebitda_sensitivity_rank": 31,
            "valid_range": (0.0, 1e12), "benchmark_p50": None,
        }
        cohort = _synthetic_cohort(20, seed=5)
        out = predict_missing_metrics({}, cohort, registry,
                                      coverage=0.90, seed=0)
        self.assertNotIn("net_revenue", out)

    def test_deterministic_with_seed(self):
        cohort = _synthetic_cohort(20, seed=5)
        known = {"days_in_ar": 50.0, "bed_count": 400.0,
                 "clean_claim_rate": 91.0}
        a = predict_missing_metrics(known, cohort, self.registry, seed=123)
        b = predict_missing_metrics(known, cohort, self.registry, seed=123)
        self.assertAlmostEqual(a["denial_rate"].value, b["denial_rate"].value)
        self.assertAlmostEqual(a["denial_rate"].ci_low, b["denial_rate"].ci_low)

    def test_accepts_packet_comparable_set(self):
        from rcm_mc.analysis.packet import ComparableHospital, ComparableSet
        raw = _synthetic_cohort(20, seed=6)
        cs = ComparableSet(peers=[
            ComparableHospital(
                id=r["ccn"], similarity_score=r["similarity_score"],
                fields={k: v for k, v in r.items()
                        if k not in ("ccn", "similarity_score")},
            ) for r in raw
        ])
        known = {"days_in_ar": 50.0, "bed_count": 400.0}
        out = predict_missing_metrics(known, cs, self.registry,
                                      coverage=0.90, seed=0)
        self.assertIn("denial_rate", out)


class TestReliabilityGrade(unittest.TestCase):
    def test_benchmark_is_d(self):
        self.assertEqual(_grade("benchmark_fallback", 0, 0.0), "D")

    def test_weighted_median_band(self):
        self.assertEqual(_grade("weighted_median", 10, 0.0), "B")
        self.assertEqual(_grade("weighted_median", 6, 0.0), "C")

    def test_ridge_thresholds(self):
        self.assertEqual(_grade("ridge_regression", 30, 0.62), "A")
        self.assertEqual(_grade("ridge_regression", 20, 0.50), "B")
        self.assertEqual(_grade("ridge_regression", 15, 0.30), "C")
        self.assertEqual(_grade("ridge_regression", 15, 0.10), "D")


# ── Packet integration ──────────────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):
    def test_to_packet_converts_fields(self):
        rp = RidgePredictedMetric(
            value=6.5, method="ridge_regression", ci_low=5.0, ci_high=8.0,
            coverage_target=0.90, n_comparables_used=22, r_squared=0.52,
            feature_importances={"days_in_ar": 1.0},
            reliability_grade="B",
        )
        pm = to_packet_predicted_metric(rp, upstream=["days_in_ar"])
        from rcm_mc.analysis.packet import PredictedMetric as PacketPM
        self.assertIsInstance(pm, PacketPM)
        self.assertEqual(pm.reliability_grade, "B")
        self.assertEqual(pm.coverage_target, 0.90)
        self.assertEqual(pm.provenance_chain, ["days_in_ar"])

    def test_packet_builder_step5_uses_ridge(self):
        import tempfile
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        from rcm_mc.portfolio.store import PortfolioStore
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            store = PortfolioStore(path)
            store.upsert_deal("t", name="T", profile={
                "bed_count": 400, "region": "midwest",
                "payer_mix": {"medicare": 0.4, "commercial": 0.4, "medicaid": 0.2},
            })
            pool = _synthetic_cohort(25, seed=10)
            packet = build_analysis_packet(
                store, "t", skip_simulation=True,
                observed_override={
                    "days_in_ar": __import__("rcm_mc.analysis.packet",
                                              fromlist=["ObservedMetric"]
                                              ).ObservedMetric(value=50.0),
                },
                comparables_pool=pool,
            )
            self.assertIn("denial_rate", packet.predicted_metrics)
            pm = packet.predicted_metrics["denial_rate"]
            # Should carry the new conformal fields from ridge_predictor.
            self.assertEqual(pm.coverage_target, 0.90)
            self.assertIn(pm.reliability_grade, ("A", "B", "C", "D"))
            self.assertGreater(pm.ci_high, pm.ci_low)
            self.assertIn(pm.method,
                          ("ridge_regression", "knn", "weighted_median",
                           "benchmark_fallback"))
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── Backtesting ─────────────────────────────────────────────────────

class TestBacktestPredictions(unittest.TestCase):
    def test_returns_empty_on_tiny_pool(self):
        result = backtest_predictions([], n_trials=5)
        self.assertEqual(result.overall_reliability, "F")
        self.assertEqual(result.n_trials, 0)

    def test_runs_and_populates_coverage(self):
        pool = _synthetic_cohort(35, seed=8)
        result = backtest_predictions(
            pool, holdout_fraction=0.3, n_trials=10,
            coverage=0.90, seed=99,
        )
        self.assertIsInstance(result, PredictionBacktestResult)
        self.assertEqual(result.n_trials, 10)
        # At least one metric should have been predicted and scored.
        self.assertGreater(len(result.coverage_rate), 0)
        for m, rate in result.coverage_rate.items():
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)

    def test_conformal_coverage_close_to_target(self):
        """Cohort-level coverage health: on a well-behaved synthetic
        cohort, the 90% conformal intervals should cover the truth
        50-100% of the time — tolerant of small-n noise but catches
        catastrophically miscalibrated intervals.
        """
        pool = _synthetic_cohort(40, seed=13)
        result = backtest_predictions(
            pool, holdout_fraction=0.3, n_trials=40,
            coverage=0.90, seed=7,
        )
        # Average coverage across metrics with enough samples.
        rates = [result.coverage_rate[m] for m in result.coverage_rate
                 if result.n_predictions.get(m, 0) >= 5]
        if rates:
            mean_coverage = float(np.mean(rates))
            self.assertGreater(mean_coverage, 0.50)
            self.assertLessEqual(mean_coverage, 1.0)

    def test_to_dict_roundtrip(self):
        pool = _synthetic_cohort(10, seed=2)
        result = backtest_predictions(pool, n_trials=3, seed=1)
        d = result.to_dict()
        self.assertIn("per_metric_mae", d)
        self.assertIn("per_metric_r_squared", d)
        self.assertIn("coverage_rate", d)
        self.assertIn("overall_reliability", d)


# ── Percentile interval ─────────────────────────────────────────────

class TestPercentileInterval(unittest.TestCase):
    def test_percentile_interval_returns_tuple(self):
        point, low, high = percentile_interval(3.0, 5.2, 9.8)
        self.assertEqual(point, 5.2)
        self.assertEqual(low, 3.0)
        self.assertEqual(high, 9.8)


# ── Ridge model sanity ─────────────────────────────────────────────

class TestRidgeModel(unittest.TestCase):
    def test_learns_linear_relationship(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(100, 2))
        y = X @ [2.0, -1.0] + rng.normal(0, 0.05, size=100)
        m = _RidgeModel(alpha=0.1).fit(X, y)
        pred = m.predict(np.asarray([[1.0, 1.0]]))
        self.assertAlmostEqual(float(pred[0]), 1.0, delta=0.2)

    def test_handles_single_feature(self):
        X = np.arange(10.0).reshape(-1, 1)
        y = 3.0 * X.squeeze() + 1.0
        m = _RidgeModel().fit(X, y)
        pred = m.predict(np.asarray([[5.0]]))
        self.assertAlmostEqual(float(pred[0]), 16.0, delta=1.0)

    def test_constant_column_does_not_crash(self):
        X = np.column_stack([np.zeros(10), np.arange(10.0)])
        y = np.arange(10.0) * 2.0
        m = _RidgeModel().fit(X, y)
        pred = m.predict(X)
        self.assertEqual(pred.shape, (10,))


# ── Train/cal split helper ─────────────────────────────────────────

class TestSplit(unittest.TestCase):
    def test_split_sizes(self):
        X = np.arange(100.0).reshape(-1, 1)
        y = X.squeeze()
        X_tr, y_tr, X_cal, y_cal = split_train_calibration(
            X, y, cal_fraction=0.3, random_state=0,
        )
        self.assertEqual(len(X_tr) + len(X_cal), 100)
        self.assertEqual(len(X_cal), 30)

    def test_split_handles_tiny_pool(self):
        X = np.asarray([[1.0], [2.0]])
        y = np.asarray([1.0, 2.0])
        X_tr, y_tr, X_cal, y_cal = split_train_calibration(X, y)
        self.assertEqual(len(X_tr) + len(X_cal), 2)
        self.assertGreaterEqual(len(X_tr), 1)


if __name__ == "__main__":
    unittest.main()
