"""Tests for /healthz — Heroku / Kubernetes liveness probe convention.

Verifies two things:
  1. /healthz returns 200 "ok"
  2. /healthz bypasses auth (no session cookie, no HTTP basic) — because
     Heroku's router is not logged in.

Uses a real HTTP server on a free port, per the package convention
(see RCM_MC/CLAUDE.md — "no mocks for our own code").
"""
from __future__ import annotations

import socket
import threading
import unittest
import urllib.request
from contextlib import closing

from rcm_mc.server import build_server


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HealthzRouteTest(unittest.TestCase):
    def setUp(self):
        self.port = _free_port()
        # auth=None + no users = open mode; still, /healthz should work even
        # if auth were enforced (see test below which forces multi-user mode).
        self.server, _ = build_server(port=self.port, host="127.0.0.1", auth=None)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_healthz_returns_200(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/healthz", timeout=5
        ) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode()
            self.assertEqual(body.strip(), "ok")

    def test_health_still_returns_200(self):
        # Regression — don't break /health while adding /healthz.
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/health", timeout=5
        ) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode()
            self.assertEqual(body.strip(), "ok")


class HealthzBypassesAuthTest(unittest.TestCase):
    """Force the server into multi-user mode and confirm /healthz still works
    without credentials (Heroku's router never logs in)."""

    def setUp(self):
        self.port = _free_port()
        # auth="u:p" forces HTTP-Basic to be required for non-public paths.
        self.server, _ = build_server(port=self.port, host="127.0.0.1", auth="u:p")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_healthz_bypass_when_auth_required(self):
        # No credentials, no cookie — yet /healthz should return 200.
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/healthz", timeout=5
        ) as resp:
            self.assertEqual(resp.status, 200)

    def test_home_is_gated(self):
        # Sanity: confirm auth *is* being enforced for non-public paths.
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/home")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
