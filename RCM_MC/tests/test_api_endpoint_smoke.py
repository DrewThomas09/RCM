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
    # path). /api/deals/compare requires ?ids= with two demo deals.
    ("/api/alerts/active-count",                          200),
    ("/api/data/hospitals",                               200),
    ("/api/deals",                                        200),
    ("/api/deals/compare?ids=demo-acme,demo-baxter",      200),
    ("/api/portfolio/regression",                         400),
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


if __name__ == "__main__":
    unittest.main()
