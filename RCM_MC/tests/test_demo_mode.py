"""Demo Mode — the in-app /demo page, downloads, and one-click load.

Settings → Demo Mode loads a credible KKR healthcare portfolio so the whole
console populates. These tests lock in: the page renders with the deals + load
action + downloads, the JSON/CSV ingestion files download, the Settings card
links to it, and POST /demo/load actually seeds the workspace (after which the
page flips to the 'loaded' state).
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # don't follow — we assert on the 3xx itself


class TestDemoPageRender(unittest.TestCase):
    def test_render_states(self):
        from rcm_mc.ui.demo_page import render_demo_page
        not_loaded = render_demo_page(loaded=False, deal_count=0)
        loaded = render_demo_page(loaded=True, deal_count=13)
        # The load action (form) is present only when not loaded; the loaded
        # state replaces it with the command-center entry point.
        self.assertIn('action="/demo/load"', not_loaded)
        self.assertNotIn('action="/demo/load"', loaded)
        self.assertIn("Open command center", loaded)
        for nm in ("Cotiviti", "Envision", "BrightSpring"):
            self.assertIn(nm, not_loaded)
        self.assertIn("/demo/download/kkr-deals.json", not_loaded)


class TestDemoRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        cls.srv, _ = build_server(
            port=cls.port, db_path=os.path.join(cls.tmp.name, "p.db"),
            host="127.0.0.1")
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        time.sleep(0.3)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=25) as r:
            return r.getcode(), r.headers.get("Content-Type", ""), r.read()

    def test_demo_page_lists_deals_and_action(self):
        code, ctype, body = self._get("/demo")
        b = body.decode("utf-8", "replace")
        self.assertEqual(code, 200)
        self.assertIn("Load KKR demo portfolio", b)
        self.assertIn("Cotiviti", b)
        self.assertIn("Envision", b)

    def test_settings_has_demo_card(self):
        code, _, body = self._get("/settings")
        b = body.decode("utf-8", "replace")
        self.assertEqual(code, 200)
        self.assertIn("Demo Mode", b)
        self.assertIn('href="/demo"', b)

    def test_csv_download(self):
        code, ctype, body = self._get("/demo/download/kkr-deals.csv")
        self.assertEqual(code, 200)
        self.assertIn("text/csv", ctype)
        self.assertIn("Cotiviti", body.decode("utf-8", "replace"))

    def test_json_download(self):
        code, ctype, body = self._get("/demo/download/kkr-deals.json")
        self.assertEqual(code, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["sponsor"], "KKR")
        self.assertGreaterEqual(len(payload["deals"]), 13)

    def test_load_seeds_workspace(self):
        # POST /demo/load should seed and redirect (302/303) to the command
        # center; afterwards /demo flips to the loaded state.
        opener = urllib.request.build_opener(_NoRedirect)
        req = urllib.request.Request(self.base + "/demo/load", data=b"",
                                     method="POST")
        try:
            resp = opener.open(req, timeout=30)
            code = resp.getcode()
        except urllib.error.HTTPError as e:
            code = e.code  # 3xx surfaces here with _NoRedirect
        self.assertIn(code, (302, 303))
        # Workspace now populated → /demo shows the loaded state.
        _, _, body = self._get("/demo")
        b = body.decode("utf-8", "replace")
        self.assertIn("Demo portfolio loaded", b)
        self.assertIn("Open command center", b)
        # And the loaded state offers a reversible unload.
        self.assertIn('action="/demo/unload"', b)

    def test_unload_clears_workspace(self):
        # POST /demo/load then /demo/unload should return the workspace to its
        # pre-demo state (the demo is reversible). Run after load via name order
        # isn't guaranteed, so load explicitly first.
        opener = urllib.request.build_opener(_NoRedirect)
        for path in ("/demo/load", "/demo/unload"):
            req = urllib.request.Request(self.base + path, data=b"",
                                         method="POST")
            try:
                code = opener.open(req, timeout=30).getcode()
            except urllib.error.HTTPError as e:
                code = e.code
            self.assertIn(code, (302, 303))
        # After unload, /demo offers the load form again (not the loaded state).
        _, _, body = self._get("/demo")
        b = body.decode("utf-8", "replace")
        self.assertIn('action="/demo/load"', b)


if __name__ == "__main__":
    unittest.main()
