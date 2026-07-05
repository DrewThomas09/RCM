"""What partners see is a ruling, not an emergent score.

Guards the surface-visibility registry (rcm_mc/ui/_surface_visibility.py):
internal routes (auth / admin / debug / file-download artifacts) never render
as partner-facing destination cards, sentinel "All X →" rows and alias
duplicates collapse, and the same rules apply on every generic listing
surface — /tools showcase, the auto-built section catalogs, the ranked /best
fallback, and the topbar bars.
"""
from __future__ import annotations

import re
import unittest


class CurateRowsTests(unittest.TestCase):
    def test_drops_internal_sentinel_and_alias_rows(self):
        from rcm_mc.ui._surface_visibility import curate_rows
        rows = [
            {"route": "/login", "label": "Login"},
            {"route": "/labor-market.xlsx", "label": "Labor Market.Xlsx"},
            {"route": "/diligence", "label": "All Diligence →"},
            {"route": "/diligence/", "label": "Diligence"},
            {"route": "/pipeline", "label": "Deal Pipeline"},
            {"route": "/deal-pipeline", "label": "Deal Pipeline"},
            {"route": "/diligence/xray", "label": "CMS X-Ray"},
        ]
        kept = [r["route"] for r in curate_rows(rows)]
        # /pipeline wins its label dupe; the sentinel AND its trailing-slash
        # alias both drop; internal/auth/file rows drop.
        self.assertEqual(kept, ["/pipeline", "/diligence/xray"])

    def test_is_internal_covers_auth_admin_debug_and_artifacts(self):
        from rcm_mc.ui._surface_visibility import is_internal
        for route in ("/login", "/forgot", "/demo", "/users",
                      "/cli-runs", "/pricing-power.xlsx"):
            self.assertTrue(is_internal(route), route)
        for route in ("/diligence/hcris-xray", "/pipeline", "/notes"):
            self.assertFalse(is_internal(route), route)


class ListingSurfacesTests(unittest.TestCase):
    _INTERNAL_SAMPLE = ("/login", "/forgot", "/demo", "/users",
                        "/cli-runs")

    def test_tools_showcase_shows_each_destination_once_no_internal(self):
        from rcm_mc.ui.tools_showcase_page import render_tools_showcase
        h = render_tools_showcase(355)
        rows = re.findall(r'class="tx-row" href="([^"]+)"', h)
        labels = re.findall(r'tx-row-label">([^<]+)<', h)
        for r in rows:
            self.assertNotIn(r, self._INTERNAL_SAMPLE)
            self.assertFalse(r.endswith(".xlsx"), r)
        self.assertNotIn("/diligence/", rows)   # alias of /diligence
        self.assertEqual(len(labels), len(set(labels)),
                         "duplicate tool labels on /tools")
        self.assertFalse([lab for lab in labels if "→" in lab])

    def test_auto_catalog_never_leaks_internal_routes(self):
        # The uncategorized pool is where auth/admin/debug routes rank; its
        # auto-built catalog (and the ranked /best fallback) must not render
        # them as TOOL CARDS. Assertions scope to the card links (sc-link /
        # sb-card) — the shell chrome legitimately links /users from the
        # user-menu "Admin" item.
        from rcm_mc.ui.section_best_page import render_section_best
        from rcm_mc.ui.section_landings import render_section_landing
        cards_re = re.compile(
            r'class="(?:sc-link|sb-card)" href="([^"]+)"')
        for html in (render_section_landing("uncategorized"),
                     render_section_best("uncategorized")):
            self.assertIsNotNone(html)
            cards = cards_re.findall(html)
            self.assertTrue(cards, "no catalog cards rendered")
            for route in cards:
                self.assertNotIn(route, self._INTERNAL_SAMPLE)
                self.assertFalse(route.endswith(".xlsx"), route)

    def test_nav_bars_never_carry_internal_routes(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _ranked_subnav_items
        from rcm_mc.ui._surface_visibility import is_internal
        for sec in _SUB_NAV:
            top, _ = _ranked_subnav_items(sec)
            for s in top:
                self.assertFalse(is_internal(s["href"]), f"{sec}: {s}")


if __name__ == "__main__":
    unittest.main()
