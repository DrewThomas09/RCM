"""Tests for /portfolio/risk-scan — the morning portfolio risk scan.

The scan answers the partner's Monday-morning question "which of my
deals needs attention today?" in one screen. Every source is
best-effort, so a fresh DB with no deals renders an empty state
(not a crash), and a deal that fails one compute renders with "—"
in that cell (not the whole page).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestEmptyStateRendering(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_deals_renders_without_crashing(self):
        from rcm_mc.ui.portfolio_risk_scan_page import render_portfolio_risk_scan
        html = render_portfolio_risk_scan(self.db)
        self.assertIn("Portfolio risk scan", html)
        self.assertIn("No active deals", html)
        # Empty state links to import + new-deal
        self.assertIn('href="/new-deal"', html)
        self.assertIn('href="/import"', html)


class TestPrioritySort(unittest.TestCase):
    """A TRIPPED-covenant deal must sort above a SAFE-covenant deal,
    regardless of order in the deals table. That's what makes the
    scan "morning view" — worst-first."""

    def test_tripped_beats_safe(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _priority_rank
        tripped = {"covenant_status": "TRIPPED", "alerts": 0,
                   "overdue_deadlines": 0, "score": 80,
                   "snap_age_days": 5}
        safe = {"covenant_status": "SAFE", "alerts": 10,
                "overdue_deadlines": 0, "score": 30,
                "snap_age_days": 5}
        self.assertGreater(_priority_rank(tripped),
                           _priority_rank(safe))

    def test_overdue_deadlines_raise_priority(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _priority_rank
        with_overdue = {"covenant_status": "SAFE",
                        "alerts": 0, "overdue_deadlines": 3,
                        "score": 80, "snap_age_days": 5}
        clean = {"covenant_status": "SAFE", "alerts": 0,
                 "overdue_deadlines": 0, "score": 80,
                 "snap_age_days": 5}
        self.assertGreater(_priority_rank(with_overdue),
                           _priority_rank(clean))

    def test_low_health_increases_priority(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _priority_rank
        low = {"covenant_status": "SAFE", "alerts": 0,
               "overdue_deadlines": 0, "score": 30, "snap_age_days": 5}
        high = {"covenant_status": "SAFE", "alerts": 0,
                "overdue_deadlines": 0, "score": 90, "snap_age_days": 5}
        self.assertGreater(_priority_rank(low), _priority_rank(high))


class TestCellRenderers(unittest.TestCase):
    def test_health_cell_colors_by_band(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _health_cell
        excellent = _health_cell(95, "excellent")
        poor = _health_cell(25, "poor")
        self.assertIn("#d1fae5", excellent)  # green
        self.assertIn("#fee2e2", poor)       # red
        self.assertIn("95", excellent)
        self.assertIn("25", poor)

    def test_covenant_cell_tripped_is_red(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _covenant_cell
        self.assertIn("TRIPPED", _covenant_cell("TRIPPED"))
        self.assertIn("#fee2e2", _covenant_cell("TRIPPED"))

    def test_covenant_unknown_renders_dash(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _covenant_cell
        self.assertIn("—", _covenant_cell(None))

    def test_alerts_threshold(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _alerts_cell
        self.assertIn("#fee2e2", _alerts_cell(5))     # red when ≥3
        self.assertIn("#fef3c7", _alerts_cell(2))     # amber when 1-2
        self.assertIn("#f3f4f6", _alerts_cell(0))     # neutral when 0

    def test_freshness_thresholds(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _freshness_cell
        self.assertIn("#d1fae5", _freshness_cell(3))    # <7d green
        self.assertIn("#fef3c7", _freshness_cell(15))   # <30d amber
        self.assertIn("#fee2e2", _freshness_cell(90))   # ≥30d red
        self.assertIn("never", _freshness_cell(None))

    def test_deadlines_cell_flags_overdue(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _deadlines_cell
        out = _deadlines_cell(5, 2)
        self.assertIn("5", out)
        self.assertIn("overdue", out)
        self.assertIn("#fee2e2", out)


class TestHttpRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_route_returns_200(self):
        """Route resolves on an empty portfolio — empty state
        shows "No active deals yet" rather than the summary strip
        (which only renders once there are deals to scan)."""
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/portfolio/risk-scan",
            timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode()
        self.assertIn("Portfolio risk scan", html)
        self.assertIn("No active deals", html)

    def test_dashboard_links_to_risk_scan(self):
        """The Daily-workflow section must lead with the risk scan."""
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/dashboard",
            timeout=10,
        ) as resp:
            html = resp.read().decode()
        self.assertIn('/portfolio/risk-scan', html)
        self.assertIn('Portfolio risk scan', html)

    def test_palette_includes_risk_scan(self):
        """Cmd-K should surface the risk scan as a Go command."""
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/dashboard",
            timeout=10,
        ) as resp:
            html = resp.read().decode()
        # Legacy palette entry
        self.assertIn("Portfolio risk scan", html)


class TestGatherGracefulFailure(unittest.TestCase):
    def test_fresh_db_returns_empty_not_crash(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db)
            from rcm_mc.ui.portfolio_risk_scan_page import _gather_per_deal
            out = _gather_per_deal(db)
            self.assertEqual(out, [])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
