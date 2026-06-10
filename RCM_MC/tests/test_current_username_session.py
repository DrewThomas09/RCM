"""Regression — _current_username must resolve a real session to a username.

user_for_session returns a dict ({username, display_name, role}); the handler
did ``user.username`` which raised AttributeError into a blanket except, so
EVERY logged-in session resolved to None: owner-gated features (saved
screens) never rendered for partners and audit rows fell back to "api".
Exercise the real path: create a user, log in over HTTP, hit an owner-gated
page, and assert the owner-only chrome renders.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request as _u

from rcm_mc.auth.auth import create_user
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server


class CurrentUsernameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(db)
        create_user(store, "alice", "Str0ng!Pass", role="admin")
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=db)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start(); time.sleep(0.2)
        # login over HTTP → capture the rcm_session cookie
        data = urllib.parse.urlencode(
            {"username": "alice", "password": "Str0ng!Pass"}).encode()

        class _NoRedirect(_u.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = _u.build_opener(_NoRedirect)
        try:
            resp = opener.open(_u.Request(
                f"http://127.0.0.1:{cls.port}/api/login", data=data,
                method="POST"), timeout=10)
            headers = resp.headers
        except _u.HTTPError as e:        # 303 lands here with NoRedirect
            headers = e.headers
        cls.session = ""
        for sc in headers.get_all("Set-Cookie") or []:
            if sc.startswith("rcm_session="):
                cls.session = sc.split(";")[0]
                break

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    def test_login_issued_a_session(self):
        self.assertTrue(self.session, "login must set rcm_session")

    def test_owner_gated_saved_screens_render_for_session_user(self):
        req = _u.Request(
            f"http://127.0.0.1:{self.port}/target-screener?view=saved")
        req.add_header("Cookie", self.session)
        with _u.urlopen(req, timeout=20) as r:
            html = r.read().decode()
        # The owner-only panel + save form must render — before the fix the
        # page silently fell back to the anonymous shareable-URL-only state.
        self.assertIn("Your saved screens", html)
        self.assertIn("/api/target-screener/save", html)

    def test_anonymous_request_is_still_challenged(self):
        # With users present the server stays auth-gated: no session → 401,
        # never a leaked page. (The anonymous shareable-URL fallback only
        # exists on open-mode servers.)
        import urllib.error as _ue
        with _u.urlopen(
            f"http://127.0.0.1:{self.port}/login", timeout=10
        ) as r:
            self.assertEqual(r.status, 200)
        with self.assertRaises(_ue.HTTPError) as ctx:
            _u.urlopen(
                f"http://127.0.0.1:{self.port}/target-screener?view=saved",
                timeout=20)
        self.assertEqual(ctx.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
