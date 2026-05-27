"""Heteroskedasticity-robust joint F-test (HC1 Wald on the slopes).

The classical overall F assumes homoskedasticity; the regression page uses
robust SEs because hospital data usually isn't homoskedastic, so the headline
"is the model jointly significant?" needs a robust version too. Verified
behaviorally (no scipy): a real relationship under engineered heteroskedasticity
is flagged highly significant, and under a true null the test is roughly
calibrated (false-reject rate ≈ 0.05). Also checks the full HC1 covariance
matches the diagonal SEs and degenerate safety.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.regression import (
    hc1_robust_cov,
    hc1_robust_se,
    robust_joint_f_test,
)
from rcm_mc.ui.regression_page import _run_ols


def _fit(X, y):
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    return beta, y - X @ beta


class RobustCov(unittest.TestCase):
    def test_cov_diag_matches_robust_se(self):
        rng = np.random.default_rng(1)
        n = 500
        X = np.column_stack([np.ones(n), rng.normal(0, 1, n), rng.normal(2, 1, n)])
        y = X @ np.array([1.0, 2.0, -1.0]) + rng.normal(0, 1, n)
        _, resid = _fit(X, y)
        cov = hc1_robust_cov(X, resid)
        se = hc1_robust_se(X, resid)
        self.assertTrue(np.allclose(np.sqrt(np.clip(np.diag(cov), 0, None)), se))


class RobustJointF(unittest.TestCase):
    def test_real_relationship_under_heteroskedasticity_significant(self):
        rng = np.random.default_rng(2)
        n = 2000
        x1 = rng.uniform(1, 6, n)
        x2 = rng.normal(0, 1, n)
        sd = 0.3 + 1.0 * x1                      # heteroskedastic
        X = np.column_stack([np.ones(n), (x1 - x1.mean()) / x1.std(),
                             (x2 - x2.mean()) / x2.std()])
        y = 1.0 + 0.8 * x1 + 0.5 * x2 + rng.normal(0, 1, n) * sd
        beta, resid = _fit(X, y)
        r = robust_joint_f_test(X, beta, resid)
        self.assertTrue(r["significant"])
        self.assertLess(r["p_value"], 1e-6)
        self.assertEqual(r["df_model"], 2)

    def test_calibrated_under_null(self):
        # Under no real relationship the false-reject rate should sit near the
        # nominal 0.05 (binomial slack over 200 trials).
        n = 1500
        rej = 0
        trials = 200
        for s in range(trials):
            rng = np.random.default_rng(5000 + s)
            y = rng.normal(0, 1, n)
            Xr = rng.normal(0, 1, (n, 2))
            Xn = (Xr - Xr.mean(0)) / Xr.std(0)
            X = np.column_stack([np.ones(n), Xn])
            beta, resid = _fit(X, y)
            if robust_joint_f_test(X, beta, resid)["p_value"] < 0.05:
                rej += 1
        self.assertLess(rej / trials, 0.11, f"over-rejecting: {rej}/{trials}")

    def test_degenerate_safe(self):
        rng = np.random.default_rng(3)
        # intercept only (no slopes) → undefined
        X = np.ones((10, 1))
        beta, resid = _fit(X, rng.normal(0, 1, 10))
        self.assertIsNone(robust_joint_f_test(X, beta, resid)["significant"])


class RunOLSExposesRobustF(unittest.TestCase):
    def test_result_carries_robust_f(self):
        rng = np.random.default_rng(7)
        n = 300
        x = rng.normal(100, 20, n)
        df = pd.DataFrame({
            "beds": x,
            "operating_expenses": x * 1000 + rng.normal(0, 4000, n),
            "net_patient_revenue": x * 900 + rng.normal(0, 8000, n),
        })
        res = _run_ols(df, "net_patient_revenue", ["beds", "operating_expenses"])
        self.assertIsNotNone(res)
        self.assertIn("robust_f", res)
        rf = res["robust_f"]
        for key in ("f_stat", "p_value", "df_model", "df_resid", "significant"):
            self.assertIn(key, rf)
        self.assertTrue(rf["significant"])   # beds/opex strongly predict NPR


if __name__ == "__main__":
    unittest.main()
