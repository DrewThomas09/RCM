"""Tests for the trained margin predictor."""
from __future__ import annotations

import unittest
import numpy as np
import pandas as pd


def _sample_hcris(n=300):
    rng = np.random.RandomState(42)
    rev = rng.uniform(1e7, 5e9, n)
    opex = rev * rng.uniform(0.85, 1.15, n)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL"], n),
        "beds": rng.randint(20, 600, n).astype(float),
        "net_patient_revenue": rev,
        "operating_expenses": opex,
        "gross_patient_revenue": rev * rng.uniform(2, 4, n),
        "medicare_day_pct": rng.uniform(0.1, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.3, n),
        "total_patient_days": rng.randint(1000, 100000, n).astype(float),
        "bed_days_available": rng.randint(5000, 200000, n).astype(float),
    })


class TestTrainModel(unittest.TestCase):

    def test_trains(self):
        from rcm_mc.ml.margin_predictor import train_margin_model
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        model = train_margin_model(df)
        self.assertGreater(model.n, 100)
        self.assertGreater(model.r2, 0)
        self.assertGreater(len(model.features_used), 3)

    def test_conformal_margin_positive(self):
        from rcm_mc.ml.margin_predictor import train_margin_model
        from rcm_mc.ui.regression_page import _add_computed_features
        model = train_margin_model(_add_computed_features(_sample_hcris()))
        self.assertGreater(model.conformal_margin, 0)


class TestPredictMargin(unittest.TestCase):

    def test_predicts(self):
        from rcm_mc.ml.margin_predictor import predict_margin
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        pred = predict_margin("000001", df)
        self.assertIsNotNone(pred)
        self.assertGreaterEqual(pred.predicted_margin, -1)
        self.assertLessEqual(pred.predicted_margin, 1)
        self.assertLess(pred.ci_low, pred.ci_high)

    def test_has_drivers(self):
        from rcm_mc.ml.margin_predictor import predict_margin
        from rcm_mc.ui.regression_page import _add_computed_features
        pred = predict_margin("000001", _add_computed_features(_sample_hcris()))
        self.assertGreater(len(pred.top_drivers), 0)
        for d in pred.top_drivers:
            self.assertIsInstance(d.explanation, str)
            self.assertIn(d.direction, ["positive", "negative", "neutral"])

    def test_confidence_grade(self):
        from rcm_mc.ml.margin_predictor import predict_margin
        from rcm_mc.ui.regression_page import _add_computed_features
        pred = predict_margin("000001", _add_computed_features(_sample_hcris()))
        self.assertIn(pred.confidence_grade, ["A", "B", "C", "D"])

    def test_nonexistent(self):
        from rcm_mc.ml.margin_predictor import predict_margin
        df = _sample_hcris(10)
        self.assertIsNone(predict_margin("999999", df))


class TestBatchPredict(unittest.TestCase):

    def test_batch(self):
        from rcm_mc.ml.margin_predictor import batch_predict
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        model, results = batch_predict(df, n_sample=50)
        self.assertGreater(len(results), 0)
        self.assertGreater(model.r2, 0)

    def test_coverage(self):
        from rcm_mc.ml.margin_predictor import batch_predict
        from rcm_mc.ui.regression_page import _add_computed_features
        _, results = batch_predict(_add_computed_features(_sample_hcris()), n_sample=100)
        in_ci = [r["in_ci"] for r in results if r["in_ci"] is not None]
        if len(in_ci) > 20:
            coverage = np.mean(in_ci)
            self.assertGreater(coverage, 0.7)


if __name__ == "__main__":
    unittest.main()
