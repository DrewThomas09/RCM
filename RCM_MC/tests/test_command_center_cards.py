"""Command-center add/customize cards — functional (was a disabled stub).

The /app dossier grid's "Customize" and "+ Add card" buttons used to be
disabled "coming soon" placeholders. They now drive a real, cookie-persisted
card layout: a customize panel toggles each card on/off; POST /app/cards saves
the hidden set in ck_cards_hidden; the grid filters hidden cards. Re-checking a
hidden card is the "add card" path. These tests lock that in.
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class TestCardRegistryAndPanel(unittest.TestCase):
    def test_registry_and_panel(self):
        from rcm_mc.ui.chartis._app_grid import (
            _CARD_ORDER, _CARD_IDS, _customize_panel,
        )
        self.assertGreaterEqual(len(_CARD_ORDER), 10)
        self.assertEqual(len(_CARD_IDS), len(_CARD_ORDER))
        panel = _customize_panel(hidden={"alerts"})
        self.assertIn('action="/app/cards"', panel)
        self.assertIn("Customize cards", panel)
        # A checkbox per card; the hidden one is unchecked.
        self.assertIn('name="card" value="alerts"', panel)
        self.assertIn('name="card" value="moic" checked', panel)


class TestCardsRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        PortfolioStore(os.path.join(cls.tmp.name, "p.db")).init_db()
        cls.port = _free_port()
        cls.srv, _ = build_server(port=cls.port,
                                  db_path=os.path.join(cls.tmp.name, "p.db"),
                                  host="127.0.0.1")
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        time.sleep(0.3)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _get(self, path, cookie=None):
        req = urllib.request.Request(self.base + path)
        if cookie:
            req.add_header("Cookie", cookie)
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")

    def test_customize_buttons_are_live(self):
        code, b = self._get("/app")
        self.assertEqual(code, 200)
        # No more "coming soon" stub; the buttons link into the panel.
        self.assertNotIn("coming soon", b)
        self.assertIn("/app?customize=1", b)

    def test_customize_panel_renders(self):
        code, b = self._get("/app?customize=1")
        self.assertEqual(code, 200)
        self.assertIn("Customize cards", b)
        self.assertIn('action="/app/cards"', b)

    def test_hide_then_show_round_trip(self):
        from rcm_mc.ui.chartis._app_grid import _CARD_ORDER
        # Hide 'deliverables' by POSTing every card EXCEPT it.
        visible = [cid for cid, _ in _CARD_ORDER if cid != "deliverables"]
        data = "&".join(f"card={c}" for c in visible).encode()
        opener = urllib.request.build_opener(_NoRedirect)
        req = urllib.request.Request(
            self.base + "/app/cards", data=data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            resp = opener.open(req, timeout=25)
            code, setck = resp.getcode(), resp.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as e:
            code, setck = e.code, e.headers.get("Set-Cookie", "")
        self.assertIn(code, (302, 303))
        self.assertIn("ck_cards_hidden=", setck)
        self.assertIn("deliverables", setck)
        cookie = setck.split(";")[0]
        # The grid now omits the Deliverables card.
        _, b = self._get("/app", cookie=cookie)
        self.assertEqual(b.count("Deliverables"), 0)
        # Re-add it: POST with the full set → cookie clears it from hidden.
        full = [cid for cid, _ in _CARD_ORDER]
        data2 = "&".join(f"card={c}" for c in full).encode()
        req2 = urllib.request.Request(
            self.base + "/app/cards", data=data2, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            resp2 = opener.open(req2, timeout=25)
            setck2 = resp2.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as e:
            setck2 = e.headers.get("Set-Cookie", "")
        # hidden set is now empty.
        self.assertIn("ck_cards_hidden=;", setck2 + ";")


if __name__ == "__main__":
    unittest.main()
