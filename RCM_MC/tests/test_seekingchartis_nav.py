"""Tests for SeekingChartis navigation — every nav item should render.

Verifies that all 8 nav items return 200 and contain SeekingChartis branding.
Also tests the analysis landing and portfolio overview pages.
"""
from __future__ import annotations

import os as _os
import pytest as _pytest

# v2-shell-only tests. The editorial reskin was reverted at commit
# d8bfac4; these assertions check for v2-only HTML markers (ck-topbar,
# shell-v2 branding) that no longer exist on the legacy shell. Skipped
# unless CHARTIS_UI_V2=1 — flip the env var when v2 ships again to
# automatically re-enable.
pytestmark = _pytest.mark.skipif(
    not _os.environ.get('CHARTIS_UI_V2'),
    reason='v2 editorial shell reverted at d8bfac4; tests assert v2-only markers'
)

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestAnalysisLanding(unittest.TestCase):

    def test_analysis_landing_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/analysis",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Analysis", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("Import Deals", body)
                self.assertIn("Market Heatmap", body)
                self.assertIn("Regression", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_analysis_landing_with_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("test1", name="Test Hospital",
                              profile={"denial_rate": 14, "days_in_ar": 50})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/analysis",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Test Hospital", body)
                self.assertIn("models/dcf", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestPortfolioOverview(unittest.TestCase):

    def test_portfolio_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Portfolio", body)
                self.assertIn("No Deals in Portfolio", body)
                self.assertIn("Screen Hospitals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_portfolio_with_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Hospital Alpha",
                              profile={"denial_rate": 12, "days_in_ar": 45,
                                       "net_revenue": 200e6})
            store.upsert_deal("d2", name="Hospital Beta",
                              profile={"denial_rate": 18, "days_in_ar": 58,
                                       "net_revenue": 150e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Hospital Alpha", body)
                self.assertIn("Hospital Beta", body)
                self.assertIn("All Deals (2)", body)
                self.assertIn("Active Deals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestAllNavItemsRender(unittest.TestCase):
    """Every nav item should return 200 and contain SeekingChartis."""

    def test_all_nav_items_return_200(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                nav_paths = [
                    "/home",
                    "/analysis",
                    "/news",
                    "/market-data/map",
                    "/screen",
                    "/portfolio",
                    "/library",
                    "/settings",
                ]
                for path in nav_paths:
                    with self.subTest(path=path):
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}{path}",
                        ) as r:
                            self.assertEqual(r.status, 200,
                                             f"{path} returned non-200")
                            body = r.read().decode()
                            self.assertIn("<html", body,
                                          f"{path} didn't return HTML")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_shell_v2_pages_have_branding(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                v2_paths = ["/home", "/analysis", "/news",
                            "/market-data/map", "/portfolio", "/library"]
                for path in v2_paths:
                    with self.subTest(path=path):
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}{path}",
                        ) as r:
                            body = r.read().decode()
                            self.assertIn("SeekingChartis", body,
                                          f"{path} missing SeekingChartis branding")
                self.assertIn("ck-topbar", body,
                                          f"{path} missing topbar")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
