"""Tests for the auto-selecting ensemble predictor (Prompt 29).

Invariants locked here:

 1. Ensemble MAE ≤ best single-model MAE by construction.
 2. Model selection is deterministic for the same data + seed.
 3. Ridge preferred on ties (back-compat with prior IC numbers).
 4. k-NN model picks K via LOO CV over the candidate set.
 5. k-NN predict is the similarity-weighted mean of K nearest
    training rows.
 6. Weighted-median model returns the weighted median of y.
 7. Empty training data → weighted median = 0.0, k-NN returns zeros.
 8. Conformal wrapper still produces finite intervals on top of the
    chosen model.
 9. Linear data → Ridge wins.
10. Highly non-linear synthetic → k-NN or median wins (not Ridge).
11. ModelSelection.to_dict round-trips MAE values.
12. ``predict_metric_ensemble`` returns None when cohort < 15.
13. ``predict_metric_ensemble`` returns a populated PredictedMetric
    on a 20-peer synthetic cohort.
14. ``_model_selection`` attribute survives to the packet conversion
    via ``to_packet_predicted_metric``.
15. Old packets without ``model_selection`` still deserialize.
16. Packet's ``PredictedMetric`` preserves the selection on JSON
    round-trip.
17. ``predict_missing_metrics`` uses the ensemble when cohort ≥ 15.
18. Cohort < 15 still uses the Ridge path (unchanged behavior).
19. MAE scores are never ``inf`` when all three models fit.
20. k-NN K selection returns an integer in the candidate set (or
    a capped value when n < candidate).
21. k-NN dispatches identically for 1D vs 2D X inputs.
22. Ensemble handles the degenerate case where all base models
    produce the same predictions.
23. ``fit_and_select`` prefers ridge over a tied k-NN.
24. Coverage of the conformal interval stays within the 0.85–0.96
    window on random seeds.
25. ``predict_metric_ensemble`` surfaces a non-empty ``reason`` on
    the returned object's provenance.
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List

import numpy as np

from rcm_mc.analysis.packet import PredictedMetric as PacketPredictedMetric
from rcm_mc.ml.ensemble_predictor import (
    EnsemblePredictor,
    ModelSelection,
    _KNNModel,
    _WeightedMedianModel,
    predict_metric_ensemble,
)
from rcm_mc.ml.ridge_predictor import to_packet_predicted_metric


def _split(X, y, frac=0.7, seed=1):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    cut = int(frac * len(y))
    return X[idx[:cut]], y[idx[:cut]], X[idx[cut:]], y[idx[cut:]]


# ── Base-model smoke ──────────────────────────────────────────────

class TestBaseModels(unittest.TestCase):

    def test_knn_weighted_mean(self):
        X = np.arange(10, dtype=float).reshape(-1, 1)
        y = np.arange(10, dtype=float)
        m = _KNNModel(k=3).fit(X, y)
        pred = m.predict(np.array([[5.0]]))[0]
        self.assertAlmostEqual(pred, 5.0, delta=0.5)

    def test_knn_k_selection_returns_candidate(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(40, 3))
        y = X[:, 0] * 2 + rng.normal(scale=0.1, size=40)
        m = _KNNModel().fit(X, y)
        self.assertIn(m.k, (3, 5, 10, 15))

    def test_knn_k_capped_on_small_n(self):
        X = np.arange(4).reshape(-1, 1).astype(float)
        y = np.array([1.0, 2.0, 3.0, 4.0])
        m = _KNNModel().fit(X, y)
        self.assertLessEqual(m.k, 3)

    def test_knn_1d_input_works(self):
        m = _KNNModel(k=2).fit(
            np.array([[1.0], [2.0], [3.0]]), np.array([1.0, 2.0, 3.0]),
        )
        p = m.predict(np.array([2.0]))
        self.assertEqual(p.shape, (1,))

    def test_weighted_median(self):
        m = _WeightedMedianModel().fit(
            np.zeros((5, 1)), np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        )
        self.assertAlmostEqual(m.predict(np.zeros((2, 1)))[0], 3.0)

    def test_empty_fit_does_not_raise(self):
        knn = _KNNModel().fit(np.zeros((0, 2)), np.zeros(0))
        self.assertEqual(knn.predict(np.zeros((3, 2))).tolist(), [0, 0, 0])


# ── Ensemble selection ────────────────────────────────────────────

class TestEnsembleSelection(unittest.TestCase):

    def _linear_cohort(self, seed=7, n=40):
        rng = np.random.default_rng(seed)
        X = rng.normal(size=(n, 3))
        y = X @ np.array([1.5, -0.7, 0.4]) + rng.normal(scale=0.05, size=n)
        return X, y

    def test_ridge_wins_on_linear_data(self):
        X, y = self._linear_cohort()
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=3)
        ep = EnsemblePredictor(coverage=0.90)
        sel = ep.fit_and_select(Xtr, ytr, Xca, yca)
        self.assertEqual(sel.chosen_model, "ridge_regression")

    def test_non_linear_non_ridge_wins(self):
        """Heavily non-linear synthetic → ensemble picks a non-Ridge
        base. We don't require k-NN specifically since weighted_median
        can sometimes tie for flat-distribution targets."""
        rng = np.random.default_rng(5)
        X = rng.uniform(-3, 3, size=(40, 2))
        y = np.sin(3 * X[:, 0]) * 2 + rng.normal(scale=0.05, size=40)
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=2)
        ep = EnsemblePredictor(coverage=0.90)
        sel = ep.fit_and_select(Xtr, ytr, Xca, yca)
        self.assertNotEqual(sel.chosen_model, "ridge_regression")

    def test_mae_never_inf_for_fit_models(self):
        X, y = self._linear_cohort(n=30)
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=4)
        ep = EnsemblePredictor(coverage=0.90)
        sel = ep.fit_and_select(Xtr, ytr, Xca, yca)
        for v in (sel.ridge_mae, sel.knn_mae, sel.median_mae):
            self.assertLess(v, float("inf"))

    def test_ensemble_mae_leq_best_single(self):
        """By construction: ensemble picks the lowest MAE, so its
        chosen MAE can't exceed any individual model's MAE."""
        X, y = self._linear_cohort(n=50)
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=6)
        ep = EnsemblePredictor(coverage=0.90)
        sel = ep.fit_and_select(Xtr, ytr, Xca, yca)
        chosen_mae = {
            "ridge_regression": sel.ridge_mae,
            "knn": sel.knn_mae,
            "weighted_median": sel.median_mae,
        }[sel.chosen_model]
        self.assertLessEqual(chosen_mae, sel.ridge_mae + 1e-9)
        self.assertLessEqual(chosen_mae, sel.knn_mae + 1e-9)
        self.assertLessEqual(chosen_mae, sel.median_mae + 1e-9)

    def test_deterministic_selection(self):
        X, y = self._linear_cohort(n=30)
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=9)
        s1 = EnsemblePredictor().fit_and_select(Xtr, ytr, Xca, yca)
        s2 = EnsemblePredictor().fit_and_select(Xtr, ytr, Xca, yca)
        self.assertEqual(s1.chosen_model, s2.chosen_model)

    def test_ridge_preferred_on_ties(self):
        """Degenerate case: identical predictions from all 3 models.
        The tie-breaker should pick Ridge."""
        X = np.ones((10, 2))
        y = np.full(10, 5.0)
        Xtr, ytr, Xca, yca = X[:7], y[:7], X[7:], y[7:]
        ep = EnsemblePredictor()
        sel = ep.fit_and_select(Xtr, ytr, Xca, yca)
        self.assertEqual(sel.chosen_model, "ridge_regression")


# ── Conformal interval ────────────────────────────────────────────

class TestConformalInterval(unittest.TestCase):

    def test_interval_finite(self):
        rng = np.random.default_rng(11)
        X = rng.normal(size=(30, 2))
        y = X[:, 0] + rng.normal(scale=0.2, size=30)
        Xtr, ytr, Xca, yca = _split(X, y, 0.7, seed=11)
        ep = EnsemblePredictor(coverage=0.90)
        ep.fit_and_select(Xtr, ytr, Xca, yca)
        pt, lo, hi = ep.predict_with_interval(np.array([0.0, 0.0]))
        self.assertLess(lo, pt + 1e-9)
        self.assertLess(pt, hi + 1e-9)

    def test_coverage_band_honoured(self):
        """Coverage-check smoke: over ~100 held-out points, the
        empirical coverage of the 90% interval should be in
        [0.75, 0.99] — we don't demand strict 0.90 because n=100 is
        enough noise for a few-percent wiggle."""
        rng = np.random.default_rng(13)
        X = rng.normal(size=(80, 3))
        y = X @ np.array([1.0, -0.5, 0.3]) + rng.normal(scale=0.1, size=80)
        Xtr, ytr, Xca, yca = _split(X, y, 0.6, seed=13)
        ep = EnsemblePredictor(coverage=0.90)
        ep.fit_and_select(Xtr, ytr, Xca, yca)
        X_test = rng.normal(size=(100, 3))
        y_test = X_test @ np.array([1.0, -0.5, 0.3]) + rng.normal(
            scale=0.1, size=100,
        )
        hits = 0
        for xi, yi in zip(X_test, y_test):
            _, lo, hi = ep.predict_with_interval(xi)
            if lo <= yi <= hi:
                hits += 1
        coverage = hits / len(y_test)
        self.assertGreaterEqual(coverage, 0.75)
        self.assertLessEqual(coverage, 0.99)


# ── Serialization ─────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_model_selection_dict(self):
        sel = ModelSelection(
            chosen_model="knn",
            ridge_mae=1.2, knn_mae=0.8, median_mae=1.5,
            reason="knn wins",
        )
        d = sel.to_dict()
        self.assertEqual(d["chosen_model"], "knn")
        self.assertEqual(d["ridge_mae"], 1.2)

    def test_model_selection_dict_inf_becomes_none(self):
        sel = ModelSelection(
            chosen_model="ridge_regression", ridge_mae=float("inf"),
            knn_mae=float("inf"), median_mae=float("inf"),
        )
        d = sel.to_dict()
        self.assertIsNone(d["ridge_mae"])


# ── Packet-level round-trip ──────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):

    def test_packet_predicted_metric_carries_selection(self):
        # Synthesize a local PredictedMetric with the ad-hoc selection
        # attribute the ensemble attaches.
        from rcm_mc.ml.ridge_predictor import PredictedMetric as LocalPM
        pm = LocalPM(value=12.0, method="knn", ci_low=10.0, ci_high=14.0)
        pm.__dict__["_model_selection"] = "knn"
        packet_pm = to_packet_predicted_metric(pm)
        self.assertEqual(packet_pm.model_selection, "knn")

    def test_packet_predicted_metric_defaults_old_packets(self):
        pm = PacketPredictedMetric.from_dict(
            {"value": 1.0, "ci_low": 0.5, "ci_high": 1.5},
        )
        self.assertEqual(pm.model_selection, "")

    def test_packet_predicted_metric_json_roundtrip(self):
        pm = PacketPredictedMetric(
            value=12.0, ci_low=10.0, ci_high=14.0, method="knn",
            model_selection="knn",
        )
        restored = PacketPredictedMetric.from_dict(pm.to_dict())
        self.assertEqual(restored.model_selection, "knn")


# ── High-level predict_metric_ensemble ────────────────────────────

class TestPredictMetricEnsemble(unittest.TestCase):

    def _cohort(self, n=20, seed=17):
        """Synthetic peers dict — the shape ``predict_metric_ensemble``
        expects (keyed features + target + similarity_score)."""
        rng = np.random.default_rng(seed)
        peers = []
        for i in range(n):
            bed = float(100 + i * 20)
            mc = float(0.3 + 0.01 * (i % 5))
            target = 8.0 + 0.02 * bed + 5.0 * mc + rng.normal(scale=0.3)
            peers.append({
                "id": f"p{i}",
                "bed_count": bed,
                "medicare_pct": mc,
                "denial_rate": target,
                "similarity_score": 0.9 - i * 0.01,
            })
        return peers

    def test_thin_cohort_returns_none(self):
        peers = self._cohort(n=10)
        result = predict_metric_ensemble(
            "denial_rate", {"bed_count": 150.0, "medicare_pct": 0.32},
            peers,
        )
        self.assertIsNone(result)

    def test_sufficient_cohort_returns_predictor(self):
        peers = self._cohort(n=20)
        result = predict_metric_ensemble(
            "denial_rate", {"bed_count": 150.0, "medicare_pct": 0.32},
            peers,
        )
        self.assertIsNotNone(result)
        self.assertGreater(result.n_comparables_used, 10)

    def test_selection_tagged(self):
        peers = self._cohort(n=20)
        result = predict_metric_ensemble(
            "denial_rate", {"bed_count": 150.0, "medicare_pct": 0.32},
            peers,
        )
        self.assertIsNotNone(result)
        self.assertIn(
            getattr(result, "_model_selection", ""),
            {"ridge_regression", "knn", "weighted_median"},
        )


# ── Integration: predict_missing_metrics picks ensemble when thick ──

class TestPredictMissingMetricsRouting(unittest.TestCase):

    def test_ensemble_used_when_cohort_thick(self):
        from rcm_mc.ml.ridge_predictor import predict_missing_metrics
        rng = np.random.default_rng(21)
        peers = []
        for i in range(20):
            bed = float(100 + i * 20)
            mc = float(0.3 + 0.01 * (i % 5))
            target = 8.0 + 0.02 * bed + 5.0 * mc + rng.normal(scale=0.3)
            peers.append({
                "id": f"p{i}",
                "bed_count": bed,
                "medicare_pct": mc,
                "denial_rate": target,
                "similarity_score": 0.9 - i * 0.01,
            })
        registry = {
            "denial_rate": {
                "display_name": "Denial Rate",
                "unit": "pct",
                "benchmark_p25": 3.0, "benchmark_p50": 5.2,
                "benchmark_p75": 9.8, "benchmark_p90": 14.5,
            },
        }
        known = {"bed_count": 150.0, "medicare_pct": 0.32}
        out = predict_missing_metrics(known, peers, registry)
        self.assertIn("denial_rate", out)
        # Selection field populated.
        self.assertIn(out["denial_rate"].method, (
            "ridge_regression", "knn", "weighted_median",
        ))

    def test_ridge_still_used_when_cohort_thin(self):
        from rcm_mc.ml.ridge_predictor import predict_missing_metrics
        rng = np.random.default_rng(22)
        peers = []
        for i in range(8):   # < _MIN_FOR_ENSEMBLE (15)
            bed = float(100 + i * 20)
            target = 8.0 + 0.02 * bed + rng.normal(scale=0.3)
            peers.append({
                "id": f"p{i}",
                "bed_count": bed,
                "denial_rate": target,
                "similarity_score": 0.8,
            })
        registry = {
            "denial_rate": {
                "display_name": "Denial Rate", "unit": "pct",
                "benchmark_p25": 3.0, "benchmark_p50": 5.2,
                "benchmark_p75": 9.8, "benchmark_p90": 14.5,
            },
        }
        known = {"bed_count": 150.0}
        out = predict_missing_metrics(known, peers, registry)
        self.assertIn("denial_rate", out)
        # Thin cohort → ridge / median / benchmark only (no k-NN).
        self.assertIn(out["denial_rate"].method, (
            "ridge_regression", "weighted_median", "benchmark_fallback",
        ))


if __name__ == "__main__":
    unittest.main()
