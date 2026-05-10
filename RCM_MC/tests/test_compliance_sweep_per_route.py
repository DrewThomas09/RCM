"""Per-route compliance sweep — Phase 7 / Prompt 100 acceptance.

Boots a real RCM-MC server, logs in as the demo user, fetches a
representative set of routes, and scores each with the P100
compliance checker. Prints per-route results and asserts the
median score meets a floor.

The floor starts at 0.6 (60%) — every shelled page picks up the
kit's CSS bundles automatically (motion tokens, focus rule, print
stylesheet, etc.) so even un-migrated pages clear that bar. The
acceptance target from PROMPTS.md is 0.95; raise the floor
incrementally as more pages migrate to the kit primitives.

Routes that 401 / 404 / 5xx are skipped — the sweep is about
content compliance, not auth-gate correctness.
"""
from __future__ import annotations

import os
import socket
import statistics
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


REPRESENTATIVE_ROUTES = [
    "/login",
    "/now",
    "/home",
    "/library",
    "/data",
    "/diligence/checklist",
    "/methodology",
    "/methodology/pe_math",
    "/alerts",
    "/escalations",
    "/portfolio",
    "/lp-update",
    "/audit",
    "/scenarios",
    "/team",
    "/settings",
    "/diligence/bear-case",
    "/screening/bankruptcy-survivor",
    "/cms-sources",
    "/market-rates",
    # Added — broader workflow coverage:
    "/import",
    "/verticals",
    "/predictive-screener",
    "/runs",
    "/calibration",
    "/news",
    "/source",
    # Workflow + analytics broadening (2026-05):
    "/cohorts",
    "/comparables",
    "/compare",
    "/dashboard",
    "/benchmarks",
    "/backtest",
    "/covenant-headroom",
    "/capital-pacing",
    "/cms-data-browser",
    "/cap-structure",
    "/watchlist",
    "/admin/audit-chain",
    "/admin/data-sources",
    "/board-governance",
    "/capital-efficiency",
    "/concentration-risk",
    "/corpus-backtest",
    "/corpus-coverage",
    "/corpus-dashboard",
    "/clinical-outcomes",
    "/aco-economics",
    "/conferences",
    "/corpus-ic-memo",
    "/covenant-monitor",
    "/provider-network",
    "/value-creation",
    "/mgmt-fee-tracker",
    "/caduceus",
    "/activity",
    "/backtester",
    "/underwriting-model",
]

# Per-route minimum compliance scores. Each route is pinned at
# its observed current state (rounded down slightly for floating-
# point safety on the 15-rule denominator). Any regression on
# *that specific route* fails the test, even if the median stays
# high — single-route regressions can't hide behind aggregate.
#
# Floors that should ratchet UP as routes migrate fully:
#   - 0.92 routes (currently 14/15) have an interpretive-prose
#     ``number-format-clean`` residual; they'd hit 100% if the
#     prose were rephrased to avoid round-percent references.
#   - 0.25 (bankruptcy-survivor) is a bespoke print layout — un-
#     migrated by design.
ROUTE_MIN_SCORES: dict[str, float] = {
    # 100% routes — pinned at 1.0; any kit-presence regression
    # drops a rule and fails this floor.
    "/now":         1.0,
    "/data":        1.0,
    "/methodology": 1.0,
    "/alerts":      1.0,
    "/escalations": 1.0,
    "/portfolio":   1.0,
    "/lp-update":   1.0,
    "/audit":       1.0,
    "/team":                1.0,
    "/settings":            1.0,
    "/cms-sources":         1.0,
    "/diligence/checklist":   1.0,
    "/scenarios":             1.0,
    "/diligence/bear-case":   1.0,
    "/methodology/pe_math":   1.0,
    # Added in the broader-workflow batch:
    "/import":                1.0,
    "/verticals":             1.0,
    "/runs":                  1.0,
    "/calibration":           1.0,
    "/source":                1.0,
    "/predictive-screener":   1.0,
    "/home":                  1.0,
    "/library":               1.0,
    "/market-rates":          1.0,
    # Workflow + analytics broadening (2026-05) — 100% routes:
    "/cohorts":               1.0,
    "/comparables":           1.0,
    "/compare":               1.0,
    "/benchmarks":            1.0,
    "/backtest":              1.0,
    "/watchlist":             1.0,
    "/admin/audit-chain":     1.0,
    "/concentration-risk":    1.0,
    "/corpus-backtest":       1.0,
    "/corpus-dashboard":      1.0,
    "/dashboard":             1.0,
    "/cms-data-browser":      1.0,
    "/admin/data-sources":    1.0,
    "/capital-pacing":        1.0,
    "/capital-efficiency":    1.0,
    "/covenant-headroom":     1.0,
    "/corpus-coverage":       1.0,
    "/clinical-outcomes":     1.0,
    "/aco-economics":         1.0,
    "/cap-structure":         1.0,
    "/board-governance":      1.0,
    "/conferences":           1.0,
    "/corpus-ic-memo":        1.0,
    "/covenant-monitor":      1.0,
    "/provider-network":      1.0,
    "/value-creation":        1.0,
    "/mgmt-fee-tracker":      1.0,
    "/caduceus":              1.0,
    "/activity":              1.0,
    "/backtester":            1.0,
    "/underwriting-model":    1.0,

    # 92% route — /news renders editorial copy with many embedded
    # press-release financial figures ("$8.2B Sale", "12% margin")
    # that read as journalistic citations, not metric values.
    # Forcing 2dp / 1dp throughout the news feed harms readability.
    "/news":                  0.92,

    # Bespoke print layout — un-migrated by design.
    "/screening/bankruptcy-survivor": 0.25,
}
# Fallback for any route added without an explicit pin. Tight at
# 1.0 — every existing pinned route is at 100% (or one of the two
# explicit residual exceptions /news, /bankruptcy-survivor). A new
# route added to ``REPRESENTATIVE_ROUTES`` without an explicit
# pin must therefore score 100% from the start, or its addition
# would be the regression that fails this floor.
DEFAULT_ROUTE_MIN_SCORE = 1.0

