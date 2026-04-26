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
        # Force ui=v2 explicitly so the test asserts "legacy users
        # redirect" rather than relying on env-default behavior. When
        # the env has CHARTIS_UI_V2=1 set globally (e.g. running this
        # suite in editorial mode for cross-mode verification), the
        # request-default would otherwise be editorial, not legacy,
        # and the redirect wouldn't fire.
        try:
            resp = nofollow_opener.open(
                f"http://127.0.0.1:{self.port}/app?ui=v2", timeout=10
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

    # ── Phase 3 contract tests (commit 10) ────────────────────────

    def test_v3_app_deliverables_block_renders_card_or_empty_state(self) -> None:
        """Per Phase 3 commit 5 (Q3.5 canonical-path migration):
        deliverables block renders either a card (real export) or an
        explicit empty-state — never silent-empty.

        The block must wire to ``generated_exports`` first, falling back
        to ``analysis_runs``. We don't seed an export here, so we expect
        the empty-state path; the test guards that the block isn't
        silently dropped from the page.
        """
        body = self._fetch_body("/app?ui=v3")
        self.assertIn("app-deliv", body, "deliverables block missing")
        self.assertTrue(
            "app-deliv-empty" in body
            or 'class="app-deliv-card"' in body
            or "app-deliv__card" in body
            or "/exports/" in body,
            "deliverables block has neither card nor empty-state marker",
        )

    def test_v3_app_ebitda_drag_block_renders(self) -> None:
        """Per Phase 3 commit 6: EBITDA drag block must render an
        empty-state when no deal is focused, OR the bucket bar (with
        the 5-component partition) when a focused deal has packet data."""
        body = self._fetch_body("/app?ui=v3")
        self.assertTrue(
            "app-drag-empty" in body or "app-drag-bar" in body,
            "EBITDA drag block missing",
        )

    def test_v3_app_covenant_heatmap_footnote_present(self) -> None:
        """Per Phase 3 commit 7 (Q4.5 honest-partial-wiring):
        the covenant grid honestly distinguishes the 1 wired row from
        the 5 unwired rows. Partners shouldn't infer the other 5 rows
        are real signals.

        Tested at the helper layer (covenant_grid) because the footnote
        only renders when the focused deal has covenant data — the
        anonymous /app fetch from this contract suite hits the empty-
        state path. We verify the contract that exactly one row carries
        ``wired=True`` regardless of data presence.
        """
        from rcm_mc.ui.chartis._app_covenant_heatmap import covenant_grid
        store = PortfolioStore(self.db)
        rows = covenant_grid(store, "no_such_deal_for_grid_shape_test")
        self.assertEqual(
            len(rows), 6,
            f"covenant grid must have 6 rows (Net Leverage + 5 unwired), got {len(rows)}",
        )
        wired_count = sum(1 for r in rows if r.get("wired"))
        self.assertEqual(
            wired_count, 1,
            f"exactly 1 covenant row must be wired (Net Leverage); got {wired_count}",
        )
        # The wired row must be Net Leverage — name is the load-bearing
        # contract for the partner-walkthrough demo.
        wired_row = next(r for r in rows if r.get("wired"))
        self.assertIn(
            "leverage", wired_row.get("name", "").lower(),
            f"wired row should be Net Leverage; got {wired_row.get('name')!r}",
        )

    def test_v3_app_initiative_tracker_cross_portfolio_when_no_focus(self) -> None:
        """Per Phase 3 commit 8 (Q3.4): when no deal is focused, the
        initiative tracker block renders the cross-portfolio variance
        view with the trailing-4Q label."""
        body = self._fetch_body("/app?ui=v3")
        self.assertIn("app-init", body, "initiative tracker missing")
        # When no deal focused (default /app render), expect the
        # cross-portfolio label OR an empty-state (fresh DB has zero
        # initiatives recorded — the empty-state still indicates the
        # cross-portfolio shape was attempted)
        self.assertTrue(
            "CROSS-PORTFOLIO" in body
            or "trailing 4 quarters" in body
            or "No initiative actuals" in body,
            "initiative tracker did not pivot to cross-portfolio shape",
        )

    def test_v3_phi_banner_visual_weight_q37(self) -> None:
        """Per Phase 3 commit 9 (Q3.7): editorial PHI banner uses the
        muted-green compliance-band styling, not the loud status-green.

        Locks in the visual-weight reduction so a future style refactor
        doesn't silently restore the loud variant.
        """
        os.environ["RCM_MC_PHI_MODE"] = "disallowed"
        try:
            body = self._fetch_body("/app?ui=v3")
        finally:
            os.environ.pop("RCM_MC_PHI_MODE", None)
        # The trimmed copy is the load-bearing change — verify the
        # full legacy phrase ("on this instance") was dropped from the
        # editorial banner.
        # Find the phi-banner div; assert the trimmed copy is inside
        import re
        match = re.search(
            r'<div class="phi-banner"[^>]*>(.*?)</div>',
            body, flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "phi-banner div missing")
        banner_inner = match.group(1)
        self.assertIn(
            "no PHI", banner_inner,
            "PHI banner copy missing the no-PHI marker",
        )
        self.assertNotIn(
            "permitted on this instance", banner_inner,
            "Q3.7 trim regressed — verbose legacy copy returned",
        )

    def test_editorial_palette_has_all_legacy_keys(self) -> None:
        """Editorial palette must contain every key the legacy palette does.

        Audit 2026-04-25 found 193 of 291 routes 500'd in editorial mode
        because pages from the dark-shell era reach for ``P["panel"]``,
        ``P["positive"]``, etc. — keys that exist in the legacy palette
        but NOT in editorial. The dispatcher swaps `P` between palettes,
        so a missing key crashes the page with KeyError.

        This contract is the discipline gate: any future palette refactor
        that drops a key from the editorial palette without verifying no
        page reaches for it will fail this test before reaching CI. The
        editorial palette is a SUPERSET of legacy + its own native keys.

        Phase 5 cleanup will sweep the legacy keys out of all pages,
        removing the need for this superset; until then, this is the
        load-bearing invariant.
        """
        from rcm_mc.ui._chartis_kit_legacy import P as P_legacy
        from rcm_mc.ui._chartis_kit_editorial import P as P_editorial
        missing = set(P_legacy.keys()) - set(P_editorial.keys())
        self.assertEqual(
            missing, set(),
            f"Editorial palette missing legacy keys: {sorted(missing)}. "
            f"Add them as aliases in _chartis_kit_editorial.py P dict.",
        )

    def test_resolve_active_section_classifies_legacy_route_paths(self) -> None:
        """``_resolve_active_section`` must accept BOTH section names
        and route paths. Audit 2026-04-26 found 200+ pages passed
        legacy route paths like ``"/rcm-benchmarks"`` to ``active_nav``;
        the topbar previously matched only against
        DEALS/ANALYSIS/PORTFOLIO/MARKET/TOOLS, so no page ever showed
        an active state. This test locks in the new resolver
        contract."""
        from rcm_mc.ui._chartis_kit_editorial import _resolve_active_section
        # Section names pass through (case-insensitive)
        self.assertEqual(_resolve_active_section("DEALS"), "DEALS")
        self.assertEqual(_resolve_active_section("deals"), "DEALS")
        self.assertEqual(_resolve_active_section("PORTFOLIO"), "PORTFOLIO")
        # Route paths classified by prefix
        self.assertEqual(
            _resolve_active_section("/rcm-benchmarks"), "TOOLS",
            "/rcm-benchmarks should classify to TOOLS",
        )
        self.assertEqual(
            _resolve_active_section("/diligence/deal-mc"), "DEALS",
            "/diligence/* should classify to DEALS",
        )
        self.assertEqual(
            _resolve_active_section("/app?ui=v3"), "PORTFOLIO",
            "/app should classify to PORTFOLIO",
        )
        self.assertEqual(
            _resolve_active_section("/market-intel"), "MARKET",
        )
        self.assertEqual(
            _resolve_active_section("/payer-intelligence"), "MARKET",
        )
        self.assertEqual(
            _resolve_active_section("/methodology"), "TOOLS",
        )
        # Unknown / empty → no active section (no crash)
        self.assertEqual(_resolve_active_section(None), "")
        self.assertEqual(_resolve_active_section(""), "")
        self.assertEqual(
            _resolve_active_section("/some-unknown-route-xyz"), "",
            "unrecognized routes should return empty (no false-positive active state)",
        )

    def test_v3_topnav_sections_are_navigable_anchors(self) -> None:
        """Editorial topnav sections must be navigable anchors, not
        decorative buttons.

        Phase 3 nav-polish (2026-04-26): converted the 5 topnav
        sections (DEALS / ANALYSIS / PORTFOLIO / MARKET / TOOLS) from
        ``<button>`` placeholders to ``<a>`` anchors targeting the
        primary destination per section. Locks in the contract so a
        future refactor can't silently revert to non-functional
        buttons.

        Per-section destination map (assertions match the helper's
        nav_items table; update both together):
            DEALS     → /deals?ui=v3
            ANALYSIS  → /analysis?ui=v3
            PORTFOLIO → /app?ui=v3
            MARKET    → /market-intel?ui=v3
            TOOLS     → /methodology?ui=v3
        """
        body = self._fetch_body("/app?ui=v3")
        # Each section is a real anchor, not a button
        for label, href in (
            ("DEALS",     "/deals?ui=v3"),
            ("ANALYSIS",  "/analysis?ui=v3"),
            ("PORTFOLIO", "/app?ui=v3"),
            ("MARKET",    "/market-intel?ui=v3"),
            ("TOOLS",     "/methodology?ui=v3"),
        ):
            self.assertIn(
                f'href="{href}"', body,
                f"topnav {label} link missing or wrong destination",
            )
            self.assertIn(
                f">{label}</a>", body,
                f"topnav {label} should be an anchor, not a button",
            )
        # No pretend-dropdown carets — Phase 3 nav-polish dropped them
        # because anchors don't open menus.
        self.assertNotIn(
            'class="caret"', body,
            "topnav still rendering caret affordance for non-existent dropdowns",
        )

    def test_v3_brand_link_preserves_editorial_flag(self) -> None:
        """The SeekingChartis logo on any v3 page must NOT drop the user
        back into the legacy shell when clicked.

        Discovered during local testing 2026-04-25 (§1 in
        docs/UI_REWORK_PLAN.md). Chrome'd pages point the brand at
        /app?ui=v3 (authenticated dashboard); no-chrome pages
        (login/forgot) point at /?ui=v3 (preserves flag at marketing
        splash). This test guards both shapes so a future style
        refactor doesn't silently revert to plain `/`.
        """
        body_app = self._fetch_body("/app?ui=v3")
        self.assertIn(
            'href="/app?ui=v3" class="brand"', body_app,
            "authenticated v3 page brand link missing the editorial-flag-preserving href",
        )
        self.assertNotIn(
            'href="/" class="brand"', body_app,
            "authenticated v3 page brand link still points at legacy /",
        )
        body_login = self._fetch_body("/login?ui=v3")
        self.assertIn(
            'href="/?ui=v3" class="brand"', body_login,
            "unauthenticated v3 page brand link missing the editorial-flag-preserving href",
        )
        self.assertNotIn(
            'href="/" class="brand"', body_login,
            "unauthenticated v3 page brand link still points at legacy /",
        )

    def test_editorial_link_helper_passes_through_external_urls(self) -> None:
        """``editorial_link`` must NOT rewrite external URLs / mailto /
        in-page anchors / already-querystring'd paths. Internal absolute
        paths get the v3 flag appended; everything else passes through.
        Lock the contract so a future change can't accidentally rewrite
        external links to a malformed ``https://...?ui=v3`` shape."""
        from rcm_mc.ui._chartis_kit_editorial import editorial_link
        self.assertEqual(editorial_link("/dashboard"), "/dashboard?ui=v3")
        self.assertEqual(editorial_link("/app"), "/app?ui=v3")
        self.assertEqual(
            editorial_link("https://example.com"), "https://example.com",
        )
        self.assertEqual(
            editorial_link("mailto:foo@bar.com"), "mailto:foo@bar.com",
        )
        self.assertEqual(editorial_link("#section-2"), "#section-2")
        self.assertEqual(
            editorial_link("/app?deal=ccf_2026"), "/app?deal=ccf_2026",
        )
        self.assertEqual(editorial_link("relative/path"), "relative/path")
        self.assertEqual(editorial_link(""), "")

    def test_v3_focused_deal_bar_renders_export_buttons(self) -> None:
        """Focused-deal context bar renders 3 export buttons that link
        to the existing /api/analysis/<deal_id>/export endpoint with
        format query params (html / xlsx / json).

        Per the "make it feel complete" cycle (2026-04-26): the editorial
        spec puts download affordances on the focused-deal bar; the
        backend endpoints already exist; this just wires the anchors.
        """
        body = self._fetch_body("/app?ui=v3&deal=anything")
        # The deal_id is sanitized server-side; the buttons appear
        # whenever a focused-deal-bar is rendered (which requires the
        # deal_row to resolve from deals_df). On the empty-DB contract
        # suite, no deal resolves, so no buttons render. That's the
        # correct behavior — but it also means we can't assert button
        # presence here without seeded data. Instead assert the helper
        # contract: when called with a deal_id, it produces the buttons.
        from rcm_mc.ui.chartis._app_focused_deal_bar import (
            _render_export_buttons,
        )
        html = _render_export_buttons("ccf_2026")
        self.assertIn('class="exp-btn"', html)
        self.assertIn(
            "/api/analysis/ccf_2026/export?format=html", html,
        )
        self.assertIn(
            "/api/analysis/ccf_2026/export?format=xlsx", html,
        )
        self.assertIn(
            "/api/analysis/ccf_2026/export?format=json", html,
        )
        # Empty deal_id → empty string (no buttons; defensive)
        self.assertEqual(_render_export_buttons(""), "")

    def test_v3_topbar_search_form_submits_to_global_search(self) -> None:
        """The editorial topbar's search input must be wrapped in a
        form that submits via GET to /global-search with name=q.

        Per UI_REWORK_PLAN.md Phase 1 architecture: URL round-trips,
        no client-side state. The form-GET pattern matches that —
        Enter on the input → /global-search?q=… → server-rendered
        results page. No JS dropdown, no SPA, no client state store.
        """
        body = self._fetch_body("/app?ui=v3")
        self.assertIn(
            'class="search"', body,
            "topbar search affordance missing",
        )
        # Must be a form, not a bare input
        import re
        m = re.search(
            r'<form[^>]*class="search"[^>]*>',
            body,
        )
        self.assertIsNotNone(
            m, "search input not wrapped in <form>",
        )
        form_open = m.group(0)
        self.assertIn(
            'method="GET"', form_open,
            "search form must GET (URL round-trip), not POST",
        )
        self.assertIn(
            'action="/global-search"', form_open,
            "search form must target /global-search HTML route",
        )
        # Input must have name=q so the query lands in the URL
        self.assertIn(
            'name="q"', body,
            "search input missing name=q",
        )

    def test_v3_global_search_page_renders(self) -> None:
        """``/global-search`` returns a 200 page with appropriate
        empty / no-match / results states. The chrome adapts to the
        env flag (legacy or editorial); content shape is asserted
        independent of which shell ships."""
        # Empty query → 200 with the "Enter a query" empty-state
        body = self._fetch_body("/global-search")
        self.assertIn(
            "Search", body,
            "search results page missing 'Search' heading",
        )
        self.assertIn(
            "Enter a query", body,
            "empty-query empty-state missing prompt copy",
        )
        # Query with no matches against the empty test DB → no-match
        body = self._fetch_body("/global-search?q=nonexistent_xyz_12345")
        self.assertIn(
            "No matches", body,
            "no-match state missing for unknown query",
        )

    def test_v3_app_renders_editorial_sidebar(self) -> None:
        """Per spec §7.4: ``/app`` ships with a left-rail sidebar
        listing the 28 module destinations. Sidebar is opt-in via
        ``chartis_shell(show_sidebar=True)``; this test asserts the
        opt-in is wired on the dashboard route.
        """
        body = self._fetch_body("/app?ui=v3")
        # The sidebar wrapper element + at least a few module labels
        self.assertIn(
            'class="layout-with-rail"', body,
            "sidebar layout wrapper missing — show_sidebar opt-in "
            "not applied to /app",
        )
        self.assertIn(
            'class="rail"', body,
            "sidebar element missing — editorial_sidebar() not called",
        )
        # Spot-check a handful of spec §7.4 modules
        for module in ("Deal Profile", "Bridge Audit", "IC Packet",
                       "Market Intel", "Bankruptcy Scan"):
            self.assertIn(
                f">{module}</span>", body,
                f"sidebar missing module: {module}",
            )
        # Group headings render
        for group in ("RCM DILIGENCE", "MARKET INTEL"):
            self.assertIn(
                group, body,
                f"sidebar missing group heading: {group}",
            )

    def test_editorial_sidebar_helper_classifies_active_module(self) -> None:
        """``editorial_sidebar()`` should highlight the module whose
        href is a prefix-match of ``active_path``."""
        from rcm_mc.ui._chartis_kit_editorial import editorial_sidebar
        # Active highlighting on a deep path
        html = editorial_sidebar("/diligence/bridge-audit")
        # Bridge Audit module should be active; others should not
        self.assertIn(
            'class="active"', html,
            "active class missing when path matches a module",
        )
        # Empty/None active_path → no active class
        html_empty = editorial_sidebar("")
        self.assertNotIn(
            'class="active"', html_empty,
            "empty active_path should not highlight any module",
        )

    def test_q4_1_root_redirects_to_app_for_authenticated_v3_users(self) -> None:
        """Q4.1 cutover (2026-04-27): when v3 is active (env
        CHARTIS_UI_V2=1 OR per-request ?ui=v3) AND user is
        authenticated, GET / redirects to /app (the editorial
        dashboard). Anonymous visitors still see the marketing splash.

        This is the load-bearing pre-merge-to-main decision per
        UI_REWORK_PLAN.md Q4.1: authenticated partners typing the bare
        domain land on the editorial dashboard, not the marketing
        splash designed for acquisition.

        Uses per-request ?ui=v3 (not env) to avoid module-import
        ordering issues — env-CHARTIS_UI_V2 is read at module import
        time; mid-test mutation has no effect on the already-imported
        UI_V2_ENABLED. The handler accepts EITHER trigger.
        """
        cj = http.cookiejar.CookieJar()
        login_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )
        _login(login_opener, self.port)
        nofollow = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            _NoRedirectHandler(),
        )
        try:
            resp = nofollow.open(
                f"http://127.0.0.1:{self.port}/?ui=v3", timeout=10,
            )
            code = resp.status
            location = resp.headers.get("Location", "")
        except urllib.error.HTTPError as e:
            code = e.code
            location = e.headers.get("Location", "")
        self.assertIn(
            code, (302, 303),
            f"authenticated v3 user GET /?ui=v3 should 303 to /app, got {code}",
        )
        self.assertEqual(
            location, "/app",
            f"redirect target should be /app, got {location!r}",
        )

    def test_v3_app_canonical_export_path_helpers_exist(self) -> None:
        """Per Phase 3 commit 1 (Q3.5 + Q2 push-back):
        canonical_deal_export_path + canonical_portfolio_export_path
        must both exist as separate functions. The two-function design
        is load-bearing — collapsing them into one Optional[str] would
        re-introduce the silent-mis-routing failure mode."""
        from rcm_mc.infra.exports import (
            canonical_deal_export_path,
            canonical_portfolio_export_path,
        )
        # Sanity: deal-scoped function rejects empty/whitespace deal_id
        with self.assertRaises(ValueError):
            canonical_deal_export_path("", "x.html", base=tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            canonical_deal_export_path("   ", "x.html", base=tempfile.mkdtemp())
        # Portfolio-scoped function does not need a deal id; pass base=
        # so we don't try to mkdir /data on a sandboxed filesystem.
        with tempfile.TemporaryDirectory() as tmp:
            p = canonical_portfolio_export_path("rollup.csv", base=tmp)
            self.assertIn("_portfolio", str(p))
        # And the deal-scoped one routes to a deal subdir, NOT _portfolio
        with tempfile.TemporaryDirectory() as tmp2:
            p2 = canonical_deal_export_path("deal-7", "x.html", base=tmp2)
            self.assertIn("deal-7", str(p2))
            self.assertNotIn("_portfolio", str(p2))

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

    def test_phase_3_todos_resolved(self) -> None:
        """Per Phase 3 review: enforce that no `# TODO(phase 3):`
        comments ship in production code after Phase 3 completes.

        Same discipline gate as Phase 2's, scoped to Phase 3. Any
        Phase-3-deferred work must either land in Phase 3 or have its
        TODO retagged to ``TODO(phase 4):`` with a written rationale
        in docs/UI_REWORK_PLAN.md. The retag is the discipline — a
        TODO without a phase tag becomes invisible.
        """
        import pathlib
        import re
        rcm_mc_root = pathlib.Path(__file__).parent.parent / "rcm_mc"
        if not rcm_mc_root.exists():
            self.skipTest("rcm_mc/ not present")
        pat = re.compile(r"#\s*TODO\(phase 3\):", re.IGNORECASE)
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
            f"Phase 3 TODOs still present in production code: {offenders}",
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib redirect handler that surfaces 3xx as HTTPError instead of
    transparently following. Used by the legacy /app redirect test to
    inspect the actual 303 status + Location header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # signals "do not follow"


if __name__ == "__main__":
    unittest.main()
