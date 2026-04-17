"""Tests for RCM performance predictor."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=200):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL"], n),
        "beds": rng.randint(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e7, 5e9, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "gross_patient_revenue": rng.uniform(5e7, 1e10, n),
        "total_patient_days": rng.randint(1000, 100000, n).astype(float),
        "bed_days_available": rng.randint(5000, 200000, n).astype(float),
        "medicare_day_pct": rng.uniform(0.1, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.3, n),
    })


class TestRCMPredictor(unittest.TestCase):

    def test_predict_hospital(self):
        from rcm_mc.ml.rcm_performance_predictor import predict_hospital_rcm
        df = _sample_hcris()
        result = predict_hospital_rcm("000001", df)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.predictions), 4)
        self.assertIn(result.overall_rcm_grade, ["A", "B", "C", "D"])

    def test_predictions_in_range(self):
        from rcm_mc.ml.rcm_performance_predictor import predict_hospital_rcm
        df = _sample_hcris()
        result = predict_hospital_rcm("000001", df)
        for p in result.predictions:
            lo, hi = p.confidence_interval
            self.assertLessEqual(lo, p.predicted_value)
            self.assertGreaterEqual(hi, p.predicted_value)

    def test_feature_importances(self):
        from rcm_mc.ml.rcm_performance_predictor import predict_hospital_rcm
        df = _sample_hcris()
        result = predict_hospital_rcm("000001", df)
        for p in result.predictions:
            self.assertGreater(len(p.feature_importances), 0)

    def test_screen_opportunities(self):
        from rcm_mc.ml.rcm_performance_predictor import screen_rcm_opportunities
        df = _sample_hcris()
        results = screen_rcm_opportunities(df, top_n=10)
        self.assertLessEqual(len(results), 10)
        if len(results) >= 2:
            self.assertLessEqual(results[0]["rcm_score"], results[1]["rcm_score"])

    def test_nonexistent(self):
        from rcm_mc.ml.rcm_performance_predictor import predict_hospital_rcm
        df = _sample_hcris(50)
        self.assertIsNone(predict_hospital_rcm("999999", df))


if __name__ == "__main__":
    unittest.main()
