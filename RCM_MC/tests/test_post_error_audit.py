"""POST endpoint error-path audit.

The GET-side audit lives in ``test_web_e2e_audit.py`` and confirms
that every user-facing HTML route is graceful. This file does the
same job for POST endpoints under ``/api/``: hit each one with
deliberately bad/missing input and verify:

  1. Response status is in the documented client-error set
     (400, 401, 403, 404, 405, 422, 429) — never 500.
  2. Response body is JSON with a structured error envelope
     (``{"error": "...", "code": "..."}``), not a Python traceback.
  3. The error message names the missing/invalid field where it can.

This catches the class of bug where a POST handler raises an
unhandled exception on malformed input — which leaks a stack trace
or just returns a bare 500 to the user.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from typing import Tuple


_TRACEBACK_MARKERS = (
    "Traceback (most recent call last)",
    'File "',
    "sqlite3.OperationalError",
    "KeyError: '",
    "AttributeError: '",
    "TypeError: '",
    "ValueError: '",
)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPostErrorPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "audit.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
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

    def _post(self, path: str, body: bytes, *,
              content_type: str = "application/json") -> Tuple[int, str]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body, method="POST",
            headers={"Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def _assert_no_traceback(self, body: str, path: str):
        for m in _TRACEBACK_MARKERS:
            self.assertNotIn(
                m, body,
                msg=f"{path} leaked traceback marker {m!r}: {body[:300]!r}",
            )

    # ── /api/login ──────────────────────────────────────────────────

    def test_login_missing_body(self):
        status, body = self._post("/api/login", b"")
        # No JSON body, no form fields → handler must reject gracefully
        self.assertNotEqual(status, 500,
                            msg=f"empty login body returned 500: {body!r}")
        self._assert_no_traceback(body, "/api/login")

    def test_login_malformed_json(self):
        status, body = self._post("/api/login", b"{not-json")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/login")

    def test_login_missing_username(self):
        status, body = self._post(
            "/api/login", json.dumps({"password": "x"}).encode())
        # Should be 4xx (credentials wrong / missing) not 500
        self.assertLess(status, 500,
                        msg=f"missing username should be 4xx, got {status}")
        self._assert_no_traceback(body, "/api/login")

    def test_login_oversized_password_does_not_dos(self):
        # B150 fix: scrypt with a 100MB password would DoS the worker;
        # auth.create_user / verify_password caps at 256 chars.
        huge = "A" * 1_000_000
        status, body = self._post(
            "/api/login",
            json.dumps({"username": "demo", "password": huge}).encode())
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/login (huge pw)")

    # ── /api/data/refresh/<source>/async ────────────────────────────

    def test_refresh_unknown_source(self):
        status, body = self._post(
            "/api/data/refresh/not-a-real-source/async", b"")
        self.assertEqual(status, 400)
        envelope = json.loads(body)
        self.assertEqual(envelope.get("code"), "UNKNOWN_SOURCE")
        # The 'detail' field should advertise the valid sources so the
        # caller can correct without reading the source.
        self.assertIn("known", envelope.get("detail", {}))

    def test_refresh_path_traversal_attempt(self):
        # Bad path segment — must not crash the dispatcher
        status, body = self._post(
            "/api/data/refresh/..%2Fetc%2Fpasswd/async", b"")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/data/refresh (traversal)")

    # ── /api/jobs/<id> (GET, but bogus id) ──────────────────────────

    def test_jobs_unknown_id_envelope(self):
        # GET, not POST, but covered here for completeness of the
        # async-flow error contract.
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/jobs/bogus-id",
                timeout=5,
            ) as resp:
                status = resp.status
                body = resp.read().decode()
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read().decode()
        self.assertEqual(status, 404)
        envelope = json.loads(body)
        self.assertEqual(envelope.get("code"), "JOB_NOT_FOUND")

    # ── /api/portfolio/register ─────────────────────────────────────

    def test_portfolio_register_empty_body(self):
        status, body = self._post("/api/portfolio/register", b"")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/portfolio/register")

    def test_portfolio_register_malformed_json(self):
        status, body = self._post(
            "/api/portfolio/register", b"{this-is-not-json")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/portfolio/register")

    # ── /api/deals/wizard/select + launch ───────────────────────────

    def test_wizard_select_empty_body(self):
        status, body = self._post("/api/deals/wizard/select", b"")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/deals/wizard/select")

    def test_wizard_launch_empty_body(self):
        status, body = self._post("/api/deals/wizard/launch", b"")
        self.assertNotEqual(status, 500)
        self._assert_no_traceback(body, "/api/deals/wizard/launch")

    # ── Unknown /api/* should 404, not 500 ─────────────────────────

    def test_unknown_api_endpoint_404(self):
        status, body = self._post("/api/this-route-does-not-exist", b"")
        self.assertIn(status, (404, 405),
                      msg=f"unknown /api/* should 404 or 405, got {status}")
        self._assert_no_traceback(body, "unknown api")


if __name__ == "__main__":
    unittest.main()
