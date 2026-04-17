"""Tests for prediction ledger and model validation."""
from __future__ import annotations

import os
import sqlite3
import tempfile
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


class TestPredictionLedger(unittest.TestCase):

    def setUp(self):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.con = sqlite3.connect(self.tf.name)

    def tearDown(self):
        self.con.close()
        os.unlink(self.tf.name)

    def test_record_prediction(self):
        from rcm_mc.ml.prediction_ledger import record_prediction
        pid = record_prediction(self.con, "010001", "denial_rate", 0.085,
                                ci_low=0.05, ci_high=0.12, method="ridge")
        self.con.commit()
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)

    def test_record_actual(self):
        from rcm_mc.ml.prediction_ledger import record_prediction, record_actual
        pid = record_prediction(self.con, "010001", "denial_rate", 0.085)
        record_actual(self.con, pid, 0.092)
        self.con.commit()
        row = self.con.execute(
            "SELECT actual_value FROM prediction_actuals WHERE prediction_id = ?",
            (pid,)).fetchone()
        self.assertAlmostEqual(row[0], 0.092)

    def test_get_predictions_with_actuals(self):
        from rcm_mc.ml.prediction_ledger import (
            record_prediction, record_actual, get_predictions_with_actuals)
        for i in range(5):
            pid = record_prediction(self.con, f"00000{i}", "denial_rate",
                                    0.08 + i * 0.01, ci_low=0.05, ci_high=0.15)
            record_actual(self.con, pid, 0.09 + i * 0.005)
        self.con.commit()
        results = get_predictions_with_actuals(self.con, metric="denial_rate")
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertIsNotNone(r.error)
            self.assertIsNotNone(r.covered)

    def test_coverage_tracking(self):
        from rcm_mc.ml.prediction_ledger import (
            record_prediction, record_actual, get_predictions_with_actuals)
        # In range
        pid1 = record_prediction(self.con, "000001", "margin", 0.05,
                                 ci_low=0.02, ci_high=0.08)
        record_actual(self.con, pid1, 0.06)
        # Out of range
        pid2 = record_prediction(self.con, "000002", "margin", 0.05,
                                 ci_low=0.02, ci_high=0.08)
        record_actual(self.con, pid2, 0.15)
        self.con.commit()
        results = get_predictions_with_actuals(self.con, metric="margin")
        covered = [r.covered for r in results]
        self.assertIn(True, covered)
        self.assertIn(False, covered)

    def test_compute_metric_performance(self):
        from rcm_mc.ml.prediction_ledger import (
            record_prediction, record_actual, compute_metric_performance)
        rng = np.random.RandomState(42)
        for i in range(20):
            pred = 0.08 + rng.normal(0, 0.01)
            actual = pred + rng.normal(0, 0.02)
            pid = record_prediction(self.con, f"{i:06d}", "test_metric", pred,
                                    ci_low=pred - 0.05, ci_high=pred + 0.05)
            record_actual(self.con, pid, actual)
        self.con.commit()
        perf = compute_metric_performance(self.con, "test_metric")
        self.assertIsNotNone(perf)
        self.assertGreater(perf.mae, 0)
        self.assertIn(perf.grade, ["A", "B", "C", "D"])
        self.assertGreater(perf.n_actuals, 0)

    def test_batch_predictions(self):
        from rcm_mc.ml.prediction_ledger import record_batch_predictions
        preds = [
            {"ccn": "000001", "metric": "denial", "predicted_value": 0.08},
            {"ccn": "000002", "metric": "denial", "predicted_value": 0.12},
        ]
        ids = record_batch_predictions(self.con, preds)
        self.con.commit()
        self.assertEqual(len(ids), 2)

    def test_performance_trend(self):
        from rcm_mc.ml.prediction_ledger import (
            log_performance, get_performance_trend, MetricPerformance)
        perf = MetricPerformance(
            metric="test", mae=0.02, rmse=0.03, r2=0.65,
            coverage_rate=0.88, mean_interval_width=0.10,
            bias=-0.005, n_predictions=100, n_actuals=80, grade="B")
        log_performance(self.con, perf)
        self.con.commit()
        trend = get_performance_trend(self.con, "test")
        self.assertEqual(len(trend), 1)
        self.assertAlmostEqual(trend[0]["r2"], 0.65)


class TestSyntheticBacktest(unittest.TestCase):

    def setUp(self):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.con = sqlite3.connect(self.tf.name)

    def tearDown(self):
        self.con.close()
        os.unlink(self.tf.name)

    def test_run_backtest(self):
        from rcm_mc.ml.prediction_ledger import run_synthetic_backtest
        df = _sample_hcris(200)
        perfs = run_synthetic_backtest(self.con, df, n_trials=30)
        self.con.commit()
        self.assertGreater(len(perfs), 0)
        for metric, perf in perfs.items():
            self.assertGreater(perf.n_actuals, 0)
            self.assertIn(perf.grade, ["A", "B", "C", "D"])

    def test_backtest_populates_ledger(self):
        from rcm_mc.ml.prediction_ledger import run_synthetic_backtest
        df = _sample_hcris(100)
        run_synthetic_backtest(self.con, df, n_trials=20)
        self.con.commit()
        count = self.con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        self.assertGreater(count, 0)
        actual_count = self.con.execute("SELECT COUNT(*) FROM prediction_actuals").fetchone()[0]
        self.assertEqual(count, actual_count)


class TestModelValidationPage(unittest.TestCase):

    def test_renders_with_backtest(self):
        from rcm_mc.ui.model_validation_page import render_model_validation
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris(200))
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            html = render_model_validation(tf.name, hcris_df=df)
            self.assertIn("SeekingChartis", html)
            self.assertIn("Model Validation", html)
            self.assertIn("Compounding", html)
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
