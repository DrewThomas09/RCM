"""Tests for ensemble methods (bag / blend / stack)."""
from __future__ import annotations

import unittest

import numpy as np


def _synth(n=200, n_feat=5, noise=0.05, seed=7):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_feat))
    beta = np.array([0.5, -0.3, 0.2, -0.4, 0.1])[:n_feat]
    y = X @ beta + 0.5 + rng.normal(0, noise, n)
    return X, y


class TestBagging(unittest.TestCase):
    def test_bagging_runs(self):
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X, y = _synth(n=200)
        names = [f"f{i}" for i in range(5)]
        bagged = bag_train_predictor(
            X, y,
            feature_names=names,
            target_metric="synthetic",
            n_bags=10)
        self.assertEqual(bagged.bag_count, 10)
        self.assertEqual(bagged.target_metric, "synthetic")

    def test_predict_one_matches_predict(self):
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X, y = _synth(n=150)
        names = [f"f{i}" for i in range(5)]
        bagged = bag_train_predictor(
            X, y, feature_names=names,
            target_metric="x", n_bags=5)
        # Build feature dict from row 0
        feature_dict = {n: float(X[0, i])
                        for i, n in enumerate(names)}
        single = bagged.predict_one(feature_dict)
        batch = float(bagged.predict(X[0:1])[0])
        self.assertAlmostEqual(single, batch, places=5)

    def test_interval_uses_inter_bag_variance(self):
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X, y = _synth(n=200, noise=0.10)
        names = [f"f{i}" for i in range(5)]
        bagged = bag_train_predictor(
            X, y, feature_names=names,
            target_metric="x", n_bags=15)
        feature_dict = {n: float(X[0, i])
                        for i, n in enumerate(names)}
        yhat, (lo, hi) = bagged.predict_with_interval(
            feature_dict)
        self.assertLess(lo, yhat)
        self.assertLess(yhat, hi)

    def test_too_few_rows_rejected(self):
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X = np.random.normal(0, 1, size=(5, 3))
        y = np.random.normal(0, 1, size=5)
        with self.assertRaises(ValueError):
            bag_train_predictor(
                X, y, feature_names=["a", "b", "c"],
                target_metric="x")

    def test_sanity_range_clipped(self):
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X, y = _synth(n=150)
        names = [f"f{i}" for i in range(5)]
        bagged = bag_train_predictor(
            X, y, feature_names=names,
            target_metric="x", n_bags=5,
            sanity_range=(0.4, 0.6))
        # Push features way out of distribution
        out = {n: 100.0 for n in names}
        yhat = bagged.predict_one(out)
        self.assertGreaterEqual(yhat, 0.4)
        self.assertLessEqual(yhat, 0.6)


class TestSimplexProjection(unittest.TestCase):
    def test_already_on_simplex(self):
        from rcm_mc.ml.ensemble_methods import (
            _project_simplex,
        )
        v = np.array([0.4, 0.3, 0.3])
        result = _project_simplex(v)
        np.testing.assert_array_almost_equal(result, v)

    def test_negative_clamped(self):
        from rcm_mc.ml.ensemble_methods import (
            _project_simplex,
        )
        v = np.array([0.6, -0.1, 0.5])
        result = _project_simplex(v)
        # All ≥ 0
        self.assertTrue(np.all(result >= 0))
        # Sums to 1
        self.assertAlmostEqual(float(result.sum()), 1.0)


