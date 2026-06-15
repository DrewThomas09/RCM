"""Tests for the Advanced Analytics UI surface (/diligence/advanced-analytics).

Covers the render path, end-to-end route (real HTTP server, the e2e
pattern from CLAUDE.md), and the nav + palette registration so the
route can't be removed from one place without the test catching it.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing

from rcm_mc.ui.advanced_analytics_page import render_advanced_analytics_page

_ROUTE = "/diligence/advanced-analytics"


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RenderTests(unittest.TestCase):

    def test_renders_shell_and_content(self):
        h = render_advanced_analytics_page()
        self.assertIn("Advanced Analytics", h)
        self.assertIn("EBITDA at Risk", h)
        self.assertIn("Findings", h)
        # Provenance citation keys for the marts should appear in findings.
        self.assertIn("[RA1]", h)
        self.assertIn("[PS1]", h)

    def test_deterministic(self):
        self.assertEqual(
            render_advanced_analytics_page(),
            render_advanced_analytics_page(),
        )

    def test_qs_optional(self):
        # The signature accepts a query-string dict but must not require it.
        self.assertTrue(render_advanced_analytics_page(qs={"x": ["1"]}))


class RegistrationTests(unittest.TestCase):

    def test_in_sub_nav(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = {e["href"] for e in _SUB_NAV["diligence"]}
        self.assertIn(_ROUTE, hrefs)

    def test_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn(_ROUTE, routes)


class RouteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None,
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
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{_ROUTE}", timeout=15,
            ) as resp:
                self.assertEqual(resp.status, 200)
                body = resp.read().decode()
        except urllib.error.HTTPError as e:  # pragma: no cover
            self.fail(f"{_ROUTE} returned {e.code}")
        self.assertIn("Advanced Analytics", body)


if __name__ == "__main__":
    unittest.main()
