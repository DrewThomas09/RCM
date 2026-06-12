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

    def test_panel_dataset_select_present(self):
        h = render_exhibit_page({})
        self.assertIn('name="ds0"', h)
        self.assertIn('name="ds3"', h)
        self.assertIn("Platform data…", h)
        self.assertIn("Ownership mix by sector", h)

    def test_dataset_pick_alone_loads_real_data_not_defaults(self):
        # ds0 with no pasted data must leave example-default mode and
        # fill panel 1 from the platform dataset.
        h = render_exhibit_page({"ds0": ["snf_by_state"]})
        self.assertIn("TX", h)
        self.assertIn("SNF / nursing homes providers by state", h)
        # The example defaults (donut mix, operator share) must NOT
        # silently pre-fill the other panels.
        self.assertNotIn("Option Care", h)

    def test_pasted_data_wins_over_selected_dataset(self):
        h = render_exhibit_page({
            "ds0": ["snf_by_state"], "d0": ["Q\tV\nQ1\t10\nQ2\t20"],
            "pt0": ["My panel"]})
        self.assertIn("My panel", h)
        # The dataset table did not overwrite the pasted one.
        self.assertNotIn("SNF / nursing homes providers by state",
                         h.split('name="pt0"')[1].split(">")[0])

    def test_panel_edit_in_builder_link(self):
        h = render_exhibit_page({
            "t0": ["pie"], "pt0": ["Mix"], "d0": ["A\tV\nX\t60\nY\t40"]})
        self.assertIn("edit in Chart Builder", h)
        self.assertIn("/chart-builder?type=pie", h)

    def test_bogus_dataset_key_ignored(self):
        h = render_exhibit_page({"ds0": ["drop_table"]})
        self.assertIn("Exhibit Composer", h)

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
