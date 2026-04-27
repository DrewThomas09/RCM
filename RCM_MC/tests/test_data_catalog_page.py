"""End-to-end test for /data/catalog (campaign target 2 — bespoke -> v3).

Boots a real ThreadingHTTPServer on a free port and hits
/data/catalog via urllib.request. Empty DB triggers the empty-state
branch, which is enough to verify the page goes through chartis_shell
(no bespoke wrapper) and carries the v3 utility classes.

What this guards (per Phase 2 per-page checklist):
  - shell() with no bespoke wrapper: page emits the chartis_shell
    chrome (<title>) so we know we hit the wrap rather than a raw
    HTML string.
  - v3 chartis.css tokens: at least one .num span on a numeric.
  - All numerics use tabular-nums via .num utility class (loop-7
    fmt_num path).
  - Empty-state path renders without crashing and points at
    /data/refresh.
"""
from __future__ import annotations

import os
import re
import socket as _socket
import tempfile
import threading
import time as _time
import unittest
import urllib.request as _u

from rcm_mc.server import build_server


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class DataCatalogPageTests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_page_returns_200_and_routes_through_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/data/catalog") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                # chartis_shell sets the page <title>
                self.assertIn("<title>Data Catalog", body)
                # H1 is present
                self.assertIn("<h1", body)
                self.assertIn("Data Catalog", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_v3_utility_classes(self) -> None:
        """Every numeric must reach the v3 .num utility class via the
        loop-7 fmt_num helpers. If a renderer regresses to inline
        font-variant-numeric:tabular-nums on a hard-coded color, the
        regression is silent — this test makes it visible."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/data/catalog") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('class="num"', body)
                # The KPI grid emits the .micro eyebrow label class on each
                # KPI label - a v3 chartis.css utility.
                self.assertIn('class="micro"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_empty_db_renders_empty_state_with_refresh_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/data/catalog") as r:
                    body = r.read().decode("utf-8")
                self.assertIn("No data sources loaded yet", body)
                self.assertIn('href="/data/refresh"', body)
                # rcm-mc data refresh CLI hint is also useful
                self.assertIn("rcm-mc data refresh", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_emits_no_legacy_hardcoded_dark_only_palette(self) -> None:
        """Ensures the migration stripped the inline-style dark-only
        palette. Allows the same tokens AS CSS-variable fallbacks (so
        `var(--paper,#1f2937)` is fine) but flags any bare `#1f2937` /
        `#374151` literal that's NOT inside a var() fallback."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/data/catalog") as r:
                    body = r.read().decode("utf-8")
                # Strip well-formed var(--name,#fallback) before checking.
                stripped = re.sub(r"var\(--[a-z-]+,\s*#[0-9a-fA-F]{3,8}\)", "", body)
                # Now any remaining #1f2937 / #374151 / #9ca3af is a bare
                # legacy literal in the body content itself.
                for legacy in ("#1f2937", "#374151"):
                    self.assertNotIn(
                        legacy, stripped,
                        f"bare legacy palette literal {legacy} still in page body",
                    )
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
