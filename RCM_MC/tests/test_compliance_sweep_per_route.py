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
    "/risk-adjustment",
    "/capital-schedule",
    "/cms-apm",
    "/exit-multiple",
    "/capex-budget",
    "/capital-call",
    "/clinical-ai",
    "/biosimilars",
    "/workforce-planning",
    "/coinvest-pipeline",
    "/compliance-attestation",
    "/cyber-risk",
    "/cost-structure",
    "/continuation-vehicle",
    "/bolton-analyzer",
    "/key-person",
    "/operating-partners",
    "/supply-chain",
    "/vdr-tracker",
    "/digital-front-door",
    "/entry-multiple",
    "/health-equity",
    "/quality-scorecard",
    "/tech-stack",
    "/multiple-decomp",
    "/payer-stress",
    "/qoe-analyzer",
    "/tax-credits",
    "/hold-optimizer",
    "/antitrust-screener",
    "/acq-timing",
    "/ai-operating-model",
    "/analysis",
    "/deadlines",
    "/deal-flow-heatmap",
    "/deal-search",
    "/demand-forecast",
    "/engagements",
    "/exit-readiness",
    "/exports",
    "/find-comps",
    "/fund-learning",
    "/gp-benchmarking",
    "/initiatives",
    "/insights",
    "/jobs",
    "/ma-contracts",
    "/module-index",
    "/msa-concentration",
    "/notes",
    "/ops",
    "/owners",
    "/patient-experience",
    "/payer-intel",
    "/payer-intelligence",
    "/physician-productivity",
    "/portfolio-analytics",
    "/portfolio-optimizer",
    "/pressure",
    "/query",
    "/real-estate",
    "/return-attribution",
    "/revenue-leakage",
    "/risk-matrix",
    "/screen",
    "/search",
    "/sector-correlation",
    "/sector-intel",
    "/sector-momentum",
    "/sponsor-league",
    "/sponsor-track-record",
    "/surrogate",
    "/upload",
    "/users",
    "/variance",
    "/vintage-perf",
    "/diligence-checklist",
    "/pipeline",
    "/data-intelligence",
    "/direct-lending",
    "/exit-timing",
    "/pe-intelligence",
    "/provider-retention",
    "/rcm-benchmarks",
    "/redflag-scanner",
    "/regulatory-risk",
    "/scenario-mc",
    "/value-creation-plan",
    "/deal-quality",
    "/denovo-expansion",
    "/direct-employer",
    "/esg-dashboard",
    "/esg-impact",
    "/medical-realestate",
    "/rw-insurance",
    "/underwriting",
    "/unit-economics",
    "/vintage-cohorts",
    "/distress",
    "/drug-shortage",
    "/pmi-playbook",
    "/vcp-tracker",
    "/zbb-tracker",
    "/deal-risk-scores",
    "/tax-structure",
    "/telehealth-econ",
    "/gpo-supply",
    "/hold-analysis",
    "/payer-contracts",
    "/ref-pricing",
    "/competitive-intel",
    "/debt-service",
    "/leverage-intel",
    "/nav-loan-tracker",
    "/litigation",
    "/payer-concentration",
    "/growth-runway",
    "/peer-transactions",
    "/treasury",
    "/tracker-340b",
    "/payer-shift",
    "/peer-valuation",
    "/rcm-red-flags",
    "/debt-financing",
    "/working-capital",
    "/lp-dashboard",
    "/drug-pricing-340b",
    "/irr-dispersion",
    "/size-intel",
    "/earnout",
    "/fraud-detection",
    "/dpi-tracker",
    "/escrow-earnout",
    "/medicaid-unwinding",
    "/lp-reporting",
    "/mgmt-comp",
    "/partner-economics",
    "/payer-rate-trends",
    "/platform-maturity",
    "/market-intel",
    "/hcit-platform",
    "/cin-analyzer",
    "/transition-services",
    "/geo-market",
    "/locum-tracker",
    "/deal-origination",
    "/reit-analyzer",
    "/rollup-economics",
    "/dividend-recap",
    "/sellside-process",
    "/tax-structure-analyzer",
    "/deal-sourcing",
    "/fundraising",
    "/workforce-retention",
    "/ic-memo-gen",
    "/deal-postmortem",
    "/base-rates",
    "/refi-optimizer",
    "/sponsor-heatmap",
    "/insurance-tracker",
    "/nsa-tracker",
    "/reinvestment",
    "/hospital-anchor",
    "/physician-labor",
    "/fund-attribution",
    "/deal-pipeline",
    "/trial-site-econ",
    "/diligence-vendors",
    "/phys-comp-plan",
    "/secondaries-tracker",
    "/pmi-integration",
    "/ml-insights",
    "/model-validation",
    "/quant-lab",
    "/ma-star",
    "/lbo-stress",
    "/specialty-benchmarks",
    "/deal-screening",
    "/diligence/comparable-outcomes",
    "/diligence/compare",
    "/diligence/covenant-stress",
    "/diligence/deal-mc",
    "/diligence/deal",
    "/diligence/exit-timing",
    "/diligence/physician-attrition",
    "/diligence/regulatory-calendar",
    "/diligence/risk-workbench",
    "/diligence/sponsor-detail",
    "/portfolio/heatmap",
    "/portfolio/map",
    "/portfolio/risk-scan",
    "/diligence/bridge-audit",
    "/diligence/counterfactual",
    "/diligence/hcris-xray",
    "/diligence/ic-packet",
    "/diligence/management",
    "/diligence/payer-stress",
    "/portfolio/regression",
    "/diligence/benchmarks",
    "/diligence/denial-prediction",
    "/diligence/ingest",
    "/diligence/root-cause",
    "/diligence/thesis-pipeline",
    "/diligence/value",
    "/data/refresh",
    "/pipeline/bridge",
    "/settings/ai",
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
    "/risk-adjustment":       1.0,
    "/capital-schedule":      1.0,
    "/cms-apm":               1.0,
    "/exit-multiple":         1.0,
    "/capex-budget":          1.0,
    "/capital-call":          1.0,
    "/clinical-ai":           1.0,
    "/biosimilars":           1.0,
    "/workforce-planning":    1.0,
    "/coinvest-pipeline":     1.0,
    "/compliance-attestation": 1.0,
    "/cyber-risk":            1.0,
    "/cost-structure":        1.0,
    "/continuation-vehicle":  1.0,
    "/bolton-analyzer":       1.0,
    "/key-person":            1.0,
    "/operating-partners":    1.0,
    "/supply-chain":          1.0,
    "/vdr-tracker":           1.0,
    "/digital-front-door":    1.0,
    "/entry-multiple":        1.0,
    "/health-equity":         1.0,
    "/quality-scorecard":     1.0,
    "/tech-stack":            1.0,
    "/multiple-decomp":       1.0,
    "/payer-stress":          1.0,
    "/qoe-analyzer":          1.0,
    "/tax-credits":           1.0,
    "/hold-optimizer":        1.0,
    "/antitrust-screener":    1.0,
    "/acq-timing":            1.0,
    "/ai-operating-model":    1.0,
    "/analysis":              1.0,
    "/deadlines":             1.0,
    "/deal-flow-heatmap":     1.0,
    "/deal-search":           1.0,
    "/demand-forecast":       1.0,
    "/engagements":           1.0,
    "/exit-readiness":        1.0,
    "/exports":               1.0,
    "/find-comps":            1.0,
    "/fund-learning":         1.0,
    "/gp-benchmarking":       1.0,
    "/initiatives":           1.0,
    "/insights":              1.0,
    "/jobs":                  1.0,
    "/ma-contracts":          1.0,
    "/module-index":          1.0,
    "/msa-concentration":     1.0,
    "/notes":                 1.0,
    "/ops":                   1.0,
    "/owners":                1.0,
    "/patient-experience":    1.0,
    "/payer-intel":           1.0,
    "/payer-intelligence":    1.0,
    "/physician-productivity": 1.0,
    "/portfolio-analytics":   1.0,
    "/portfolio-optimizer":   1.0,
    "/pressure":              1.0,
    "/query":                 1.0,
    "/real-estate":           1.0,
    "/return-attribution":    1.0,
    "/revenue-leakage":       1.0,
    "/risk-matrix":           1.0,
    "/screen":                1.0,
    "/search":                1.0,
    "/sector-correlation":    1.0,
    "/sector-intel":          1.0,
    "/sector-momentum":       1.0,
    "/sponsor-league":        1.0,
    "/sponsor-track-record":  1.0,
    "/surrogate":             1.0,
    "/upload":                1.0,
    "/users":                 1.0,
    "/variance":              1.0,
    "/vintage-perf":          1.0,
    "/diligence-checklist":   1.0,
    "/pipeline":              1.0,
    "/data-intelligence":     1.0,
    "/direct-lending":        1.0,
    "/exit-timing":           1.0,
    "/pe-intelligence":       1.0,
    "/provider-retention":    1.0,
    "/rcm-benchmarks":        1.0,
    "/redflag-scanner":       1.0,
    "/regulatory-risk":       1.0,
    "/scenario-mc":           1.0,
    "/value-creation-plan":   1.0,
    "/deal-quality":          1.0,
    "/denovo-expansion":      1.0,
    "/direct-employer":       1.0,
    "/esg-dashboard":         1.0,
    "/esg-impact":            1.0,
    "/medical-realestate":    1.0,
    "/rw-insurance":          1.0,
    "/underwriting":          1.0,
    "/unit-economics":        1.0,
    "/vintage-cohorts":       1.0,
    "/distress":              1.0,
    "/drug-shortage":         1.0,
    "/pmi-playbook":          1.0,
    "/vcp-tracker":           1.0,
    "/zbb-tracker":           1.0,
    "/deal-risk-scores":      1.0,
    "/tax-structure":         1.0,
    "/telehealth-econ":       1.0,
    "/gpo-supply":            1.0,
    "/hold-analysis":         1.0,
    "/payer-contracts":       1.0,
    "/ref-pricing":           1.0,
    "/competitive-intel":     1.0,
    "/debt-service":          1.0,
    "/leverage-intel":        1.0,
    "/nav-loan-tracker":      1.0,
    "/litigation":            1.0,
    "/payer-concentration":   1.0,
    "/growth-runway":         1.0,
    "/peer-transactions":     1.0,
    "/treasury":              1.0,
    "/tracker-340b":          1.0,
    "/payer-shift":           1.0,
    "/peer-valuation":        1.0,
    "/rcm-red-flags":         1.0,
    "/debt-financing":        1.0,
    "/working-capital":       1.0,
    "/lp-dashboard":          1.0,
    "/drug-pricing-340b":     1.0,
    "/irr-dispersion":        1.0,
    "/size-intel":            1.0,
    "/earnout":               1.0,
    "/fraud-detection":       1.0,
    "/dpi-tracker":           1.0,
    "/escrow-earnout":        1.0,
    "/medicaid-unwinding":    1.0,
    "/lp-reporting":          1.0,
    "/mgmt-comp":             1.0,
    "/partner-economics":     1.0,
    "/payer-rate-trends":     1.0,
    "/platform-maturity":     1.0,
    "/market-intel":          1.0,
    "/hcit-platform":         1.0,
    "/cin-analyzer":          1.0,
    "/transition-services":   1.0,
    "/geo-market":            1.0,
    "/locum-tracker":         1.0,
    "/deal-origination":      1.0,
    "/reit-analyzer":         1.0,
    "/rollup-economics":      1.0,
    "/dividend-recap":        1.0,
    "/sellside-process":      1.0,
    "/tax-structure-analyzer": 1.0,
    "/deal-sourcing":         1.0,
    "/fundraising":           1.0,
    "/workforce-retention":   1.0,
    "/ic-memo-gen":           1.0,
    "/deal-postmortem":       1.0,
    "/base-rates":            1.0,
    "/refi-optimizer":        1.0,
    "/sponsor-heatmap":       1.0,
    "/insurance-tracker":     1.0,
    "/nsa-tracker":           1.0,
    "/reinvestment":          1.0,
    "/hospital-anchor":       1.0,
    "/physician-labor":       1.0,
    "/fund-attribution":      1.0,
    "/deal-pipeline":         1.0,
    "/trial-site-econ":       1.0,
    "/diligence-vendors":     1.0,
    "/phys-comp-plan":        1.0,
    "/secondaries-tracker":   1.0,
    "/pmi-integration":       1.0,
    "/ml-insights":           1.0,
    "/model-validation":      1.0,
    "/quant-lab":             1.0,
    "/ma-star":               1.0,
    "/lbo-stress":            1.0,
    "/specialty-benchmarks":  1.0,
    "/deal-screening":        1.0,
    "/diligence/comparable-outcomes": 1.0,
    "/diligence/compare":     1.0,
    "/diligence/covenant-stress": 1.0,
    "/diligence/deal-mc":     1.0,
    "/diligence/deal":        1.0,
    "/diligence/exit-timing": 1.0,
    "/diligence/physician-attrition": 1.0,
    "/diligence/regulatory-calendar": 1.0,
    "/diligence/risk-workbench": 1.0,
    "/diligence/sponsor-detail": 1.0,
    "/portfolio/heatmap":     1.0,
    "/portfolio/map":         1.0,
    "/portfolio/risk-scan":   1.0,
    "/diligence/bridge-audit": 1.0,
    "/diligence/counterfactual": 1.0,
    "/diligence/hcris-xray":  1.0,
    "/diligence/ic-packet":   1.0,
    "/diligence/management":  1.0,
    "/diligence/payer-stress": 1.0,
    "/portfolio/regression":  1.0,
    "/diligence/benchmarks":  1.0,
    "/diligence/denial-prediction": 1.0,
    "/diligence/ingest":      1.0,
    "/diligence/root-cause":  1.0,
    "/diligence/thesis-pipeline": 1.0,
    "/diligence/value":       1.0,
    "/data/refresh":          1.0,
    "/pipeline/bridge":       1.0,
    "/settings/ai":           1.0,

    # /news — editorial press-release copy, now reformatted to 2dp
    # money / 1dp percent / 2dp multiples to match the rest of the
    # platform. Range bounds (``5-7 years``, ``50.0%+``) preserved.
    "/news":                  1.0,

    # Migrated to v2 chrome. The result page (POST → printable PDF)
    # stays bespoke because the editorial chrome would carry into
    # the print layout, but the GET landing form now wraps in
    # chartis_shell and scores 100%.
    "/screening/bankruptcy-survivor": 1.0,
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
PERFECT_ROUTE_FLOOR = 264


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

    def setUp(self) -> None:
        """Re-pin CHARTIS_UI_V2=1 + drop cached kit modules at the
        start of every test method.

        Background: the conftest autouse fixture drops kit modules
        and resets CHARTIS_UI_V2 to its session-start value between
        every test method. With multiple test methods in this class,
        the second method onward would lazy-import the kit with the
        env var unset and bind to the v1 shell — every kit-presence
        rule would then fail across all 264 routes.
        """
        import sys
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)

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

    def test_html_routes_set_required_security_headers(self) -> None:
        """Every 200-returning HTML route must set the four
        baseline browser-security headers:

        * X-Content-Type-Options: nosniff (MIME-confusion guard)
        * X-Frame-Options: DENY (clickjacking guard)
        * Content-Security-Policy (XSS / injection guard)
        * Referrer-Policy (cross-origin leak guard)

        Regressing any of these is silent in normal use — the page
        still renders, but a partner's browser loses a layer of
        defence-in-depth. Pre-flight scan: 0/264 routes had a gap;
        this guard locks that state in.
        """
        REQUIRED = (
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
        )
        gaps: list[tuple[str, str]] = []
        for path in REPRESENTATIVE_ROUTES:
            try:
                resp = self.opener.open(
                    self.base + path, timeout=8,
                )
            except Exception:
                continue
            if resp.status != 200:
                continue
            for h in REQUIRED:
                if not resp.headers.get(h):
                    gaps.append((path, h))
        self.assertEqual(
            gaps, [],
            f"HTML routes lacking baseline security headers "
            f"({len(gaps)}): {gaps[:20]}",
        )

    def test_no_route_leaks_python_exceptions_in_html(self) -> None:
        """For every 200-returning HTML route, the body must not
        contain Python-exception strings.

        Mirrors the API smoke harness's exception-leakage guard
        (test_no_endpoint_leaks_python_exceptions_in_body) — a
        handler that catches an internal error and renders a
        traceback into the HTML response is partner-visible damage
        but the editorial compliance sweep wouldn't fail it (the
        kit primitives are still present in the shell). This guard
        catches it directly.
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
        for path in REPRESENTATIVE_ROUTES:
            status, body = self._fetch(path)
            if status != 200 or not body:
                continue
            for phrase in bad_phrases:
                if phrase in body:
                    suspects.append((path, phrase))
                    break
        self.assertEqual(
            suspects, [],
            f"HTML routes leaking Python-exception text into the "
            f"response body: {suspects}",
        )


if __name__ == "__main__":
    unittest.main()
