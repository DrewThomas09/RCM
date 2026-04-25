"""Empty-data resilience suite.

Every page should handle null / empty / missing data gracefully —
no crashes, no tracebacks shown to the user, helpful empty-state
messages. This suite hits every recent UI surface with completely
empty inputs and verifies:

  • render returns HTML (no exception)
  • empty-state message present (or graceful fallback)
  • no Python exception text leaks into the output

Exercises the recent UI sprint output:
  - dashboard_v3, deal_profile_v2, model_quality_dashboard,
    feature_importance_viz, data_catalog_page, power_table,
    power_chart, compare, empty_states, preferences, nav,
    metric_glossary, provenance_badge.
"""
from __future__ import annotations

import os
import tempfile
import unittest


def _empty_store():
    from rcm_mc.portfolio.store import PortfolioStore
    tmp = tempfile.TemporaryDirectory()
    db = os.path.join(tmp.name, "p.db")
    store = PortfolioStore(db)
    store.init_db()
    return store, tmp


# ── Page-level empty-state coverage ─────────────────────────

class TestPageEmptyStates(unittest.TestCase):
    def test_dashboard_v3_with_empty_store(self):
        from rcm_mc.ui.dashboard_v3 import (
            render_dashboard_v3,
        )
        store, tmp = _empty_store()
        try:
            html = render_dashboard_v3(store)
            self.assertGreater(len(html), 100)
            self.assertIn("Morning view", html)
            # No Python exception text leaked
            self.assertNotIn("Traceback", html)
            self.assertNotIn(
                "object has no attribute", html)
        finally:
            tmp.cleanup()

    def test_deal_profile_v2_with_no_packet(self):
        from rcm_mc.ui.deal_profile_v2 import (
            render_deal_profile_v2,
        )
        store, tmp = _empty_store()
        try:
            html = render_deal_profile_v2(
                store, "nonexistent")
            self.assertGreater(len(html), 100)
            self.assertIn("nonexistent", html)
            # Empty-state with CTA
            self.assertIn("No analysis packet", html)
            self.assertNotIn("Traceback", html)
        finally:
            tmp.cleanup()

    def test_data_catalog_with_no_tables(self):
        from rcm_mc.ui.data_catalog_page import (
            render_data_catalog_page,
        )
        store, tmp = _empty_store()
        try:
            html = render_data_catalog_page(store)
            self.assertIn("Data Catalog", html)
            self.assertNotIn("Traceback", html)
        finally:
            tmp.cleanup()

    def test_model_quality_with_no_results(self):
        from rcm_mc.ui.model_quality_dashboard import (
            render_model_quality_dashboard,
        )
        html = render_model_quality_dashboard([])
        self.assertIn("Model Quality", html)
        self.assertIn("No backtest results", html)
        self.assertNotIn("Traceback", html)

    def test_feature_importance_with_no_panel(self):
        from rcm_mc.ui.feature_importance_viz import (
            render_feature_importance_page,
        )
        html = render_feature_importance_page({})
        self.assertIn("Feature Importance", html)
        self.assertIn("No model importance data", html)


# ── Component-level empty-state coverage ────────────────────

