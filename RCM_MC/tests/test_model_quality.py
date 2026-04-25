"""Tests for unified backtest harness + CI calibration + dashboard."""
from __future__ import annotations

import math
import socket
import threading
import time
import unittest
import urllib.request

import numpy as np


def _synth(n=200, n_feat=5, noise=0.02, seed=7):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, size=(n, n_feat))
    beta = np.array([0.05, -0.03, 0.02, -0.04, 0.01])[:n_feat]
    y = X @ beta + 0.10 + rng.normal(0, noise, n)
    return X, y


class TestCalibration(unittest.TestCase):
    def test_well_calibrated_intervals(self):
        from rcm_mc.ml.model_quality import (
            calibrate_confidence_intervals,
        )
        rng = np.random.default_rng(7)
        n = 500
        # Symmetric residuals; CI half-width ≈ p90 of residuals
        # by construction
        residuals = rng.normal(0, 1, n)
        pred = np.zeros(n)
        actual = pred + residuals
        margin = float(np.quantile(np.abs(residuals), 0.90))
        lo = pred - margin
        hi = pred + margin
        result = calibrate_confidence_intervals(
            pred, actual, lo, hi, nominal_coverage=0.90)
        # Observed coverage should be ~90%
        self.assertGreater(result.observed_coverage, 0.85)
        self.assertLess(result.observed_coverage, 0.95)
        self.assertEqual(
            result.quality_label, "well_calibrated")

    def test_overconfident_intervals(self):
        from rcm_mc.ml.model_quality import (
            calibrate_confidence_intervals,
        )
        rng = np.random.default_rng(7)
        n = 500
        residuals = rng.normal(0, 1, n)
        pred = np.zeros(n)
        actual = pred + residuals
        # Way-too-tight CI: half-width = 0.5 instead of ~1.65
        lo = pred - 0.5
        hi = pred + 0.5
        result = calibrate_confidence_intervals(
            pred, actual, lo, hi, nominal_coverage=0.90)
        # Observed coverage should be << 90%
        self.assertLess(result.observed_coverage, 0.50)
        self.assertEqual(
            result.quality_label, "overconfident")
        # Calibration factor > 1 — widen the CI
        self.assertGreater(result.calibration_factor, 1.5)

    def test_underconfident_intervals(self):
        from rcm_mc.ml.model_quality import (
            calibrate_confidence_intervals,
        )
        rng = np.random.default_rng(7)
        n = 500
        residuals = rng.normal(0, 1, n)
        pred = np.zeros(n)
        actual = pred + residuals
        # Way-too-wide CI: half-width = 5
        lo = pred - 5.0
        hi = pred + 5.0
        result = calibrate_confidence_intervals(
            pred, actual, lo, hi, nominal_coverage=0.90)
        self.assertGreater(result.observed_coverage, 0.95)
        self.assertEqual(
            result.quality_label, "underconfident")
        # Calibration factor < 1 — tighten the CI
        self.assertLess(result.calibration_factor, 1.0)

    def test_empty_returns_no_data(self):
        from rcm_mc.ml.model_quality import (
            calibrate_confidence_intervals,
        )
        result = calibrate_confidence_intervals(
            np.array([]), np.array([]),
            np.array([]), np.array([]))
        self.assertEqual(result.quality_label, "no_data")


class TestKFoldBacktest(unittest.TestCase):
    def test_runs_on_clean_synthetic_data(self):
        from rcm_mc.ml.model_quality import kfold_backtest
        X, y = _synth(n=200, noise=0.005)
        result = kfold_backtest(
            X, y,
            feature_names=[f"f{i}" for i in range(5)],
            target_metric="synthetic")
        self.assertGreater(result.cv_r2, 0.7)
        self.assertIn(result.grade, ["A", "B"])
        # Calibration should be reasonable on clean data
        self.assertGreater(
            result.calibration.observed_coverage, 0.70)

    def test_grade_letters(self):
        from rcm_mc.ml.model_quality import _grade_for_r2
        self.assertEqual(_grade_for_r2(0.80), "A")
        self.assertEqual(_grade_for_r2(0.65), "B")
        self.assertEqual(_grade_for_r2(0.45), "C")
        self.assertEqual(_grade_for_r2(0.25), "D")
        self.assertEqual(_grade_for_r2(-0.10), "F")

    def test_too_few_rows_rejected(self):
        from rcm_mc.ml.model_quality import kfold_backtest
        X = np.random.normal(0, 1, size=(8, 3))
        y = np.random.normal(0, 1, size=8)
        with self.assertRaises(ValueError):
            kfold_backtest(
                X, y,
                feature_names=["a", "b", "c"],
                target_metric="x")


