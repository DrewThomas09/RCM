"""Blocking shell-bug regression: no legacy second nav rail; one nav system.

Two production bugs this pins:
1. A server post-processor backfilled a `<nav class="ck-subnav">` second rail
   into every topbar page when absent — which became *always*, since the rail
   was removed from the topbar in favor of the mega-menu. Result: a persistent
   second nav bar under the topbar (two competing nav systems). The backfill
   is removed; the rail must not appear on any topbar page.
2. Mega-menu panels could stay open / stack. The single-open controller must
   close on Escape, outside-click, AND clicks on the in-topbar Guide / Search /
   avatar controls (anything not inside a nav group).
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


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class NoSecondRailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def test_no_second_rail_on_topbar_pages(self):
        # The legacy ".ck-subnav" rail element must not be backfilled anywhere.
        for path in ("/app", "/portfolio/map", "/diligence", "/research",
                     "/target-screener"):
            status, html = self._get(path)
            with self.subTest(path=path):
                self.assertEqual(status, 200)
                self.assertIn("ck-topbar", html)                   # one nav system
                self.assertNotIn('<nav class="ck-subnav"', html)   # no second bar
                self.assertIn("ck-nav-mega", html)                 # mega-menu present

    def test_command_center_keeps_active_link_marking(self):
        # Removing the rail must not remove the topbar active-link highlight.
        _, html = self._get("/app")
        self.assertIn('class="active"', html)


class SingleOpenControllerTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.css = chartis_shell(body="<main/>", title="x", active_nav="/app")

    def test_no_menu_open_by_default(self):
        from rcm_mc.ui._chartis_kit import _topbar
        self.assertNotIn("is-open", _topbar("portfolio"))

    def test_controller_closes_on_any_non_group_click(self):
        # Clicking Guide/Search/avatar (in-topbar, not a nav group) closes menus.
        self.assertIn("closest('.ck-nav-group')", self.css)
        self.assertIn("function closeAll", self.css)
        self.assertIn("function openOnly", self.css)
        self.assertIn("'Escape'", self.css)


if __name__ == "__main__":
    unittest.main()
