"""Tests for unified feature importance + SVG visualization."""
from __future__ import annotations

import socket
import threading
import time
import unittest
import urllib.request

import numpy as np


class TestFeatureImportancePairs(unittest.TestCase):
    def test_basic_aggregation(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        out = FeatureImportance.from_pairs([
            ("a", 0.5),
            ("b", -0.3),
            ("c", 0.0),
        ])
        # Sorted by |raw_value| descending
        self.assertEqual(
            [r.feature for r in out],
            ["a", "b", "c"])
        # Relative sums to 1.0
        self.assertAlmostEqual(
            sum(r.relative for r in out), 1.0, places=4)
        # Direction labels
        self.assertEqual(out[0].direction, "positive")
        self.assertEqual(out[1].direction, "negative")
        self.assertEqual(out[2].direction, "neutral")

    def test_empty_pairs(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        self.assertEqual(
            FeatureImportance.from_pairs([]), [])

    def test_all_zero_values(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        out = FeatureImportance.from_pairs([
            ("a", 0.0), ("b", 0.0)])
        for r in out:
            self.assertEqual(r.relative, 0.0)
            self.assertEqual(r.direction, "neutral")


class TestTrainedRidgeAdapter(unittest.TestCase):
    def test_round_trip(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        from rcm_mc.ml.feature_importance import (
            importance_from_trained_ridge,
        )
        rng = np.random.default_rng(7)
        X = rng.normal(0, 1, size=(100, 4))
        y = X @ np.array([0.5, -0.3, 0.1, 0.0]) + 0.5
        names = ["a", "b", "c", "d"]
        p = train_ridge_with_cv(
            X, y, feature_names=names,
            target_metric="x")
        imps = importance_from_trained_ridge(p)
        self.assertEqual(len(imps), 4)
        # 'a' has largest beta → top of list
        self.assertEqual(imps[0].feature, "a")
        # Relative sums to ~1 (rounded to 4dp inside)
        self.assertAlmostEqual(
            sum(r.relative for r in imps), 1.0, places=2)


class TestRegimeAdapter(unittest.TestCase):
    def test_regime_to_importance(self):
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        from rcm_mc.ml.feature_importance import (
            importance_from_regime,
        )
        rng = np.random.default_rng(11)
        report = analyze_hospital_regime({
            "revenue": [
                100 * (1.05 ** i) + rng.normal(0, 0.5)
                for i in range(8)],
            "ebitda_margin": [
                0.04 + 0.005 * i + rng.normal(0, 0.001)
                for i in range(8)],
        })
        imps = importance_from_regime(report)
        self.assertEqual(len(imps), 2)
        feature_names = {i.feature for i in imps}
        self.assertIn("revenue", feature_names)
        self.assertIn("ebitda_margin", feature_names)


class TestVolumeAdapter(unittest.TestCase):
    def test_volume_to_importance(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            build_hospital_trajectory_report,
        )
        from rcm_mc.ml.feature_importance import (
            importance_from_volume_report,
        )

        def _series(start, growth, n=12):
            return [(f"{2020 + q // 4}Q{q % 4 + 1}",
                     start * (1 + growth) ** q)
                    for q in range(n)]

        report = build_hospital_trajectory_report({
            "Surgery": _series(10000, 0.025),
            "ED": _series(5000, -0.02),
        })
        imps = importance_from_volume_report(report)
        self.assertEqual(len(imps), 2)
        # Surgery has bigger volume + positive growth → top
        # absolute importance
        self.assertEqual(imps[0].feature, "Surgery")
        self.assertEqual(imps[0].direction, "positive")


class TestServiceLineAdapter(unittest.TestCase):
    def test_service_line_to_importance(self):
        from rcm_mc.ml.service_line_profitability import (
            CostCenterRecord,
            compute_service_line_profitability,
        )
        from rcm_mc.ml.feature_importance import (
            importance_from_service_lines,
        )
        records = [
            CostCenterRecord(
                ccn="X", fiscal_year=2023,
                line_number=60, cost_center_name="OR",
                direct_cost=1_000_000,
                overhead_allocation=200_000,
                gross_charges=5_000_000,
                net_revenue=2_000_000),
            CostCenterRecord(
                ccn="X", fiscal_year=2023,
                line_number=89, cost_center_name="ED",
                direct_cost=5_000_000,
                overhead_allocation=1_000_000,
                gross_charges=8_000_000,
                net_revenue=3_000_000),
        ]
        margins = compute_service_line_profitability(
            records)
        imps = importance_from_service_lines(margins)
        self.assertEqual(len(imps), 2)
        # Surgery is positive, ED is negative
        names = {i.feature: i.direction for i in imps}
        self.assertEqual(names["Surgery"], "positive")
        self.assertEqual(names["ED"], "negative")


class TestSVGRender(unittest.TestCase):
    def test_renders_svg_bars(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        from rcm_mc.ui.feature_importance_viz import (
            render_importance_bar_chart,
        )
        imps = FeatureImportance.from_pairs([
            ("a", 0.5), ("b", -0.3),
        ])
        svg = render_importance_bar_chart(
            imps, title="Test")
        self.assertIn("<svg", svg)
        self.assertIn("Test", svg)
        # Both bars rendered
        self.assertEqual(svg.count("<rect"), 2)

    def test_empty_importance(self):
        from rcm_mc.ui.feature_importance_viz import (
            render_importance_bar_chart,
        )
        html = render_importance_bar_chart([])
        self.assertIn("No feature importance", html)

    def test_max_bars_caps(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        from rcm_mc.ui.feature_importance_viz import (
            render_importance_bar_chart,
        )
        imps = FeatureImportance.from_pairs([
            (f"f{i}", float(i + 1)) for i in range(20)])
        svg = render_importance_bar_chart(
            imps, max_bars=5)
        self.assertEqual(svg.count("<rect"), 5)


class TestPanelRender(unittest.TestCase):
    def test_panel_with_multiple_models(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
        )
        from rcm_mc.ui.feature_importance_viz import (
            render_importance_panel,
        )
        panel = {
            "Model A": FeatureImportance.from_pairs([
                ("a", 0.5), ("b", -0.3)]),
            "Model B": FeatureImportance.from_pairs([
                ("c", 0.4), ("d", 0.2)]),
        }
        html = render_importance_panel(panel)
        self.assertIn("Model A", html)
        self.assertIn("Model B", html)

    def test_default_panel(self):
        from rcm_mc.ui.feature_importance_viz import (
            _build_default_importance_panel,
        )
        panel = _build_default_importance_panel()
        # 3 default models
        self.assertGreaterEqual(len(panel), 3)
        for name, imps in panel.items():
            self.assertGreater(len(imps), 0)


class TestPageRender(unittest.TestCase):
    def test_full_page(self):
        from rcm_mc.ui.feature_importance_viz import (
            _build_default_importance_panel,
            render_feature_importance_page,
        )
        panel = _build_default_importance_panel()
        html = render_feature_importance_page(panel)
        self.assertIn("Feature Importance", html)
        self.assertIn("<svg", html)

    def test_empty_page(self):
        from rcm_mc.ui.feature_importance_viz import (
            render_feature_importance_page,
        )
        html = render_feature_importance_page({})
        self.assertIn("Feature Importance", html)
        self.assertIn("No model importance data", html)


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
                       "/models/importance")
                with urllib.request.urlopen(
                        url, timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode()
                    self.assertIn(
                        "Feature Importance", body)
                    self.assertIn("<svg", body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
