"""Tests for the healthcare unit-economics spine page (/cdd/unit-economics).

The page reads straight from the cdd registry (NEW-22 through NEW-26), so the
load-bearing guarantees are: it renders without leaking internals into broken
markup, every panel's headline figures reach the HTML, and the route is wired
into the server, nav, breadcrumbs, and command palette.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.cdd_unit_economics_page import ROUTE, render_cdd_unit_economics


class CddUnitEconomicsPageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_cdd_unit_economics()

    def test_renders_all_five_exhibits(self):
        # Each panel carries its feature code chip.
        for code in ("NEW-22", "NEW-23", "NEW-24", "NEW-25", "NEW-26"):
            self.assertIn(f"[{code}]", self.html)
        self.assertIn("Healthcare Unit Economics", self.html)

    def test_shows_headline_anchors(self):
        # A verified anchor (LTACH discharge) and the dialysis concentration.
        self.assertIn("Long-term acute care", self.html)
        self.assertIn("50,824.51", self.html)
        self.assertIn("Dialysis", self.html)

    def test_estimates_marked(self):
        # Secondary-source rows render with the estimate marker.
        self.assertIn("(estimate)", self.html)

    def test_no_unescaped_conflict_or_template_leak(self):
        self.assertNotIn("{", self.html.split("<style>")[0])  # no stray f-fields in body head
        self.assertNotIn("None /", self.html)

    def test_route_is_served(self):
        import rcm_mc.server as server_mod
        with open(server_mod.__file__, encoding="utf-8") as f:
            src = f.read()
        handled = set(re.findall(r"""path\s*==\s*['"](/[^'"]+)['"]""", src))
        self.assertIn(ROUTE, handled)

    def test_registered_in_nav_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_NAV, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn(ROUTE, routes)
        self.assertEqual(_SUB_SECTION_MAP.get(ROUTE), "diligence")
        nav_hrefs = {item["href"] for item in _SUB_NAV["diligence"]}
        self.assertIn(ROUTE, nav_hrefs)


if __name__ == "__main__":
    unittest.main()
