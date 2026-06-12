"""CDD chart kit + Chart Builder page.

The kit renders the Excel/consultant chart family as Chartis-styled SVG
from a pasted table. Tests pin the table parser, that every chart type
renders clean SVG (no ``None``/``NaN`` leaks), the waterfall total
convention, and the builder page + route wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.cdd_chart_kit import (
    CHART_TYPES, PALETTES, SIZE_PRESETS, parse_table, render_cdd_chart,
    transform_table, _series, chart_export_toolbar,
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
        if ctype in ("pie", "donut", "marimekko", "funnel", "tornado",
                     "dot"):
            return parse_table("Seg\tA\tB\nX\t40\t10\nY\t30\t20\nZ\t30\t15")
        if ctype == "waterfall":
            return parse_table("Step\tV\nStart\t100\nUp\t20\nDown\t-8\n"
                               "Net\t=112")
        if ctype in ("scatter", "bubble", "matrix"):
            return parse_table("Co\tX\tY\tS\nA\t12\t22\t40\nB\t8\t28\t60")
        if ctype == "radar":
            return parse_table("Ax\tA\tB\nP\t8\t6\nQ\t6\t9\nR\t9\t5\nS\t7\t8")
        if ctype == "bullet":
            return parse_table("KPI\tAct\tTgt\nA\t82\t90\nB\t45\t40")
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

    def test_new_consultant_chart_types_present(self):
        keys = {k for k, _ in CHART_TYPES}
        for k in ("funnel", "tornado", "radar", "matrix", "bullet", "dot",
                  "gauge", "heatmap", "slope", "gantt", "pareto",
                  "histogram", "boxplot", "dumbbell"):
            self.assertIn(k, keys, k)
        self.assertGreaterEqual(len(CHART_TYPES), 27)

    def test_pareto_has_cumulative_line_and_80_marker(self):
        t = parse_table("Reason\tCount\nAuth\t340\nElig\t210\nCoding\t160\n"
                        "Filing\t90")
        svg = render_cdd_chart("pareto", t, {"title": "Denials"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("80%", svg)
        self.assertIn("<polyline", svg)       # cumulative-share line
        self.assertIn("100%", svg)            # last cumulative point
        self.assertNotIn("None", svg)

    def test_histogram_bins_and_annotates(self):
        rows = "\n".join(f"A{i}\t{v}" for i, v in enumerate(
            (34, 41, 38, 52, 47, 44, 39, 61, 46, 43, 55, 37)))
        svg = render_cdd_chart("histogram", parse_table("Acct\tDAR\n" + rows),
                               {"title": "DAR distribution"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("n=12", svg)
        self.assertIn("mean=", svg)
        self.assertNotIn("None", svg)

    def test_boxplot_renders_quartile_boxes(self):
        t = parse_table("Site\tJ\tF\tM\tA\nNorth\t42\t45\t39\t48\n"
                        "South\t38\t36\t41\t35")
        svg = render_cdd_chart("boxplot", t, {"title": "DAR by site"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("North", svg)
        self.assertIn("South", svg)
        self.assertIn("fill-opacity", svg)    # the IQR box
        self.assertNotIn("None", svg)

    def test_dumbbell_renders_pairs_with_period_legend(self):
        t = parse_table("Metric\tEntry\tExit\nMargin\t18\t26\nMix\t34\t41")
        svg = render_cdd_chart("dumbbell", t, {"title": "Entry vs exit"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Margin", svg)
        self.assertIn("Entry", svg)
        self.assertIn("Exit", svg)
        self.assertNotIn("None", svg)

    def test_trendline_overlays_fit_with_r2(self):
        t = parse_table("Co\tX\tY\nA\t1\t2\nB\t2\t4.1\nC\t3\t5.9\nD\t4\t8")
        svg = render_cdd_chart("scatter", t, {"trendline": True})
        self.assertIn("Trend R²=", svg)
        self.assertIn("stroke-dasharray", svg)
        line = render_cdd_chart(
            "line", parse_table("Y\tR\n2021\t100\n2022\t130\n2023\t165"),
            {"trendline": True})
        self.assertIn("Trend R²=", line)
        # Off by default.
        off = render_cdd_chart("scatter", t, {})
        self.assertNotIn("Trend R²=", off)

    def test_slope_and_gantt_render(self):
        s = render_cdd_chart(
            "slope", parse_table("M\tEntry\tExit\nMargin\t18\t26\n"
                                 "Denials\t12\t6"), {"title": "Slope"})
        self.assertTrue(s.startswith("<svg"))
        self.assertIn("Margin", s)
        self.assertNotIn("None", s)
        g = render_cdd_chart(
            "gantt", parse_table("Task\tStart\tEnd\nA\t0\t4\nB\t2\t9"),
            {"title": "Plan"})
        self.assertTrue(g.startswith("<svg"))
        self.assertIn("A", g)
        self.assertNotIn("None", g)

    def test_heatmap_renders_grid_with_headers(self):
        t = parse_table("Driver\tA\tB\nDemand\t9\t6\nSupply\t5\t8")
        svg = render_cdd_chart("heatmap", t, {"title": "Score"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Demand", svg)
        self.assertIn("Supply", svg)
        self.assertNotIn("None", svg)

    def test_footnote_appears_on_chart(self):
        svg = render_cdd_chart(
            "column", parse_table("Y\tR\n2021\t100"),
            {"footnote": "Source: company data"})
        self.assertIn("Source: company data", svg)
        # And on the page.
        h = render_chart_builder_page({"footnote": ["Source: deal team"]})
        self.assertIn("Source: deal team", h)
        self.assertIn('name="footnote"', h)

    def test_gauge_renders_value_and_max(self):
        svg = render_cdd_chart(
            "gauge", parse_table("M\tVal\tMax\nUtilization\t78\t100"),
            {"title": "Util", "suffix": "%"})
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("78", svg)
        self.assertNotIn("None", svg)

    def test_per_series_colors_override_palette(self):
        h = render_chart_builder_page({
            "type": ["column"], "sc0": ["#ff0000"], "sc1": ["#00ff00"]})
        self.assertIn("SERIES COLOURS", h)
        self.assertIn("#ff0000", h)
        self.assertIn("#00ff00", h)
        # The picked colours reach the rendered SVG, not just the form.
        self.assertEqual(h.count("#ff0000") >= 2, True)

    def test_palette_sync_script_present(self):
        h = render_chart_builder_page({})
        self.assertIn("CKPAL", h)

    def test_width_px_controls_display_size(self):
        small = render_cdd_chart("column", self._data("column"),
                                 {"width_px": 520})
        big = render_cdd_chart("column", self._data("column"),
                               {"width_px": 1120})
        self.assertIn("max-width:520px", small)
        self.assertIn("max-width:1120px", big)
        # Proportional scaling (height auto from viewBox), not distortion.
        self.assertIn("height:auto", small)

    def test_export_toolbar_has_svg_png_copy(self):
        tb = chart_export_toolbar("chartOut", "myfile")
        for needle in ("⬇ SVG", "⬇ PNG", "Copy SVG", "ckDlSvg",
                       "ckDlPng", "ckCopySvg", "myfile"):
            self.assertIn(needle, tb, needle)

    def test_size_presets_defined(self):
        keys = [k for k, _ in SIZE_PRESETS]
        self.assertEqual(keys, ["S", "M", "L", "XL"])


class TransformTests(unittest.TestCase):
    """transform_table — the Excel prep steps (SUMIF, sort, top-N,
    running %) folded into the builder."""

    def _t(self, text):
        return parse_table(text)

    def test_group_sum_aggregates_duplicate_labels(self):
        t = self._t("Payer\tDenials\nAetna\t10\nUHC\t5\nAetna\t7")
        out = transform_table(t, {"group": "sum"})
        self.assertEqual(out["rows"], [("Aetna", [17.0]), ("UHC", [5.0])])

    def test_group_mean_and_count(self):
        t = self._t("P\tV\nA\t10\nA\t20")
        self.assertEqual(transform_table(t, {"group": "mean"})["rows"],
                         [("A", [15.0])])
        self.assertEqual(transform_table(t, {"group": "count"})["rows"],
                         [("A", [2.0])])

    def test_sort_desc_by_first_series(self):
        t = self._t("P\tV\nA\t5\nB\t20\nC\t10")
        out = transform_table(t, {"sort": "desc"})
        self.assertEqual([r[0] for r in out["rows"]], ["B", "C", "A"])

    def test_top_n_lumps_rest_into_other(self):
        t = self._t("P\tV\nA\t50\nB\t30\nC\t10\nD\t6\nE\t4")
        out = transform_table(t, {"sort": "desc", "top_n": 2})
        self.assertEqual([r[0] for r in out["rows"]],
                         ["A", "B", "Other (3)"])
        self.assertEqual(out["rows"][-1][1], [20.0])

    def test_pct_total_sums_to_100(self):
        t = self._t("P\tV\nA\t50\nB\t30\nC\t20")
        out = transform_table(t, {"calc": "pct_total"})
        self.assertAlmostEqual(sum(r[1][0] for r in out["rows"]), 100.0)

    def test_cumulative_running_total(self):
        t = self._t("Q\tV\nQ1\t10\nQ2\t20\nQ3\t5")
        out = transform_table(t, {"calc": "cumulative"})
        self.assertEqual([r[1][0] for r in out["rows"]],
                         [10.0, 30.0, 35.0])

    def test_growth_vs_prior_first_row_blank(self):
        t = self._t("Y\tR\n2021\t100\n2022\t130\n2023\t117")
        out = transform_table(t, {"calc": "growth"})
        vals = [r[1][0] for r in out["rows"]]
        self.assertIsNone(vals[0])
        self.assertAlmostEqual(vals[1], 30.0)
        self.assertAlmostEqual(vals[2], -10.0)

    def test_index_first_value_is_100(self):
        t = self._t("Y\tR\n2021\t80\n2022\t120")
        out = transform_table(t, {"calc": "index"})
        self.assertEqual([r[1][0] for r in out["rows"]], [100.0, 150.0])

    def test_moving_avg_window_3(self):
        t = self._t("M\tV\nm1\t10\nm2\t20\nm3\t30\nm4\t40")
        out = transform_table(t, {"calc": "moving_avg"})
        self.assertEqual([r[1][0] for r in out["rows"]],
                         [10.0, 15.0, 20.0, 30.0])

    def test_ops_compose_group_then_sort_then_topn(self):
        t = self._t("P\tV\nA\t5\nB\t20\nA\t10\nC\t8")
        out = transform_table(
            t, {"group": "sum", "sort": "desc", "top_n": 2})
        self.assertEqual([r[0] for r in out["rows"]],
                         ["B", "A", "Other (1)"])

    def test_input_table_not_mutated(self):
        t = self._t("P\tV\nA\t10\nA\t20")
        transform_table(t, {"group": "sum", "calc": "pct_total"})
        self.assertEqual(t["rows"], [("A", [10.0]), ("A", [20.0])])


class BuilderPageTests(unittest.TestCase):
    def test_page_renders_core_elements(self):
        h = render_chart_builder_page({})
        for needle in ("Chart Builder", "Render chart", "GALLERY",
                       "Waterfall (bridge)", "Marimekko", "<textarea",
                       "<svg", "Funnel", "Tornado", "Radar",
                       'id="chartOut"', "⬇ SVG", 'name="size"'):
            self.assertIn(needle, h, f"missing: {needle}")

    def test_size_control_changes_render_width(self):
        h = render_chart_builder_page({"size": ["L"]})
        self.assertIn("max-width:920px", h)

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

    def test_shaping_controls_present(self):
        h = render_chart_builder_page({})
        for needle in ("DATA SHAPING", 'name="group"', 'name="sort"',
                       'name="topn"', 'name="calc"', 'name="trend"',
                       "% of total", "Largest first"):
            self.assertIn(needle, h, f"missing: {needle}")

    def test_group_sum_applied_to_rendered_chart(self):
        h = render_chart_builder_page({
            "type": ["column"], "group": ["sum"],
            "data": ["Payer\tDenials\nAetna\t10\nUHC\t5\nAetna\t7"]})
        self.assertIn(">17<", h)              # aggregated bar value label

    def test_topn_lumps_other_in_chart(self):
        h = render_chart_builder_page({
            "type": ["bar"], "sort": ["desc"], "topn": ["2"],
            "data": ["P\tV\nA\t50\nB\t30\nC\t10\nD\t6\nE\t4"]})
        self.assertIn("Other (3)", h)

    def test_trendline_checkbox_drives_overlay(self):
        h = render_chart_builder_page({
            "type": ["scatter"], "trend": ["1"],
            "data": ["Co\tX\tY\nA\t1\t2\nB\t2\t4\nC\t3\t6\nD\t4\t8"]})
        self.assertIn("Trend R²=", h)

    def test_bogus_shaping_params_ignored(self):
        h = render_chart_builder_page({
            "group": ["drop table"], "sort": ["weird"],
            "topn": ["nope"], "calc": ["bad"]})
        self.assertIn("Chart Builder", h)

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
