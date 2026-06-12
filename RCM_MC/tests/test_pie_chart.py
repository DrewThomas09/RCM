"""Pie Chart — client-ready pie/donut from per-slice label/value/colour.

Tests pin the presentation-grade renderer (per-slice colours, share
math, legend), the simple row input, and the route/nav/guide wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.cdd_chart_kit import presentable_pie
from rcm_mc.ui.pie_chart_page import render_pie_chart_page, _collect_slices


class PresentablePieTests(unittest.TestCase):
    def _slices(self):
        return [
            {"label": "A", "value": 40, "color": "#0b2341"},
            {"label": "B", "value": 25, "color": "#1F7A75"},
            {"label": "C", "value": 35, "color": "#b8732a"},
        ]

    def test_renders_clean_svg_with_title_and_legend(self):
        svg = presentable_pie(self._slices(), {"title": "Segment Mix"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.rstrip().endswith("</svg>"))
        self.assertNotIn("None", svg)
        self.assertIn("Segment Mix", svg)
        # Legend carries each label + the computed share.
        for lab in ("A", "B", "C"):
            self.assertIn(f">{lab}<", svg)
        self.assertIn("(40%)", svg)   # 40/100

    def test_uses_per_slice_colors(self):
        svg = presentable_pie(self._slices(), {})
        self.assertIn("#0b2341", svg)
        self.assertIn("#1f7a75".upper().lower(), svg.lower())

    def test_falls_back_to_palette_when_color_missing(self):
        svg = presentable_pie([{"label": "X", "value": 1}], {})
        self.assertTrue(svg.startswith("<svg"))

    def test_zero_and_blank_slices_dropped(self):
        svg = presentable_pie(
            [{"label": "A", "value": 10}, {"label": "B", "value": 0},
             {"label": "C", "value": None}], {})
        self.assertIn(">A<", svg)
        self.assertNotIn(">B<", svg)

    def test_empty_shows_prompt(self):
        svg = presentable_pie([], {})
        self.assertIn("Enter slice values", svg)

    def test_donut_has_hole_and_total(self):
        svg = presentable_pie(self._slices(),
                              {"donut": True, "value_suffix": ""})
        self.assertIn("TOTAL", svg)
        self.assertIn(">100<", svg)   # 40+25+35


class PieChartPageTests(unittest.TestCase):
    def test_default_page_is_populated(self):
        h = render_pie_chart_page({})
        for needle in ("Pie Chart", "SLICES — LABEL", "Render chart",
                       "Donut (ring)", 'type="color"', "<svg", "Segment A",
                       'id="pieOut"', "⬇ SVG", "⬇ PNG", 'name="size"'):
            self.assertIn(needle, h, f"missing: {needle}")

    def test_size_control_scales_pie(self):
        h = render_pie_chart_page({"size": ["XL"]})
        self.assertIn("max-width:1120px", h)

    def test_custom_slices_render(self):
        h = render_pie_chart_page({
            "l0": ["Commercial"], "v0": ["45"], "c0": ["#0b2341"],
            "l1": ["Medicare"], "v1": ["35"], "title": ["Payer Mix"]})
        self.assertIn("Payer Mix", h)
        self.assertIn("Commercial", h)
        self.assertIn("(56%)", h)   # 45 / (45+35)

    def test_collect_slices_defaults_then_qs(self):
        # No slice params → the example defaults populate.
        d = _collect_slices(None)
        self.assertEqual(d[0]["label"], "Segment A")
        # Any slice param present → defaults drop out.
        q = _collect_slices({"l0": ["Only"], "v0": ["5"]})
        self.assertEqual(q[0]["label"], "Only")
        self.assertEqual(q[1]["label"], "")

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/pie-chart", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/pie-chart"), "research")
        self.assertIsNotNone(
            build_guide_context_packet("/pie-chart").page_context)


if __name__ == "__main__":
    unittest.main()
