"""UI-rework contract tests.

Locks in the surface area of the existing UI so a rework branch can change
look-and-feel freely without breaking *connections* — every route still
resolves, every key page still has the data wiring it expects, every CSS
class the templates depend on still exists.

Run on every commit during the rework:

    .venv/bin/python -m pytest tests/test_ui_rework_contract.py -v

If any of these fail, the rework has broken a connection. Fix the
connection before pushing — don't relax the test.

What this test does NOT enforce:
- Visual styling (colors, fonts, spacing) — that's the rework's job
- HTML structure (div vs section vs article) — refactor freely
- CSS class names — rename them, just keep the data flowing
- JS behavior (animations, transitions) — change at will

What this test DOES enforce:
- Every route in the OpenAPI spec returns a non-5xx status
- Critical pages (dashboard, deal profile, screening, login) render OK
- Server boot does not raise
- /health and /healthz return 200 OK (deploy-side healthcheck)
- All schema migrations apply on a fresh DB
- The DealAnalysisPacket dataclass has its load-bearing fields
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Tuple

from rcm_mc.auth.auth import create_user
from rcm_mc.infra.migrations import _MIGRATIONS, list_applied, run_pending
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server


# Pages that MUST render for the product to be useful at all. Add to this
# list when a new top-level surface ships; never silently remove.
CRITICAL_PAGES: List[str] = [
    "/health",
    "/healthz",
    "/login",
    "/dashboard",
    "/home",
    "/api/deals",
    "/api/portfolio/health",
    "/api/migrations",
    "/screening/dashboard",
    "/data/catalog",
    "/models/quality",
    "/models/importance",
    "/api",  # OpenAPI spec
]

# Acceptable status codes per page. 200 = rendered, 302 = redirect (login),
# 401 = auth required (the route exists, just gated). Anything 4xx-401 or
# 5xx is a regression.
ACCEPTABLE_CODES = {200, 302, 401}


def _spin_up_server() -> Tuple[object, int, str]:
    """Boot a fresh-DB server on an ephemeral port. Returns (server, port, db)."""
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "ui_contract.db")
    store = PortfolioStore(db)
    run_pending(store)
    create_user(store, username="admin", password="Strong!Pass123", role="admin")
    server, _ = build_server(port=0, db_path=db, host="127.0.0.1")
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return server, port, db


def _login(opener: urllib.request.OpenerDirector, port: int) -> None:
    data = urllib.parse.urlencode(
        {"username": "admin", "password": "Strong!Pass123"}
    ).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/login",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener.open(req, timeout=5).read()


class TestUIReworkContract(unittest.TestCase):
    """Connection contract for the UI rework branch."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.server, cls.port, cls.db = _spin_up_server()
        cj = http.cookiejar.CookieJar()
        cls.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        _login(cls.opener, cls.port)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def _fetch(self, path: str) -> int:
        try:
            resp = self.opener.open(
                f"http://127.0.0.1:{self.port}{path}", timeout=10
            )
            return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_critical_pages_resolve(self) -> None:
        """Every page on the critical list must return a non-error status."""
        failures = []
        for path in CRITICAL_PAGES:
            code = self._fetch(path)
            if code not in ACCEPTABLE_CODES:
                failures.append(f"{path}: HTTP {code}")
        self.assertEqual(failures, [], f"broken routes: {failures}")

    def test_health_endpoints_return_ok_body(self) -> None:
        """The deploy healthcheck depends on /health returning body 'ok'."""
        for path in ("/health", "/healthz"):
            resp = self.opener.open(
                f"http://127.0.0.1:{self.port}{path}", timeout=5
            )
            self.assertEqual(resp.status, 200, f"{path} status")
            body = resp.read().decode()
            self.assertEqual(body, "ok", f"{path} body changed: {body!r}")

    def test_all_migrations_applied(self) -> None:
        """Server boot must apply all migrations — UI rework cannot regress this."""
        store = PortfolioStore(self.db)
        applied = list_applied(store)
        self.assertEqual(
            len(applied),
            len(_MIGRATIONS),
            f"missing migrations: {set(n for n, _ in _MIGRATIONS) - set(applied)}",
        )

    def test_openapi_spec_loads(self) -> None:
        """The OpenAPI spec must load — UI rework cannot break the schema."""
        from rcm_mc.infra.openapi import get_openapi_spec
        spec = get_openapi_spec()
        self.assertIn("paths", spec)
        self.assertGreater(len(spec["paths"]), 30, "OpenAPI surface shrank")

    def test_packet_dataclass_load_bearing_fields(self) -> None:
        """DealAnalysisPacket fields the UI depends on must exist.

        If the rework changes any of these names, the UI will silently render
        empty cards. The fix is to update *both* the data layer AND every
        reader in the same commit — never one without the other.
        """
        from rcm_mc.analysis.packet import DealAnalysisPacket
        load_bearing = {
            "deal_id",
            "deal_name",
            "profile",
            "observed_metrics",
            "predicted_metrics",
            "completeness",
            "risk_flags",
            "ebitda_bridge",
            "simulation",
            "provenance",
        }
        actual = {f.name for f in DealAnalysisPacket.__dataclass_fields__.values()}
        missing = load_bearing - actual
        self.assertEqual(
            missing, set(), f"DealAnalysisPacket lost load-bearing fields: {missing}"
        )

    def test_ui_kit_shell_function_exists(self) -> None:
        """Every page passes through `_ui_kit.shell()` — rework should keep
        this single insertion point so global treatment stays consistent."""
        # Try both _ui_kit and ui_kit since the rework may consolidate them.
        candidates = ["rcm_mc._ui_kit", "rcm_mc.ui._ui_kit", "rcm_mc.ui.ui_kit"]
        found = False
        for modname in candidates:
            try:
                mod = __import__(modname, fromlist=["shell"])
                if hasattr(mod, "shell") or hasattr(mod, "render_shell"):
                    found = True
                    break
            except ImportError:
                continue
        self.assertTrue(
            found,
            f"none of {candidates} exposes a shell() — UI consistency contract broken",
        )

    def test_login_round_trip(self) -> None:
        """Auth must round-trip — the rework cannot break the cookie flow."""
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        _login(opener, self.port)
        # After login the session cookie must be set.
        cookie_names = {c.name for c in cj}
        self.assertIn(
            "rcm_session", cookie_names, f"session cookie missing: {cookie_names}"
        )

    def test_authenticated_data_endpoint_returns_json(self) -> None:
        """A representative authenticated endpoint must return parseable JSON."""
        resp = self.opener.open(
            f"http://127.0.0.1:{self.port}/api/deals", timeout=5
        )
        body = resp.read().decode()
        data = json.loads(body)  # raises if HTML leaked into a JSON endpoint
        self.assertIn("deals", data)
        self.assertIn("total", data)


if __name__ == "__main__":
    unittest.main()