class TestBlending(unittest.TestCase):
    def test_blend_finds_good_weights(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.ensemble_methods import (
            blend_predictors,
        )
        X, y = _synth(n=300)
        names = [f"f{i}" for i in range(5)]
        # Train 3 base models on different alphas → mild variation
        base_a = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x", alpha=0.1)
        base_b = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x", alpha=1.0)
        base_c = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x", alpha=10.0)
        blended = blend_predictors(
            [base_a, base_b, base_c],
            X[200:], y[200:],
            target_metric="x",
            feature_names=names)
        # Weights sum to 1, all ≥ 0
        self.assertAlmostEqual(
            float(blended.weights.sum()), 1.0, places=4)
        self.assertTrue(np.all(blended.weights >= -1e-6))
        # Should achieve reasonable R² on the holdout
        self.assertGreater(blended.blend_cv_r2, 0.5)

    def test_blend_predict_one(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.ensemble_methods import (
            blend_predictors,
        )
        X, y = _synth(n=300)
        names = [f"f{i}" for i in range(5)]
        base = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x")
        blended = blend_predictors(
            [base],
            X[200:], y[200:],
            target_metric="x", feature_names=names)
        # Single base → weight=1
        self.assertAlmostEqual(
            float(blended.weights[0]), 1.0, places=4)
        single = blended.predict_one(
            {n: float(X[0, i])
             for i, n in enumerate(names)})
        self.assertIsInstance(single, float)

    def test_empty_base_models_rejected(self):
        from rcm_mc.ml.ensemble_methods import (
            blend_predictors,
        )
        X, y = _synth(n=100)
        with self.assertRaises(ValueError):
            blend_predictors(
                [], X, y, target_metric="x",
                feature_names=["a"])


class TestStacking(unittest.TestCase):
    def test_stack_runs(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.ensemble_methods import (
            stack_predictors,
        )
        X, y = _synth(n=300)
        names = [f"f{i}" for i in range(5)]
        base_a = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x", alpha=0.1)
        base_b = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x", alpha=1.0)
        stacked = stack_predictors(
            [base_a, base_b],
            X[200:], y[200:],
            target_metric="x", feature_names=names)
        self.assertEqual(
            len(stacked.meta_coefficients), 2)
        self.assertGreater(stacked.stack_cv_r2, 0.5)

    def test_stack_too_few_rows_rejected(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.ensemble_methods import (
            stack_predictors,
        )
        X, y = _synth(n=300)
        names = [f"f{i}" for i in range(5)]
        base = train_ridge_with_cv(
            X[:200], y[:200], feature_names=names,
            target_metric="x")
        with self.assertRaises(ValueError):
            stack_predictors(
                [base], X[:5], y[:5],
                target_metric="x",
                feature_names=names)


class TestStrategyRecommender(unittest.TestCase):
    def test_recommends_bagging_for_weak_model(self):
        from rcm_mc.ml.ensemble_methods import (
            recommend_ensemble_strategy,
        )
        rec = recommend_ensemble_strategy(
            single_model_r2=0.30,
            single_model_r2_std=0.05)
        self.assertEqual(rec.strategy, "bagging")

    def test_recommends_bagging_for_unstable_model(self):
        from rcm_mc.ml.ensemble_methods import (
            recommend_ensemble_strategy,
        )
        rec = recommend_ensemble_strategy(
            single_model_r2=0.55,
            single_model_r2_std=0.15)
        self.assertEqual(rec.strategy, "bagging")

    def test_recommends_blending_for_two_models(self):
        from rcm_mc.ml.ensemble_methods import (
            recommend_ensemble_strategy,
        )
        rec = recommend_ensemble_strategy(
            single_model_r2=0.50,
            single_model_r2_std=0.05,
            n_complementary_models=2)
        self.assertEqual(rec.strategy, "blending")

    def test_recommends_stacking_for_three_models(self):
        from rcm_mc.ml.ensemble_methods import (
            recommend_ensemble_strategy,
        )
        rec = recommend_ensemble_strategy(
            single_model_r2=0.65,
            single_model_r2_std=0.05,
            n_complementary_models=3)
        self.assertEqual(rec.strategy, "stacking")

    def test_no_ensemble_for_strong_single_model(self):
        from rcm_mc.ml.ensemble_methods import (
            recommend_ensemble_strategy,
        )
        rec = recommend_ensemble_strategy(
            single_model_r2=0.85,
            single_model_r2_std=0.03,
            n_complementary_models=1)
        self.assertEqual(rec.strategy, "no_ensemble")
        self.assertEqual(rec.expected_lift_r2, 0.0)


class TestBaggingLiftsWeakModel(unittest.TestCase):
    def test_bagging_helps_high_noise(self):
        """On high-noise data, bagged predictor should achieve
        comparable-or-better point predictions than single
        predictor on a holdout."""
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
            _r2_score,
        )
        from rcm_mc.ml.ensemble_methods import (
            bag_train_predictor,
        )
        X, y = _synth(n=200, noise=0.20)
        names = [f"f{i}" for i in range(5)]
        # Single model
        single = train_ridge_with_cv(
            X[:150], y[:150], feature_names=names,
            target_metric="x")
        single_pred = single.predict(X[150:])
        single_r2 = _r2_score(y[150:], single_pred)
        # Bagged
        bagged = bag_train_predictor(
            X[:150], y[:150], feature_names=names,
            target_metric="x", n_bags=20)
        bagged_pred = bagged.predict(X[150:])
        bagged_r2 = _r2_score(y[150:], bagged_pred)
        # Bagged R² shouldn't be much worse than single
        self.assertGreater(bagged_r2, single_r2 - 0.10)


if __name__ == "__main__":
    unittest.main()
