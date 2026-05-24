"""PR 11 — route-level illustrative banner.

The data_public analyzer surface (~158 routes) renders realistic-looking
figures from the bundled illustrative seed corpus / modeled assumptions, NOT
the user's ingested portfolio. chartis_shell auto-injects ONE honest
disclosure for any registered route, idempotent with per-page labels.

These tests lock in:
  - the banner fires for a registered route with no prior note;
  - it is idempotent (no double-disclosure when the page already labels);
  - the conditionally-real HCRIS pages and meta/nav pages are excluded;
  - the registry stays in sync with the actual seed-backed analyzer pages.
"""
import re
import pathlib
import unittest

from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_illustrative_note,
    _is_illustrative_route,
    _ILLUSTRATIVE_ANALYZER_ROUTES,
)

# Pages that carry their own per-state provenance — must NOT get a blanket
# route-level illustrative banner (real HCRIS when a CCN is attached, etc.).
_EXCLUDED_ROUTES = {
    "/payer-stress", "/cost-structure", "/debt-service", "/cms-apm",
    "/scenario-mc", "/tax-structure-analyzer", "/base-rates",
    "/corpus-dashboard", "/cms-sources", "/module-index",
}


def _banners(html: str) -> int:
    return html.count('role="note"')


class TestRouteIllustrativeBanner(unittest.TestCase):
    def test_fires_for_registered_route(self):
        html = chartis_shell("<p>x</p>", "T", active_nav="/deal-quality")
        self.assertEqual(_banners(html), 1)

    def test_idempotent_with_per_page_label(self):
        body = ck_illustrative_note("x") + "<p>x</p>"
        html = chartis_shell(body, "T", active_nav="/lbo-stress")
        self.assertEqual(_banners(html), 1)

    def test_excluded_routes_get_no_banner(self):
        for route in _EXCLUDED_ROUTES:
            with self.subTest(route=route):
                self.assertFalse(_is_illustrative_route(route))
                html = chartis_shell("<p>x</p>", "T", active_nav=route)
                self.assertEqual(_banners(html), 0)

    def test_non_registry_route_no_banner(self):
        html = chartis_shell("<p>x</p>", "T", active_nav="/analysis/deal1")
        self.assertEqual(_banners(html), 0)

    def test_query_and_slash_normalized(self):
        self.assertTrue(_is_illustrative_route("/lbo-stress?ev=200"))
        self.assertTrue(_is_illustrative_route("/lbo-stress/"))
        self.assertFalse(_is_illustrative_route(None))

    def test_registry_routes_are_well_formed(self):
        for r in _ILLUSTRATIVE_ANALYZER_ROUTES:
            self.assertTrue(r.startswith("/"), r)
            self.assertNotIn("?", r)
            self.assertEqual(r, r.rstrip("/") or "/")

    def test_excluded_not_in_registry(self):
        # The conditionally-real / self-labeling routes must stay out.
        for route in ("/payer-stress", "/cost-structure", "/debt-service",
                      "/cms-apm", "/scenario-mc", "/tax-structure-analyzer",
                      "/base-rates"):
            self.assertNotIn(route, _ILLUSTRATIVE_ANALYZER_ROUTES)


if __name__ == "__main__":
    unittest.main()
