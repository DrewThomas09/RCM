"""PR E — unified Target Screener under Source.

One entry that explains and routes to the three overlapping screeners (Thesis
Sourcing, Hospital Screener, Predictive Screener), all over the same CMS/HCRIS
universe. The three old routes are PRESERVED unchanged (backward compatible).
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


class TargetScreenerRenderTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.h = render_target_screener({})

    def test_unified_header_and_cms_label(self):
        self.assertIn("Target Screener", self.h)
        self.assertIn("CMS PUBLIC DATA", self.h)        # market data, not deals

    def test_three_modes_route_to_existing_screeners(self):
        for href in ("/source", "/screen", "/predictive-screener"):
            self.assertIn(f'href="{href}"', self.h)

    def test_explains_same_universe(self):
        low = self.h.lower()
        self.assertIn("same", low)
        self.assertIn("universe", low)
        self.assertIn("promote", low)                   # path into Pipeline

    def test_active_mode_highlights(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.assertIn("is-active", render_target_screener({"mode": ["hospital"]}))


class NavAndRouteTests(unittest.TestCase):
    def test_source_anchor_is_target_screener(self):
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV, _SUB_NAV, _resolve_sub_section
        src = next(n for n in _CORPUS_NAV if n["key"] == "source")
        self.assertEqual(src["href"], "/target-screener")
        self.assertEqual(_SUB_NAV["source"][0]["label"], "Target Screener")
        self.assertEqual(_resolve_sub_section("/target-screener"), "source")


class BackwardCompatTests(unittest.TestCase):
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

    def _status(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_target_screener_route_200(self):
        self.assertEqual(self._status("/target-screener"), 200)

    def test_old_screener_routes_still_work(self):
        # No redirects/deletes — the three screeners are unchanged.
        for path in ("/source", "/screen", "/predictive-screener"):
            self.assertEqual(self._status(path), 200, msg=path)


if __name__ == "__main__":
    unittest.main()
