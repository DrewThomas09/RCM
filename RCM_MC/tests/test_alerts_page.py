"""E2E test for /alerts after Phase 2 migration to chartis_shell.

The /alerts route was rendering through the legacy ``shell()`` helper
with ~150 lines of inline HTML composition in
``server._route_alerts``. Phase 2 extracts the body composition to
``rcm_mc/ui/alerts_page.py::render_alerts(store, ...)`` and routes
the page through ``chartis_shell`` so it inherits the v5 design
chrome (Inter Tight type, #1F4E78 accent, dark mode default,
JetBrains Mono numerics).

Asserts:
  - GET /alerts returns 200 with chartis_shell signal in body.
  - Empty-state copy ("Portfolio looks clean") still renders.
  - Owner-filter form action="/alerts" survives.
  - Active/all toggle link survives.
  - Title block renders "Alerts" via chartis_shell.
"""
from __future__ import annotations

import os
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


class AlertsPageE2ETests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_get_alerts_returns_200(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertGreater(len(body), 0)
            finally:
                server.shutdown()
                server.server_close()

    def test_alerts_renders_through_chartis_shell(self) -> None:
        """The chartis_shell adds a SeekingChartis title suffix and
        the ck-main wrapper. Both should be present after the
        migration; their absence means the legacy shell crept back."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode("utf-8")
                self.assertIn("Alerts · SeekingChartis", body)
                self.assertIn("ck-main", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_empty_state_copy_preserved(self) -> None:
        """A fresh DB has no deals → no active alerts → empty-state
        card should render with the unchanged copy."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode("utf-8")
                self.assertIn("Portfolio looks clean", body)
                self.assertIn("Evaluators run on every page load", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_owner_filter_form_survives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('action="/alerts"', body)
                self.assertIn('name="owner"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_active_all_toggle_survives(self) -> None:
        """Active-only view shows 'show acked / all' link;
        ?show=all view shows 'active only' link back."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    active_body = r.read().decode("utf-8")
                self.assertIn("show acked / all", active_body)
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/alerts?show=all"
                ) as r:
                    all_body = r.read().decode("utf-8")
                self.assertIn("active only", all_body)
            finally:
                server.shutdown()
                server.server_close()


class AlertsPageRendererTests(unittest.TestCase):
    """Renderer-level checks that don't need an HTTP server."""

    def test_render_alerts_returns_str(self) -> None:
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.alerts_page import render_alerts

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            html = render_alerts(store, show_all=False, owner_filter=None)
            self.assertIsInstance(html, str)
            self.assertGreater(len(html), 100)
            self.assertIn("<!doctype html>", html)
            self.assertIn("Alerts · SeekingChartis", html)

    def test_owner_filter_value_is_html_escaped(self) -> None:
        """User-supplied owner filter must be HTML-escaped to prevent
        XSS via reflected query string (CLAUDE.md invariant)."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.alerts_page import render_alerts

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            html = render_alerts(
                store, show_all=False,
                owner_filter='<script>alert(1)</script>',
            )
            self.assertNotIn('<script>alert(1)</script>', html)
            self.assertIn('&lt;script&gt;', html)


if __name__ == "__main__":
    unittest.main()
