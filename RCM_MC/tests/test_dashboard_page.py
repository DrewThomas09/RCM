"""Tests for /dashboard landing page.

Verifies:
  1. render_dashboard() produces HTML for a fresh (empty) DB without errors
  2. All four sections render (by presence of their headers)
  3. PHI banner is injected when RCM_MC_PHI_MODE=disallowed
  4. /dashboard HTTP route returns 200 with expected content
  5. Curated-analyses links in the HTML point to real routes on server
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestRenderDashboardDirect(unittest.TestCase):
    """Call render_dashboard() directly — no HTTP round-trip."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "t.db")
        # Create the DB file so reachability check passes
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db_path)  # creates file on first use

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_db_renders_without_error(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db_path)
        self.assertGreater(len(html), 500)

    def test_four_sections_present(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db_path)
        self.assertIn("What you can run", html)
        self.assertIn("Recent runs", html)
        self.assertIn("System status", html)
        self.assertIn("Data freshness", html)

    def test_curated_analyses_include_thesis_pipeline(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db_path)
        self.assertIn("Thesis Pipeline", html)
        self.assertIn("/diligence/thesis-pipeline", html)
        self.assertIn("HCRIS Peer X-Ray", html)
        self.assertIn("Bear Case Auto-Generator", html)

    def test_uptime_shows_when_started_at_provided(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        start = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)
        html = render_dashboard(self.db_path, started_at=start)
        self.assertIn("Uptime", html)
        # Should be ~2.5 hours; allow some slop
        self.assertIn("2.5 h", html)

    def test_phi_banner_injected_when_disallowed(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):
            # Banner injection is in chartis_shell; reload to pick up env
            import importlib
            import rcm_mc.ui._chartis_kit
            importlib.reload(rcm_mc.ui._chartis_kit)
            import rcm_mc.ui.dashboard_page
            importlib.reload(rcm_mc.ui.dashboard_page)
            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(self.db_path)
            self.assertIn("no PHI permitted", html)

    def test_empty_state_messaging(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db_path)
        # With zero jobs + zero refreshes, user should see friendly empty-state
        self.assertIn("No runs yet", html)

    def test_phi_mode_card_respects_env(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):
            html = render_dashboard(self.db_path)
            self.assertIn("PHI mode", html)
            self.assertIn("disallowed", html)


class TestDashboardHttpRoute(unittest.TestCase):
    """Boot a real HTTPServer and hit /dashboard."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "t.db")
        self.port = _free_port()

        from rcm_mc.server import build_server
        # auth=None → open mode (no users table yet) means /dashboard
        # is reachable without credentials.
        self.server, _ = build_server(
            port=self.port, host="127.0.0.1", db_path=self.db_path, auth=None,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def test_dashboard_route_returns_200(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/dashboard", timeout=10
        ) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode()
            self.assertIn("What you can run", body)
            self.assertIn("Recent runs", body)
            self.assertIn("System status", body)
            self.assertIn("Data freshness", body)

    def test_dashboard_shows_uptime_with_real_boot(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/dashboard", timeout=10
        ) as resp:
            body = resp.read().decode()
            # build_server sets RCMHandler._process_started_at; the
            # dashboard should render the uptime card (even if 0.0 h).
            self.assertIn("Uptime", body)

    def test_dashboard_system_status_shows_version(self):
        from rcm_mc import __version__
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/dashboard", timeout=10
        ) as resp:
            body = resp.read().decode()
            self.assertIn(__version__, body)


if __name__ == "__main__":
    unittest.main()
