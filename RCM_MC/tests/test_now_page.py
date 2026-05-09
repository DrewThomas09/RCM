"""tests for ``/now`` 30-second view.

PROMPTS.md Phase 4 / Prompt 54. The page must render fast, fit
above the fold, and gracefully degrade when tables are missing
(e.g. a fresh DB on first server boot).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


class NowPageRenders(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls.tmp = tempfile.mkdtemp(prefix="rcm_p54_")
        cls.db = os.path.join(cls.tmp, "p.db")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def test_now_returns_200(self) -> None:
        with urllib.request.urlopen(self.base + "/now", timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_now_contains_five_lines(self) -> None:
        with urllib.request.urlopen(self.base + "/now", timeout=5) as r:
            body = r.read().decode()
        # Five li elements inside the now-list.
        self.assertIn("now-list", body)
        # At least five <li tags inside the list.
        list_start = body.find("now-list")
        list_end = body.find("</ul>", list_start)
        section = body[list_start:list_end]
        self.assertGreaterEqual(section.count("<li"), 5)

    def test_now_renders_under_500ms(self) -> None:
        # Spec: page should render fast (5 aggregations).
        t0 = time.time()
        with urllib.request.urlopen(self.base + "/now", timeout=5) as r:
            r.read()
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.5)


class NowPageRendersDirectly(unittest.TestCase):
    """Calling render_now() with a missing-table DB must not crash."""

    def test_empty_db_does_not_crash(self) -> None:
        import tempfile
        from rcm_mc.ui.now_page import render_now

        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            html = render_now(tf.name)
        self.assertIn("now-list", html)


class NowPageInPaletteRegistry(unittest.TestCase):
    """The cmd-K palette default catalog must include /now so the
    keyboard shortcut path reaches the page out of the box."""

    def test_now_route_in_default_palette(self) -> None:
        from rcm_mc.ui._chartis_kit_v2 import _DEFAULT_PALETTE_ROUTES
        routes = [r["route"] for r in _DEFAULT_PALETTE_ROUTES]
        self.assertIn("/now", routes)


if __name__ == "__main__":
    unittest.main()
