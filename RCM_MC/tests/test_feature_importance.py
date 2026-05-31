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


# ── PR #1341: cover the 3 functions test_feature_importance.py was
# missing — importance_from_contract_strength,
# importance_from_explain_pairs, and aggregate_importance_by_category.
# Same pattern as the existing adapter tests (small stub fixture +
# assertion against the uniform FeatureImportance shape).


class TestExplainPairsAdapter(unittest.TestCase):
    """``importance_from_explain_pairs`` is a thin forwarder — verify
    it just delegates to ``FeatureImportance.from_pairs``."""

    def test_forwards_to_from_pairs(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
            importance_from_explain_pairs,
        )
        pairs = [("denial_rate", 0.4), ("days_in_ar", -0.3)]
        out = importance_from_explain_pairs(pairs)
        ref = FeatureImportance.from_pairs(pairs)
        self.assertEqual(len(out), len(ref))
        for a, b in zip(out, ref):
            self.assertEqual(a.feature, b.feature)
            self.assertEqual(a.raw_value, b.raw_value)
            self.assertEqual(a.relative, b.relative)
            self.assertEqual(a.direction, b.direction)

    def test_empty_input(self):
        from rcm_mc.ml.feature_importance import (
            importance_from_explain_pairs,
        )
        self.assertEqual(importance_from_explain_pairs([]), [])


class TestContractStrengthAdapter(unittest.TestCase):
    """``importance_from_contract_strength`` repackages
    ContractStrengthScore's top-above / top-below lists into the
    uniform shape, emitting signed log(rate_ratio) per contract."""

    @staticmethod
    def _score(above=(), below=()):
        from dataclasses import dataclass

        @dataclass
        class _C:
            payer_name: str
            code: str
            rate_ratio: float

        @dataclass
        class _S:
            top_above_market: list
            top_below_market: list

        return _S(
            top_above_market=[_C(*a) for a in above],
            top_below_market=[_C(*b) for b in below],
        )

    def test_log_ratio_of_rate(self):
        from rcm_mc.ml.feature_importance import (
            importance_from_contract_strength,
        )
        score = self._score(
            above=[("Aetna", "99213", 1.5)],
            below=[("BCBS", "99214", 0.5)],
        )
        import math
        out = importance_from_contract_strength(score)
        # |log(0.5)| ≈ 0.693 > |log(1.5)| ≈ 0.405 → BCBS first
        self.assertEqual(out[0].feature, "BCBS · 99214")
        self.assertEqual(out[0].direction, "negative")
        self.assertAlmostEqual(out[0].raw_value, math.log(0.5),
                                places=4)
        self.assertEqual(out[1].feature, "Aetna · 99213")
        self.assertEqual(out[1].direction, "positive")

    def test_zero_or_negative_rate_ratio_emits_zero_log(self):
        # math.log(0) blows up — code falls back to 0 (neutral).
        from rcm_mc.ml.feature_importance import (
            importance_from_contract_strength,
        )
        score = self._score(
            above=[("X", "1", 0.0), ("Y", "2", -1.0)],
        )
        out = importance_from_contract_strength(score)
        for f in out:
            self.assertEqual(f.raw_value, 0.0)
            self.assertEqual(f.direction, "neutral")

    def test_empty_score(self):
        from rcm_mc.ml.feature_importance import (
            importance_from_contract_strength,
        )
        out = importance_from_contract_strength(self._score())
        self.assertEqual(out, [])


