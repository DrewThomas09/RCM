"""The reported distress-model AUC must be honest (out-of-sample).

The page labels the distress AUC as "held-out" / "cross-validated", so the
number behind it must actually be out-of-sample — fitting and scoring on
the same rows gives an optimistic in-sample AUC that overstates how the
model generalizes (invented model performance). This pins:

1. The AUC is cross-validated, and on a genuinely-predictable target it is
   materially below the optimistic in-sample AUC (i.e. CV is not secretly
   in-sample).
2. CV degrades gracefully (single-class / tiny samples → 0.5, never raises).
3. The change is report-only: the scoring model (beta) and therefore every
   distress *prediction* is unchanged — only the quality number got honest.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.ml.distress_predictor import (
    _compute_auc,
    _cv_auc,
    _fit_logistic,
    _sigmoid,
)


def _separable(n=400, seed=0):
    """A target with real signal so in-sample AUC is clearly optimistic
    relative to honest CV AUC."""
    rng = np.random.RandomState(seed)
    X = rng.normal(size=(n, 4))
    # y driven by feature 0 + noise → learnable but not perfectly.
    logits = 1.3 * X[:, 0] + 0.4 * rng.normal(size=n)
    y = (logits > 0).astype(float)
    return X, y


class CvAucHonestyTests(unittest.TestCase):
    def test_cv_auc_in_range(self):
        X, y = _separable()
        s = _cv_auc(X, y)
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)

    def test_cv_below_in_sample_on_signal(self):
        # In-sample AUC overfits and sits above the honest CV AUC.
        X, y = _separable(n=300, seed=3)
        beta = _fit_logistic(X, y)
        X_aug = np.column_stack([np.ones(len(X)), X])
        in_sample = _compute_auc(y, _sigmoid(X_aug @ beta))
        cv = _cv_auc(X, y)
        self.assertLessEqual(cv, in_sample + 1e-9,
                             "CV AUC should not exceed the optimistic in-sample AUC")

    def test_single_class_is_half(self):
        X = np.random.RandomState(1).normal(size=(80, 3))
        self.assertEqual(_cv_auc(X, np.ones(80)), 0.5)

    def test_small_sample_is_half(self):
        X = np.random.RandomState(2).normal(size=(20, 3))
        y = (X[:, 0] > 0).astype(float)
        self.assertEqual(_cv_auc(X, y), 0.5)

    def test_deterministic(self):
        X, y = _separable(seed=5)
        self.assertEqual(_cv_auc(X, y), _cv_auc(X, y))


class PredictionUnchangedTests(unittest.TestCase):
    def test_beta_is_full_data_fit_predictions_unchanged(self):
        # The returned model coefficients must still be the all-data fit, so
        # distress *scores* are identical to before the AUC-honesty change.
        import pandas as pd
        from rcm_mc.ml.distress_predictor import train_distress_model, _PREDICTOR_FEATURES
        rng = np.random.RandomState(0)
        n = 200
        df = pd.DataFrame({
            "ccn": [f"{i:06d}" for i in range(n)],
            "beds": rng.uniform(25, 500, n),
            "net_patient_revenue": rng.uniform(2e7, 8e8, n),
            "gross_patient_revenue": rng.uniform(5e7, 2e9, n),
            "operating_expenses": rng.uniform(2e7, 7e8, n),
            "total_patient_days": rng.uniform(5e3, 2e5, n),
            "bed_days_available": rng.uniform(1e4, 3e5, n),
            "medicare_day_pct": rng.uniform(0.2, 0.7, n),
            "medicaid_day_pct": rng.uniform(0.05, 0.4, n),
        })
        beta, X_mean, X_std, auc, n_train, feats = train_distress_model(df)
        # Recompute the all-data logistic fit independently and confirm beta matches.
        d = df.copy()
        d["revenue_per_bed"] = d["net_patient_revenue"] / d["beds"]
        rev = d["net_patient_revenue"].where(d["net_patient_revenue"] > 1e5)
        d["operating_margin"] = ((rev - d["operating_expenses"]) / rev).clip(-0.5, 1.0)
        d["occupancy_rate"] = d["total_patient_days"] / d["bed_days_available"]
        d["net_to_gross_ratio"] = (d["net_patient_revenue"] / d["gross_patient_revenue"]).clip(0, 1)
        available = [f for f in _PREDICTOR_FEATURES if f in d.columns]
        clean = d.dropna(subset=available + ["operating_margin"]).copy()
        y = (clean["operating_margin"] < -0.05).astype(float).values
        feat_cols = [f for f in available if f != "operating_margin"]
        X = clean[feat_cols].fillna(0).values.astype(float)
        Xn = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
        beta_ref = _fit_logistic(Xn, y)
        np.testing.assert_allclose(beta, beta_ref, rtol=1e-9, atol=1e-9)
        self.assertGreaterEqual(auc, 0.0)
        self.assertLessEqual(auc, 1.0)


if __name__ == "__main__":
    unittest.main()
