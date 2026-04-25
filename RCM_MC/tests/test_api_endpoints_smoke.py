"""Systematic API smoke tests — verify every recent + core endpoint
returns sensible responses (200 / proper error / valid JSON, no 500s).

Scope:
  • Every endpoint added in the recent UI/data sprint
    (/data/catalog, /models/quality, /models/importance,
    /deal/<id>/profile, /api/global-search, /?v3=1).
  • Representative legacy endpoints (/api/health,
    /api/system/info, /api/openapi.json, root /) for
    regression coverage.
  • Error-path tests (invalid query strings, missing query
    params, oversized inputs).

The platform's auth defaults to disabled in build_server()
unless RCM_MC_AUTH is set, so we test the no-auth path.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ServerHarness:
    """Spin up the platform server on a free port for a single
    test class. Reusable via setUp/tearDown."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.port = _free_port()
        self.srv = None
        self.thread = None

    def start(self):
        from rcm_mc.server import build_server
        srv, _ = build_server(
            port=self.port, db_path=self.db,
            host="127.0.0.1")
        self.srv = srv
        self.thread = threading.Thread(
            target=srv.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)

    def stop(self):
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()
        self.tmp.cleanup()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path: str, *, timeout: float = 10):
        try:
            return urllib.request.urlopen(
                self.url(path), timeout=timeout)
        except urllib.error.HTTPError as exc:
            return exc


# ── Recently-added endpoints ─────────────────────────────────

class TestRecentEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _ServerHarness()
        cls.h.start()

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_data_catalog(self):
        resp = self.h.get("/data/catalog")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Data Catalog", body)

    def test_models_quality(self):
        resp = self.h.get("/models/quality")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Model Quality", body)

    def test_models_importance(self):
        resp = self.h.get("/models/importance")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Feature Importance", body)

    def test_dashboard_v3(self):
        resp = self.h.get("/?v3=1")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Morning view", body)

    def test_deal_profile_v2_no_packet(self):
        resp = self.h.get("/deal/ghost/profile")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        # Empty-state copy
        self.assertIn("ghost", body)
        self.assertIn("No analysis packet", body)


# ── Global search API ────────────────────────────────────────

class TestGlobalSearchAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _ServerHarness()
        cls.h.start()

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_returns_json(self):
        resp = self.h.get(
            "/api/global-search?q=denial")
        self.assertEqual(resp.status, 200)
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("json", ct)
        data = json.loads(resp.read().decode())
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_empty_query_empty_results(self):
        resp = self.h.get("/api/global-search?q=")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["results"], [])

    def test_no_query_param(self):
        """Missing q parameter shouldn't 500 — should return
        empty."""
        resp = self.h.get("/api/global-search")
        # Either 200 with empty or 400; never 500
        self.assertNotEqual(resp.status, 500)
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            self.assertEqual(data["results"], [])

    def test_special_characters_handled(self):
        """URL-special characters shouldn't crash the search."""
        resp = self.h.get(
            "/api/global-search?q=%26%3C%3E%22")
        self.assertNotEqual(resp.status, 500)

    def test_long_query_handled(self):
        """A 1000-char query should not crash; it might return
        empty results or get truncated."""
        long_q = "a" * 1000
        resp = self.h.get(
            f"/api/global-search?q={long_q}")
        self.assertNotEqual(resp.status, 500)


# ── Core legacy endpoints (regression coverage) ──────────────

class TestCoreEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _ServerHarness()
        cls.h.start()

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_root(self):
        resp = self.h.get("/")
        # Either renders a marketing page (UI v2) or the
        # legacy dashboard
        self.assertEqual(resp.status, 200)

    def test_api_health(self):
        resp = self.h.get("/api/health")
        # Healthcheck should return 200 and JSON
        self.assertEqual(resp.status, 200)
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("json", ct)

    def test_api_openapi_spec(self):
        resp = self.h.get("/api/openapi.json")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        spec = json.loads(body)
        self.assertIn("openapi", spec)
        self.assertIn("paths", spec)

    def test_404_on_nonexistent_path(self):
        resp = self.h.get("/this/does/not/exist")
        # Must be 404, not 500
        self.assertEqual(resp.status, 404)

    def test_data_refresh(self):
        """Existing /data/refresh page should still render."""
        resp = self.h.get("/data/refresh")
        self.assertEqual(resp.status, 200)


# ── Error-path / input-validation regression tests ───────────

class TestErrorPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = _ServerHarness()
        cls.h.start()

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_deal_profile_with_special_chars(self):
        """Path-traversal-style deal_id should not crash —
        either 200 with empty-state or 404."""
        resp = self.h.get(
            "/deal/..%2F..%2Fetc/profile")
        self.assertNotEqual(resp.status, 500)

    def test_data_catalog_with_garbage_query(self):
        resp = self.h.get(
            "/data/catalog?garbage=xyz&drop=table")
        self.assertEqual(resp.status, 200)

    def test_models_quality_with_garbage_query(self):
        resp = self.h.get(
            "/models/quality?garbage=xyz")
        self.assertEqual(resp.status, 200)

    def test_dashboard_v3_with_garbage_query(self):
        resp = self.h.get("/?v3=1&garbage=xyz")
        self.assertEqual(resp.status, 200)


# ── No-500 sanity sweep across known GET endpoints ───────────

class TestNo500Sweep(unittest.TestCase):
    """Bulk check: every endpoint we know about returns
    something that's not a 500.

    Failures here flag actual platform bugs the directive asked
    us to fix."""

    @classmethod
    def setUpClass(cls):
        cls.h = _ServerHarness()
        cls.h.start()

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_endpoint_sweep(self):
        endpoints = [
            "/",
            "/?v3=1",
            "/data/catalog",
            "/data/refresh",
            "/models/quality",
            "/models/importance",
            "/deal/ghost/profile",
            "/api/health",
            "/api/openapi.json",
            "/api/global-search?q=denial",
            "/api/global-search?q=",
            "/exports",
        ]
        failures = []
        for path in endpoints:
            resp = self.h.get(path)
            status = getattr(resp, "status",
                             getattr(resp, "code", 0))
            if status == 500:
                # Capture body for the failure message
                try:
                    body = resp.read().decode(
                        errors="replace")[:200]
                except Exception:
                    body = ""
                failures.append(
                    f"{path} → 500: {body}")
        self.assertEqual(
            failures, [],
            f"{len(failures)} endpoints returned 500: "
            + " | ".join(failures))


if __name__ == "__main__":
    unittest.main()
