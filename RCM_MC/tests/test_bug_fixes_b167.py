"""b167 — gate chrome-only JS/HTML on ``show_chrome=False``.

The 2026-05-29 audit walk measured ``/login`` and ``/forgot`` shipping
~177 KB and ~170 KB respectively despite carrying no topbar. Both
pages already pass ``show_chrome=False`` to ``chartis_shell``, but
the shell unconditionally appended every chrome-coupled JS bundle —
shortcuts overlay, command palette, topbar menu handlers, user menu,
quick-capture, default-tour, qpill — ~62 KB of dead weight that has
nothing to operate on without a topbar to host its triggers.

The fix gates the chrome-coupled blocks on ``show_chrome=True``:

    palette HTML + JS   shortcuts modal + JS   user-menu JS
    nav-menu JS         qpill JS               default-tour HTML
    quick-capture HTML

The blocks that stay unconditional are the ones any page may need
even without chrome — CSRF (for form POSTs), toast/flash, and the
``ck_section_intro`` dismiss handler.

End result on a route walk against an empty DB:

    /login   177,058b →  115,174b   (-61.9 KB, -35%)
    /forgot  170,561b →  108,677b   (-61.9 KB, -36%)

Chromed pages are byte-for-byte unchanged.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestChromeFlagGatesAncillaryBundles(unittest.TestCase):
    """Helper-level coverage of the new gating behavior."""

    def test_chromed_default_still_ships_everything(self):
        """The 290+ partner pages that use chartis_shell with default
        show_chrome=True must keep every chrome bundle (no surprise
        loss of Cmd-K, shortcuts, user menu, etc.)."""
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell("<p>page body</p>", title="Demo")
        # Topbar + chrome-coupled bundles all present.
        self.assertIn("ck-palette", html, "palette HTML missing")
        self.assertIn("ck-shortcuts", html,
                      "shortcuts overlay HTML missing")
        # The user-menu JS is one of the chrome-only bundles — its
        # signature handler comment lives near the top of _USER_MENU_JS.
        self.assertIn("ck-user-menu", html,
                      "user-menu chrome bundle missing")

    def test_chromeless_skips_palette_and_overlays(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            "<p>auth body</p>", title="Demo",
            show_chrome=False,
        )
        # Palette, shortcuts modal, tour, quick-capture all skipped.
        self.assertNotIn('class="ck-palette"', html,
                         "palette HTML must be skipped")
        self.assertNotIn('class="ck-shortcuts"', html,
                         "shortcuts HTML must be skipped")
        self.assertNotIn("ck-default-tour", html,
                         "default tour HTML must be skipped")
        self.assertNotIn("ck-quick-capture", html,
                         "quick-capture HTML must be skipped")

    def test_chromeless_keeps_form_essentials(self):
        """CSRF + toast + intro-dismiss are NOT chrome-coupled — any
        page with a form (login, forgot) needs them."""
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            "<form>x</form>", title="Demo",
            show_chrome=False,
        )
        # CSRF JS still present (patches form POSTs with token).
        self.assertIn("csrf", html.lower())
        # Toast container still present.
        self.assertIn("ck-toast", html)

    def test_chromeless_is_smaller_than_chromed(self):
        """The whole point of the patch — chromeless pages are
        materially smaller. Worth asserting because a future
        refactor could re-import a bundle unconditionally."""
        from rcm_mc.ui._chartis_kit import chartis_shell
        chromed = chartis_shell("<p>x</p>", title="Demo")
        chromeless = chartis_shell(
            "<p>x</p>", title="Demo", show_chrome=False)
        # Auth pages should be at least 40 KB smaller. The audit
        # measured -62 KB; 40 KB is a safe floor that catches a
        # future "I re-added the palette" regression while not
        # being brittle to small bundle-size drift.
        delta = len(chromed) - len(chromeless)
        self.assertGreater(delta, 40_000,
                           f"chrome-gating saved only {delta}b "
                           "(expected >40 KB)")


class TestLoginForgotPagesAreLean(unittest.TestCase):
    """End-to-end byte check on the two real chrome-less pages."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        PortfolioStore(cls.db)
        cls.port = _free_port()
        cls.server, _h = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _fetch(self, path: str) -> bytes:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        ) as resp:
            return resp.read()

    def test_login_under_140kb(self):
        body = self._fetch("/login")
        # Pre-patch: 177 KB. Post-patch: ~115 KB. 140 KB is the
        # upper bound that catches a regression while leaving room
        # for legitimate future content additions on the page.
        self.assertLess(len(body), 140_000,
                        f"/login bloated back to {len(body)}b")

    def test_forgot_under_140kb(self):
        body = self._fetch("/forgot")
        self.assertLess(len(body), 140_000,
                        f"/forgot bloated back to {len(body)}b")

    def test_login_still_has_one_h1(self):
        """The chrome-gating must not regress the One-H1 invariant
        landed in #1148-#1151."""
        body = self._fetch("/login").decode()
        self.assertEqual(body.count("<h1"), 1)

    def test_forgot_still_has_one_h1(self):
        body = self._fetch("/forgot").decode()
        self.assertEqual(body.count("<h1"), 1)


if __name__ == "__main__":
    unittest.main()
