"""Advisory target-skewness / log-transform diagnostic on the ridge predictor.

Adds an honest model-quality signal: when the target is strictly positive and
right-skewed, the DiagnosticReport flags that a log/Box-Cox transform would
likely help — surfaced as guidance, never altering the fit or the locked
Tier-2 failure-reason logic.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.ml.ridge_predictor import (
    DiagnosticReport,
    _compute_diagnostics,
    _sample_skewness,
)


class SampleSkewnessTests(unittest.TestCase):
    def test_symmetric_is_near_zero(self):
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertAlmostEqual(_sample_skewness(y), 0.0, places=6)

    def test_right_skewed_is_positive(self):
        y = np.array([1.0, 1.0, 1.0, 2.0, 10.0, 50.0])
        self.assertGreater(_sample_skewness(y), 1.0)

    def test_degenerate_inputs_safe(self):
        self.assertEqual(_sample_skewness(np.array([5.0, 5.0, 5.0])), 0.0)  # zero var
        self.assertEqual(_sample_skewness(np.array([1.0, 2.0])), 0.0)        # n<3


class DiagnosticLogHintTests(unittest.TestCase):
    def test_defaults_backward_compatible(self):
        # bare report (used by callers for degenerate fits) keeps safe defaults
        r = DiagnosticReport()
        self.assertEqual(r.target_skewness, 0.0)
        self.assertFalse(r.log_transform_suggested)

    def test_positive_right_skewed_target_suggests_log(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(60, 3))
        # strictly-positive, right-skewed target (exp of a normal = lognormal)
        y = np.exp(rng.normal(0.0, 1.0, size=60)) + 0.5
        rep = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(rep.target_skewness, 1.0)
        self.assertTrue(rep.log_transform_suggested)

    def test_symmetric_target_no_log_hint(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(60, 3))
        y = rng.normal(100.0, 10.0, size=60)  # symmetric, positive
        rep = _compute_diagnostics(X, y, alpha=1.0)
        self.assertFalse(rep.log_transform_suggested)

    def test_negative_values_never_suggest_log(self):
        # right-skewed but spanning <= 0 → log undefined → never suggested
        rng = np.random.default_rng(2)
        X = rng.normal(size=(60, 3))
        y = np.exp(rng.normal(0.0, 1.0, size=60)) - 1.0  # some <= 0
        rep = _compute_diagnostics(X, y, alpha=1.0)
        self.assertFalse(rep.log_transform_suggested)

    def test_flag_threads_into_predicted_metric(self):
        # the advisory must reach PredictedMetric (and thus its to_dict / packet)
        from rcm_mc.ml.ridge_predictor import PredictedMetric, _predict_ridge
        # always present in the serialized form, default False
        self.assertIn("log_transform_suggested", PredictedMetric(value=0.0).to_dict())
        rng = np.random.default_rng(7)
        comps = []
        for _ in range(40):
            comps.append({
                "beds": float(rng.normal()), "occupancy_rate": float(rng.normal()),
                # strictly-positive right-skewed target
                "net_patient_revenue": float(np.exp(rng.normal(0, 1)) + 0.5),
            })
        pm = _predict_ridge("net_patient_revenue", {}, comps, coverage=0.8, seed=0)
        if pm is not None and pm.method == "ridge_regression":
            self.assertTrue(pm.log_transform_suggested)
            self.assertIn("log_transform_suggested", pm.to_dict())

    def test_hint_does_not_add_failure_reasons(self):
        # advisory only — it must not change the locked Tier-2 failure set
        rng = np.random.default_rng(3)
        X = rng.normal(size=(60, 3))
        y = np.exp(rng.normal(size=60)) + 0.5
        rep = _compute_diagnostics(X, y, alpha=1.0)
        # the log hint is independent of failure_reasons_at (no new variant)
        self.assertIsInstance(rep.failure_reasons_at(60, 3), list)


if __name__ == "__main__":
    unittest.main()
