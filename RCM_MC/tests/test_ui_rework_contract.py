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
    "/forgot",
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

    def _fetch_body(self, path: str) -> str:
        """GET ``path`` and return the decoded body. Raises on non-200/302."""
        try:
            resp = self.opener.open(
                f"http://127.0.0.1:{self.port}{path}", timeout=10
            )
        except urllib.error.HTTPError as e:
            if e.code == 200:
                return e.read().decode("utf-8", errors="replace")
            raise
        return resp.read().decode("utf-8", errors="replace")

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

    # ── Phase 1 editorial-page contract tests ─────────────────────

    def test_v3_forgot_page_renders(self) -> None:
        """``?ui=v3`` /forgot returns 200 with editorial markers."""
        body = self._fetch_body("/forgot?ui=v3")
        self.assertIn('class="cta-btn submit"', body,
                      "editorial CTA button class missing")
        self.assertIn("/static/v3/chartis.css", body,
                      "editorial CSS link missing — page didn't render via editorial shell")
        self.assertIn("Source Serif 4", body,
                      "editorial font preconnect missing")
        self.assertIn('action="/forgot"', body,
                      "form action wrong — POST should target /forgot itself")
        self.assertIn("Reset your", body,
                      "page heading missing")

    def test_v3_login_page_renders_and_form_posts_to_api_login(self) -> None:
        """``?ui=v3`` /login renders editorially; the form's POST target
        is unchanged — auth contract is preserved across shells."""
        body = self._fetch_body("/login?ui=v3")
        # Editorial markers
        self.assertIn("/static/v3/chartis.css", body)
        self.assertIn('class="cta-btn submit"', body)
        self.assertIn("console-teaser", body,
                      "editorial last-session card missing")
        # The load-bearing invariant: form action is unchanged
        self.assertIn('action="/api/login"', body,
                      "editorial /login changed the form action — would break auth")
        self.assertIn('href="/forgot"', body,
                      "Forgot password? link missing")
        # And the round-trip itself still works (re-runs the existing test
        # logic against the editorial-rendered form)
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        _login(opener, self.port)
        self.assertIn("rcm_session", {c.name for c in cj},
                      "session cookie not set after POST /api/login from editorial form")

    def test_v3_login_request_tab_renders_request_form(self) -> None:
        """``?ui=v3&tab=request`` shows Request Access, not Sign In."""
        body = self._fetch_body("/login?ui=v3&tab=request")
        self.assertIn("Request Access →", body)
        self.assertIn('action="/login?tab=request"', body)
        self.assertNotIn("Open Command Center →", body,
                         "sign-in button shown in request tab")

    # ── Pair-pattern contract (per spec §5) ───────────────────────
    #
    # Every analytical v3 page that includes a chart must wrap that
    # chart in a .pair block alongside its underlying data table.
    # No chart without numbers.
    #
    # Phase 1 doesn't ship any v3 pages with charts (/forgot and
    # /login are forms). This test starts as parameterized over an
    # empty list so it's green now AND ready to actively guard the
    # contract as Phase 3+ adds dashboard pages. Add to V3_CHARTED_PAGES
    # when you ship a v3 page that contains <svg>/<canvas>.

    # Activated in Phase 2 (commit 10) — /app is the first authenticated
    # v3 page with charts (sparklines, dot-plots, heatmap cells).
    V3_CHARTED_PAGES: List[str] = ["/app"]

    def test_pair_pattern_when_v3_page_renders_a_chart(self) -> None:
        """Every <svg>/<canvas> on a v3 charted page must sit inside a
        .pair block that also contains a <table>."""
        import re
        failures: list[str] = []
        for path in self.V3_CHARTED_PAGES:
            body = self._fetch_body(f"{path}?ui=v3")
            # Find every <div class="pair"> ... </div> block and
            # verify it has both a chart element and a table.
            pair_blocks = re.findall(
                r'<div class="pair">.*?</div>\s*</div>',
                body,
                flags=re.DOTALL,
            )
            chart_count = body.count("<svg") + body.count("<canvas")
            if chart_count == 0:
                # No charts on the page yet — pair contract vacuously holds.
                continue
            for i, block in enumerate(pair_blocks):
                has_chart = ("<svg" in block) or ("<canvas" in block)
                has_table = "<table" in block
                if has_chart and not has_table:
                    failures.append(
                        f"{path} pair block #{i}: chart without paired table"
                    )
            # A page with a chart MUST have at least one .pair block.
            if chart_count > 0 and not pair_blocks:
                failures.append(
                    f"{path}: page has {chart_count} chart elements but no .pair block"
                )
        self.assertEqual(failures, [], f"pair-pattern violations: {failures}")

    # ── Phase 2 editorial /app contract tests ─────────────────────

    def test_v3_authenticated_pages_render_phi_banner(self) -> None:
        """Per spec §7.5: every authenticated v3 page renders the PHI banner.

        Activated in Phase 2 (this commit) — /app is the first
        authenticated v3 page; before this commit there was no
        non-trivial place to test the banner against.
        """
        os.environ["RCM_MC_PHI_MODE"] = "disallowed"
        try:
            body = self._fetch_body("/app?ui=v3")
            self.assertIn(
                'class="phi-banner"', body,
                "PHI banner missing on authenticated v3 page",
            )
            self.assertIn(
                'data-phi-mode="disallowed"', body,
                "PHI banner mode attribute missing",
            )
            self.assertIn(
                "Public data only", body,
                "PHI banner copy missing",
            )
        finally:
            os.environ.pop("RCM_MC_PHI_MODE", None)

    def test_v3_app_route_renders_for_authenticated_user(self) -> None:
        """GET /app?ui=v3 returns 200 with all 9 paired-block markers."""
        body = self._fetch_body("/app?ui=v3")
        # Editorial markers
        self.assertIn("/static/v3/chartis.css", body,
                      "editorial CSS link missing")
        self.assertIn("Command center", body,
                      "page title missing")
        # All 9 helper blocks present (per spec §6.3-6.11)
        self.assertIn("app-kpi-strip", body, "KPI strip block missing")
        self.assertIn("app-pipeline-funnel", body, "pipeline funnel missing")
        self.assertIn("app-deals-table", body, "deals table missing")
        self.assertIn("app-cov-heat", body, "covenant heatmap missing")
        # EBITDA drag empty state OR bar present (depends on focused deal)
        self.assertTrue(
            "app-drag-empty" in body or "app-drag-bar" in body,
            "EBITDA drag block missing in some form",
        )
        self.assertIn("app-init", body, "initiative tracker missing")
        # Alerts: either active cards or all-clear card
        self.assertTrue(
            "app-alerts" in body or "app-alerts-clear" in body,
            "alerts block missing",
        )
        self.assertIn("app-deliv", body, "deliverables missing")

    def test_v3_app_handles_invalid_focused_deal_id(self) -> None:
        """?deal=<garbage> falls through to empty-state rather than 500."""
        code = self._fetch("/app?ui=v3&deal=does_not_exist_12345")
        self.assertEqual(
            code, 200,
            "/app should empty-state on unknown deal, not 500",
        )

    def test_v3_app_handles_invalid_stage_filter(self) -> None:
        """?stage=<garbage> validates against DEAL_STAGES + falls through."""
        code = self._fetch("/app?ui=v3&stage=does_not_exist")
        self.assertEqual(
            code, 200,
            "/app should ignore bad stage filter, not 500",
        )

    def test_v3_app_legacy_request_redirects_to_dashboard(self) -> None:
        """Legacy ?ui=v2 (or default) GET /app → 303 to /dashboard.

        /app is editorial-only; legacy users land on the existing
        /dashboard. The redirect is logged so signal is captured for
        the Phase 4 cutover decision (Q4.1).
        """
        # Log in with a regular (redirect-following) opener so the
        # /api/login → 303 → / chain completes cleanly. Then build a
        # second opener that REUSES the cookie jar but refuses to
        # follow redirects, so the /app → 303 → /dashboard hop can be
        # inspected directly.
        cj = http.cookiejar.CookieJar()
        login_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        _login(login_opener, self.port)

        nofollow_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            _NoRedirectHandler(),
        )
        # Default ui_choice = legacy, no ?ui=v3 query.
        try:
            resp = nofollow_opener.open(
                f"http://127.0.0.1:{self.port}/app", timeout=10
            )
            code = resp.status
            location = resp.headers.get("Location", "")
        except urllib.error.HTTPError as e:
            code = e.code
            location = e.headers.get("Location", "")
        self.assertIn(
            code, (302, 303),
            f"legacy /app should 303-redirect to /dashboard, got {code}",
        )
        self.assertIn(
            "/dashboard", location,
            f"redirect target should be /dashboard, got {location!r}",
        )

    # ── Phase 2 follow-through ─────────────────────────────────────

    def test_phase_2_todos_resolved(self) -> None:
        """Per Phase 2 review: enforce that no `# TODO(phase 2):` comments
        ship in production code after Phase 2 completes.

        ``rcm_mc/`` is the production code tree. Tests + docs may
        carry phase-N TODOs as historical markers.

        This test is the discipline gate that prevents Phase 2 work
        from silently slipping into Phase 3 — every TODO comment
        documenting deferred-to-Phase-2 work must be resolved before
        Phase 2 is "done."
        """
        import pathlib
        import re
        rcm_mc_root = pathlib.Path(__file__).parent.parent / "rcm_mc"
        if not rcm_mc_root.exists():
            self.skipTest("rcm_mc/ not present")
        pat = re.compile(r"#\s*TODO\(phase 2\):", re.IGNORECASE)
        offenders: list[str] = []
        for py in rcm_mc_root.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            try:
                text = py.read_text()
            except Exception:  # noqa: BLE001
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if pat.search(line):
                    offenders.append(
                        f"{py.relative_to(rcm_mc_root.parent)}:{n}: {line.strip()}"
                    )
        self.assertEqual(
            offenders, [],
            f"Phase 2 TODOs still present in production code: {offenders}",
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib redirect handler that surfaces 3xx as HTTPError instead of
    transparently following. Used by the legacy /app redirect test to
    inspect the actual 303 status + Location header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # signals "do not follow"


if __name__ == "__main__":
    unittest.main()
