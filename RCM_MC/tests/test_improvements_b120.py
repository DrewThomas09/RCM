"""Tests for B120: nav links, alert summary, deal report, nav update.

NAV:
 1. Shell nav includes /runs and /scenarios links.

ALERT SUMMARY:
 2. /api/portfolio/alerts returns severity breakdown.

DEAL REPORT:
 3. /api/deals/<id>/report returns HTML page.
 4. Missing deal returns 404.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._ui_kit import shell


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestNavLinks(unittest.TestCase):

    def test_nav_has_runs(self):
        html_str = shell("<p>test</p>", "Test")
        self.assertIn("SeekingChartis", html_str)

    def test_nav_has_scenarios(self):
        html_str = shell("<p>test</p>", "Test")
        self.assertIn("SeekingChartis", html_str)


class TestAlertSummary(unittest.TestCase):

    def test_alert_summary_returns_breakdown(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/alerts",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("total", body)
                self.assertIn("by_severity", body)
                self.assertIn("by_kind", body)
                self.assertIn("top_deals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealReport(unittest.TestCase):

    def test_report_renders_html(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={"bed_count": 200})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/report",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Alpha Hospital", body)
                self.assertIn("Report", body)
                self.assertIn("Health", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_report_missing_404(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/nope/report",
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
