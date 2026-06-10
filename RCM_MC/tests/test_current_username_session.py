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


class MarketDataRedirectTests(unittest.TestCase):
    """/market-data was a dead link: the Guide context, DQ consumer list and
    5+ related_routes point at the bare slug, but only /map and /state/<ST>
    were served. It now redirects to the canonical national map."""

    def test_bare_slug_redirects_to_map(self):
        import socket as _s, tempfile as _tf, threading as _th, time as _t
        import urllib.request as _u2
        from rcm_mc.server import build_server as _bs
        sk = _s.socket(); sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]; sk.close()
        tmp = _tf.mkdtemp()
        srv, _ = _bs(port=port, host="127.0.0.1",
                     db_path=os.path.join(tmp, "m.db"), auth=None)
        th = _th.Thread(target=srv.serve_forever, daemon=True)
        th.start(); _t.sleep(0.2)
        try:
            class _NR(_u2.HTTPRedirectHandler):
                def redirect_request(self, *a, **k):
                    return None
            op = _u2.build_opener(_NR)
            try:
                r = op.open(f"http://127.0.0.1:{port}/market-data", timeout=10)
                code, loc = r.status, r.headers.get("Location", "")
            except _u2.HTTPError as e:
                code, loc = e.code, e.headers.get("Location", "")
            self.assertIn(code, (301, 302, 303))
            self.assertEqual(loc, "/market-data/map")
        finally:
            srv.shutdown(); srv.server_close(); th.join(timeout=5)


class PipelineAddBedsOverflowTests(unittest.TestCase):
    """POST /pipeline/add 500'd on beds=1e309 (int(inf) OverflowError,
    uncaught) and on 1e24 (overflows SQLite 64-bit INTEGER on insert).
    Both now clamp to [0, 100000]."""

    def test_overflow_beds_values_do_not_500(self):
        import socket as _s, tempfile as _tf, threading as _th, time as _t
        import urllib.parse as _up, urllib.request as _u2, urllib.error as _ue
        from rcm_mc.server import build_server as _bs
        sk = _s.socket(); sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]; sk.close()
        tmp = _tf.mkdtemp()
        srv, _ = _bs(port=port, host="127.0.0.1",
                     db_path=os.path.join(tmp, "p.db"), auth=None)
        th = _th.Thread(target=srv.serve_forever, daemon=True)
        th.start(); _t.sleep(0.2)
        try:
            for v in ("1e309", "999999999999999999999999", "nan", "-5"):
                data = _up.urlencode({"ccn": "450358", "name": "T",
                                      "state": "TX", "beds": v}).encode()
                req = _u2.Request(f"http://127.0.0.1:{port}/pipeline/add",
                                  data=data, method="POST")
                try:
                    code = _u2.urlopen(req, timeout=20).status
                except _ue.HTTPError as e:
                    code = e.code
                self.assertLess(code, 500, f"beds={v} -> {code}")
        finally:
            srv.shutdown(); srv.server_close(); th.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