class TestComponentEmptyStates(unittest.TestCase):
    def test_power_table_with_empty_rows(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table,
        )
        html = render_power_table(
            table_id="empty",
            columns=[Column("a", "A")],
            rows=[])
        # Counter shows 0 of 0; no traceback
        self.assertIn("0 of 0", html)
        self.assertNotIn("Traceback", html)

    def test_compare_rejects_one_entity(self):
        """compare requires ≥2 entities — should raise
        ValueError with a helpful message, not crash mid-render."""
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
            render_comparison,
        )
        with self.assertRaises(ValueError) as ctx:
            render_comparison(
                [ComparableEntity(
                    label="solo", values={})],
                [ComparisonMetric("x")])
        self.assertIn("compare", str(ctx.exception).lower())

    def test_compare_with_all_none_values(self):
        """All values None → no winner identified, no crash."""
        from rcm_mc.ui.compare import (
            ComparableEntity, ComparisonMetric,
            render_comparison,
        )
        html = render_comparison(
            [
                ComparableEntity(
                    label="A",
                    values={"x": None}),
                ComparableEntity(
                    label="B",
                    values={"x": None}),
            ],
            [ComparisonMetric(
                "x", kind="number",
                show_in_glossary=False)])
        # Renders without ▲ since no winner
        self.assertNotIn("▲", html)
        # — placeholder for None
        self.assertIn("—", html)
        self.assertNotIn("Traceback", html)

    def test_provenance_badge_with_minimal_data(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        # Bare-minimum data point
        html = provenance_badge({
            "value": None,
            "source": "USER_INPUT",
        })
        # Renders with — fallback for the value
        self.assertIn("—", html)
        self.assertNotIn("Traceback", html)

    def test_metric_glossary_unknown_key(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip("totally_made_up_metric")
        # Falls back to title-cased key, no crash
        self.assertIn("Totally Made Up Metric", html)
        self.assertNotIn("Traceback", html)

    def test_breadcrumb_empty_returns_empty(self):
        from rcm_mc.ui.nav import breadcrumb
        self.assertEqual(breadcrumb([]), "")

    def test_search_bar_renders_with_no_data(self):
        from rcm_mc.ui.global_search import (
            render_search_bar,
        )
        html = render_search_bar()
        self.assertIn(
            "global-search-input", html)


# ── Data-layer empty / insufficient input ───────────────────

class TestDataLayerEmpty(unittest.TestCase):
    def test_inventory_data_sources_empty_store(self):
        from rcm_mc.data.catalog import (
            inventory_data_sources,
            compute_data_estate_summary,
        )
        store, tmp = _empty_store()
        try:
            # No tables → no entries, no crash
            entries = inventory_data_sources(store)
            self.assertIsInstance(entries, list)
            summary = compute_data_estate_summary(entries)
            self.assertEqual(summary["n_sources"],
                             len(entries))
        finally:
            tmp.cleanup()

    def test_global_search_empty_store(self):
        from rcm_mc.ui.global_search import search
        store, tmp = _empty_store()
        try:
            results = search(store, "denial")
            # Metrics still searchable from the glossary
            self.assertGreater(len(results), 0)
            # No deals/packets in empty store →
            # those source results are absent but no
            # exception
        finally:
            tmp.cleanup()

    def test_preferences_missing_user(self):
        from rcm_mc.ui.preferences import (
            get_preferences, list_favorite_hospitals,
            is_favorite_hospital,
        )
        store, tmp = _empty_store()
        try:
            # Returns defaults for never-saved user
            prefs = get_preferences(store, "ghost")
            self.assertEqual(prefs.username, "ghost")
            self.assertEqual(
                prefs.favorite_hospitals, [])
            self.assertEqual(
                list_favorite_hospitals(
                    store, "ghost"), [])
            self.assertFalse(
                is_favorite_hospital(
                    store, "ghost", "010001"))
        finally:
            tmp.cleanup()

    def test_preferences_empty_username(self):
        from rcm_mc.ui.preferences import (
            get_preferences, list_favorite_hospitals,
        )
        store, tmp = _empty_store()
        try:
            # Empty username is gracefully handled
            prefs = get_preferences(store, "")
            self.assertEqual(prefs.username, "")
            self.assertEqual(
                list_favorite_hospitals(store, ""), [])
        finally:
            tmp.cleanup()


# ── ML predictor minimum-row guards ─────────────────────────

class TestPredictorEmptyGuards(unittest.TestCase):
    def test_train_with_too_few_rows_raises(self):
        """Predictors must raise ValueError on insufficient
        data, not crash with a numpy / linalg error."""
        import numpy as np
        from rcm_mc.ml.trained_rcm_predictor import (
            train_ridge_with_cv,
        )
        X = np.random.normal(0, 1, size=(8, 3))
        y = np.random.normal(0, 1, size=8)
        with self.assertRaises(ValueError):
            train_ridge_with_cv(
                X, y,
                feature_names=["a", "b", "c"],
                target_metric="x")

    def test_compute_service_line_empty_records(self):
        from rcm_mc.ml.service_line_profitability import (
            compute_service_line_profitability,
            analyze_hospital_service_lines,
        )
        # Empty input — no crash, returns []
        self.assertEqual(
            compute_service_line_profitability([]), [])
        # The composer raises ValueError with a clear message
        with self.assertRaises(ValueError) as ctx:
            analyze_hospital_service_lines([])
        self.assertIn(
            "empty", str(ctx.exception).lower())

    def test_payer_mix_zero_rejected(self):
        from rcm_mc.ml.payer_mix_cascade import PayerMix
        m = PayerMix(
            medicare=0, medicaid=0,
            commercial=0, self_pay=0)
        with self.assertRaises(ValueError):
            m.normalize()

    def test_regime_detection_empty_series(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
            analyze_hospital_regime,
        )
        # Empty series → handled gracefully
        result = analyze_metric_regime("revenue", [])
        self.assertEqual(result.n_periods, 0)
        self.assertEqual(
            result.current_regime, "stable")
        # Multi-metric with empty dict
        report = analyze_hospital_regime({})
        self.assertEqual(
            report.overall_regime, "stable")


# ── HTTP-level no-crash on empty-portfolio routes ──────────

class TestHTTPEmptyResilience(unittest.TestCase):
    """End-to-end: spin up server with empty DB, hit every
    recent endpoint, verify 200 / no 500 / no traceback in body."""

    def test_no_500_with_empty_db(self):
        import socket, threading, time
        import urllib.request
        from rcm_mc.server import build_server

        def _free_port():
            with socket.socket(socket.AF_INET,
                               socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            port = _free_port()
            srv, _h = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                endpoints = [
                    "/?v3=1",
                    "/data/catalog",
                    "/models/quality",
                    "/models/importance",
                    "/deal/ghost/profile",
                    "/api/global-search?q=x",
                ]
                failures = []
                for ep in endpoints:
                    url = (f"http://127.0.0.1:"
                           f"{port}{ep}")
                    try:
                        with urllib.request.urlopen(
                                url, timeout=10) as resp:
                            body = resp.read().decode(
                                errors="replace")
                            if resp.status == 500:
                                failures.append(
                                    f"{ep} → 500")
                            if "Traceback" in body:
                                failures.append(
                                    f"{ep}: traceback "
                                    f"in body")
                    except urllib.error.HTTPError as e:
                        if e.code == 500:
                            failures.append(
                                f"{ep} → 500")
                self.assertEqual(failures, [])
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
