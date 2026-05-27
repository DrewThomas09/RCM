"""Correctness tests for HC1 robust SEs + the Breusch–Pagan test.

No scipy/statsmodels available, so we verify the math BEHAVIORALLY against
data with known properties (the only honest way to confirm a statistic is
right): under homoskedasticity robust ≈ classical and BP doesn't fire; under
engineered heteroskedasticity robust diverges and BP fires.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.finance.regression import (
    breusch_pagan_test,
    f_pvalue,
    hc1_robust_se,
)


def _classical_se(X, resid):
    n, kp1 = X.shape
    mse = float(np.sum(resid ** 2)) / (n - kp1)
    return np.sqrt(np.clip(np.diag(mse * np.linalg.pinv(X.T @ X)), 0.0, None))


def _fit(X, y):
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    return beta, y - X @ beta


class HC1RobustSE(unittest.TestCase):
    def test_shape_finite_nonnegative(self):
        rng = np.random.default_rng(1)
        n = 200
        X = np.column_stack([np.ones(n), rng.normal(0, 1, n), rng.normal(5, 2, n)])
        y = X @ np.array([1.0, 2.0, -1.0]) + rng.normal(0, 1, n)
        _, resid = _fit(X, y)
        se = hc1_robust_se(X, resid)
        self.assertEqual(se.shape, (3,))
        self.assertTrue(np.all(np.isfinite(se)))
        self.assertTrue(np.all(se >= 0))

    def test_robust_approx_classical_under_homoskedasticity(self):
        # Constant-variance errors → HC1 should track classical SEs closely.
        rng = np.random.default_rng(2)
        n = 4000
        x1 = rng.normal(0, 1, n)
        X = np.column_stack([np.ones(n), x1])
        y = 1.0 + 2.0 * x1 + rng.normal(0, 1.0, n)   # homoskedastic
        _, resid = _fit(X, y)
        robust = hc1_robust_se(X, resid)
        classical = _classical_se(X, resid)
        ratio = robust[1] / classical[1]
        self.assertTrue(0.85 < ratio < 1.18, f"ratio={ratio}")

    def test_robust_diverges_under_heteroskedasticity(self):
        # Error SD grows with |x| → classical understates the slope SE; HC1
        # should be materially larger (the whole point of robust SEs).
        rng = np.random.default_rng(3)
        n = 4000
        x1 = rng.normal(0, 1, n)
        sd = 0.5 + 2.0 * np.abs(x1)                   # variance depends on x
        X = np.column_stack([np.ones(n), x1])
        y = 1.0 + 2.0 * x1 + rng.normal(0, 1, n) * sd
        _, resid = _fit(X, y)
        robust = hc1_robust_se(X, resid)
        classical = _classical_se(X, resid)
        self.assertGreater(robust[1] / classical[1], 1.25,
                           "HC1 should exceed classical under heteroskedasticity")


class BreuschPagan(unittest.TestCase):
    def test_not_detected_under_homoskedasticity(self):
        rng = np.random.default_rng(4)
        n = 3000
        x1 = rng.normal(0, 1, n)
        X = np.column_stack([np.ones(n), x1])
        y = 1.0 + 2.0 * x1 + rng.normal(0, 1, n)
        _, resid = _fit(X, y)
        bp = breusch_pagan_test(X, resid)
        self.assertFalse(bp["heteroskedastic"], f"false positive: p={bp['p_value']}")
        self.assertGreater(bp["p_value"], 0.05)

    def test_detected_under_heteroskedasticity(self):
        # Variance MONOTONIC in a positive regressor — the form BP is built to
        # catch (it tests for variance that is linear in the regressors; a
        # symmetric variance ∝ x² is BP's known blind spot, so we don't test
        # that here).
        rng = np.random.default_rng(5)
        n = 3000
        x1 = rng.uniform(1.0, 6.0, n)               # strictly positive
        sd = 0.3 + 1.0 * x1                          # SD rises monotonically
        X = np.column_stack([np.ones(n), x1])
        y = 1.0 + 2.0 * x1 + rng.normal(0, 1, n) * sd
        _, resid = _fit(X, y)
        bp = breusch_pagan_test(X, resid)
        self.assertTrue(bp["heteroskedastic"], f"missed: p={bp['p_value']}")
        self.assertLess(bp["p_value"], 0.01)

    def test_degenerate_inputs_are_safe(self):
        rng = np.random.default_rng(6)
        X = np.column_stack([np.ones(5), rng.normal(0, 1, 5)])
        bp = breusch_pagan_test(X, np.zeros(5))   # perfect fit / no residual var
        self.assertIn(bp["heteroskedastic"], (False, None))
        self.assertEqual(f_pvalue(0.0, 1, 3), 1.0)


if __name__ == "__main__":
    unittest.main()