class TestBacktestTrainedPredictor(unittest.TestCase):
    def test_holdout_evaluation(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.model_quality import (
            backtest_trained_predictor,
        )
        # Train on first 150, hold out last 50
        X, y = _synth(n=200, noise=0.005)
        names = [f"f{i}" for i in range(5)]
        predictor = train_ridge_with_cv(
            X[:150], y[:150],
            feature_names=names,
            target_metric="synthetic")
        result = backtest_trained_predictor(
            predictor, X[150:], y[150:])
        self.assertEqual(result.target_metric, "synthetic")
        self.assertEqual(result.n_holdout, 50)
        self.assertGreater(result.cv_r2, 0.7)

    def test_empty_holdout(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.model_quality import (
            backtest_trained_predictor,
        )
        X, y = _synth(n=200)
        names = [f"f{i}" for i in range(5)]
        predictor = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="x")
        result = backtest_trained_predictor(
            predictor, np.array([]).reshape(0, 5),
            np.array([]))
        self.assertEqual(result.n_holdout, 0)
        self.assertEqual(result.grade, "F")


class TestModelQualityPanel(unittest.TestCase):
    def test_panel_runs(self):
        from rcm_mc.ml.model_quality import (
            run_model_quality_panel, kfold_backtest,
        )
        X, y = _synth(n=200)
        names = [f"f{i}" for i in range(5)]

        def _spec_a():
            return kfold_backtest(
                X, y, feature_names=names,
                target_metric="model_a")

        def _spec_b():
            return kfold_backtest(
                X, y * 2, feature_names=names,
                target_metric="model_b")

        results = run_model_quality_panel([
            ("Model A", _spec_a),
            ("Model B", _spec_b),
        ])
        self.assertEqual(len(results), 2)
        # Both should run successfully + sorted by R²
        self.assertTrue(
            results[0].cv_r2 >= results[1].cv_r2)

    def test_failed_spec_recorded(self):
        from rcm_mc.ml.model_quality import (
            run_model_quality_panel,
        )

        def _broken():
            raise RuntimeError("boom")

        results = run_model_quality_panel([
            ("BrokenModel", _broken),
        ])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].grade, "F")
        self.assertTrue(any(
            "Backtest failed" in n
            for n in results[0].notes))

    def test_default_quality_panel(self):
        from rcm_mc.ml.model_quality import (
            _build_default_quality_panel,
        )
        results = _build_default_quality_panel()
        # 4 models in the default panel
        self.assertGreaterEqual(len(results), 3)
        # Each has the expected fields populated
        for r in results:
            self.assertIsNotNone(r.target_metric)
            self.assertIsNotNone(r.calibration)


class TestDashboardRender(unittest.TestCase):
    def test_renders_panel(self):
        from rcm_mc.ml.model_quality import (
            _build_default_quality_panel,
        )
        from rcm_mc.ui.model_quality_dashboard import (
            render_model_quality_dashboard,
        )
        results = _build_default_quality_panel()
        html = render_model_quality_dashboard(results)
        self.assertIn("Model Quality", html)
        self.assertIn("CV R²", html)
        self.assertIn("Calibration", html)
        # KPI strip
        self.assertIn("Models tracked", html)
        self.assertIn("Avg CV R²", html)

    def test_empty_state(self):
        from rcm_mc.ui.model_quality_dashboard import (
            render_model_quality_dashboard,
        )
        html = render_model_quality_dashboard([])
        self.assertIn("Model Quality", html)
        self.assertIn("No backtest results", html)


class TestHTTPRoute(unittest.TestCase):
    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_route_renders(self):
        from rcm_mc.server import build_server
        import os, tempfile
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            port = self._free_port()
            srv, _h = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                url = (f"http://127.0.0.1:{port}"
                       "/models/quality")
                with urllib.request.urlopen(
                        url, timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode()
                    self.assertIn("Model Quality", body)
                    self.assertIn("CV R²", body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
