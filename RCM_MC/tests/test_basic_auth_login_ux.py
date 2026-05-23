"""Production Basic-Auth (RCM_MC_AUTH) login UX.

When RCM_MC_AUTH is set: the marketing Sign In CTA points at /app (browser
Basic Auth prompt), /login redirects to /app instead of showing the in-app
form that rejects the shared credential, and /app stays protected (401
without auth, 200 with). Uses a throwaway test credential — never a real one.
"""
from __future__ import annotations

import base64
import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.server import build_server
from rcm_mc.ui.chartis.marketing_page import render_marketing_page

_TEST_USER = "tuser"
_TEST_PASS = "tpass123"          # throwaway test value, not a real credential
_AUTH = f"{_TEST_USER}:{_TEST_PASS}"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _Server:
    def __init__(self, auth=None):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.port = _free_port()
        self.server, _ = build_server(port=self.port, db_path=self.tf.name,
                                      auth=auth)
        self.t = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.t.start()

    def get(self, path, auth_header=None, accept=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        if accept:
            headers["Accept"] = accept
        c.request("GET", path, headers=headers)
        r = c.getresponse()
        body = r.read().decode("utf-8", "replace")
        status, loc = r.status, r.getheader("Location")
        cache = r.getheader("Cache-Control")
        self._last_www_auth = r.getheader("WWW-Authenticate")
        c.close()
        return status, loc, cache, body

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        import os
        os.unlink(self.tf.name)


class BasicAuthLoginUXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _Server(auth=_AUTH)
        cls.basic = "Basic " + base64.b64encode(_AUTH.encode()).decode()

    @classmethod
    def tearDownClass(cls):
        cls.srv.close()

    def test_every_login_variant_redirects_to_app(self):
        # Plain + the stale-error + the next= variants all redirect; the
        # in-app form never renders under Basic Auth.
        for path in ("/login", "/login?err=Invalid", "/login?next=/app",
                     "/login?tab=request&err=Invalid"):
            status, loc, _, body = self.srv.get(path)
            self.assertIn(status, (302, 303), path)
            self.assertEqual(loc, "/app", path)
            self.assertNotIn("Invalid credentials", body, path)
            self.assertNotIn("name=\"password\"", body.lower(), path)

    def test_login_redirect_is_not_cached(self):
        # Cache-Control: no-store so a stale login page can't keep showing.
        _, _, cache, _ = self.srv.get("/login?err=Invalid")
        self.assertIsNotNone(cache)
        self.assertIn("no-store", cache.lower())

    def test_app_unauthenticated_is_401(self):
        status, _, _, _ = self.srv.get("/app")
        self.assertEqual(status, 401)

    def test_browser_get_app_is_401_not_login_redirect(self):
        # The redirect-loop bug: a BROWSER GET (Accept: text/html) to a
        # protected route under Basic Auth must 401 with WWW-Authenticate,
        # NOT 303 to /login (which would loop with /login -> /app).
        status, loc, _, _ = self.srv.get("/app", accept="text/html")
        self.assertEqual(status, 401)
        self.assertNotEqual(loc, "/login?next=%2Fapp")
        self.assertIsNotNone(self.srv._last_www_auth)
        self.assertIn("Basic", self.srv._last_www_auth)

    def test_no_infinite_loop_login_then_app(self):
        # Follow the chain manually: /login?next=/app -> 303 /app; then a
        # browser GET /app -> 401 (terminates), never back to /login.
        s1, loc1, _, _ = self.srv.get("/login?next=%2Fapp", accept="text/html")
        self.assertIn(s1, (302, 303))
        self.assertEqual(loc1, "/app")
        s2, loc2, _, _ = self.srv.get(loc1, accept="text/html")
        self.assertEqual(s2, 401)            # stops here — no bounce to /login
        self.assertNotEqual(loc2, "/login?next=%2Fapp")

    def test_app_authenticated_is_200(self):
        status, _, _, _ = self.srv.get("/app", auth_header=self.basic)
        self.assertEqual(status, 200)

    def test_marketing_ctas_target_app(self):
        # Sign In AND Open Deal Workspace point at /app, not the /login form.
        status, _, _, body = self.srv.get("/")
        self.assertEqual(status, 200)
        self.assertIn('href="/app"', body)
        self.assertNotIn("/login?next=/app", body)


class NoAuthDefaultTests(unittest.TestCase):
    def test_marketing_keeps_login_form_when_no_basic_auth(self):
        # Without RCM_MC_AUTH the CTA keeps the in-app /login flow.
        html = render_marketing_page(basic_auth=False)
        self.assertIn("/login?next=/app", html)

    def test_login_form_still_renders_without_basic_auth(self):
        # Session/DB-user mode: /login still renders the in-app form (not a
        # redirect) — the loop fix is scoped to Basic Auth mode only.
        srv = _Server(auth=None)
        try:
            status, loc, _, body = srv.get("/login", accept="text/html")
            self.assertEqual(status, 200)
            self.assertIsNone(loc)
            self.assertIn("password", body.lower())   # the form rendered
        finally:
            srv.close()


if __name__ == "__main__":
    unittest.main()
