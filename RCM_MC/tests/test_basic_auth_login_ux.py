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
import urllib.parse

from rcm_mc.server import RCMHandler, build_server
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
    def __init__(self, auth=None, auth_ui=None):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.port = _free_port()
        self.server, _ = build_server(port=self.port, db_path=self.tf.name,
                                      auth=auth, auth_ui=auth_ui)
        self.t = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.t.start()

    def get(self, path, auth_header=None, accept=None, cookie=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        if accept:
            headers["Accept"] = accept
        if cookie:
            headers["Cookie"] = cookie
        c.request("GET", path, headers=headers)
        r = c.getresponse()
        body = r.read().decode("utf-8", "replace")
        status, loc = r.status, r.getheader("Location")
        cache = r.getheader("Cache-Control")
        self._last_www_auth = r.getheader("WWW-Authenticate")
        c.close()
        return status, loc, cache, body

    def post(self, path, fields, accept=None, cookie=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body = urllib.parse.urlencode(fields)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if accept:
            headers["Accept"] = accept
        if cookie:
            headers["Cookie"] = cookie
        c.request("POST", path, body=body, headers=headers)
        r = c.getresponse()
        rbody = r.read().decode("utf-8", "replace")
        status, loc = r.status, r.getheader("Location")
        set_cookies = r.msg.get_all("Set-Cookie") or []
        c.close()
        return status, loc, set_cookies, rbody

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


def _session_cookie(set_cookies):
    for sc in set_cookies:
        if sc.startswith("rcm_session="):
            return sc.split(";", 1)[0]
    return None


class StyledFormLoginTests(unittest.TestCase):
    """Styled form-login mode (RCM_MC_AUTH + RCM_MC_AUTH_UI=form).

    The shared credential is presented via the pretty in-app /login form
    backed by a session cookie — never the native Basic Auth popup.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = _Server(auth=_AUTH, auth_ui="form")

    @classmethod
    def tearDownClass(cls):
        cls.srv.close()

    def setUp(self):
        # _login_fail_log is class-level on RCMHandler and shared across
        # instances; clear it so a prior test's bad attempt can't trip
        # this one's rate limiter.
        RCMHandler._login_fail_log.clear()

    def test_app_unauthenticated_redirects_to_login_not_popup(self):
        # No Basic Auth popup: a browser GET to /app gets a friendly 303
        # to the styled /login form, with NO WWW-Authenticate header.
        status, loc, _, _ = self.srv.get("/app", accept="text/html")
        self.assertIn(status, (302, 303))
        self.assertEqual(loc, "/login?next=%2Fapp")
        self.assertIsNone(self.srv._last_www_auth)

    def test_login_renders_the_styled_form(self):
        # /login renders the in-app form (not a redirect to /app).
        status, loc, _, body = self.srv.get("/login?next=%2Fapp",
                                            accept="text/html")
        self.assertEqual(status, 200)
        self.assertIsNone(loc)
        self.assertIn("password", body.lower())

    def test_valid_shared_credential_creates_session_and_redirects(self):
        status, loc, cookies, _ = self.srv.post(
            "/api/login",
            {"username": _TEST_USER, "password": _TEST_PASS, "next": "/app"},
            accept="text/html",
        )
        self.assertIn(status, (302, 303))
        self.assertEqual(loc, "/app")
        sess = _session_cookie(cookies)
        self.assertIsNotNone(sess)
        # The minted session authenticates /app (200, no popup).
        s2, _, _, _ = self.srv.get("/app", accept="text/html", cookie=sess)
        self.assertEqual(s2, 200)

    def test_invalid_credential_shows_invalid_message(self):
        status, loc, cookies, _ = self.srv.post(
            "/api/login",
            {"username": _TEST_USER, "password": "wrongpass", "next": "/app"},
            accept="text/html",
        )
        self.assertIn(status, (302, 303))
        self.assertIn("/login?err=", loc)
        self.assertIn("Invalid", urllib.parse.unquote(loc))
        self.assertIsNone(_session_cookie(cookies))

    def test_no_native_popup_for_browser_get(self):
        # The defining contract: form mode never sends WWW-Authenticate to
        # a browser navigation (that would pop the native prompt).
        status, _, _, _ = self.srv.get("/app", accept="text/html")
        self.assertNotEqual(status, 401)
        self.assertIsNone(self.srv._last_www_auth)

    def test_marketing_cta_targets_login_form_in_form_mode(self):
        # Form mode keeps the in-app /login CTA (Basic mode points at /app).
        status, _, _, body = self.srv.get("/")
        self.assertEqual(status, 200)
        self.assertIn("/login?next=/app", body)


if __name__ == "__main__":
    unittest.main()
