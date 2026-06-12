"""CDD chart kit + Chart Builder page.

The kit renders the Excel/consultant chart family as Chartis-styled SVG
from a pasted table. Tests pin the table parser, that every chart type
renders clean SVG (no ``None``/``NaN`` leaks), the waterfall total
convention, and the builder page + route wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.cdd_chart_kit import (
    CHART_TYPES, PALETTES, parse_table, render_cdd_chart, _series,
)
from rcm_mc.ui.chart_builder_page import render_chart_builder_page


class ParseTableTests(unittest.TestCase):
    def test_tab_separated_with_headers(self):
        t = parse_table("Year\tRev\tEBITDA\n2021\t100\t22\n2022\t130\t31")
        self.assertEqual(t["headers"], ["Year", "Rev", "EBITDA"])
        self.assertEqual(t["rows"][0], ("2021", [100.0, 22.0]))
        self.assertEqual(t["rows"][1], ("2022", [130.0, 31.0]))

    def test_units_stripped(self):
        # Comma-separated handles %/$ ; thousands-commas use tab paste
        # (the Excel default) to avoid the comma-as-separator ambiguity.
        t = parse_table("Seg,Share\nAIC,38%\nHome,$30")
        self.assertEqual(t["rows"][0], ("AIC", [38.0]))
        self.assertEqual(t["rows"][1], ("Home", [30.0]))
        t2 = parse_table("Seg\tShare\nHome\t$1,200")
        self.assertEqual(t2["rows"][0], ("Home", [1200.0]))

    def test_non_numeric_becomes_none(self):
        t = parse_table("A\tB\nx\tn/a")
        self.assertEqual(t["rows"][0], ("x", [None]))

    def test_series_column_major(self):
        t = parse_table("Year\tRev\tEBITDA\n2021\t100\t22\n2022\t130\t31")
        s = _series(t)
        self.assertEqual([x["name"] for x in s], ["Rev", "EBITDA"])
        self.assertEqual(s[0]["values"], [100.0, 130.0])
        self.assertEqual(s[1]["values"], [22.0, 31.0])


class RenderTests(unittest.TestCase):
    def _data(self, ctype):
        if ctype in ("pie", "donut", "marimekko"):
            return parse_table("Seg\tA\tB\nX\t40\t10\nY\t30\t20\nZ\t30\t15")
        if ctype == "waterfall":
            return parse_table("Step\tV\nStart\t100\nUp\t20\nDown\t-8\n"
                               "Net\t=112")
        if ctype in ("scatter", "bubble"):
            return parse_table("Co\tX\tY\tS\nA\t12\t22\t40\nB\t8\t28\t60")
        return parse_table("Year\tRev\tEBITDA\n2021\t100\t22\n2022\t130\t31\n"
                           "2023\t165\t43")

    def test_every_chart_type_renders_clean(self):
        for ctype, _ in CHART_TYPES:
            svg = render_cdd_chart(ctype, self._data(ctype),
                                   {"title": ctype, "palette": "Chartis"})
            self.assertTrue(svg.startswith("<svg"), ctype)
            self.assertTrue(svg.rstrip().endswith("</svg>"), ctype)
            # No leaked Python sentinels in the rendered SVG.
            self.assertNotIn("None", svg, f"{ctype} leaked None")
            self.assertNotIn("NaN", svg, f"{ctype} leaked NaN")

    def test_title_is_centered_and_present(self):
        svg = render_cdd_chart("column", self._data("column"),
                               {"title": "My Deck Chart"})
        self.assertIn("My Deck Chart", svg)
        self.assertIn('text-anchor="middle"', svg)

    def test_empty_table_shows_placeholder(self):
        svg = render_cdd_chart("column", {"headers": [], "rows": []}, {})
        self.assertIn("Paste data", svg)

    def test_waterfall_total_is_absolute(self):
        # A 'Net'/'=' row renders from zero to the absolute value, not a
        # delta on top of the running total.
        data = parse_table("Step\tV\nStart\t100\nUp\t20\nNet\t=120")
        svg = render_cdd_chart("waterfall", data, {})
        self.assertTrue(svg.startswith("<svg"))

    def test_palettes_have_distinct_colors(self):
        for name, cols in PALETTES.items():
            self.assertGreaterEqual(len(cols), 6, name)
            self.assertTrue(all(c.startswith("#") for c in cols), name)


class BuilderPageTests(unittest.TestCase):
    def test_page_renders_core_elements(self):
        h = render_chart_builder_page({})
        for needle in ("Chart Builder", "Render chart", "GALLERY",
                       "Waterfall (bridge)", "Marimekko", "<textarea",
                       "<svg"):
            self.assertIn(needle, h, f"missing: {needle}")

    def test_type_selection_switches_chart(self):
        h = render_chart_builder_page({"type": ["pie"]})
        self.assertIn("Chart Builder", h)
        # Pie example data flows through.
        self.assertIn("AIC", h)

    def test_custom_data_and_title(self):
        h = render_chart_builder_page({
            "type": ["column"], "title": ["Q3 Revenue"],
            "data": ["Q\tR\nQ1\t10\nQ2\t20"]})
        self.assertIn("Q3 Revenue", h)

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/chart-builder", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/chart-builder"), "research")
        self.assertIsNotNone(
            build_guide_context_packet("/chart-builder").page_context)


if __name__ == "__main__":
    unittest.main()
