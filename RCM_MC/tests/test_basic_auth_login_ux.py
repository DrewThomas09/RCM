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

    def get(self, path, auth_header=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        c.request("GET", path, headers=headers)
        r = c.getresponse()
        body = r.read().decode("utf-8", "replace")
        status, loc = r.status, r.getheader("Location")
        cache = r.getheader("Cache-Control")
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


if __name__ == "__main__":
    unittest.main()
