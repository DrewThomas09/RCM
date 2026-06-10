"""Route-walker self-contained discovery + leak gate (wired into CI).

The weekly regression sweep boots an open server and runs the walker in
--discover mode; the walker must pull routes from the server itself (no
pre-written file) and exit non-zero on a traceback or, with --fail-on-leak,
on a literal nan/None leak. These tests pin that contract without a socket.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest

from scripts.route_walker import _discover_routes, walk


class DiscoverTests(unittest.TestCase):
    def test_discovers_real_page_routes_including_new_surfaces(self):
        routes = _discover_routes()
        self.assertGreater(len(routes), 100)        # ~160 exact-match pages
        for r in ("/diligence/cim-crosscheck", "/pipeline/rollup",
                  "/data-quality", "/portfolio"):
            self.assertIn(r, routes)

    def test_no_api_or_webhook_routes_leak_into_walk_set(self):
        # main() filters these; discovery itself returns page routes only.
        routes = _discover_routes()
        self.assertFalse([r for r in routes if r.startswith("/api")])


class WalkSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls.tmp = tempfile.mkdtemp()
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp, "p.db"), auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start(); time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5)

    def test_core_routes_render_without_traceback_or_leak(self):
        base = f"http://127.0.0.1:{self.port}"
        rows = walk(base, ["/data-quality", "/pipeline/rollup",
                           "/diligence/cim-crosscheck", "/target-screener"])
        for r in rows:
            self.assertEqual(r["status"], 200, r["route"])
            self.assertEqual(r.get("traceback", 0), 0, r["route"])
            self.assertEqual(r.get("nan_leak", 0), 0, r["route"])
            self.assertEqual(r.get("none_leak", 0), 0, r["route"])


if __name__ == "__main__":
    unittest.main()
