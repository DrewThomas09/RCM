"""Tests for the story-driven dashboard v3."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestEmptyPortfolio(unittest.TestCase):
    def test_empty_portfolio_renders(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.dashboard_v3 import (
            render_dashboard_v3,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            html = render_dashboard_v3(store)
            self.assertIn("Morning view", html)
            self.assertIn("No deals in the portfolio", html)
            # All 4 narrative sections present
            self.assertIn("Top opportunities", html)
            self.assertIn("Key alerts", html)
            self.assertIn("Recent activity", html)
        finally:
            tmp.cleanup()


class TestHelpers(unittest.TestCase):
    def test_money_formatting(self):
        from rcm_mc.ui.dashboard_v3 import _fmt_money
        self.assertEqual(_fmt_money(1_234), "$1K")
        self.assertEqual(
            _fmt_money(1_500_000), "$1.5M")
        self.assertEqual(
            _fmt_money(2_300_000_000), "$2.30B")
        self.assertEqual(_fmt_money(None), "—")

    def test_pct_formatting(self):
        from rcm_mc.ui.dashboard_v3 import _fmt_pct
        self.assertEqual(_fmt_pct(0.05), "+5.0%")
        self.assertEqual(_fmt_pct(-0.10), "-10.0%")
        self.assertEqual(_fmt_pct(None), "—")

    def test_days_since(self):
        from rcm_mc.ui.dashboard_v3 import _days_since
        self.assertIsNone(_days_since(None))
        self.assertIsNone(_days_since("garbage"))
        # Just-now → 0
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        self.assertEqual(_days_since(now), 0)


class TestHeroStripNarrative(unittest.TestCase):
    def test_no_deals_narrative(self):
        from rcm_mc.ui.dashboard_v3 import _hero_strip
        html = _hero_strip({
            "n_deals": 0, "n_active": 0, "n_archived": 0,
            "total_npr": 0, "total_ebitda": 0,
            "weighted_health": None,
        })
        self.assertIn("No deals", html)
        self.assertIn("Active deals", html)

    def test_high_health_narrative(self):
        from rcm_mc.ui.dashboard_v3 import _hero_strip
        html = _hero_strip({
            "n_deals": 5, "n_active": 5, "n_archived": 0,
            "total_npr": 2_500_000_000,
            "total_ebitda": 250_000_000,
            "weighted_health": 82,
        })
        self.assertIn("good shape", html)
        self.assertIn("growth plays", html)

    def test_mid_health_narrative(self):
        from rcm_mc.ui.dashboard_v3 import _hero_strip
        html = _hero_strip({
            "n_deals": 5, "n_active": 5, "n_archived": 0,
            "total_npr": 2_500_000_000,
            "total_ebitda": 100_000_000,
            "weighted_health": 65,
        })
        self.assertIn("mid-tier", html)
        self.assertIn("underperformers", html)

    def test_low_health_narrative(self):
        from rcm_mc.ui.dashboard_v3 import _hero_strip
        html = _hero_strip({
            "n_deals": 5, "n_active": 5, "n_archived": 0,
            "total_npr": 2_500_000_000,
            "total_ebitda": -50_000_000,
            "weighted_health": 45,
        })
        self.assertIn("material drag", html)
        self.assertIn("restructuring", html)

    def test_health_not_computed_narrative(self):
        from rcm_mc.ui.dashboard_v3 import _hero_strip
        html = _hero_strip({
            "n_deals": 3, "n_active": 3, "n_archived": 0,
            "total_npr": 1_000_000_000,
            "total_ebitda": 80_000_000,
            "weighted_health": None,
        })
        self.assertIn("Health scores not yet computed",
                     html)


class TestOpportunitiesSection(unittest.TestCase):
    def test_renders_table(self):
        from rcm_mc.ui.dashboard_v3 import (
            _opportunities_section,
        )
        opps = [
            {"deal_id": "deal-a",
             "uplift": 5_000_000,
             "current_ebitda": 30_000_000,
             "target_ebitda": 35_000_000,
             "uplift_pct": 0.167},
            {"deal_id": "deal-b",
             "uplift": 3_000_000,
             "current_ebitda": 20_000_000,
             "target_ebitda": 23_000_000,
             "uplift_pct": 0.15},
        ]
        html = _opportunities_section(opps)
        self.assertIn("Top opportunities", html)
        self.assertIn("deal-a", html)
        self.assertIn("deal-b", html)
        # Total uplift mentioned
        self.assertIn("$8.0M", html)

    def test_empty_opportunities(self):
        from rcm_mc.ui.dashboard_v3 import (
            _opportunities_section,
        )
        html = _opportunities_section([])
        self.assertIn("No realized EBITDA uplift", html)


class TestAlertsSection(unittest.TestCase):
    def test_no_alerts(self):
        from rcm_mc.ui.dashboard_v3 import _alerts_section
        html = _alerts_section([])
        self.assertIn("Nothing demanding your decision",
                     html)
        self.assertIn("All clear", html)

    def test_alerts_rendered(self):
        from rcm_mc.ui.dashboard_v3 import _alerts_section
        alerts = [
            {"deal_id": "deal-x", "kind": "covenant",
             "severity": "critical",
             "message": "Covenant breach on deal-x"},
            {"deal_id": "deal-y", "kind": "variance",
             "severity": "medium",
             "message": "EBITDA -8% vs plan on deal-y"},
        ]
        html = _alerts_section(alerts)
        # User-supplied strings are HTML-escaped — verify
        # the message text appears verbatim
        self.assertIn("Covenant breach on deal-x", html)
        self.assertIn("EBITDA -8% vs plan on deal-y", html)
        # Critical badge surfaces
        self.assertIn("requiring partner attention", html)
        # Severity badges
        self.assertIn("critical", html)


class TestActivitySection(unittest.TestCase):
    def test_no_activity(self):
        from rcm_mc.ui.dashboard_v3 import (
            _activity_section,
        )
        html = _activity_section([])
        self.assertIn("No recent activity", html)
        self.assertIn("data is steady", html)

    def test_activity_renders(self):
        from rcm_mc.ui.dashboard_v3 import (
            _activity_section,
        )
        activity = [
            {"deal_id": "deal-a",
             "kind": "packet_built",
             "label": "Analysis packet built (today)",
             "days": 0},
            {"deal_id": "deal-b",
             "kind": "packet_built",
             "label": "Analysis packet built (3d ago)",
             "days": 3},
        ]
        html = _activity_section(activity)
        self.assertIn("deal-a", html)
        self.assertIn("today", html)
        self.assertIn("3d ago", html)


class TestHTTPRoute(unittest.TestCase):
    def test_v3_query_param(self):
        from rcm_mc.server import build_server
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
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/?v3=1",
                        timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode()
                    self.assertIn("Morning view", body)
                    self.assertIn(
                        "Top opportunities", body)
                    self.assertIn("Key alerts", body)
                    self.assertIn("Recent activity", body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
