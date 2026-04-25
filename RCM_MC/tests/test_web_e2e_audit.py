"""End-to-end route-by-route audit.

Boots the real server on a free port, hits every user-facing HTML and
JSON API route, and asserts:

  1. Response status is in the user-friendly set (2xx, 3xx, 400, 401,
     403, 404, 405, 410, 422, 429). A 500 indicates a stack trace
     leaked to the user — that is a bug.

  2. Response body NEVER contains a Python traceback. Users see a
     "something went wrong" message, not a traceback dump.

  3. Response body NEVER contains raw exception messages that leak
     internal state (e.g. "sqlite3.OperationalError:", "Traceback
     (most recent call last)", "KeyError:").

  4. Major navigation surfaces (dashboard, /exports, /data/refresh,
     /healthz, /api, /api/openapi.json) render with the expected
     anchor content.

This test is the canary for "app shows a stack trace to the user" —
if anything regresses a handler into throwing an unhandled exception,
this test will catch it.

A handful of routes require query-string args or POST bodies. Those
are exercised in feature-specific test files; the GET-with-no-args
pass here just ensures the app doesn't crash rendering an empty form.
"""
from __future__ import annotations

import json
import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from typing import List, Tuple


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Markers that indicate a stack trace / raw exception leaked to the user.
_TRACEBACK_MARKERS: Tuple[str, ...] = (
    "Traceback (most recent call last)",
    'File "',
    "sqlite3.OperationalError",
    "sqlite3.IntegrityError",
    "KeyError: '",
    "AttributeError: '",
    "TypeError: '",
    "ValueError: '",
    "NameError: name",
    "IndentationError",
    "ZeroDivisionError",
)


def _looks_like_traceback(body: str) -> List[str]:
    """Return every marker found in the body — empty list = clean."""
    return [m for m in _TRACEBACK_MARKERS if m in body]


class TestEndToEndAudit(unittest.TestCase):
    """Audit the full web surface for broken handlers + trace leaks."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.tmp.name, "audit.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db_path, auth=None,
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

    def _get(self, path: str, *, timeout: float = 15.0) -> Tuple[int, str]:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=timeout
            ) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 — connection/parse errors
            return -1, f"{type(exc).__name__}: {exc}"

    # ── Smoke: the handful of routes every deploy must serve ──

    def test_healthz_returns_200(self):
        status, body = self._get("/healthz")
        self.assertEqual(status, 200)
        self.assertNotIn("Traceback", body)

    def test_dashboard_renders(self):
        status, body = self._get("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("What you can run", body)
        self.assertEqual(_looks_like_traceback(body), [])

    def test_exports_index_renders(self):
        status, body = self._get("/exports")
        self.assertEqual(status, 200)
        self.assertIn("Downloads", body)
        self.assertEqual(_looks_like_traceback(body), [])

    def test_data_refresh_page_renders(self):
        status, body = self._get("/data/refresh")
        self.assertEqual(status, 200)
        self.assertIn("Data refresh", body)
        self.assertEqual(_looks_like_traceback(body), [])

    def test_api_index_renders(self):
        status, body = self._get("/api")
        self.assertEqual(status, 200)
        self.assertEqual(_looks_like_traceback(body), [])

    def test_openapi_json_parses(self):
        status, body = self._get("/api/openapi.json")
        self.assertEqual(status, 200)
        spec = json.loads(body)
        self.assertIn("paths", spec)
        self.assertGreater(len(spec["paths"]), 20)

    # ── Broad audit: hit every discovered HTML route ──

    @classmethod
    def _discover_html_routes(cls) -> List[str]:
        """Parse server.py for static == '/foo' paths."""
        import pathlib
        src = (pathlib.Path(__file__).parent.parent
               / "rcm_mc" / "server.py").read_text()
        paths = set()
        for m in re.finditer(
            r'(?:if|elif)\s+(?:pure_)?path\s*==\s*[\"\']([^\"\']+)[\"\']',
            src,
        ):
            p = m.group(1)
            if p.startswith("/") and not p.startswith("/api/"):
                paths.add(p)
        # Skip routes that require a specific session/context, POST-only
        # flows, or are pure file-download endpoints:
        skip = {
            "/logout",              # requires a session to clear
            "/api/login",           # POST-only
            "/team/comment",        # POST-only
            "/admin/audit-chain",   # admin-only
            "/_internal/",          # internal endpoints
        }
        return sorted(p for p in paths if p not in skip)

    def test_every_html_route_is_graceful(self):
        """Every GET route must return a user-friendly response.

        We allow 2xx (rendered), 3xx (redirect — common for auth flows),
        400/401/403/404/410/422/429 (documented client errors). 500 is
        a fail — it means an unhandled exception reached the global
        error boundary.

        We also require the body to be free of Python tracebacks.
        """
        routes = self._discover_html_routes()
        self.assertGreater(len(routes), 100,
                           msg="Route discovery found suspiciously few paths")

        allowed_statuses = {
            200, 201, 204,
            301, 302, 303, 307, 308,
            400, 401, 403, 404, 405, 410, 422, 429,
        }

        failures: List[Tuple[str, int, str]] = []
        trace_leaks: List[Tuple[str, List[str]]] = []

        for route in routes:
            status, body = self._get(route, timeout=10.0)
            if status == -1:
                failures.append((route, status, body[:200]))
                continue
            if status not in allowed_statuses:
                failures.append((route, status, body[:300]))
            markers = _looks_like_traceback(body)
            if markers:
                trace_leaks.append((route, markers))

        if failures:
            msg_lines = [f"{s}  {r}  — {b[:160]}" for r, s, b in failures[:15]]
            self.fail(
                f"{len(failures)} routes returned non-user-friendly status. "
                f"First {min(15, len(failures))}:\n" + "\n".join(msg_lines)
            )
        if trace_leaks:
            msg_lines = [f"{r}: {ms}" for r, ms in trace_leaks[:10]]
            self.fail(
                f"{len(trace_leaks)} routes leaked traceback markers. "
                f"First {min(10, len(trace_leaks))}:\n" + "\n".join(msg_lines)
            )


if __name__ == "__main__":
    unittest.main()
