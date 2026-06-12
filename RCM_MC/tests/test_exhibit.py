"""Exhibit composer — lay up to 4 charts on one deck slide.

Tests pin the composition (nested chart SVGs, layout by panel count,
title/source), the page form, and the route/nav/guide wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.cdd_chart_kit import compose_exhibit, parse_table
from rcm_mc.ui.exhibit_page import render_exhibit_page


class ComposeTests(unittest.TestCase):
    def _panels(self, n):
        base = [
            {"type": "column", "title": "A",
             "table": parse_table("Y\tR\n2021\t100\n2022\t130")},
            {"type": "donut", "title": "B",
             "table": parse_table("S\tV\nX\t60\nY\t40")},
            {"type": "waterfall", "title": "C",
             "table": parse_table("S\tV\na\t10\nNet\t=10")},
            {"type": "bar", "title": "D",
             "table": parse_table("O\tV\np\t5\nq\t7")},
        ]
        return base[:n]

    def test_composes_one_svg_with_nested_charts(self):
        svg = compose_exhibit(self._panels(4), title="Highlights",
                              eyebrow="CDD", source="Source: x")
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.rstrip().endswith("</svg>"))
        self.assertNotIn("None", svg)
        # Parent + 4 nested chart svgs.
        self.assertEqual(svg.count("<svg"), 5)
        self.assertIn("Highlights", svg)
        self.assertIn("Source: x", svg)

    def test_panel_count_drives_layout(self):
        # Blank panels drop; only those with rows compose.
        self.assertEqual(compose_exhibit(self._panels(1)).count("<svg"), 2)
        self.assertEqual(compose_exhibit(self._panels(2)).count("<svg"), 3)

    def test_empty_panels_yield_just_the_frame(self):
        svg = compose_exhibit([], title="Empty")
        self.assertEqual(svg.count("<svg"), 1)
        self.assertIn("Empty", svg)


class ExhibitPageTests(unittest.TestCase):
    def test_default_page_populated(self):
        h = render_exhibit_page({})
        for needle in ("Exhibit Composer", "PANEL 1", "PANEL 4",
                       "Compose exhibit", 'id="exhibitOut"', "⬇ SVG",
                       "<svg"):
            self.assertIn(needle, h, f"missing: {needle}")

    def test_custom_slide(self):
        h = render_exhibit_page({
            "t0": ["pie"], "pt0": ["Mix"], "d0": ["A\tV\nX\t60\nY\t40"],
            "title": ["My Slide"], "source": ["Source: deal"]})
        self.assertIn("My Slide", h)
        self.assertIn("Source: deal", h)

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/exhibit", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/exhibit"), "research")
        self.assertIsNotNone(
            build_guide_context_packet("/exhibit").page_context)


if __name__ == "__main__":
    unittest.main()
