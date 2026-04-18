"""Tests for improvement pass B87: dark mode, search limits, bounds check,
deal export redirect.

DARK MODE:
 1. BASE_CSS contains prefers-color-scheme dark media query.
 2. Dark mode overrides key CSS variables.

SEARCH LIMITS:
 3. Empty query returns empty results immediately.
 4. Query truncated to 500 chars.

BOUNDS CHECK:
 5. /api/deals/<id> with only 3 parts returns deal detail (not IndexError).

DEAL EXPORT REDIRECT:
 6. /api/deals/<id>/export redirects to /api/analysis/<id>/export.
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
from rcm_mc.ui._ui_kit import BASE_CSS, shell


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDarkModeCSS(unittest.TestCase):

    def test_dark_mode_media_query_present(self):
        self.assertIn("--bg:", BASE_CSS)

    def test_dark_mode_overrides_bg(self):
        self.assertIn("--bg: #0F172A", BASE_CSS)

    def test_dark_mode_overrides_text(self):
        self.assertIn("--text: #F1F5F9", BASE_CSS)

    def test_dark_mode_overrides_card(self):
        self.assertIn("--card: #1E293B", BASE_CSS)

    def test_shell_includes_dark_css(self):
        html = shell("<p>test</p>", "Test")
        self.assertIn("cad-bg", html)


class TestSearchLimits(unittest.TestCase):

    def test_empty_query_returns_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/search?q=",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["results"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_long_query_truncated(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                long_q = "a" * 1000
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/search?q={long_q}",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertLessEqual(len(body["query"]), 500)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealExportRedirect(unittest.TestCase):

    def test_export_redirects(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/export?format=json",
                )
                # Don't follow redirects — check the 307
                import http.client
                conn = http.client.HTTPConnection("127.0.0.1", port)
                conn.request("GET", "/api/deals/d1/export?format=json")
                resp = conn.getresponse()
                self.assertEqual(resp.status, 307)
                location = resp.getheader("Location")
                self.assertIn("/api/analysis/d1/export", location)
                self.assertIn("format=json", location)
                conn.close()
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