class TestAggregateImportanceByCategory(unittest.TestCase):
    """``aggregate_importance_by_category`` sums per-feature
    relatives into higher-level buckets for the rollup view."""

    def test_basic_aggregation(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
            aggregate_importance_by_category,
        )
        imps = FeatureImportance.from_pairs([
            ("denial_rate", 0.4),
            ("days_in_ar", 0.3),
            ("revenue", 0.2),
            ("ebitda", 0.1),
        ])
        cats = aggregate_importance_by_category(imps, {
            "denial_rate": "rcm",
            "days_in_ar": "rcm",
            "revenue": "financial",
            "ebitda": "financial",
        })
        self.assertEqual(set(cats.keys()), {"rcm", "financial"})
        self.assertAlmostEqual(
            cats["rcm"] + cats["financial"], 1.0, places=3)
        # rcm holds 0.7 share (0.4 + 0.3 of total |1.0|)
        self.assertGreater(cats["rcm"], cats["financial"])

    def test_unmapped_features_go_to_other(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
            aggregate_importance_by_category,
        )
        imps = FeatureImportance.from_pairs([
            ("known", 1.0), ("unknown", 1.0),
        ])
        cats = aggregate_importance_by_category(imps, {
            "known": "explicit",
        })
        self.assertEqual(set(cats.keys()), {"explicit", "other"})
        self.assertAlmostEqual(cats["explicit"], 0.5)
        self.assertAlmostEqual(cats["other"], 0.5)

    def test_empty_importances(self):
        from rcm_mc.ml.feature_importance import (
            aggregate_importance_by_category,
        )
        self.assertEqual(aggregate_importance_by_category([], {}), {})
        self.assertEqual(
            aggregate_importance_by_category([], {"x": "y"}), {},
        )

    def test_no_category_map_everything_other(self):
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
            aggregate_importance_by_category,
        )
        imps = FeatureImportance.from_pairs([("a", 1), ("b", 1)])
        cats = aggregate_importance_by_category(imps, {})
        self.assertEqual(set(cats.keys()), {"other"})
        self.assertAlmostEqual(cats["other"], 1.0, places=3)

    def test_output_rounded_to_four_decimals(self):
        # 3 equal features → each gets relative=0.3333; summed by
        # category → 0.9999 (the rounding-pre-aggregation artifact).
        from rcm_mc.ml.feature_importance import (
            FeatureImportance,
            aggregate_importance_by_category,
        )
        imps = FeatureImportance.from_pairs([
            ("a", 1), ("b", 1), ("c", 1),
        ])
        cats = aggregate_importance_by_category(
            imps, {"a": "g", "b": "g", "c": "g"},
        )
        self.assertEqual(cats["g"], 0.9999)


class TestFromPairsExtraEdgeCases(unittest.TestCase):
    """Edge cases on FeatureImportance.from_pairs that the existing
    test class didn't cover."""

    def test_sorts_by_absolute_value_desc(self):
        from rcm_mc.ml.feature_importance import FeatureImportance
        out = FeatureImportance.from_pairs([
            ("small", 0.5), ("huge", -5.0), ("medium", 2.0),
        ])
        self.assertEqual([f.feature for f in out],
                         ["huge", "medium", "small"])

    def test_direction_neutral_band_at_1e_minus_9(self):
        # Contract uses 1e-9 as the neutral band — values strictly
        # smaller in absolute value → 'neutral'.
        from rcm_mc.ml.feature_importance import FeatureImportance
        out = FeatureImportance.from_pairs([
            ("tiny_pos", 1e-10),
            ("tiny_neg", -1e-10),
            ("above_band_pos", 1e-8),
            ("above_band_neg", -1e-8),
        ])
        by_name = {f.feature: f.direction for f in out}
        self.assertEqual(by_name["tiny_pos"], "neutral")
        self.assertEqual(by_name["tiny_neg"], "neutral")
        self.assertEqual(by_name["above_band_pos"], "positive")
        self.assertEqual(by_name["above_band_neg"], "negative")

    def test_relative_rounded_to_four_decimals(self):
        from rcm_mc.ml.feature_importance import FeatureImportance
        out = FeatureImportance.from_pairs([
            ("a", 1.0), ("b", 2.0), ("c", 3.0),
        ])
        rels = {f.feature: f.relative for f in out}
        self.assertEqual(rels["b"], 0.3333)
        self.assertEqual(rels["c"], 0.5)

    def test_preserves_signed_raw_value(self):
        # raw_value is signed (NOT abs) — the visualization layer
        # needs the sign to color bars positive vs negative.
        from rcm_mc.ml.feature_importance import FeatureImportance
        out = FeatureImportance.from_pairs([("a", -7.5)])
        self.assertEqual(out[0].raw_value, -7.5)

    def test_coerces_feature_name_to_str(self):
        from rcm_mc.ml.feature_importance import FeatureImportance
        out = FeatureImportance.from_pairs([(123, 1.0), ("x", 2.0)])
        # |2| > |1| → x first, then 123 (stringified)
        self.assertEqual(out[0].feature, "x")
        self.assertEqual(out[1].feature, "123")


if __name__ == "__main__":
    unittest.main()
