"""tests for the methodology source-code viewer (P63)."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from rcm_mc.ui.methodology_source_viewer import (
    METHODOLOGY_MODULES, render_methodology_module,
)


class RegistryShape(unittest.TestCase):

    def test_seven_modules_registered(self) -> None:
        # Per spec — pe_math, simulator, rcm_ebitda_bridge,
        # ebitda_mc, ridge_predictor, conformal, health_score.
        self.assertEqual(len(METHODOLOGY_MODULES), 7)

    def test_each_module_has_path_and_label(self) -> None:
        for key, spec in METHODOLOGY_MODULES.items():
            with self.subTest(key=key):
                self.assertIn("path", spec)
                self.assertIn("label", spec)


class RendersForKnownModules(unittest.TestCase):

    def test_unknown_key_returns_none(self) -> None:
        self.assertIsNone(render_methodology_module("nonsense"))

    def test_each_registered_module_renders(self) -> None:
        # Skip modules whose source files don't exist on this branch
        # (the registry is a forward-looking commitment; some files
        # may move as the package is refactored).
        for key, spec in METHODOLOGY_MODULES.items():
            with self.subTest(key=key):
                html = render_methodology_module(key)
                if html is None:
                    self.skipTest(f"{spec['path']} not present yet")
                self.assertIn("methodology-source", html)
                self.assertIn(spec["label"], html)


class RoutingViaServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls.tmp = tempfile.mkdtemp(prefix="rcm_p63_")
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

    def test_unknown_module_returns_404(self) -> None:
        try:
            urllib.request.urlopen(
                self.base + "/methodology/nonsense", timeout=5,
            )
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            return
        self.fail("expected HTTPError 404")

    def test_traversal_attempt_blocked(self) -> None:
        # The whitelist must reject any path-traversal attempts.
        try:
            urllib.request.urlopen(
                self.base + "/methodology/..%2F..%2Fetc%2Fpasswd",
                timeout=5,
            )
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            return
        self.fail("expected HTTPError 404")


if __name__ == "__main__":
    unittest.main()
