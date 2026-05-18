"""Tests for Phase-4A k-fold cross-validation.

Pins:
  - CV folds split the data into k disjoint subsets, every row
    held out exactly once
  - The same seed produces the same fold assignment (deterministic;
    re-running shouldn't shuffle the partner-facing OOS numbers)
  - On a clean linear-with-noise dataset, mean test R² ≈ baseline
    in-sample R² (no overfit signal because there's nothing to
    overfit)
  - On an overfit-prone setup (n ~ p, lots of irrelevant features)
    mean test R² is much lower than baseline in-sample R²
  - Log-target propagates correctly to every fold
  - Edge cases: k < 2, too few rows for k folds, all-zero target
    + log mode
"""
import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.cross_validation import (
    CVResult,
    run_cv_regression,
)


def _clean_linear(n=400, seed=42):
    """y = 1 + 2*x1 - 0.5*x2 + noise(σ=0.5)."""
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = 1.0 + 2.0 * x1 - 0.5 * x2 + rng.normal(0, 0.5, n)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2})


class FoldSplitTests(unittest.TestCase):
    def test_folds_are_disjoint_and_cover_all_rows(self):
        df = _clean_linear(200)
        res = run_cv_regression(df, "y", ["x1", "x2"], k=5)
        # n_test summed across folds should equal n_total
        total_test = sum(f.n_test for f in res.folds)
        self.assertEqual(total_test, len(df))
        # Every fold's train + test should equal n_total
        for f in res.folds:
            self.assertEqual(f.n_train + f.n_test, len(df))

    def test_k_folds_produced(self):
        df = _clean_linear(200)
        res = run_cv_regression(df, "y", ["x1", "x2"], k=10)
        self.assertEqual(len(res.folds), 10)
        self.assertEqual(res.k, 10)


class DeterminismTests(unittest.TestCase):
    """Re-running CV with the same random_state must produce the
    same OOS numbers — partners shouldn't see the dashboard wiggle."""

    def test_same_seed_same_test_r2(self):
        df = _clean_linear(300, seed=7)
        a = run_cv_regression(df, "y", ["x1", "x2"], k=5,
                              random_state=99)
        b = run_cv_regression(df, "y", ["x1", "x2"], k=5,
                              random_state=99)
        self.assertEqual(
            [round(f.test_r_squared, 8) for f in a.folds],
            [round(f.test_r_squared, 8) for f in b.folds],
        )

    def test_different_seed_different_split(self):
        df = _clean_linear(300, seed=7)
        a = run_cv_regression(df, "y", ["x1", "x2"], k=5,
                              random_state=1)
        b = run_cv_regression(df, "y", ["x1", "x2"], k=5,
                              random_state=2)
        # Folds are different splits → numbers differ even if close
        self.assertNotEqual(
            [round(f.test_r_squared, 8) for f in a.folds],
            [round(f.test_r_squared, 8) for f in b.folds],
        )


class GeneralizationTests(unittest.TestCase):
    """The core contract: on a clean signal, OOS ≈ in-sample. On
    an overfit setup (many irrelevant features), OOS << in-sample.
    """

    def test_clean_signal_oos_near_in_sample(self):
        df = _clean_linear(500, seed=42)
        res = run_cv_regression(df, "y", ["x1", "x2"], k=5)
        # Mean OOS R² should be within 5pp of the in-sample baseline
        # — the model fits a true signal, no overfit
        gap = res.overfit_gap
        self.assertLess(
            abs(gap), 0.05,
            f"unexpected gap on clean signal: {gap}",
        )

    def test_overfit_setup_shows_gap(self):
        # ~200 rows, 20 irrelevant features — clears the min-rows-
        # per-fold guard but still wildly overfit (~7 obs per
        # parameter in each fold). In-sample R² will be high
        # because OLS finds spurious fits; OOS R² will be much
        # lower (often negative) because the spurious fits don't
        # generalize.
        rng = np.random.default_rng(13)
        n = 200
        p = 20
        X = rng.normal(0, 1, (n, p))
        y = rng.normal(0, 1, n)  # target is pure noise
        cols = [f"x{i}" for i in range(p)]
        df = pd.DataFrame(X, columns=cols)
        df["y"] = y
        res = run_cv_regression(df, "y", cols, k=4)
        # Overfit gap should be substantial — in-sample fits noise,
        # OOS doesn't generalize
        self.assertGreater(
            res.overfit_gap, 0.1,
            f"expected meaningful overfit gap, got {res.overfit_gap}",
        )


class LogTargetTests(unittest.TestCase):
    def test_log_transform_propagates_to_folds(self):
        rng = np.random.default_rng(42)
        n = 400
        x = rng.uniform(0, 10, n)
        y = np.exp(1.0 + 0.3 * x + rng.normal(0, 0.05, n))
        df = pd.DataFrame({"y": y, "x": x})
        res = run_cv_regression(df, "y", ["x"], k=5,
                                log_transform_target=True)
        self.assertTrue(res.target_was_log_transformed)
        # Log fit should recover near-perfect generalization on
        # an exp-linear DGP
        self.assertGreater(res.mean_test_r2, 0.95)

    def test_log_target_drops_nonpositive_rows(self):
        rng = np.random.default_rng(11)
        n = 400
        x = rng.uniform(0, 10, n)
        y = np.exp(1.0 + 0.3 * x + rng.normal(0, 0.05, n))
        # Inject 5 non-positive rows
        df = pd.DataFrame({"y": y, "x": x})
        df.loc[:4, "y"] = [-1.0, 0.0, -0.5, 0.0, -2.0]
        res = run_cv_regression(df, "y", ["x"], k=5,
                                log_transform_target=True)
        # 5 rows dropped → still fits cleanly on the 395 positives
        total_test = sum(f.n_test for f in res.folds)
        self.assertEqual(total_test, n - 5)


class EdgeCaseTests(unittest.TestCase):
    def test_k_less_than_2_raises(self):
        df = _clean_linear(100)
        with self.assertRaises(ValueError):
            run_cv_regression(df, "y", ["x1", "x2"], k=1)

    def test_too_few_rows_raises(self):
        # 10 rows for k=5 with 2 features needs at least ~40
        df = _clean_linear(10)
        with self.assertRaises(ValueError):
            run_cv_regression(df, "y", ["x1", "x2"], k=5)

    def test_all_zero_target_with_log_raises(self):
        df = pd.DataFrame({
            "y": [0.0] * 200,
            "x1": list(range(200)),
            "x2": list(range(200)),
        })
        with self.assertRaises(ValueError):
            run_cv_regression(df, "y", ["x1", "x2"], k=5,
                              log_transform_target=True)

    def test_missing_target_raises(self):
        df = _clean_linear(200)
        with self.assertRaises(ValueError):
            run_cv_regression(df, "missing_col", ["x1", "x2"], k=5)


class ResultStructureTests(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        df = _clean_linear(300)
        res = run_cv_regression(df, "y", ["x1", "x2"], k=4)
        d = res.to_dict()
        self.assertEqual(d["k"], 4)
        self.assertEqual(len(d["folds"]), 4)
        for key in ("mean_train_r2", "mean_test_r2", "std_test_r2",
                    "overfit_gap", "baseline_in_sample_r2"):
            self.assertIn(key, d)

    def test_overfit_gap_computed(self):
        df = _clean_linear(400)
        res = run_cv_regression(df, "y", ["x1", "x2"], k=5)
        self.assertAlmostEqual(
            res.overfit_gap,
            res.baseline_in_sample_r2 - res.mean_test_r2,
            places=8,
        )


if __name__ == "__main__":
    unittest.main()
