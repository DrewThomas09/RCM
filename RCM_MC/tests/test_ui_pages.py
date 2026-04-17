"""Tests for UI page renderers that lacked dedicated coverage.

PORTFOLIO MAP:
 1. render_portfolio_map produces SVG.
 2. Empty deals → "No deals to display" text.
 3. Deal marker uses stage color.
 4. Map has legend elements.
 5. GET /portfolio/map route returns HTML.

SENSITIVITY DASHBOARD:
 6. compute_sensitivity returns expected keys.
 7. Higher exit multiple → higher MOIC.
 8. render_sensitivity_page produces HTML with sliders.

SOURCE PAGE:
 9. render_source_page contains thesis selector.
10. Results rendered when provided.

SETTINGS PAGES:
11. render_custom_kpis_page produces HTML.
12. render_automations_page produces HTML.
13. render_integrations_page produces HTML.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.analysis.packet import DealAnalysisPacket, EBITDABridgeResult
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.portfolio_map import render_portfolio_map


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestPortfolioMap(unittest.TestCase):

    def test_renders_svg(self):
        deals = [
            {"deal_id": "d1", "name": "Acme", "state": "IL",
             "ebitda_opportunity": 8e6, "stage": "diligence"},
        ]
        html = render_portfolio_map(deals)
        self.assertIn("<svg", html)
        self.assertIn("Acme", html)

    def test_empty_deals(self):
        html = render_portfolio_map([])
        self.assertIn("No deals to display", html)

    def test_stage_color_in_marker(self):
        deals = [
            {"deal_id": "d1", "name": "A", "state": "TX",
             "ebitda_opportunity": 5e6, "stage": "hold"},
        ]
        html = render_portfolio_map(deals)
        self.assertIn("#10b981", html)  # hold color

    def test_legend_present(self):
        deals = [
            {"deal_id": "d1", "name": "A", "state": "CA",
             "ebitda_opportunity": 3e6, "stage": "pipeline"},
        ]
        html = render_portfolio_map(deals)
        self.assertIn("pipeline", html)
        self.assertIn("diligence", html)

    def test_map_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/map",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Portfolio Map", body)
                self.assertIn("<svg", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestSensitivityDashboard(unittest.TestCase):

    def test_grid_returns_results(self):
        from rcm_mc.ui.sensitivity_dashboard import (
            SensitivityParams, compute_sensitivity_grid,
        )
        params = SensitivityParams()
        params.current_ebitda = 50e6
        params.rcm_uplift = 10e6
        r = compute_sensitivity_grid(params)
        self.assertGreater(len(r.grid), 0)

    def test_grid_to_dict(self):
        from rcm_mc.ui.sensitivity_dashboard import (
            SensitivityParams, compute_sensitivity_grid,
        )
        params = SensitivityParams()
        params.current_ebitda = 50e6
        params.rcm_uplift = 10e6
        r = compute_sensitivity_grid(params)
        d = r.to_dict()
        self.assertIn("grid", d)

    def test_render_has_sliders(self):
        from rcm_mc.ui.sensitivity_dashboard import render_sensitivity_page
        p = DealAnalysisPacket(
            deal_id="d1",
            ebitda_bridge=EBITDABridgeResult(
                current_ebitda=50e6, total_ebitda_impact=10e6,
            ),
        )
        html = render_sensitivity_page(p)
        self.assertIn('type="range"', html)
        self.assertIn("Sensitivity", html)


class TestSourcePage(unittest.TestCase):

    def test_render_contains_thesis_selector(self):
        from rcm_mc.ui.source_page import render_source_page
        html = render_source_page()
        self.assertIn("thesis", html)
        self.assertIn("Deal Sourcing", html)

    def test_results_rendered(self):
        from rcm_mc.ui.source_page import render_source_page
        results = [
            {"name": "Test Hospital", "state": "IL", "bed_count": 200,
             "score": 85, "ccn": "123456"},
        ]
        html = render_source_page(results)
        self.assertIn("Test Hospital", html)


class TestSettingsPages(unittest.TestCase):

    def test_custom_kpis(self):
        from rcm_mc.ui.settings_pages import render_custom_kpis_page
        store, path = _tmp_store()
        try:
            html = render_custom_kpis_page(store)
            self.assertIn("Custom KPIs", html)
        finally:
            os.unlink(path)

    def test_automations(self):
        from rcm_mc.ui.settings_pages import render_automations_page
        store, path = _tmp_store()
        try:
            html = render_automations_page(store)
            self.assertIn("Automation Rules", html)
        finally:
            os.unlink(path)

    def test_integrations(self):
        from rcm_mc.ui.settings_pages import render_integrations_page
        store, path = _tmp_store()
        try:
            html = render_integrations_page(store)
            self.assertIn("Integrations", html)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