# The aggregate target. With 45/47 routes at 100% (only /news at
# 0.92 and /screening/bankruptcy-survivor at 0.25 are intentional
# residuals), the median is 100%. Pin tightly: any single-route
# regression that drops a kit-presence rule fails the median floor.
AGGREGATE_FLOOR_MEDIAN = 1.0

# Floor on the count of routes scoring at exactly 100%. The aggregate
# median can stay 1.0 even if multiple routes drop to 99% (one
# rule slip), so this guard catches a different regression mode:
# silent erosion of the *count* of perfect routes. With 45/47
# pinned at 1.0, any new <100% slip fails this floor.
PERFECT_ROUTE_FLOOR = 55


class _NoFollow(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, *a, **kw): return None
    def http_error_302(self, *a, **kw): return None
    def http_error_303(self, *a, **kw): return None


class PerRouteComplianceSweep(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Force v2 chrome on; that's the path the migrations target.
        os.environ["CHARTIS_UI_V2"] = "1"

        from rcm_mc.server import build_server
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.auth.auth import create_user

        cls.tmp = tempfile.mkdtemp(prefix="rcm_p100sweep_")
        cls.db = os.path.join(cls.tmp, "p.db")
        # Seed a demo user so the auth-gated routes are reachable.
        store = PortfolioStore(cls.db)
        create_user(store, "demo", "DemoPass!1",
                    display_name="Demo Partner", role="admin")

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

        # Log in once; reuse the cookie jar for every fetch.
        cls.cookies = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cls.cookies),
            _NoFollow(),
        )
        # Pull the login page first to seed the CSRF cookie.
        opener.open(cls.base + "/login", timeout=5).read()
        # Find the csrf token cookie.
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
            # The login route uses a 303 See Other on success; the
            # NoFollow handler returns None so we land here.
            if e.code not in (200, 303):
                raise

        cls.opener = opener

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def _fetch(self, path: str) -> tuple[int, str]:
        try:
            resp = self.opener.open(self.base + path, timeout=8)
        except urllib.error.HTTPError as e:
            return e.code, ""
        except urllib.error.URLError:
            return 0, ""
        if resp is None:
            return 0, ""
        return resp.status, resp.read().decode("utf-8", errors="replace")

    def test_per_route_compliance_meets_floor(self) -> None:
        from rcm_mc.ui.compliance_sweep import compliance_check

        scores: dict[str, float] = {}
        skipped: list[str] = []
        details: list[tuple[str, float, list[str]]] = []
        for path in REPRESENTATIVE_ROUTES:
            status, body = self._fetch(path)
            if status != 200 or not body:
                skipped.append(f"{path} ({status})")
                continue
            report = compliance_check(body)
            score = report["score"]
            scores[path] = score
            failing = [r["key"] for r in report["results"]
                       if not r["passed"]]
            details.append((path, score, failing))

        # Print a per-route table for human inspection.
        print("\nPer-route compliance:")
        for path, score, failing in details:
            mark = "✓" if score >= 1.0 else "·"
            print(f"  {mark} {path:42s} {score:5.0%}  {failing}")
        if skipped:
            print(f"  skipped: {skipped}")

        self.assertGreater(len(scores), 0,
                           "no routes returned 200 — sweep broken")

        # Aggregate floor.
        median = statistics.median(scores.values())
        self.assertGreaterEqual(
            median, AGGREGATE_FLOOR_MEDIAN,
            f"median compliance {median:.0%} below floor "
            f"{AGGREGATE_FLOOR_MEDIAN:.0%}",
        )

        # Per-route floor — catches a single-page regression that
        # the median would otherwise mask.
        for path, score in scores.items():
            floor = ROUTE_MIN_SCORES.get(path, DEFAULT_ROUTE_MIN_SCORE)
            with self.subTest(route=path):
                self.assertGreaterEqual(
                    score, floor,
                    f"{path} compliance {score:.0%} below per-route "
                    f"floor {floor:.0%}",
                )

        # Perfect-route count floor — catches silent erosion that
        # the median + per-route pins would miss. If a route drops
        # 100% → 93% (one kit rule slip), per-route pin catches it
        # only if pinned at 1.0; routes pinned at 0.93 or DEFAULT
        # would slip silently. This guard catches the count.
        perfect = sum(1 for s in scores.values() if s >= 1.0)
        self.assertGreaterEqual(
            perfect, PERFECT_ROUTE_FLOOR,
            f"only {perfect} routes at 100% — below floor "
            f"{PERFECT_ROUTE_FLOOR}. A regression dropped one or "
            f"more routes from 100% to <100%.",
        )


if __name__ == "__main__":
    unittest.main()
