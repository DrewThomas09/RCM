"""Tests for the commercial-diligence workspace-mode toggle.

Covers the lexicon engine (_workspace_mode), the settings toggle page,
and the live cookie round-trip / ?mode= override through the server.
The mode swaps audience vocabulary (PE Partner <-> Chartis Consulting)
without touching data, routes, or page structure.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request as _u

from rcm_mc.ui import _workspace_mode as wm
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server


class TestLexicon(unittest.TestCase):
    def setUp(self):
        wm.set_workspace_mode(wm.PARTNER)

    def tearDown(self):
        wm.set_workspace_mode(wm.PARTNER)

    def test_partner_is_default(self):
        # A fresh resolve defaults to partner copy (today's strings),
        # which keeps existing page contracts unchanged.
        self.assertEqual(wm.current_workspace_mode(), wm.PARTNER)
        self.assertEqual(wm.term("deal"), "Deal")
        self.assertEqual(wm.term("ic_memo"), "IC Memo")
        self.assertEqual(wm.term("sponsor"), "Sponsor")

    def test_consulting_swaps_vocabulary(self):
        wm.set_workspace_mode(wm.CONSULTING)
        self.assertEqual(wm.term("deal"), "Engagement")
        self.assertEqual(wm.term("ic_memo"), "Diligence Readout")
        self.assertEqual(wm.term("sponsor"), "Client")
        self.assertEqual(wm.term("lp_update"), "Client Briefing")

    def test_explicit_mode_arg_overrides_context(self):
        wm.set_workspace_mode(wm.PARTNER)
        # Passing mode= ignores the current context value.
        self.assertEqual(wm.term("deal", mode=wm.CONSULTING), "Engagement")
        self.assertEqual(wm.term("deal", mode=wm.PARTNER), "Deal")

    def test_unknown_key_degrades_to_itself(self):
        # A missing lexicon key returns the key, never raises.
        self.assertEqual(wm.term("not_a_real_key"), "not_a_real_key")

    def test_unknown_mode_falls_back_to_partner(self):
        resolved = wm.set_workspace_mode("garbage")
        self.assertEqual(resolved, wm.PARTNER)
        self.assertEqual(wm.term("deal"), "Deal")

    def test_every_key_defines_both_modes(self):
        # Lexicon completeness: each key must resolve in both modes
        # so a toggle never produces an empty string.
        for key in wm._TERMS:
            self.assertTrue(wm.term(key, mode=wm.PARTNER))
            self.assertTrue(wm.term(key, mode=wm.CONSULTING))


class TestSettingsTogglePage(unittest.TestCase):
    def setUp(self):
        wm.set_workspace_mode(wm.PARTNER)

    def tearDown(self):
        wm.set_workspace_mode(wm.PARTNER)

    def test_renders_both_cards(self):
        from rcm_mc.ui.settings_pages import render_workspace_mode_page
        html = render_workspace_mode_page()
        self.assertIn("PE Partner", html)
        self.assertIn("Chartis Consulting", html)
        # The toggle POSTs to /settings/workspace.
        self.assertIn('action="/settings/workspace"', html)

    def test_active_card_reflects_current_mode(self):
        from rcm_mc.ui.settings_pages import render_workspace_mode_page
        wm.set_workspace_mode(wm.CONSULTING)
        html = render_workspace_mode_page()
        self.assertIn("ws-card-active", html)
        self.assertIn("ACTIVE", html)


class TestServerRoundTrip(unittest.TestCase):
    def _start(self, tmp: str):
        PortfolioStore(os.path.join(tmp, "p.db"))
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.05)
        return server, port

    def test_get_renders_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/settings/workspace"
                ) as r:
                    body = r.read().decode()
                    self.assertEqual(r.status, 200)
                    self.assertIn("Workspace Mode", body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_sets_cookie_and_redirects(self):
        import urllib.parse as up
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                data = up.urlencode({"mode": "consulting"}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/settings/workspace",
                    data=data, method="POST",
                    headers={"Content-Type":
                             "application/x-www-form-urlencoded",
                             "Accept": "application/json"},
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                    # Cookie set on the response
                    set_cookie = r.headers.get("Set-Cookie", "")
                    self.assertIn("ck_workspace_mode=consulting", set_cookie)
            finally:
                server.shutdown(); server.server_close()

    def test_query_override_switches_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                # ?mode=consulting flips the deal-page eyebrow to ENGAGEMENT
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/settings/workspace?mode=consulting"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("ws-card-active", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
