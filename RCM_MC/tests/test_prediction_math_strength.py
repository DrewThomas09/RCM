"""Guardrail tests pinning the statistical strength of the prediction
stack. These are deliberately *property* tests (finite, bounded, covered,
recovers signal) rather than golden-value tests, so they stay stable
across data refreshes while still catching the two classes of bug we
hit in this rebuild:

  * OLS standard errors going NaN on collinear designs (regression page
    showed "not significant" for every coefficient) — fixed by the
    pseudo-inverse + non-negative variance clamp in finance/regression.py.
  * Leverage / Cook's distance blowing up (4.89e18) on near-singular
    hat matrices — fixed by pinv + clip in finance/influence.py.

Plus a distribution-free coverage check on the split-conformal layer:
the 90% interval must actually cover ~90% of held-out points, which is
the whole reliability promise of the ridge predictor.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


class RegressionStandardErrorTests(unittest.TestCase):
    """finance.regression must return finite SEs and surface real
    significance even when features are badly collinear."""

    def _collinear_frame(self, n: int = 300, seed: int = 0) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        x1 = rng.standard_normal(n)
        x2 = rng.standard_normal(n)
        # x3 is mechanically collinear (sums to a constant with x1/x2 —
        # the medicare/medicaid/commercial-day-% pathology) and x4 is a
        # near-duplicate of x1 (beds vs bed_days).
        x3 = 1.0 - x1 - x2
        x4 = x1 + rng.standard_normal(n) * 1e-3
        y = 2.0 * x1 - 1.0 * x2 + rng.standard_normal(n) * 0.5
        return pd.DataFrame({"y": y, "x1": x1, "x2": x2, "x3": x3, "x4": x4})

    def test_standard_errors_finite_under_collinearity(self):
        from rcm_mc.finance.regression import run_regression
        res = run_regression(self._collinear_frame(), "y")
        for c in res.coefficients:
            self.assertTrue(
                np.isfinite(c.std_error),
                f"std_error for {c.variable} is not finite ({c.std_error})",
            )
            self.assertGreaterEqual(c.std_error, 0.0)
            self.assertTrue(np.isfinite(c.t_statistic))
            self.assertTrue(np.isfinite(c.p_value))

    def test_real_signal_is_significant(self):
        # On a well-conditioned design the true drivers must come back
        # significant. (Under PERFECT collinearity the pinv min-norm
        # solution legitimately spreads the coefficient across the
        # collinear twins and individual significance can vanish — that's
        # correct, so significance is asserted on independent features;
        # finiteness is what we assert on the collinear frame above.)
        from rcm_mc.finance.regression import run_regression
        rng = np.random.default_rng(1)
        n = 300
        x1 = rng.standard_normal(n)
        x2 = rng.standard_normal(n)
        x3 = rng.standard_normal(n)  # independent noise feature
        y = 2.0 * x1 - 1.0 * x2 + rng.standard_normal(n) * 0.5
        df = pd.DataFrame({"y": y, "x1": x1, "x2": x2, "x3": x3})
        res = run_regression(df, "y")
        self.assertGreaterEqual(
            sum(1 for c in res.coefficients if c.significant), 1,
            "no coefficient significant — SE math likely regressed to NaN",
        )
        self.assertGreater(res.r_squared, 0.5)


class InfluenceLeverageTests(unittest.TestCase):
    """finance.influence leverage must stay in [0, 1] and Cook's D must
    not explode on collinear designs."""

    def test_leverage_bounded_and_cooks_sane(self):
        from rcm_mc.finance.influence import compute_influence
        rng = np.random.default_rng(3)
        n = 200
        x1 = rng.standard_normal(n)
        x2 = x1 + rng.standard_normal(n) * 1e-3  # near-duplicate
        X = np.column_stack([x1, x2])
        y = 1.5 * x1 + rng.standard_normal(n) * 0.4
        beta = np.linalg.lstsq(np.column_stack([np.ones(n), X]), y, rcond=None)[0]
        y_hat = np.column_stack([np.ones(n), X]) @ beta
        lev, stud, cooks = compute_influence(X, y, y_hat)
        finite_lev = lev[~np.isnan(lev)]
        self.assertTrue(np.all(finite_lev >= -1e-9))
        self.assertTrue(np.all(finite_lev <= 1.0 + 1e-9))
        finite_cooks = cooks[~np.isnan(cooks)]
        # No 18-digit blow-ups — Cook's D for a clean fit stays modest.
        self.assertTrue(np.all(finite_cooks < 1e6))


class ConformalCoverageTests(unittest.TestCase):
    """The split-conformal 90% interval must empirically cover ~90% of
    held-out points across noise regimes — the reliability promise."""

    def _coverage(self, noise: float, seed: int) -> float:
        from rcm_mc.ml.ridge_predictor import _RidgeModel, _loo_select_alpha
        from rcm_mc.ml.conformal import (
            ConformalPredictor, split_train_calibration,
        )
        rng = np.random.default_rng(seed)
        n, p = 320, 6
        X = rng.standard_normal((n, p))
        beta = rng.standard_normal(p)
        y = X @ beta + noise * rng.standard_normal(n)
        ntr = int(n * 0.8)
        Xtr_all, Xte = X[:ntr], X[ntr:]
        ytr_all, yte = y[:ntr], y[ntr:]
        Xtr, ytr, Xcal, ycal = split_train_calibration(
            Xtr_all, ytr_all, cal_fraction=0.4, random_state=seed,
        )
        alpha, _ = _loo_select_alpha(Xtr, ytr)
        cp = ConformalPredictor(base_model=_RidgeModel(alpha=alpha), coverage=0.90)
        cp.fit(Xtr, ytr, Xcal, ycal)
        covered = 0
        for i in range(len(Xte)):
            _, lo, hi = cp.predict_interval(Xte[i:i + 1])
            if lo <= yte[i] <= hi:
                covered += 1
        return covered / len(Xte)

    def test_mean_coverage_near_target(self):
        covs = [self._coverage(nz, seed)
                for nz in (0.3, 1.0, 2.0) for seed in range(12)]
        mean_cov = float(np.mean(covs))
        # Split conformal guarantees >= 90% in expectation; allow a small
        # finite-sample band around the nominal 0.90.
        self.assertGreaterEqual(mean_cov, 0.85, f"under-covers: {mean_cov:.3f}")
        self.assertLessEqual(mean_cov, 0.97, f"wildly over-covers: {mean_cov:.3f}")


class RidgeSignalRecoveryTests(unittest.TestCase):
    """LOO-tuned ridge must recover a real linear signal out-of-sample
    even with noise features and collinearity present."""

    def test_out_of_sample_r2_positive(self):
        from rcm_mc.ml.ridge_predictor import _RidgeModel, _loo_select_alpha
        rng = np.random.default_rng(11)
        r2s = []
        for _ in range(10):
            n, p = 160, 8
            X = rng.standard_normal((n, p))
            X[:, 2] = 0.9 * X[:, 0] + 0.1 * X[:, 2]  # collinear
            beta = rng.standard_normal(p)
            beta[p // 2:] = 0.0  # half are pure noise features
            y = X @ beta + rng.standard_normal(n)
            ntr = int(n * 0.7)
            alpha, _ = _loo_select_alpha(X[:ntr], y[:ntr])
            m = _RidgeModel(alpha=alpha).fit(X[:ntr], y[:ntr])
            yp = m.predict(X[ntr:])
            yte = y[ntr:]
            ss_res = float(np.sum((yte - yp) ** 2))
            ss_tot = float(np.sum((yte - yte.mean()) ** 2))
            r2s.append(1.0 - ss_res / ss_tot)
        self.assertGreater(float(np.mean(r2s)), 0.3)


if __name__ == "__main__":
    unittest.main()
