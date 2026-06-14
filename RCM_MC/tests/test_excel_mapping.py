"""Excel Mapping — a configurable US-state choropleth utility.

Drive it from a {state: percentage} dict (or an Excel paste) + three
gradient colours; it interpolates low→mid→high and labels each state in
black serif text. Tests pin the gradient math, the Excel-paste parser,
the form/qs overrides, and the route wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.excel_mapping_page import (
    gradient_color, parse_values_text, resolve_inputs,
    render_excel_mapping_page, _STATE_TILE, DEFAULT_STATE_VALUES,
)


class GradientTests(unittest.TestCase):
    def test_three_stops_hit_their_colors(self):
        self.assertEqual(
            gradient_color(0, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#ffffff")
        self.assertEqual(
            gradient_color(50, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#888888")
        self.assertEqual(
            gradient_color(100, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#000000")

    def test_interpolates_each_side_of_midpoint(self):
        # Quarter point = halfway between low and mid.
        self.assertEqual(
            gradient_color(25, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#c4c4c4")
        # Three-quarter = halfway between mid and high.
        self.assertEqual(
            gradient_color(75, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#444444")

    def test_none_value_is_neutral_grey(self):
        self.assertEqual(
            gradient_color(None, 0, 50, 100, "#fff", "#888", "#000"),
            "#e6e3dc")

    def test_degenerate_domain_returns_mid(self):
        self.assertEqual(
            gradient_color(5, 10, 10, 10, "#fff", "#abcabc", "#000"),
            "#abcabc")

    def test_clamps_out_of_range(self):
        self.assertEqual(
            gradient_color(-20, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#ffffff")
        self.assertEqual(
            gradient_color(200, 0, 50, 100, "#ffffff", "#888888", "#000000"),
            "#000000")


class ParseTests(unittest.TestCase):
    def test_codes_names_and_separators(self):
        out = parse_values_text(
            "TX 61\nCalifornia,63\nNY\t60\nNew York 60\nFL,62%")
        self.assertEqual(out["TX"], 61.0)
        self.assertEqual(out["CA"], 63.0)
        self.assertEqual(out["NY"], 60.0)   # full name resolves to NY
        self.assertEqual(out["FL"], 62.0)   # trailing % stripped

    def test_bad_rows_skipped(self):
        out = parse_values_text("garbage\nZZ 10\nTX 5\n\n  ")
        self.assertEqual(out, {"TX": 5.0})

    def test_every_default_state_is_a_real_tile(self):
        # The Python-editable default dict only references real states.
        for code in DEFAULT_STATE_VALUES:
            self.assertIn(code, _STATE_TILE)


class ResolveTests(unittest.TestCase):
    def test_defaults_when_no_qs(self):
        cfg = resolve_inputs(None)
        self.assertEqual(cfg["values"], dict(DEFAULT_STATE_VALUES))
        # Auto domain spans the data.
        self.assertEqual(cfg["lo"], min(DEFAULT_STATE_VALUES.values()))
        self.assertEqual(cfg["hi"], max(DEFAULT_STATE_VALUES.values()))

    def test_qs_overrides_colors_and_data(self):
        cfg = resolve_inputs({
            "low": ["#111111"], "mid": ["#222222"], "high": ["#333333"],
            "data": ["TX 61\nCA 63"], "lo": ["0"], "hi": ["100"],
            "midv": ["50"]})
        self.assertEqual(cfg["c_low"], "#111111")
        self.assertEqual(cfg["values"], {"TX": 61.0, "CA": 63.0})
        self.assertEqual((cfg["lo"], cfg["mid"], cfg["hi"]), (0.0, 50.0, 100.0))


class RenderAndRouteTests(unittest.TestCase):
    def test_page_renders_core_elements(self):
        h = render_excel_mapping_page({})
        for needle in ("Excel Mapping", "Render map", "VALUES BY STATE",
                       "HOW TO USE", "serif", 'type="color"', "<svg"):
            self.assertIn(needle, h, f"missing: {needle}")
        # The map draws the real geographic state boundaries, not tiles.
        self.assertIn("<path d=\"M", h)
        self.assertNotIn("viewBox=\"-1 -1", h)   # old tile-grid viewBox gone
        # A state value renders on the page (centroid label + value table).
        self.assertIn(">TX<", h)

    def test_custom_values_appear(self):
        h = render_excel_mapping_page({"data": ["TX 77\nCA 12"]})
        self.assertIn(">77<", h)
        self.assertIn(">12<", h)

    def test_registered_in_palette_and_nav(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/excel-mapping", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/excel-mapping"), "research")

    def test_route_has_guide_context(self):
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        pkt = build_guide_context_packet("/excel-mapping")
        self.assertIsNotNone(pkt.page_context)


if __name__ == "__main__":
    unittest.main()
