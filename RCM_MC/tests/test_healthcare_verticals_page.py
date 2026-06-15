"""Healthcare Verticals deep-dive reference page (/healthcare-verticals).

Guards the editorial invariants (single h1, masthead present), that the
19-vertical content actually renders, and that the page is wired into
the Library sub-nav, the breadcrumb section map, and the Cmd-K palette
so a partner can reach it. The route itself is exercised end-to-end by
test_subnav_integrity (every _SUB_NAV href must return 200).
"""
from __future__ import annotations

import re
import unittest


class HealthcareVerticalsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.healthcare_verticals_page import render_healthcare_verticals
        cls.html = render_healthcare_verticals()

    def test_single_h1(self) -> None:
        # Accessibility invariant — exactly one <h1> per page.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_masthead_title(self) -> None:
        self.assertIn("Healthcare Verticals Deep-Dive", self.html)

    def test_anchor_facts_present(self) -> None:
        for fact in ("202,485", "48,149", "1,367", "$33.40"):
            self.assertIn(fact, self.html, msg=f"anchor fact {fact!r} missing")

    def test_verticals_rendered(self) -> None:
        for vertical in (
            "Orthodontics",
            "Oral &amp; Maxillofacial Surgery",
            "Critical Access Hospitals",
            "Organ Transplantation",
            "Veterinary Medicine",
        ):
            self.assertIn(vertical, self.html, msg=f"{vertical!r} missing")

    def test_inline_markdown_converted(self) -> None:
        # No raw markdown leaks into the rendered HTML.
        self.assertIn("<strong>TL;DR</strong>", self.html)
        self.assertIn("<em>Am J Public Health</em>", self.html)
        self.assertNotIn("**TL;DR**", self.html)

    def test_table_of_contents_anchors(self) -> None:
        # Each group header gets an id anchor + a TOC link to it.
        self.assertIn('id="hv-key-findings"', self.html)
        self.assertIn('href="#hv-key-findings"', self.html)

    def test_nav_entry_in_library(self) -> None:
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = [item["href"] for item in _SUB_NAV["library"]]
        self.assertIn("/healthcare-verticals", hrefs)

    def test_section_map_resolves_to_library(self) -> None:
        from rcm_mc.ui._chartis_kit import _resolve_sub_section
        self.assertEqual(_resolve_sub_section("/healthcare-verticals"), "library")

    def test_palette_entry_present(self) -> None:
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = [m["route"] for m in _DEFAULT_PALETTE_MODULES]
        self.assertIn("/healthcare-verticals", routes)


if __name__ == "__main__":
    unittest.main()
