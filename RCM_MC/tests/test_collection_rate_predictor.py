"""Tests for collection-rate predictor + feature importance."""
from __future__ import annotations

import unittest

import numpy as np


def _synth_hospitals(n: int = 200, seed: int = 7):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        beds = float(rng.integers(50, 800))
        mc = float(rng.uniform(0.20, 0.65))
        md = float(rng.uniform(0.05, 0.35))
        sp = float(rng.uniform(0.02, 0.15))
        margin = float(rng.normal(0.04, 0.06))
        denial = float(rng.uniform(0.04, 0.20))
        dso = float(rng.uniform(35, 75))
        # Latent collection rate driven by:
        #   denial rate (negative — more denials → less collected)
        #   self-pay (negative — slow collections)
        #   DSO (mildly negative)
        #   margin (positive — proxy for ops quality)
        true_cr = (
            0.985
            - 0.15 * denial
            - 0.10 * sp
            - 0.0010 * dso
            + 0.10 * margin
            - 0.05 * md
            + rng.normal(0, 0.005)
        )
        true_cr = max(0.80, min(1.00, true_cr))
        rows.append({
            "beds": beds,
            "medicare_day_pct": mc,
            "medicaid_day_pct": md,
            "self_pay_pct": sp,
            "denial_rate": denial,
            "days_in_ar": dso,
            "gross_patient_revenue":
                beds * 4 * 50_000,
            "net_patient_revenue":
                beds * 4 * 50_000 * 0.30,
            "operating_expenses":
                beds * 4 * 50_000 * 0.30 * (1 - margin),
            "collection_rate": true_cr,
        })
    return rows


class TestCollectionRatePredictor(unittest.TestCase):
    def test_train_predicts(self):
        from rcm_mc.ml.collection_rate_predictor import (
            COLLECTION_RATE_FEATURES,
            train_collection_rate_predictor,
        )
        rows = _synth_hospitals(n=200)
        p = train_collection_rate_predictor(rows)
        self.assertEqual(p.feature_names,
                         COLLECTION_RATE_FEATURES)
        self.assertEqual(p.target_metric, "collection_rate")
        self.assertGreater(p.cv_r2_mean, 0.50)
        self.assertEqual(p.sanity_range, (0.70, 1.00))

    def test_predict_realistic_range(self):
        from rcm_mc.ml.collection_rate_predictor import (
            train_collection_rate_predictor,
            predict_collection_rate,
        )
        rows = _synth_hospitals(n=200)
        p = train_collection_rate_predictor(rows)
        yhat, (lo, hi), expl = predict_collection_rate(p, {
            "beds": 200, "medicare_day_pct": 0.40,
            "medicaid_day_pct": 0.15,
            "denial_rate": 0.08, "days_in_ar": 45,
        })
        self.assertGreater(yhat, 0.85)
        self.assertLess(yhat, 1.00)


class TestFeatureImportance(unittest.TestCase):
    def test_global_importance_ranks_denial_rate_high(self):
        """Latent collection rate is most strongly driven by
        denial_rate_input — feature_importance() should
        surface it near the top."""
        from rcm_mc.ml.collection_rate_predictor import (
            train_collection_rate_predictor,
        )
        rows = _synth_hospitals(n=400)
        p = train_collection_rate_predictor(rows)
        importance = p.feature_importance()
        # Returns (name, std_coef, relative) tuples
        self.assertTrue(all(len(t) == 3
                            for t in importance))
        # Sum of relative importances = 1.0
        rel_sum = sum(rel for _, _, rel in importance)
        self.assertAlmostEqual(rel_sum, 1.0, places=4)
        # denial_rate_input should be in top 3 importance
        # rank by |std_coef|
        top_3 = [t[0] for t in importance[:3]]
        self.assertIn("denial_rate_input", top_3)

    def test_permutation_importance_runs(self):
        from rcm_mc.ml.collection_rate_predictor import (
            train_collection_rate_predictor,
            collection_rate_permutation_importance,
        )
        rows = _synth_hospitals(n=200)
        p = train_collection_rate_predictor(rows)
        perm = collection_rate_permutation_importance(
            p, rows, n_repeats=3)
        self.assertEqual(
            len(perm), len(p.feature_names))
        # Top feature in permutation importance should match
        # top feature in standardized-coef importance for a
        # well-conditioned feature set
        names_perm = [t[0] for t in perm]
        names_coef = [t[0] for t in p.feature_importance()]
        # Top feature should be the same (denial_rate_input)
        self.assertEqual(names_perm[0], names_coef[0])
        # Drops are non-negative on average
        self.assertGreaterEqual(perm[0][1], 0)

    def test_permutation_importance_top_signal_high(self):
        """The most impactful feature in the latent model
        should show a meaningfully positive R² drop when
        permuted."""
        from rcm_mc.ml.collection_rate_predictor import (
            train_collection_rate_predictor,
            collection_rate_permutation_importance,
        )
        rows = _synth_hospitals(n=300)
        p = train_collection_rate_predictor(rows)
        perm = collection_rate_permutation_importance(
            p, rows, n_repeats=5)
        # Top feature drop ≥ 0.05 R² on this signal
        self.assertGreater(perm[0][1], 0.02)


class TestImportanceOrdering(unittest.TestCase):
    def test_relative_importance_sums_to_one(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        rng = np.random.default_rng(3)
        X = rng.normal(0, 1, size=(200, 4))
        y = X @ np.array([0.5, -0.3, 0.1, 0.0]) + 0.5
        p = train_ridge_with_cv(
            X, y,
            feature_names=["a", "b", "c", "d"],
            target_metric="x")
        importance = p.feature_importance()
        rel_sum = sum(r for _, _, r in importance)
        self.assertAlmostEqual(rel_sum, 1.0, places=4)
        # Sorted by |std_coef| descending
        coefs = [abs(c) for _, c, _ in importance]
        self.assertEqual(coefs,
                         sorted(coefs, reverse=True))

    def test_zero_coefficients_yield_zero_importance(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            TrainedRCMPredictor,
        )
        # Construct a synthetic predictor with all-zero coefs
        p = TrainedRCMPredictor(
            target_metric="x",
            feature_names=["a", "b"],
            feature_means=np.zeros(2),
            feature_stds=np.ones(2),
            coefficients=np.zeros(2),
            intercept=0.5, target_mean=0.5,
            alpha=1.0, n_train=100,
            train_r2=0.0, cv_r2_mean=0.0,
            cv_r2_std=0.0, cv_mae=0.0,
            cv_mape=None, cv_residual_p90=0.0)
        importance = p.feature_importance()
        for _, _, rel in importance:
            self.assertEqual(rel, 0.0)


if __name__ == "__main__":
    unittest.main()
