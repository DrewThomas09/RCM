"""API endpoint smoke test — verifies JSON endpoints return
expected status codes.

The per-route compliance test covers HTML routes (page renders +
kit-presence). This guard covers /api/* JSON endpoints that the
HTML scorer doesn't visit. Each endpoint pinned at its expected
status (200 for valid auth, 404 for routes that legitimately
404 in tests, etc.).

Lives in its own file (not inherited from PerRouteComplianceSweep)
because the conftest fixture's env restoration + module drops
break inheritance-based shared setup. A standalone class with its
own setUpClass keeps test isolation simple.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


class _NoFollow(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, *a, **kw): return None
    def http_error_302(self, *a, **kw): return None
    def http_error_303(self, *a, **kw): return None


# (path, expected_status_code) — pinned at observed status when
# the test landed. Failures surface as "API X returned N, expected
# M" with the exact path so the partner doesn't have to grep.
API_SMOKE_ROUTES: list[tuple[str, int]] = [
    # Health checks (auth-free)
    ("/healthz",                  200),
    ("/health",                   200),
    # System / admin (auth-required)
    ("/api/health/deep",          200),
    ("/api/system/info",          200),
    ("/api/migrations",           200),
    ("/api/backup",               200),
    ("/api",                      200),  # API index
    # Domain APIs — deals
    ("/api/calibration/priors",   200),
    ("/api/runs",                 200),
    ("/api/deals/stats",          200),
    ("/api/deals/search?q=test",  200),
    ("/api/deadlines",            200),
    # Domain APIs — workflows
    ("/api/automations",          200),
    ("/api/cohorts",              200),
    ("/api/watchlist",            200),
    ("/api/search?q=test",        200),
    ("/api/tags",                 200),
    ("/api/owners",               200),
    # Domain APIs — corpus + analytics
    ("/api/corpus",               200),
    ("/api/scenarios",            200),
    ("/api/export/portfolio.csv", 200),
    ("/api/health",               200),
    # Portfolio aggregations
    ("/api/portfolio/health",       200),
    ("/api/portfolio/alerts",       200),
    ("/api/portfolio/summary",      200),
    ("/api/portfolio/attribution",  200),
    ("/api/portfolio/matrix",       200),
    # Insights / market / digest
    ("/api/insights",                 200),
    ("/api/insights/headline",        200),
    ("/api/digest/morning",           200),
    ("/api/market-pulse",             200),
    ("/api/global-search",            200),
    ("/api/screener/predefined",      200),
    ("/api/webhooks",                 200),
    ("/api/metrics",                  200),
    ("/api/openapi.json",             200),
    # Diligence / market-intel
    ("/api/market-intel/peer-snapshot",      200),
    ("/api/regulatory-calendar/exposure",    200),
    ("/api/surrogate/schema",                 200),
    ("/api/diligence/comparable-outcomes",   200),
    # Additional endpoints (subpath / file extensions)
    ("/api/deals/search",                        200),
    ("/api/diligence/comparable-outcomes.csv",   200),
    ("/api/diligence/comparable-outcomes.memo",  200),
    ("/api/docs",                                200),
    ("/api/metrics/custom",                      200),
    ("/api/portfolio/risk-scan.csv",             200),
    ("/api/search",                              200),
    ("/api/webhooks/test",                       200),
    # Newly probed — partner-visible alerts + data + deal listing.
    # /api/portfolio/regression pinned at 400 (legitimate validation
    # response when no numeric columns are present in the demo
    # dataset; status guards the validator path, not a 200 happy-
    # path).
    ("/api/alerts/active-count",                          200),
    ("/api/data/hospitals",                               200),
    ("/api/deals",                                        200),
    ("/api/deals/compare?ids=smoke-a,smoke-b",            200),
    ("/api/portfolio/regression",                         400),
    # Dynamic per-deal subpaths. The setUpClass seeds two deals
    # (smoke-a, smoke-b) so these resolve. Each subpath exercises a
    # distinct downstream path: peers (similarity engine), health
    # (composite score), summary (packet renderer), checklist
    # (IC checklist), completeness (registry+grade), timeline
    # (audit join), counts (child-table aggregator), diffs
    # (snapshot trail), audit (per-deal audit log), similar
    # (numeric-distance peer search), package (export ZIP),
    # export-links (download URL builder), notes/tags/overrides
    # (workflow CRUD readers), validate (schema sanity).
    # /api/deals/<id> bare returns 404 without a snapshot row. The
    # smoke seed upserts the deal but doesn't write a snapshot, so
    # we don't pin it. The /<id>/<sub> subpaths exercise the real
    # handlers and resolve without snapshot data.
    ("/api/deals/smoke-a/peers",                          200),
    ("/api/deals/smoke-a/health",                         200),
    ("/api/deals/smoke-a/summary",                        200),
    ("/api/deals/smoke-a/checklist",                      200),
    ("/api/deals/smoke-a/completeness",                   200),
    ("/api/deals/smoke-a/timeline",                       200),
    ("/api/deals/smoke-a/counts",                         200),
    ("/api/deals/smoke-a/diffs",                          200),
    ("/api/deals/smoke-a/audit",                          200),
    ("/api/deals/smoke-a/similar",                        200),
    ("/api/deals/smoke-a/package",                        200),
    ("/api/deals/smoke-a/export-links",                   200),
    ("/api/deals/smoke-a/notes",                          200),
    ("/api/deals/smoke-a/tags",                           200),
    ("/api/deals/smoke-a/overrides",                      200),
    ("/api/deals/smoke-a/validate",                       200),
    ("/api/analysis/smoke-a",                             200),
    ("/api/analysis/smoke-a/export",                      200),
    ("/api/diligence/synthesis/smoke-a",                  200),
    # Additional dispatcher routes (rollup/digest/stages) and
    # per-deal trail surfaces. These exercise the
    # latest_per_deal / portfolio_rollup / build_digest paths and
    # the variance/initiatives/provenance per-deal subresources.
    ("/api/rollup",                                       200),
    ("/api/digest",                                       200),
    ("/api/stages",                                       200),
    ("/api/deals/smoke-a/variance",                       200),
    ("/api/deals/smoke-a/initiatives",                    200),
    ("/api/deals/smoke-a/provenance",                     200),
    ("/api/runs?deal_id=smoke-a",                         200),
]



class APIEndpointSmoke(unittest.TestCase):
    """Walks 10 API endpoints and asserts each returns 200."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        from rcm_mc.server import build_server
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.auth.auth import create_user

        cls.tmp = tempfile.mkdtemp(prefix="rcm_api_smoke_")
        cls.db = os.path.join(cls.tmp, "p.db")
        store = PortfolioStore(cls.db)
        create_user(store, "demo", "DemoPass!1",
                    display_name="Demo Partner", role="admin")
        # Seed a non-admin analyst so the admin-role guard can
        # exercise the role-gating path.
        create_user(store, "analyst", "AnalystPass!1",
                    display_name="Test Analyst", role="analyst")
        # Seed two deals so dynamic /api/deals/<id>/* probes resolve
        # to real handler paths instead of 404s. Names mirror what
        # API_SMOKE_ROUTES references.
        store.upsert_deal("smoke-a", name="Smoke A", profile={})
        store.upsert_deal("smoke-b", name="Smoke B", profile={})

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

        cls.cookies = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cls.cookies),
            _NoFollow(),
        )
        opener.open(cls.base + "/login", timeout=5).read()
        csrf = ""
        for c in cls.cookies:
            if "csrf" in c.name.lower():
                csrf = c.value
                break
        body = urllib.parse.urlencode({
            "username": "demo",
            "password": "DemoPass!1",
            "csrf_token": csrf,
        }).encode()
        try:
            opener.open(
                urllib.request.Request(
                    cls.base + "/api/login", data=body, method="POST",
                ),
                timeout=5,
            )
        except urllib.error.HTTPError as e:
            if e.code not in (200, 303):
                raise

        cls.opener = opener

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def _fetch_status(self, path: str) -> int:
        try:
            resp = self.opener.open(self.base + path, timeout=8)
        except urllib.error.HTTPError as e:
            return e.code
        except urllib.error.URLError:
            return 0
        if resp is None:
            return 0
        return resp.status

    def test_each_api_endpoint_returns_expected_status(self) -> None:
        for path, expected in API_SMOKE_ROUTES:
            with self.subTest(api=path):
                actual = self._fetch_status(path)
                self.assertEqual(
                    actual, expected,
                    f"API endpoint {path} returned {actual}, "
                    f"expected {expected}",
                )

    def test_openapi_spec_path_count_at_or_above_floor(self) -> None:
        """The OpenAPI spec is the source of truth for the /api
        index. Removing a path silently shrinks the partner-visible
        API surface (the /api index, the Swagger UI at /api/docs,
        and any client SDK regenerated from the spec).

        Floor pinned at 52 paths / 56 operations — the documented
        size in CLAUDE.md. If a contributor adds new paths, bump
        the floors. If they remove, this test fails with a clear
        message pointing at the spec drift.
        """
        import json
        OPENAPI_PATH_FLOOR = 101
        OPENAPI_OPERATION_FLOOR = 105
        resp = self.opener.open(
            self.base + "/api/openapi.json", timeout=8,
        )
        spec = json.loads(resp.read().decode("utf-8"))
        paths = spec.get("paths", {})
        operations = sum(len(m) for m in paths.values())
        self.assertGreaterEqual(
            len(paths), OPENAPI_PATH_FLOOR,
            f"OpenAPI spec has {len(paths)} paths — below floor of "
            f"{OPENAPI_PATH_FLOOR}. Removing a path silently shrinks "
            f"the discoverable API surface (/api index, Swagger UI, "
            f"client SDKs). Either restore the path or update the "
            f"floor with rationale.",
        )
        self.assertGreaterEqual(
            operations, OPENAPI_OPERATION_FLOOR,
            f"OpenAPI spec has {operations} operations — below "
            f"floor of {OPENAPI_OPERATION_FLOOR}.",
        )

    def test_api_index_count_matches_openapi_operations(self) -> None:
        """The /api JSON index is generated by walking the OpenAPI
        spec. If the index entry count diverges from the operation
        count, the index handler has drifted from the spec walker —
        either skipping operations or duplicating them. The bug is
        usually in rcm_mc/infra/openapi.py or the /api dispatcher.
        """
        import json
        idx = json.loads(
            self.opener.open(self.base + "/api", timeout=8)
            .read().decode("utf-8"),
        )
        spec = json.loads(
            self.opener.open(
                self.base + "/api/openapi.json", timeout=8,
            ).read().decode("utf-8"),
        )
        idx_count = idx.get("count", -1)
        spec_ops = sum(len(m) for m in spec.get("paths", {}).values())
        self.assertEqual(
            idx_count, spec_ops,
            f"/api index reports {idx_count} entries but the "
            f"OpenAPI spec has {spec_ops} operations. The index "
            f"handler walks the spec — divergence means the walker "
            f"skipped or duplicated operations. Check the /api "
            f"dispatcher (server.py) and infra/openapi.py.",
        )

    def test_openapi_operations_are_structurally_complete(self) -> None:
        """Every operation in the OpenAPI spec must carry a
        non-empty summary, at least one tag, and at least one
        response with a description.

        The /api index handler, the Swagger UI at /api/docs, and any
        regenerated client SDK all consume these fields. A
        contributor who adds a path-stub (no summary, no tags) gets
        a silent partial-render — the entry shows up but the partner
        sees blanks. This guard fails loud with the offending path
        instead.
        """
        from rcm_mc.infra.openapi import get_openapi_spec

        spec = get_openapi_spec()
        issues: list[str] = []
        for p, methods in spec["paths"].items():
            for method, op in methods.items():
                head = f"{method.upper()} {p}"
                if not op.get("summary"):
                    issues.append(f"{head}: empty summary")
                if not op.get("tags"):
                    issues.append(f"{head}: missing tags")
                responses = op.get("responses", {})
                if not responses:
                    issues.append(f"{head}: missing responses")
                for code, r in responses.items():
                    if not (isinstance(r, dict) and r.get("description")):
                        issues.append(
                            f"{head}: response {code} missing description",
                        )
        self.assertEqual(
            issues, [],
            f"OpenAPI structural issues ({len(issues)}): {issues}",
        )

    def test_openapi_tags_are_declared_at_top_level(self) -> None:
        """Every tag used by an operation must appear in the
        top-level ``tags`` list. The list drives the section
        grouping in the Swagger UI; tags used but not declared
        render in an "untagged" group with no description.

        This catches typos (e.g. 'Portolio' vs 'Portfolio') that
        would silently strand a tagged operation in the wrong UI
        section.
        """
        from rcm_mc.infra.openapi import get_openapi_spec

        spec = get_openapi_spec()
        declared = {t["name"] for t in spec.get("tags", [])}
        used: set[str] = set()
        for methods in spec["paths"].values():
            for op in methods.values():
                used.update(op.get("tags", []))
        undeclared = sorted(used - declared)
        self.assertEqual(
            undeclared, [],
            f"Tags used in operations but not declared at top level: "
            f"{undeclared}. Add them to _SPEC['tags'] in "
            f"rcm_mc/infra/openapi.py.",
        )

    def test_every_smoke_route_is_documented_in_openapi(self) -> None:
        """Each /api/* entry in API_SMOKE_ROUTES must be documented
        in the OpenAPI spec. Closing this loop matters because the
        smoke list IS the partner-visible regression net — if a
        route is critical enough to smoke-test, it's critical
        enough to publish in the API docs.

        Allowed exceptions: the auth-free liveness probes
        /healthz, /health, /ready (these are operations-team paths,
        not partner-developer surfaces).
        """
        from rcm_mc.infra.openapi import get_openapi_spec

        documented = set(get_openapi_spec()["paths"].keys())

        def _normalize(p: str) -> str:
            # Strip query string and re-symbolise concrete demo IDs
            # back to OpenAPI placeholders.
            p = p.split("?", 1)[0]
            parts = p.split("/")
            out = []
            for i, part in enumerate(parts):
                prev = parts[i - 1] if i > 0 else ""
                if prev == "deals" and part not in (
                    "search", "stats", "compare", "bulk", "import",
                    "import-csv", "wizard",
                ):
                    out.append("{deal_id}")
                elif prev == "analysis" and part not in ("export",):
                    out.append("{deal_id}")
                elif prev == "synthesis":
                    out.append("{deal_id}")
                elif prev == "jobs":
                    out.append("{job_id}")
                else:
                    out.append(part)
            return "/".join(out)

        skip = {"/healthz", "/health", "/ready"}
        missing: list[str] = []
        for path, _ in API_SMOKE_ROUTES:
            if path in skip:
                continue
            n = _normalize(path)
            if n in documented:
                continue
            missing.append(f"{path} (normalised: {n})")
        self.assertEqual(
            missing, [],
            f"Smoke entries not documented in OpenAPI: {missing}. "
            f"Either add them to rcm_mc/infra/openapi.py or remove "
            f"from API_SMOKE_ROUTES with rationale.",
        )

    def test_json_endpoints_return_parseable_json(self) -> None:
        """For every 200-pinned smoke endpoint that the
        Content-Type guard pins as ``application/json``, the
        response body must parse as valid JSON.

        Stronger than the existing status / exception-leakage
        guards — those catch the *symptoms* of a broken handler
        (5XX, exception strings); this catches a different failure
        mode where the handler swallows an error and returns
        a malformed JSON envelope (truncated body, embedded
        Python ``repr()`` instead of valid JSON, etc.). Any partner
        client that does ``response.json()`` will crash on this.
        """
        import json
        SKIP = {
            "/healthz", "/health",
            "/api/backup",
            "/api/deals/smoke-a/package",
            "/api/analysis/smoke-a/export",
            "/api/docs",
        }
        bad: list[str] = []
        for path, expected_status in API_SMOKE_ROUTES:
            if expected_status != 200:
                continue
            if path in SKIP:
                continue
            if path.endswith(".csv") or path.endswith(".memo"):
                continue
            try:
                resp = self.opener.open(self.base + path, timeout=8)
                body = resp.read()
            except Exception:
                continue
            try:
                json.loads(body.decode("utf-8"))
            except Exception as e:
                bad.append(f"{path}: {e!r}")
        self.assertEqual(
            bad, [],
            f"JSON endpoints returned malformed JSON ({len(bad)}): "
            f"{bad}",
        )

    def test_zzz_login_rate_limit_returns_full_429_envelope(self) -> None:
        """After ``_LOGIN_FAIL_MAX`` failed logins from one IP the
        server must return a complete 429 envelope:

        * Status 429
        * ``Retry-After`` header (seconds, integer-string)
        * ``X-Content-Type-Options: nosniff``
        * ``Cache-Control: no-store``
        * Body: ``{"error": str, "code": "RATE_LIMITED",
                  "retry_after_secs": float, "request_id": str}``

        Without Retry-After, well-behaved clients (SDK retry
        loops, partner pipelines) hammer the endpoint with no
        backoff. Without nosniff/Cache-Control, the 429 inherits
        the default headers from the underlying HTTP server,
        which omit both.
        """
        import json
        anon = urllib.request.build_opener(_NoFollow())
        # Seed the CSRF cookie.
        try:
            anon.open(self.base + "/login", timeout=5).read()
        except Exception:
            pass

        body = urllib.parse.urlencode({
            "username": "rate-limit-probe-user",  # nonexistent
            "password": "WrongPass!1",
            "csrf_token": "",
        }).encode()

        last_resp = None
        for _ in range(8):
            try:
                req = urllib.request.Request(
                    self.base + "/api/login", data=body, method="POST",
                )
                last_resp = anon.open(req, timeout=5)
            except urllib.error.HTTPError as e:
                last_resp = e
                if e.code == 429:
                    break

        self.assertIsNotNone(last_resp, "no response captured")
        self.assertEqual(
            getattr(last_resp, "code", getattr(last_resp, "status", 0)),
            429,
            "expected 429 after failed-login burst",
        )
        headers = last_resp.headers
        self.assertEqual(
            headers.get("X-Content-Type-Options", "").lower(),
            "nosniff",
        )
        self.assertEqual(
            headers.get("Cache-Control", ""), "no-store",
        )
        retry_after = headers.get("Retry-After", "")
        self.assertTrue(
            retry_after.isdigit() and int(retry_after) >= 1,
            f"Retry-After must be integer seconds ≥ 1, got "
            f"{retry_after!r}",
        )

        payload = json.loads(last_resp.read().decode("utf-8"))
        for key in ("error", "code", "retry_after_secs", "request_id"):
            self.assertIn(
                key, payload,
                f"429 body missing key {key!r}: {payload}",
            )
        self.assertEqual(payload["code"], "RATE_LIMITED")
        self.assertIsInstance(payload["retry_after_secs"], (int, float))

    def test_state_changing_posts_write_audit_entries(self) -> None:
        """Every state-changing operation must write an audit log
        entry via self._log_audit(). Compliance teams rely on
        this for SOC2 / partner-facing change-tracking. Catches
        the regression class where a contributor unwraps the
        audit hook from a handler — route still returns 200,
        partner-visible state still updates, but the trail
        breaks silently.

        Exercises three representative state-mutating POSTs:

        * /api/portfolio/register → ``portfolio.register``
        * /api/deals/import      → ``deal.import``
        * /api/deals/bulk archive → ``bulk.archive``

        Each must:
        1. Return 200 from the POST.
        2. Cause the /audit page to surface the action token AND
           a recognisable identifier (deal_id, count) so the
           entry is traceable.
        """
        import json
        csrf = ""
        for c in self.cookies:
            if c.name == "rcm_csrf":
                csrf = c.value
                break

        def _post_json(path: str, payload) -> int:
            req = urllib.request.Request(
                self.base + path,
                data=json.dumps(payload).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("X-CSRF-Token", csrf)
            try:
                resp = self.opener.open(req, timeout=8)
                return resp.status
            except urllib.error.HTTPError as e:
                return e.code

        SCENARIOS: list[tuple[str, object, str, str]] = [
            (
                "/api/portfolio/register",
                {
                    "deal_id": "audit-register-probe",
                    "name": "Register Audit Probe",
                    "stage": "sourced",
                },
                "portfolio.register",
                "audit-register-probe",
            ),
            (
                "/api/deals/import",
                [{
                    "deal_id": "audit-import-probe",
                    "name": "Import Audit Probe",
                    "profile": {},
                }],
                "deal.import",
                "audit-import-probe",
            ),
            (
                "/api/deals/bulk",
                {
                    "action": "archive",
                    "deal_ids": ["audit-import-probe"],
                },
                "bulk.archive",
                None,  # bulk action doesn't need deal_id in body
            ),
        ]

        # Run all three POSTs in sequence so the audit log
        # accumulates entries.
        statuses = [
            (path, _post_json(path, body))
            for path, body, _, _ in SCENARIOS
        ]
        bad_status = [
            f"{path}: {code}" for path, code in statuses
            if code != 200
        ]
        self.assertEqual(
            bad_status, [],
            f"State-changing POSTs that should return 200: "
            f"{bad_status}",
        )

        # Now read the audit page once and check every action.
        audit_html = self.opener.open(
            self.base + "/audit", timeout=8,
        ).read().decode("utf-8", errors="replace")

        missing: list[str] = []
        for _, _, action, identifier in SCENARIOS:
            if action not in audit_html:
                missing.append(
                    f"action token {action!r} not in /audit body"
                )
            if identifier and identifier not in audit_html:
                missing.append(
                    f"identifier {identifier!r} not in /audit body"
                )
        self.assertEqual(
            missing, [],
            f"Audit hooks unwired on state-changing handlers: "
            f"{missing}",
        )

    def test_admin_only_routes_reject_analyst_role(self) -> None:
        """Routes that show user-management or audit data must
        require role=admin, not just role=any-authenticated.

        Admin gating is layered: the auth-gating guard above
        catches public-leak regressions; this guard catches a
        different bug where a contributor accidentally widens an
        admin route to all authenticated users (e.g. by removing
        the role check or copy-pasting from a non-admin handler).
        Together they form a complete RBAC contract.
        """
        # Login as the seeded 'analyst' user (non-admin).
        analyst_jar = CookieJar()
        analyst_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(analyst_jar),
            _NoFollow(),
        )
        analyst_opener.open(self.base + "/login", timeout=5).read()
        csrf = ""
        for c in analyst_jar:
            if "csrf" in c.name.lower():
                csrf = c.value
                break
        body = urllib.parse.urlencode({
            "username": "analyst",
            "password": "AnalystPass!1",
            "csrf_token": csrf,
        }).encode()
        try:
            analyst_opener.open(
                urllib.request.Request(
                    self.base + "/api/login",
                    data=body, method="POST",
                ),
                timeout=5,
            )
        except urllib.error.HTTPError as e:
            if e.code not in (200, 303):
                raise

        ADMIN_ONLY = ["/users", "/audit"]
        leaks: list[str] = []
        for path in ADMIN_ONLY:
            try:
                resp = analyst_opener.open(
                    self.base + path, timeout=5,
                )
                code = getattr(resp, "status", 0)
            except urllib.error.HTTPError as e:
                code = e.code
            # 403 (forbidden — authenticated but not authorised)
            # is the correct response. Some installations might
            # return 401 if the gate also re-validates the
            # session — both are acceptable rejections.
            if code not in (401, 403):
                leaks.append(
                    f"{path}: status {code} for analyst user "
                    f"(expected 401 or 403 — admin-only route "
                    f"accepting non-admin)"
                )
        self.assertEqual(
            leaks, [],
            f"Admin-only routes accepting non-admin users: "
            f"{leaks}",
        )

    def test_analysis_export_content_types_per_format(self) -> None:
        """``/api/analysis/<id>/export?format=<fmt>`` must return
        the right Content-Type for each format. The export router
        switches on the format query param to dispatch to different
        renderers (HTML viewer, JSON packet, CSV, XLSX, PPTX, ZIP
        package, diligence questions). Each renderer sets its own
        Content-Type — drift between query value and header is a
        partner-visible bug (downloads with wrong extension, parsers
        that key off the header).

        Pins the five formats whose Content-Types the smoke harness
        can probe without leaking a binary blob into pytest stdout.
        """
        EXPECTED = {
            "html":    "text/html",
            "json":    "application/json",
            "csv":     "text/csv",
            "xlsx":    "application/vnd.openxmlformats",
            "package": "application/zip",
        }
        gaps: list[str] = []
        for fmt, want in EXPECTED.items():
            try:
                resp = self.opener.open(
                    self.base + f"/api/analysis/smoke-a/export"
                    f"?format={fmt}",
                    timeout=10,
                )
            except Exception as e:
                gaps.append(f"{fmt}: fetch error {e!r}")
                continue
            ct = resp.headers.get("Content-Type", "")
            if want.lower() not in ct.lower():
                gaps.append(
                    f"{fmt}: Content-Type={ct!r}, expected to "
                    f"contain {want!r}"
                )
        self.assertEqual(
            gaps, [],
            f"Export Content-Type drift across formats: {gaps}",
        )

    def test_put_patch_delete_envelope_contracts(self) -> None:
        """Companion to test_documented_post_happy_paths — the
        non-POST mutation verbs (PUT, PATCH, DELETE) on the deal
        override and profile API must:

        * PUT /api/deals/<id>/overrides/<unknown_key>: 400 with
          ``code: INVALID_OVERRIDE`` envelope
        * PATCH /api/deals/<id>/profile: 200 with
          ``{deal_id, updated_fields}`` envelope (positive path)
        * DELETE /api/deals/<id>/overrides/<missing_key>: 404 with
          ``code: OVERRIDE_NOT_FOUND`` envelope

        These verbs share the same CSRF + auth gates as POST but
        run through different dispatchers (do_PUT / do_PATCH /
        do_DELETE) — locking their envelopes catches drift in any
        of the three.
        """
        import json
        csrf = ""
        for c in self.cookies:
            if c.name == "rcm_csrf":
                csrf = c.value
                break

        # PUT with unknown override prefix → INVALID_OVERRIDE
        req = urllib.request.Request(
            self.base + "/api/deals/smoke-a/overrides/unknown_xx",
            data=json.dumps({"value": "v", "reason": "x"}).encode(),
            method="PUT",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("X-CSRF-Token", csrf)
        try:
            self.opener.open(req, timeout=5)
            self.fail("PUT with unknown prefix should 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body.get("code"), "INVALID_OVERRIDE")
            self.assertIn("error", body)

        # PATCH /profile happy path → 200 + updated_fields
        req = urllib.request.Request(
            self.base + "/api/deals/smoke-a/profile",
            data=json.dumps({"chain": "PatchTest"}).encode(),
            method="PATCH",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("X-CSRF-Token", csrf)
        resp = self.opener.open(req, timeout=5)
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(body.get("deal_id"), "smoke-a")
        self.assertIn("chain", body.get("updated_fields", []))

        # DELETE missing override → OVERRIDE_NOT_FOUND
        req = urllib.request.Request(
            self.base + "/api/deals/smoke-a/overrides/never_set",
            method="DELETE",
        )
        req.add_header("X-CSRF-Token", csrf)
        try:
            self.opener.open(req, timeout=5)
            self.fail("DELETE missing override should 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body.get("code"), "OVERRIDE_NOT_FOUND")

    def test_documented_post_happy_paths_return_200(self) -> None:
        """Companion to the rejection guards (CSRF/auth) — every
        documented POST must accept a properly-formed JSON body
        with a valid CSRF token and return 200.

        Without this positive test, the rejection guards (which
        only assert 403/401) couldn't tell the difference between
        a route that's correctly gated and one that's broken in
        a way that ALWAYS rejects (e.g. accidentally hardcoded
        403 in the handler). Pinning happy-paths catches that
        regression class.
        """
        import json
        csrf = ""
        for c in self.cookies:
            if c.name == "rcm_csrf":
                csrf = c.value
                break

        SCENARIOS: list[tuple[str, object]] = [
            ("/api/metrics/custom", {
                "metric_key": "smoke_happy_path",
                "display_name": "Smoke Happy Path",
                "unit": "pct",
                "directionality": "higher_is_better",
                "category": "custom",
                "description": "regression test",
            }),
            ("/api/screener/run", {
                "filters": [],
                "name": "Smoke Screen",
                "limit": 3,
            }),
            ("/api/chat", {"message": "ping"}),
            ("/api/webhooks", {
                "url": "https://partner.example.com/hook",
                "event": "deal.update",
                "description": "regression test",
            }),
            # /api/deals/import takes an array, not an object —
            # tested in its own clause below.
            ("/api/deals/import", [{
                "deal_id": "smoke-import-happy",
                "name": "Smoke Import Happy",
                "profile": {},
            }]),
            ("/api/deals/bulk", {
                "action": "archive",
                "deal_ids": ["smoke-import-happy"],
            }),
            ("/api/portfolio/register", {
                "deal_id": "smoke-register-happy",
                "name": "Register Smoke",
                "stage": "sourced",
            }),
        ]
        failures: list[str] = []
        for path, body_payload in SCENARIOS:
            req = urllib.request.Request(
                self.base + path,
                data=json.dumps(body_payload).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("X-CSRF-Token", csrf)
            try:
                resp = self.opener.open(req, timeout=10)
                code = getattr(resp, "status", 0)
                body = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                code = e.code
                body = e.read().decode("utf-8", errors="replace")
            if code != 200:
                failures.append(
                    f"{path}: expected 200, got {code} "
                    f"(body: {body[:200]!r})"
                )
                continue
            try:
                json.loads(body)
            except Exception as e:
                failures.append(
                    f"{path}: 200 but body not JSON ({e!r})"
                )
        self.assertEqual(
            failures, [],
            f"Documented POST happy paths failing: {failures}",
        )

    def test_form_body_post_to_json_endpoint_does_not_hang(self) -> None:
        """Every JSON-expecting POST endpoint must return promptly
        when called with Content-Type: application/x-www-form-
        urlencoded — never hang for 120 seconds.

        Background: the CSRF middleware in _do_post_inner reads
        the form body via _read_form_body() to extract csrf_token.
        Pre-fix, JSON handlers then did their own
        self.rfile.read(n) — rfile was already drained, so the
        read blocked waiting for Content-Length bytes that would
        never arrive. 120s socket timeout per call. A partner
        misconfigured to send form-urlencoded instead of JSON
        could DOS themselves; an attacker could exhaust the
        thread pool with cheap stuck sockets.

        Fix: 14 handlers migrated to ``self._raw_post_body()``
        which caches the read across CSRF + handler accesses.
        """
        import time
        csrf = ""
        for c in self.cookies:
            if c.name == "rcm_csrf":
                csrf = c.value
                break
        body = urllib.parse.urlencode({
            "csrf_token": csrf,
        }).encode()
        # Sweep every JSON-expecting POST in the documented set.
        TARGETS = [
            "/api/screener/run",
            "/api/metrics/custom",
            "/api/webhooks",
            "/api/deals/bulk",
            "/api/deals/import",
            "/api/portfolio/register",
            "/api/chat",
        ]
        slow: list[str] = []
        for path in TARGETS:
            req = urllib.request.Request(
                self.base + path, data=body, method="POST",
            )
            req.add_header("X-CSRF-Token", csrf)
            req.add_header(
                "Content-Type",
                "application/x-www-form-urlencoded",
            )
            t0 = time.time()
            try:
                self.opener.open(req, timeout=10)
            except urllib.error.HTTPError:
                pass
            except urllib.error.URLError as e:
                slow.append(
                    f"{path}: hung ({e}) — likely double-read"
                )
                continue
            elapsed = time.time() - t0
            if elapsed > 5.0:
                slow.append(
                    f"{path}: {elapsed:.1f}s — likely double-read "
                    f"after CSRF middleware drained rfile"
                )
        self.assertEqual(
            slow, [],
            f"JSON-expecting POSTs hanging on form-urlencoded "
            f"body — use self._raw_post_body() instead of "
            f"self.rfile.read(): {slow}",
        )

    def test_login_get_already_authed_rejects_open_redirect(self) -> None:
        """When an already-authenticated partner visits
        /login?next=<url>, the handler bounces them to ``next``.
        That same-origin check must reject the same vectors as
        the POST /api/login validator (B146 + backslash close):

        * ``//evil`` (protocol-relative)
        * ``https://evil`` (absolute)
        * ``/\\evil`` (browser-converts to ``//``)

        Pre-fix, the GET /login validator only checked
        ``startswith("/")`` — accepted ``//evil`` directly. This
        guard is the regression net for that fix.
        """
        EVIL = [
            "//evil.example.com",
            "https://evil.example.com",
            "/\\evil.example.com",
        ]
        SAFE = [
            "/portfolio",
            "/audit",
            "/deal/foo",
        ]

        def _follow_redirect(nxt: str) -> str:
            # cls.opener is logged in — visiting /login?next=…
            # should redirect for an authenticated user.
            try:
                resp = self.opener.open(
                    self.base + "/login?next="
                    + urllib.parse.quote(nxt),
                    timeout=5,
                )
                return resp.headers.get("Location", "") if resp else ""
            except urllib.error.HTTPError as e:
                return e.headers.get("Location", "")

        leaks: list[str] = []
        for nxt in EVIL:
            loc = _follow_redirect(nxt)
            # Acceptable: empty (no redirect — login page renders),
            # or "/" (default fallback). Unacceptable: anything
            # echoing the evil token.
            if loc and "evil" in loc.lower():
                leaks.append(
                    f"GET /login?next={nxt!r} echoed evil "
                    f"token in Location={loc!r}"
                )
            if loc and (loc.startswith("//") or "://" in loc
                        or "\\" in loc):
                leaks.append(
                    f"GET /login?next={nxt!r} → suspicious "
                    f"Location={loc!r}"
                )

        self.assertEqual(
            leaks, [],
            f"GET /login open-redirect vectors accepted: {leaks}",
        )

    def test_login_next_param_rejects_open_redirect_vectors(self) -> None:
        """The ``next`` param on /api/login must not accept any
        URL that a browser could resolve cross-origin. Vectors
        covered:

        * ``https://evil`` — absolute URL → reject
        * ``//evil`` — protocol-relative → reject
        * ``/\\evil`` — backslash variant (IE/Edge auto-convert
          ``/\\`` → ``//`` → external redirect) → reject
        * ``javascript:`` — JS pseudo-scheme → reject
        * ``/legit-path`` — same-origin path → accept

        An open redirect at the login boundary is a phishing
        gadget: an attacker links to /login?next=https://phish
        and a partner who completes login lands on the attacker's
        page, often without noticing the redirect.
        """
        anon = urllib.request.build_opener(_NoFollow())
        # Seed CSRF.
        try:
            anon.open(self.base + "/login", timeout=5).read()
        except Exception:
            pass

        EVIL = [
            "https://evil.example.com",
            "//evil.example.com",
            "/\\evil.example.com",
            "/\\\\evil.example.com",
            "javascript:alert(1)",
        ]
        SAFE = [
            "/portfolio",
            "/audit",
            "/deal/foo",
        ]

        def _login_with_next(nxt: str) -> str:
            body = urllib.parse.urlencode({
                "username": "demo",
                "password": "DemoPass!1",
                "csrf_token": "",
                "next": nxt,
            }).encode()
            try:
                resp = anon.open(
                    urllib.request.Request(
                        self.base + "/api/login",
                        data=body, method="POST",
                    ),
                    timeout=5,
                )
                return resp.headers.get("Location", "") if resp else ""
            except urllib.error.HTTPError as e:
                return e.headers.get("Location", "")

        leaks: list[str] = []
        for nxt in EVIL:
            loc = _login_with_next(nxt)
            # Must NOT echo the evil value. Acceptable: "/" or any
            # local path. Unacceptable: anything that contains the
            # evil token or starts with backslash variants.
            if (loc != "/"
                    and not (loc.startswith("/") and "\\" not in loc
                             and not loc.startswith("//"))):
                leaks.append(f"next={nxt!r} → Location={loc!r}")
            if "evil" in loc.lower() or loc.lower().startswith("javascript:"):
                leaks.append(
                    f"next={nxt!r} echoed dangerous payload in "
                    f"Location={loc!r}"
                )

        broken_safe: list[str] = []
        for nxt in SAFE:
            loc = _login_with_next(nxt)
            if loc != nxt:
                broken_safe.append(
                    f"next={nxt!r} unexpectedly rewritten to "
                    f"Location={loc!r}"
                )

        self.assertEqual(
            leaks, [],
            f"Open-redirect vectors accepted at /api/login: "
            f"{leaks}",
        )
        self.assertEqual(
            broken_safe, [],
            f"Same-origin next= paths broken: {broken_safe}",
        )

    def test_options_preflight_contract(self) -> None:
        """CORS preflight on /api/* must:

        * Return 204 No Content
        * ``Access-Control-Allow-Origin`` (any value — partners'
          browser does the actual origin match)
        * ``Access-Control-Allow-Methods`` listing GET, POST, OPTIONS
        * ``Access-Control-Allow-Headers`` listing Content-Type,
          X-CSRF-Token, AND Idempotency-Key (must mirror exactly
          what _send_json advertises on real responses — drift
          between the two breaks partners' preflights silently)
        * ``Access-Control-Max-Age`` (any positive integer string)
        """
        anon = urllib.request.build_opener(_NoFollow())
        targets = [
            "/api/deals",
            "/api/scenarios",
            "/api/system/info",
            "/api/login",
        ]
        issues: list[str] = []
        for path in targets:
            req = urllib.request.Request(
                self.base + path, method="OPTIONS",
            )
            req.add_header("Origin", "https://partner.example.com")
            req.add_header("Access-Control-Request-Method", "POST")
            req.add_header(
                "Access-Control-Request-Headers",
                "X-CSRF-Token, Content-Type, Idempotency-Key",
            )
            try:
                resp = anon.open(req, timeout=5)
            except urllib.error.HTTPError as e:
                issues.append(f"{path}: HTTPError {e.code}")
                continue
            status = getattr(resp, "status", 0)
            if status != 204:
                issues.append(f"{path}: status {status}, expected 204")
                continue
            allow_methods = (resp.headers.get("Access-Control-Allow-Methods") or "").upper()
            for m in ("GET", "POST", "OPTIONS"):
                if m not in allow_methods:
                    issues.append(
                        f"{path}: Allow-Methods missing {m} "
                        f"(got {allow_methods!r})"
                    )
            allow_headers = (resp.headers.get("Access-Control-Allow-Headers") or "")
            allow_headers_lower = allow_headers.lower()
            for h in ("content-type", "x-csrf-token", "idempotency-key"):
                if h not in allow_headers_lower:
                    issues.append(
                        f"{path}: Allow-Headers missing {h!r} "
                        f"(got {allow_headers!r})"
                    )
            if not (resp.headers.get("Access-Control-Allow-Origin") or "").strip():
                issues.append(f"{path}: Allow-Origin empty")
            max_age = resp.headers.get("Access-Control-Max-Age", "")
            if not (max_age.isdigit() and int(max_age) > 0):
                issues.append(
                    f"{path}: Max-Age={max_age!r}, expected positive integer"
                )
        self.assertEqual(
            issues, [],
            f"CORS preflight contract violations: {issues}",
        )

    def test_session_cookie_is_httponly_and_samesite(self) -> None:
        """The ``rcm_session`` cookie must be ``HttpOnly`` (XSS
        can't steal it via document.cookie) and carry
        ``SameSite=Lax`` (mitigates CSRF on top-level navigations).

        The companion ``rcm_csrf`` cookie must be ``SameSite=Lax``
        but explicitly NOT ``HttpOnly`` — it has to be JS-readable
        so the auto-injected form patcher can put the token in a
        hidden input. This is the documented design.
        """
        anon = urllib.request.build_opener(_NoFollow())
        # Trigger login to capture Set-Cookie header.
        body = urllib.parse.urlencode({
            "username": "demo",
            "password": "DemoPass!1",
            "csrf_token": "",
        }).encode()
        try:
            anon.open(self.base + "/login", timeout=5).read()
        except Exception:
            pass
        try:
            anon.open(
                urllib.request.Request(
                    self.base + "/api/login",
                    data=body, method="POST",
                ),
                timeout=5,
            )
        except urllib.error.HTTPError as e:
            # A bad-CSRF login replies 403, but Set-Cookie still
            # carries the rcm_csrf seed. We accept any code that
            # surfaces the cookies.
            if e.code not in (200, 303, 401, 403):
                raise

        # /api/login replies 303 on success — must NOT follow the
        # redirect, otherwise we capture headers from the GET /
        # follow-up (which is 401 with no Set-Cookie). Use the
        # no-follow opener and read its first response directly.
        req = urllib.request.Request(
            self.base + "/api/login", data=body, method="POST",
        )
        try:
            resp = anon.open(req, timeout=5)
            headers = resp.headers if resp else None
        except urllib.error.HTTPError as e:
            headers = e.headers
        self.assertIsNotNone(
            headers,
            "login response had no headers (no-follow opener "
            "returned None)",
        )
        set_cookies = headers.get_all("Set-Cookie") or []
        session = next(
            (c for c in set_cookies if c.startswith("rcm_session=")),
            None,
        )
        csrf = next(
            (c for c in set_cookies if c.startswith("rcm_csrf=")),
            None,
        )
        self.assertIsNotNone(
            session,
            f"no rcm_session Set-Cookie on login response "
            f"(headers: {set_cookies})",
        )
        self.assertIsNotNone(
            csrf,
            f"no rcm_csrf Set-Cookie on login response "
            f"(headers: {set_cookies})",
        )
        # Required flags on the session cookie.
        for flag in ("HttpOnly", "SameSite=Lax"):
            self.assertIn(
                flag, session,
                f"rcm_session cookie missing {flag!r}: {session!r}",
            )
        # CSRF cookie: SameSite=Lax yes, HttpOnly intentionally no.
        self.assertIn(
            "SameSite=Lax", csrf,
            f"rcm_csrf cookie missing SameSite=Lax: {csrf!r}",
        )
        self.assertNotIn(
            "HttpOnly", csrf,
            f"rcm_csrf cookie unexpectedly HttpOnly — the auto "
            f"form-patcher needs to read it via document.cookie: "
            f"{csrf!r}",
        )

    def test_state_changing_posts_reject_without_csrf(self) -> None:
        """Every documented state-changing POST must reject
        authenticated requests that lack a valid CSRF token (403)
        AND unauthenticated requests (401).

        Without CSRF, a state-mutating POST is exposed to cross-
        origin attacks: a partner browsing a malicious site while
        logged into the dashboard would have requests forged
        against /api/upload-actuals, /api/portfolio/register, etc.
        Pinning both rejection codes lets a contributor see at a
        glance whether they accidentally relaxed either gate.
        """
        # Build an unauthenticated opener — no cookie jar.
        anon = urllib.request.build_opener(_NoFollow())

        POST_PATHS = [
            "/api/upload-actuals",
            "/api/upload-initiatives",
            "/api/upload-notes",
            "/api/screener/run",
            "/api/portfolio/register",
            "/api/chat",
            "/api/deals/wizard/select",
            "/api/deals/wizard/launch",
            "/api/metrics/custom",
            "/api/webhooks",
            "/api/deals/bulk",
            "/api/deals/import",
        ]

        def _post(opener, path: str, body: bytes = b"") -> int:
            try:
                req = urllib.request.Request(
                    self.base + path, data=body, method="POST",
                )
                resp = opener.open(req, timeout=8)
            except urllib.error.HTTPError as e:
                return e.code
            if resp is None:
                return 0
            return resp.status

        csrf_leaks: list[str] = []
        auth_leaks: list[str] = []
        for path in POST_PATHS:
            # Authenticated, no CSRF token in body — must be 403.
            with_auth = _post(self.opener, path)
            if with_auth != 403:
                csrf_leaks.append(
                    f"{path}: status {with_auth} with auth+no-CSRF, "
                    f"expected 403"
                )
            # Unauthenticated — must be 401 (auth wins over CSRF).
            no_auth = _post(anon, path)
            if no_auth != 401:
                auth_leaks.append(
                    f"{path}: status {no_auth} unauth, expected 401"
                )

        self.assertEqual(
            csrf_leaks, [],
            f"State-changing POSTs accepting requests without "
            f"valid CSRF token: {csrf_leaks}",
        )
        self.assertEqual(
            auth_leaks, [],
            f"State-changing POSTs reachable to anonymous "
            f"callers: {auth_leaks}",
        )

    def test_partner_data_routes_require_auth(self) -> None:
        """Every partner-data route must reject unauthenticated
        requests with 401. A regression here is a hard data leak —
        portfolio rows, audit log, system info, deal lists would
        all be readable by anyone hitting the URL.

        The matching public-route check guards against the inverse
        regression: a contributor accidentally adds @auth_required
        to /healthz and silently breaks every load-balancer probe.
        """
        # Build an unauthenticated opener — no cookie jar.
        anon = urllib.request.build_opener(_NoFollow())

        AUTH_REQUIRED = [
            "/audit",
            "/users",
            "/api/system/info",
            "/api/migrations",
            "/api/backup",
            "/api/deals/stats",
            "/alerts",
            "/portfolio",
            "/home",
            "/api/deals",
            "/api/openapi.json",
        ]
        PUBLIC = [
            "/healthz",
            "/health",
            "/login",
        ]

        def _fetch_anon(path: str) -> int:
            try:
                resp = anon.open(self.base + path, timeout=8)
            except urllib.error.HTTPError as e:
                return e.code
            if resp is None:
                return 0
            return resp.status

        leaks: list[str] = []
        for path in AUTH_REQUIRED:
            status = _fetch_anon(path)
            if status != 401:
                leaks.append(f"{path}: status {status}, expected 401")
        broken_public: list[str] = []
        for path in PUBLIC:
            status = _fetch_anon(path)
            if status not in (200, 303):
                broken_public.append(
                    f"{path}: status {status}, expected 200 or 303",
                )
        self.assertEqual(
            leaks, [],
            f"Partner-data routes leaking to anonymous users: "
            f"{leaks}",
        )
        self.assertEqual(
            broken_public, [],
            f"Public routes broken (require auth now): "
            f"{broken_public}",
        )

    def test_server_header_does_not_leak_runtime_version(self) -> None:
        """The Server response header must NOT echo the stdlib
        BaseHTTP version or the Python version. Default
        BaseHTTPRequestHandler emits ``BaseHTTP/0.6 Python/3.14.2``
        — an attacker uses that to map known CVEs to the exact
        runtime. Three sample endpoints span the dispatch surface:

        * /healthz (anonymous liveness)
        * /api/system/info (authenticated JSON)
        * /home (authenticated HTML)
        """
        anon = urllib.request.build_opener(_NoFollow())
        SAMPLES = [
            (anon, "/healthz"),
            (self.opener, "/api/system/info"),
            (self.opener, "/home"),
        ]
        leaks: list[str] = []
        for opener, path in SAMPLES:
            try:
                resp = opener.open(self.base + path, timeout=5)
            except urllib.error.HTTPError as e:
                resp = e
            server_h = (resp.headers.get("Server") or "").lower()
            for marker in ("basehttp", "python/", "python "):
                if marker in server_h:
                    leaks.append(
                        f"{path}: Server={server_h!r} "
                        f"contains {marker!r}"
                    )
                    break
        self.assertEqual(
            leaks, [],
            f"Server header leaks runtime version: {leaks}",
        )

    def test_responses_carry_x_request_id_header(self) -> None:
        """Every JSON response (200 + 4XX + 5XX) must carry an
        ``X-Request-Id`` header. Partner SDKs and our own log
        correlation depend on this — without it, an operator
        debugging a 4XX has no way to find the matching log
        line in the access log.

        The body-level ``request_id`` field varies by handler
        (some use _send_error which adds it, some build their
        own envelope without). The header is the canonical
        correlation key.
        """
        SAMPLES = [
            ("/api/system/info",                     200),
            ("/api/portfolio/regression",            400),
            ("/api/jobs/foo",                        404),
            ("/api/digest?since=junk",               400),
            ("/api/deals/this-id-does-not-exist",    404),
        ]
        missing: list[str] = []
        for path, _ in SAMPLES:
            try:
                resp = self.opener.open(self.base + path, timeout=5)
                headers = resp.headers
            except urllib.error.HTTPError as e:
                headers = e.headers
            rid = headers.get("X-Request-Id", "").strip()
            if not rid:
                missing.append(f"{path}: X-Request-Id missing")
            elif len(rid) < 8:
                missing.append(
                    f"{path}: X-Request-Id={rid!r} suspiciously short"
                )
        self.assertEqual(
            missing, [],
            f"X-Request-Id correlation gaps: {missing}",
        )

    def test_error_pages_do_not_leak_stack_traces_or_paths(self) -> None:
        """4XX / 5XX response bodies must never leak Python stack
        trace text or absolute filesystem paths. Both reveal
        internal implementation:

        * Stack traces tell an attacker exactly where validation
          fires, which lines guard which checks, and what
          libraries are imported.
        * Absolute paths (``/Users/...``, ``site-packages``,
          ``/Library/...``) leak deployment topology — the
          install root, Python version, virtualenv structure.

        The existing exception-leakage guard catches 200-with-
        error-body. This one catches the symmetric case: an
        explicit 4XX/5XX whose body still echoes the trace.
        """
        SCENARIOS = [
            "/api/portfolio/regression",
            "/api/jobs/foo",
            "/api/deals/this-id-does-not-exist",
            "/api/digest?since=junk",
            "/non-existent-route",
            "/api/non-existent-api",
            "/deal/non-existent-deal-id",
        ]
        TRACE_MARKERS = (
            "Traceback (most recent",
            "cannot access local",
            "TypeError: ",
            "AttributeError: ",
            "KeyError: ",
            "NameError: ",
            "UnboundLocalError",
            ", in ",  # "line N, in func"
        )
        PATH_MARKERS = (
            "/Users/",
            "site-packages",
            "/Library/",
        )
        leaks: list[str] = []
        for path in SCENARIOS:
            try:
                resp = self.opener.open(self.base + path, timeout=5)
                body = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
            for marker in TRACE_MARKERS:
                if marker in body:
                    leaks.append(
                        f"{path}: stack-trace marker {marker!r} "
                        f"in body"
                    )
                    break
            for marker in PATH_MARKERS:
                if marker in body:
                    leaks.append(
                        f"{path}: path marker {marker!r} in body"
                    )
                    break
        self.assertEqual(
            leaks, [],
            f"Error responses leaking trace/path: {leaks}",
        )

    def test_4xx_responses_carry_error_envelope(self) -> None:
        """Every documented 4XX scenario must return a JSON body
        with a top-level ``error`` string field. Partners writing
        SDKs against the API depend on this envelope to surface
        actionable error text — a 4XX with a missing or
        non-string ``error`` field would crash their client.

        The fixture-list below covers each distinct validator path
        in the dispatcher: missing-required-param, out-of-range
        target, unknown-id (deal + job), and invalid-format query.
        """
        import json
        ERROR_SCENARIOS = [
            # (path, expected_status)
            ("/api/portfolio/regression",          400),
            ("/api/deals/compare",                 400),
            ("/api/counterfactual",                400),
            ("/api/jobs/nonexistent",              404),
            ("/api/deals/this-id-does-not-exist",  404),
            ("/api/digest?since=invalid",          400),
            # PUT /override with unknown prefix → INVALID_OVERRIDE 400
            # exercises the override-prefix validator's error envelope.
            # (Covered by the parametric loop; PUT-specific status is
            # exercised in test_put_patch_delete_happy_paths below.)
        ]
        issues: list[str] = []
        for path, want_status in ERROR_SCENARIOS:
            try:
                resp = self.opener.open(self.base + path, timeout=8)
                actual = resp.status
                body = resp.read()
            except urllib.error.HTTPError as e:
                actual = e.code
                body = e.read()
            if actual != want_status:
                issues.append(
                    f"{path}: status {actual}, expected {want_status}"
                )
                continue
            try:
                parsed = json.loads(body.decode("utf-8"))
            except Exception as e:
                issues.append(f"{path}: body not JSON ({e!r})")
                continue
            err = parsed.get("error") if isinstance(parsed, dict) else None
            if not isinstance(err, str) or not err:
                issues.append(
                    f"{path}: missing/non-string 'error' field "
                    f"(body keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__})"
                )
        self.assertEqual(
            issues, [],
            f"Error-envelope contract violations: {issues}",
        )

    def test_json_endpoints_set_cache_control(self) -> None:
        """Every JSON endpoint must set ``Cache-Control``. Without
        an explicit directive, intermediaries (proxies, browsers,
        CDNs) infer a default that may cache partner data — a
        downstream proxy could then return one partner's deal list
        to another partner if cookie-namespacing isn't perfect.

        Most endpoints set ``no-store`` (partner-data path); a few
        static-ish surfaces use ``private, max-age=N`` (e.g.
        /api/openapi.json caches the spec briefly per-user). The
        guard accepts either as long as the header is present.
        """
        SKIP = {
            "/healthz", "/health",
            "/api/backup",
            "/api/deals/smoke-a/package",
            "/api/analysis/smoke-a/export",
            "/api/docs",
        }
        missing: list[str] = []
        for path, expected_status in API_SMOKE_ROUTES:
            if expected_status != 200:
                continue
            if path in SKIP:
                continue
            if path.endswith(".csv") or path.endswith(".memo"):
                continue
            try:
                resp = self.opener.open(self.base + path, timeout=8)
            except Exception:
                continue
            cc = resp.headers.get("Cache-Control", "")
            if not cc:
                missing.append(path)
        self.assertEqual(
            missing, [],
            f"JSON endpoints lacking Cache-Control "
            f"({len(missing)}): {missing}",
        )

    def test_json_endpoints_set_nosniff_header(self) -> None:
        """Every 200-pinned JSON endpoint must set
        ``X-Content-Type-Options: nosniff``.

        Without nosniff, a browser can MIME-sniff a JSON response
        as HTML — a partner-supplied string reflected into the body
        could then execute as script in old browsers. The
        application/json Content-Type alone isn't sufficient
        protection.

        Routes that legitimately return non-JSON (text/csv,
        application/zip, application/x-sqlite3, text/plain liveness
        probes, text/html viewer pages) are exempt.
        """
        SKIP_NOT_JSON = {
            "/healthz", "/health",
            "/api/backup",
            "/api/deals/smoke-a/package",
            "/api/analysis/smoke-a/export",
            "/api/docs",
        }
        missing: list[str] = []
        for path, expected_status in API_SMOKE_ROUTES:
            if expected_status != 200:
                continue
            if path in SKIP_NOT_JSON:
                continue
            if path.endswith(".csv") or path.endswith(".memo"):
                continue
            try:
                resp = self.opener.open(self.base + path, timeout=8)
            except Exception:
                continue
            xcto = resp.headers.get("X-Content-Type-Options", "")
            if xcto.lower() != "nosniff":
                missing.append(
                    f"{path}: X-Content-Type-Options={xcto!r}"
                )
        self.assertEqual(
            missing, [],
            f"JSON endpoints lacking X-Content-Type-Options: nosniff "
            f"({len(missing)}): {missing}",
        )

    def test_endpoints_return_expected_content_type(self) -> None:
        """Every 200-pinned smoke endpoint must return the
        Content-Type a partner client expects:

        * ``application/json`` for /api/* JSON endpoints
        * ``text/csv`` for /api/*.csv exports
        * ``text/`` (any subtype) for /api/*.memo and /api/docs
          (HTML viewers / markdown memos)
        * ``application/x-sqlite3`` for /api/backup
        * ``application/zip`` for /api/deals/<id>/package
        * ``text/`` for /api/analysis/<id>/export (default HTML)
        * ``text/plain`` for /healthz and /health liveness probes

        A wrong Content-Type breaks partner-side parsers silently:
        a Python ``response.json()`` call against a text/plain
        body raises, and SDK regenerators key off the header.
        """
        EXPECTED_CTYPE = {
            "/healthz":                          "text/plain",
            "/health":                           "text/plain",
            "/api/backup":                       "application/x-sqlite3",
            "/api/deals/smoke-a/package":        "application/zip",
            "/api/analysis/smoke-a/export":      "text/",
            "/api/docs":                         "text/html",
        }

        def _expected(path: str) -> str:
            override = EXPECTED_CTYPE.get(path)
            if override:
                return override
            if path.endswith(".csv"):
                return "text/csv"
            if path.endswith(".memo"):
                return "text/"
            return "application/json"

        issues: list[str] = []
        for path, expected_status in API_SMOKE_ROUTES:
            if expected_status != 200:
                continue
            try:
                resp = self.opener.open(
                    self.base + path, timeout=8,
                )
            except Exception:
                continue
            ct = resp.headers.get("Content-Type", "")
            want = _expected(path)
            if want.lower() not in ct.lower():
                issues.append(
                    f"{path}: Content-Type={ct!r}, expected to "
                    f"contain {want!r}"
                )
        self.assertEqual(
            issues, [],
            f"Content-Type mismatches ({len(issues)}): {issues}",
        )

    def test_no_endpoint_leaks_python_exceptions_in_body(self) -> None:
        """For every 200-pinned smoke endpoint, the response body
        must not contain Python-exception strings.

        This generalises the regression-net for the unbound-`store`
        bug fixed in 88f717e3: that bug returned HTTP 200 with
        ``{"error": "cannot access local variable 'store' ..."}``
        for every comparison row, so the status-only smoke missed
        it. Any handler that swallows an exception into a JSON-200
        envelope leaks the same pattern; this guard catches the
        whole class.

        Failures point at the path + the phrase that tripped the
        guard so the contributor can grep the dispatcher directly.
        """
        bad_phrases = (
            "cannot access local",
            "Traceback (most recent",
            "TypeError: ",
            "AttributeError: ",
            "KeyError: ",
            "NameError: ",
            "UnboundLocalError",
        )
        suspects: list[tuple[str, str]] = []
        for path, expected in API_SMOKE_ROUTES:
            if expected != 200:
                continue
            try:
                resp = self.opener.open(
                    self.base + path, timeout=8,
                )
                body = resp.read().decode("utf-8", errors="replace")
            except Exception:
                continue
            for phrase in bad_phrases:
                if phrase in body:
                    suspects.append((path, phrase))
                    break
        self.assertEqual(
            suspects, [],
            f"Endpoints leaking Python-exception text into the "
            f"response body (likely a swallowed-exception bug "
            f"similar to the unbound-`store` defect): {suspects}",
        )

    def test_deal_compare_returns_real_rows_not_unbound_store_errors(
        self,
    ) -> None:
        """Regression net for the unbound-`store` bug in
        /api/deals/compare. Before the fix the handler returned 200
        with a body of error stubs ({"error": "cannot access local
        variable 'store' ..."}). Now each comparison row must carry
        completeness_grade + ebitda_impact + metrics. This test
        catches anyone who reverts the PortfolioStore bind."""
        import json
        resp = self.opener.open(
            self.base
            + "/api/deals/compare?ids=smoke-a,smoke-b",
            timeout=8,
        )
        body = json.loads(resp.read().decode("utf-8"))
        self.assertIn("deals", body)
        self.assertEqual(len(body["deals"]), 2)
        for row in body["deals"]:
            self.assertNotIn(
                "error", row,
                f"row {row.get('deal_id')} carries an error: "
                f"{row.get('error')!r} — likely the unbound `store` "
                f"bug has regressed",
            )
            self.assertIn("completeness_grade", row)
            self.assertIn("ebitda_impact", row)
            self.assertIn("metrics", row)


if __name__ == "__main__":
    unittest.main()
