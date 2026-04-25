"""Tests for trained RCM-KPI predictors (Ridge + k-fold CV)."""
from __future__ import annotations

import unittest

import numpy as np


def _synth_dataset(
    n: int = 200,
    n_features: int = 5,
    seed: int = 7,
    noise_std: float = 0.02,
):
    """Synthesize (X, y, true_beta) from a known linear model."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_features))
    true_beta = np.array([0.05, -0.03, 0.02, -0.04, 0.01])
    intercept = 0.10
    noise = rng.normal(0, noise_std, size=n)
    y = X @ true_beta + intercept + noise
    return X, y, true_beta


class TestRidgeFitAndCV(unittest.TestCase):
    def test_recovers_signal_on_clean_data(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=300, noise_std=0.005)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        # On clean low-noise data, R² should be high
        self.assertGreater(p.cv_r2_mean, 0.85)
        self.assertGreater(p.train_r2, 0.85)
        self.assertEqual(p.n_train, 300)

    def test_train_r2_higher_than_cv_r2(self):
        """Sanity: training R² ≥ CV R² (CV is honest)."""
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200, noise_std=0.05)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        self.assertGreaterEqual(
            p.train_r2 + 1e-6, p.cv_r2_mean)

    def test_deterministic_under_same_seed(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200)
        names = [f"f{i}" for i in range(X.shape[1])]
        p1 = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="x", seed=99)
        p2 = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="x", seed=99)
        np.testing.assert_array_almost_equal(
            p1.coefficients, p2.coefficients)
        self.assertAlmostEqual(p1.cv_r2_mean, p2.cv_r2_mean)

    def test_too_few_rows_rejected(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X = np.random.normal(0, 1, size=(8, 3))
        y = np.random.normal(0, 1, size=8)
        with self.assertRaises(ValueError):
            train_ridge_with_cv(
                X, y, feature_names=["a", "b", "c"],
                target_metric="x", n_folds=5)

    def test_dimension_mismatch_rejected(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X = np.random.normal(0, 1, size=(50, 4))
        y = np.random.normal(0, 1, size=50)
        with self.assertRaises(ValueError):
            train_ridge_with_cv(
                X, y, feature_names=["a", "b"],
                target_metric="x")

    def test_nan_rows_dropped(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200)
        # Inject NaNs in 30 rows
        X[:30, 0] = np.nan
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        self.assertEqual(p.n_train, 170)


class TestPredictAndExplain(unittest.TestCase):
    def test_predict_and_predict_one(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200, noise_std=0.005)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        # predict() on the matrix
        yhat = p.predict(X)
        self.assertEqual(yhat.shape, (200,))
        # predict_one matches predict
        feature_dict = {n: float(X[0, i])
                        for i, n in enumerate(names)}
        single = p.predict_one(feature_dict)
        self.assertAlmostEqual(single, float(yhat[0]),
                               places=5)

    def test_interval_contains_truth_majority(self):
        """90% conformal interval should cover ≥80% of held-out
        truth on synthesized data."""
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=400, noise_std=0.02)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        rng = np.random.default_rng(101)
        held_out_X, held_out_y, _ = _synth_dataset(
            n=200, seed=999, noise_std=0.02)
        covered = 0
        for i in range(held_out_X.shape[0]):
            fd = {n: float(held_out_X[i, j])
                  for j, n in enumerate(names)}
            yhat, (lo, hi) = p.predict_with_interval(fd)
            if lo <= held_out_y[i] <= hi:
                covered += 1
        self.assertGreaterEqual(
            covered / held_out_X.shape[0], 0.80)

    def test_explain_sums_close_to_residual(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic")
        feature_dict = {n: float(X[10, i])
                        for i, n in enumerate(names)}
        yhat = p.predict_one(feature_dict)
        contributions = p.explain(feature_dict)
        # contributions sum should equal yhat - target_mean
        # (intercept = target_mean for centered y)
        total_contrib = sum(c for _, c in contributions)
        self.assertAlmostEqual(
            total_contrib, yhat - p.target_mean, places=5)
        # Sorted by abs contribution descending
        absvals = [abs(c) for _, c in contributions]
        self.assertEqual(absvals,
                         sorted(absvals, reverse=True))

    def test_sanity_range_clipping(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X, y, _ = _synth_dataset(n=200)
        names = [f"f{i}" for i in range(X.shape[1])]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="synthetic",
            sanity_range=(0.05, 0.15))
        # Push features way out of training distribution
        out_of_range = {n: 100.0 for n in names}
        yhat = p.predict_one(out_of_range)
        self.assertGreaterEqual(yhat, 0.05)
        self.assertLessEqual(yhat, 0.15)


class TestDenialRatePredictor(unittest.TestCase):
    def test_train_on_synthesized_hospitals(self):
        from rcm_mc.ml.denial_rate_predictor import (
            DENIAL_RATE_FEATURES,
            train_denial_rate_predictor,
        )
        rng = np.random.default_rng(42)
        rows = []
        for _ in range(150):
            beds = float(rng.integers(50, 800))
            mc = float(rng.uniform(0.20, 0.65))
            md = float(rng.uniform(0.05, 0.35))
            n2g = float(rng.uniform(0.20, 0.45))
            occ = float(rng.uniform(0.45, 0.85))
            margin = float(rng.normal(0.04, 0.08))
            star = float(rng.uniform(2.0, 5.0))
            # Latent denial rate driven by payer mix + n2g + star
            true_dr = (
                0.12 + 0.10 * md + 0.05 * mc - 0.08 * n2g
                - 0.02 * (star - 3.0) + rng.normal(0, 0.015)
            )
            true_dr = max(0.02, min(0.30, true_dr))
            rows.append({
                "beds": beds,
                "medicare_day_pct": mc,
                "medicaid_day_pct": md,
                "net_patient_revenue": beds * 4 * 50_000 * n2g,
                "gross_patient_revenue": beds * 4 * 50_000,
                "operating_expenses": (
                    beds * 4 * 50_000 * n2g * (1 - margin)),
                "total_patient_days": beds * 365 * occ,
                "bed_days_available": beds * 365,
                "discharges": beds * 4,
                "star_rating": star,
                "denial_rate": true_dr,
            })
        p = train_denial_rate_predictor(rows)
        self.assertEqual(
            p.feature_names, DENIAL_RATE_FEATURES)
        self.assertEqual(p.target_metric, "denial_rate")
        # Should learn meaningful structure on this signal
        self.assertGreater(p.cv_r2_mean, 0.40)
        # Sanity range clipped
        self.assertEqual(p.sanity_range, (0.0, 0.40))

    def test_predict_returns_explanation(self):
        from rcm_mc.ml.denial_rate_predictor import (
            train_denial_rate_predictor,
            predict_denial_rate,
        )
        rng = np.random.default_rng(1)
        rows = []
        for _ in range(100):
            md = float(rng.uniform(0.05, 0.35))
            beds = float(rng.integers(50, 600))
            true_dr = max(
                0.02, 0.10 + 0.10 * md
                + rng.normal(0, 0.01))
            rows.append({
                "beds": beds, "medicaid_day_pct": md,
                "denial_rate": true_dr,
            })
        p = train_denial_rate_predictor(rows)

        yhat, (lo, hi), expl = predict_denial_rate(p, {
            "beds": 200, "medicaid_day_pct": 0.30,
        })
        self.assertGreater(yhat, 0)
        self.assertLess(yhat, 0.40)
        self.assertLessEqual(lo, yhat)
        self.assertLessEqual(yhat, hi)
        # explain returns (name, contribution) tuples sorted
        # by |contribution| descending
        self.assertGreater(len(expl), 0)
        absvals = [abs(c) for _, c in expl]
        self.assertEqual(absvals,
                         sorted(absvals, reverse=True))

    def test_empty_training_rejected(self):
        from rcm_mc.ml.denial_rate_predictor import (
            train_denial_rate_predictor,
        )
        with self.assertRaises(ValueError):
            train_denial_rate_predictor([])

    def test_missing_features_use_defaults(self):
        from rcm_mc.ml.denial_rate_predictor import (
            build_denial_features, DENIAL_RATE_FEATURES,
        )
        # Empty dict — every feature must come from defaults
        f = build_denial_features({})
        for n in DENIAL_RATE_FEATURES:
            self.assertIn(n, f)
            self.assertIsInstance(f[n], float)


if __name__ == "__main__":
    unittest.main()
