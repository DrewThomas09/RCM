"""Cmd-K palette route verification.

CLAUDE.md's contract: every analytic surface appears in
``_DEFAULT_PALETTE_MODULES`` and "routes in the palette are verified by
tests/test_palette_routes.py" — this file. It pins two things:

  1. Structural integrity of the palette registry (unique ids/routes,
     well-formed entries) so a bad merge can't ship a broken palette.
  2. Every palette route actually serves HTTP 200 on a fresh dev server
     — a palette entry that 404s/500s is a dead jump-target a partner
     hits from the keyboard, the worst kind of ghost page.

The full walk boots one real server (no mocks) and fetches each of the
~200 routes once; runtime is comparable to the tools-index completeness
suite.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from collections import Counter
from contextlib import closing

from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES, _resolve_sub_section


class PaletteRegistryTests(unittest.TestCase):
    def test_entries_are_well_formed(self):
        self.assertGreaterEqual(len(_DEFAULT_PALETTE_MODULES), 150)
        for m in _DEFAULT_PALETTE_MODULES:
            for key in ("id", "title", "route"):
                self.assertIn(key, m, f"palette entry missing {key}: {m}")
                self.assertTrue(str(m[key]).strip(), f"empty {key}: {m}")
            self.assertTrue(m["route"].startswith("/"), m["route"])

    def test_ids_and_routes_are_unique(self):
        ids = Counter(m["id"] for m in _DEFAULT_PALETTE_MODULES)
        routes = Counter(m["route"] for m in _DEFAULT_PALETTE_MODULES)
        self.assertEqual([i for i, c in ids.items() if c > 1], [])
        self.assertEqual([r for r, c in routes.items() if c > 1], [])

    def test_connector_estate_registered(self):
        # The estate browser must be reachable from the keyboard and
        # breadcrumb into the Research section.
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/connector-estate", routes)
        self.assertEqual(_resolve_sub_section("/connector-estate"), "research")


class PaletteRouteWalkTests(unittest.TestCase):
    """Every palette route serves 200 over real HTTP."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            cls._port = s.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "p.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _status(self, route: str):
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{route}", timeout=30)
            resp.read()
            return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception as exc:  # connection reset etc. — report, don't crash
            return f"{type(exc).__name__}: {exc}"

    def test_every_palette_route_serves_200(self):
        failures = []
        for m in _DEFAULT_PALETTE_MODULES:
            status = self._status(m["route"])
            if status != 200:
                failures.append((m["route"], status))
        self.assertEqual(failures, [],
                         f"palette routes not serving 200: {failures}")


if __name__ == "__main__":
    unittest.main()
