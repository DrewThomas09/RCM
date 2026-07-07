"""Dataviz kit improvements — cross-kit palette/axis sharing, honest
degenerate handling, and geometry correctness in rendered SVG.

Pins the improvement wave over the three chart kits:

  power_chart  — bar geometry anchored to a zero baseline inside the
                 plot (negative bars visible, no overflow), None = line
                 gap, round nice-number ticks, editorial default theme
                 (house DATA_SERIES palette), precise tooltip formatting
                 opt-in, a11y (role/aria/<title>, legend buttons), real
                 zoom contract (layout serialized, JS rescales), single
                 server-side formatter feeding the JS tooltip.
  cdd_chart_kit — waterfall total detection on word boundaries
                 ("Network fees" is a delta), None cells render as line
                 GAPS not zero dips, signed axes for line/column/
                 scatter, pie drops non-positive slices with a
                 disclosure footnote, combo gets a visible right-hand
                 axis, degenerate inputs explain themselves, bar hover
                 <title>s, legend/x-label truncation, csv-quoted and
                 accounting-negative parsing, once-per-page export JS.
  _chart_kit    — DATA_SERIES mirrors the --sc-data-* tokens, 3+-series
                 grouped charts use it (no semantic status colors as
                 categoricals), negative values on positive-only scales
                 render an explicit red tick, diverging default is the
                 house 1-dp percent, nice-ticks helper, optional SVG
                 export button.

Every assertion runs against real rendered SVG/HTML — no mocks.
"""
from __future__ import annotations

import os
import re
import unittest

from rcm_mc.ui._chart_kit import (
    DATA_SERIES,
    DATA_SERIES_EXTENDED,
    ck_bar_chart,
    ck_chart_assets,
    ck_chart_card,
    ck_diverging_bar,
    ck_grouped_bar,
    ck_nice_ticks,
)
from rcm_mc.ui.cdd_chart_kit import (
    PALETTES,
    chart_export_toolbar,
    parse_table,
    render_cdd_chart,
)
from rcm_mc.ui.power_chart import (
    ChartSeries,
    _format_y,
    render_power_chart,
)

# power_chart plot frame (fixed margins in the module).
_ML, _MT, _MB, _MR = 60, 24, 50, 24
_W, _H = 720, 360
_PW, _PH = _W - _ML - _MR, _H - _MT - _MB

# cdd default plot frame: left=60, top=60, right=W-28, bottom=H-76.
_CDD_Y0, _CDD_Y1 = 60.0, 374.0


def _point_rects(html: str):
    return [
        tuple(float(v) for v in m)
        for m in re.findall(
            r'<rect class="point" x="(-?[\d.]+)" y="(-?[\d.]+)" '
            r'width="([\d.]+)" height="([\d.]+)"', html)
    ]


# ── power_chart: bar geometry ───────────────────────────────────────

class PowerChartBarGeometryTests(unittest.TestCase):
    def test_negative_bar_is_visible_and_hangs_from_zero(self):
        html = render_power_chart(
            chart_id="neg-bar",
            series=[ChartSeries("A", [("Q1", -10), ("Q2", 5)],
                                kind="bar")])
        rects = _point_rects(html)
        self.assertEqual(len(rects), 2)
        # Both bars visible (the old code rendered the negative one
        # with height 0.0).
        for _x, _y, _w, h in rects:
            self.assertGreater(h, 5.0)
        # Negative bar top == positive bar bottom == the zero line.
        neg = rects[0]
        pos = rects[1]
        self.assertAlmostEqual(neg[1], pos[1] + pos[3], delta=0.2)

    def test_all_positive_bars_stay_inside_plot(self):
        # EBITDA 30–38 used to overflow the 360px SVG by 900+px.
        html = render_power_chart(
            chart_id="ebitda-bars",
            series=[ChartSeries("A", [
                ("Q1", 30), ("Q2", 32), ("Q3", 35), ("Q4", 38)],
                kind="bar")])
        rects = _point_rects(html)
        self.assertEqual(len(rects), 4)
        for x, y, w, h in rects:
            self.assertGreaterEqual(x, _ML - 0.5)
            self.assertLessEqual(x + w, _ML + _PW + 0.5)
            self.assertGreaterEqual(y, _MT - 0.5)
            self.assertLessEqual(y + h, _MT + _PH + 0.5)
        # Taller value → taller bar (honest length encoding from 0).
        heights = [r[3] for r in rects]
        self.assertEqual(heights, sorted(heights))

    def test_mixed_sign_bars_draw_zero_axis_line(self):
        html = render_power_chart(
            chart_id="zero-line",
            series=[ChartSeries("A", [("Q1", -3), ("Q2", 4)],
                                kind="bar")])
        # Solid (non-dashed) zero line present inside the plot.
        self.assertIn('stroke-width="1"/>', html)

    def test_first_and_last_bars_do_not_overflow_horizontally(self):
        html = render_power_chart(
            chart_id="edge-bars",
            series=[ChartSeries("A", [("Q1", 3), ("Q2", 4)],
                                kind="bar")])
        for x, _y, w, _h in _point_rects(html):
            self.assertGreaterEqual(x, _ML - 0.5)
            self.assertLessEqual(x + w, _ML + _PW + 0.5)


# ── power_chart: line gaps, ticks, formatting ───────────────────────

class PowerChartLineAndAxisTests(unittest.TestCase):
    def test_none_breaks_polyline_into_segments(self):
        html = render_power_chart(
            chart_id="gap",
            series=[ChartSeries("A", [
                ("Q1", 100), ("Q2", 110), ("Q3", None),
                ("Q4", 120), ("Q5", 130)])])
        # Two runs — the gap is never interpolated across.
        self.assertEqual(html.count("<polyline"), 2)

    def test_isolated_points_render_dots_without_polyline(self):
        html = render_power_chart(
            chart_id="dots",
            series=[ChartSeries("A", [
                ("Q1", 100), ("Q2", None), ("Q3", 120)])])
        self.assertNotIn("<polyline", html)
        self.assertEqual(html.count('<circle class="point"'), 2)

    def test_money_ticks_are_round_numbers(self):
        # 30M–38M data → $30/32/34/36/38M ticks, not $29.6M/$31.7M.
        html = render_power_chart(
            chart_id="round-ticks",
            series=[ChartSeries("A", [("Q1", 30e6), ("Q2", 38e6)])],
            y_kind="money")
        for tick in ("$30.0M", "$32.0M", "$34.0M", "$36.0M", "$38.0M"):
            self.assertIn(tick, html)

    def test_precise_money_formatting_opt_in(self):
        # Coarse default is pinned elsewhere ($2K); precise obeys the
        # house 2-decimal financial rule.
        self.assertEqual(_format_y(1500, "money"), "$2K")
        self.assertEqual(_format_y(1500, "money", precise=True),
                         "$1.50K")
        self.assertEqual(_format_y(999.4, "money", precise=True),
                         "$999.40")
        self.assertEqual(_format_y(2_500_000, "money", precise=True),
                         "$2.50M")

    def test_precise_values_flag_reaches_point_titles(self):
        html = render_power_chart(
            chart_id="precise",
            series=[ChartSeries("A", [("Q1", 1500)])],
            y_kind="money", precise_values=True)
        self.assertIn("$1.50K", html)
        default = render_power_chart(
            chart_id="coarse",
            series=[ChartSeries("A", [("Q1", 1500)])],
            y_kind="money")
        self.assertIn("<title>A: $2K</title>", default)


# ── power_chart: theme, a11y, JS contract ───────────────────────────

class PowerChartThemeTests(unittest.TestCase):
    def test_default_theme_is_editorial_with_house_palette(self):
        html = render_power_chart(
            chart_id="ed",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2)])])
        # No Tailwind-dark frame colors in the default render.
        self.assertNotIn("#1f2937", html)
        self.assertNotIn("#374151", html)
        # First house data token is the auto-assigned series color.
        self.assertIn(DATA_SERIES[0], html)

    def test_dark_theme_preserves_legacy_strings(self):
        html = render_power_chart(
            chart_id="dk",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2)])],
            theme="dark")
        self.assertIn("background:#1f2937", html)
        self.assertIn("#60a5fa", html)   # legacy palette first slot

    def test_unknown_theme_rejected(self):
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="x",
                series=[ChartSeries("A", [("Q1", 1)])],
                theme="neon")


class PowerChartA11yTests(unittest.TestCase):
    def _html(self):
        return render_power_chart(
            chart_id="a11y", title="My Chart",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2)])])

    def test_svg_has_role_arialabel_and_title_child(self):
        html = self._html()
        self.assertIn('role="img"', html)
        self.assertIn('aria-label="My Chart"', html)
        self.assertIn("<title>My Chart</title>", html)

    def test_legend_items_are_buttons_with_aria_pressed(self):
        html = self._html()
        self.assertIn('data-series-toggle="A"', html)
        m = re.search(r'<button[^>]*data-series-toggle="A"[^>]*>',
                      html)
        self.assertIsNotNone(m)
        self.assertIn('aria-pressed="true"', m.group(0))

    def test_js_adds_keyboard_drilldown(self):
        html = render_power_chart(
            chart_id="kb",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2)])],
            drilldown_url="/deal/{series}?ts={x}")
        self.assertIn('setAttribute("tabindex", "0")', html)
        self.assertIn('ev.key === "Enter"', html)


class PowerChartJsContractTests(unittest.TestCase):
    def _html(self):
        return render_power_chart(
            chart_id="js",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2),
                                      ("Q3", 3)])])

    def test_layout_serialized_for_real_zoom(self):
        html = self._html()
        self.assertIn('"layout"', html)
        for key in ('"ml"', '"pw"', '"ymin"', '"ymax"',
                    '"maxLabels"'):
            self.assertIn(key, html)
        # Zoom rescales geometry: JS owns an xToPx and rebuilds line
        # runs (it no longer merely hides dots).
        self.assertIn("function xToPx", html)
        self.assertIn("rebuildLines", html)
        self.assertIn('setAttribute("points"', html)

    def test_tooltip_reads_server_formatted_labels(self):
        html = self._html()
        # No client-side formatY — one formatter, server-side.
        self.assertNotIn("function formatY", html)
        # Per-point labels serialized as the third tuple slot.
        self.assertIn('["Q1", 1.0, "1.00"]', html)

    def test_png_export_is_3x_with_theme_background(self):
        html = self._html()
        self.assertIn("EXPORT_SCALE = 3", html)
        self.assertIn('"bg": "#ffffff"', html)
        dark = render_power_chart(
            chart_id="jsd",
            series=[ChartSeries("A", [("Q1", 1), ("Q2", 2)])],
            theme="dark")
        self.assertIn('"bg": "#1a2332"', dark)

    def test_all_x_labels_rendered_with_data_i_for_zoom(self):
        html = render_power_chart(
            chart_id="lbl",
            series=[ChartSeries("A", [(f"P{i}", i) for i in
                                      range(20)])])
        self.assertEqual(html.count('class="xlabel"'), 20)
        # Non-selected labels start hidden (server-side density).
        self.assertIn('display="none"', html)

    def test_chart_id_starting_with_digit_rejected(self):
        # '1trend'.isalnum() passed the old check but kills every
        # querySelector('#1trend-…') with a SyntaxError.
        with self.assertRaises(ValueError):
            render_power_chart(
                chart_id="1trend",
                series=[ChartSeries("A", [("Q1", 1)])])
        # Hyphenated ids still fine.
        html = render_power_chart(
            chart_id="trend-2",
            series=[ChartSeries("A", [("Q1", 1)])])
        self.assertIn('id="trend-2-root"', html)

    def test_duplicate_sanitized_names_get_distinct_group_keys(self):
        html = render_power_chart(
            chart_id="dup",
            series=[ChartSeries("A B", [("Q1", 1)]),
                    ChartSeries("A_B", [("Q1", 2)])])
        keys = re.findall(r'data-series-key="([^"]+)"', html)
        self.assertEqual(len(keys), len(set(keys)))


# ── cdd: waterfall total detection ──────────────────────────────────

class CddWaterfallTests(unittest.TestCase):
    def test_network_fees_is_a_delta_not_a_total(self):
        t = parse_table(
            "Step\tV\nStart\t100\nNetwork fees\t-20\nTotal\t80")
        svg = render_cdd_chart("waterfall", t, {})
        # Exactly ONE navy absolute bar (the Total row); the
        # 'Network fees' delta renders red (negative), from the
        # running level — not from zero.
        self.assertEqual(svg.count('fill="#0b2341" filter'), 1)
        self.assertEqual(svg.count('fill="#b5321e" filter'), 1)

    def test_net_and_grand_total_still_absolute(self):
        for label in ("Net", "Grand total", "Subtotal"):
            t = parse_table(
                f"Step\tV\nStart\t100\nUp\t20\n{label}\t120")
            svg = render_cdd_chart("waterfall", t, {})
            self.assertEqual(
                svg.count('fill="#0b2341" filter'), 1, label)

    def test_waterfall_bars_carry_hover_titles(self):
        t = parse_table("Step\tV\nStart\t100\nUp\t20\nNet\t=120")
        svg = render_cdd_chart("waterfall", t, {})
        self.assertIn("<title>Up: 20</title>", svg)


# ── cdd: None gaps + signed axes ────────────────────────────────────

class CddLineGapTests(unittest.TestCase):
    def test_blank_cell_is_a_gap_not_a_zero_dip(self):
        t = parse_table("Q\tRev\n2021\t100\n2022\tn/a\n2023\t120")
        svg = render_cdd_chart("line", t, {})
        # Two isolated points remain (no polyline through zero).
        self.assertNotIn("<polyline", svg)
        cys = [float(cy) for cy in
               re.findall(r'<circle cx="[\d.]+" cy="([\d.]+)"', svg)]
        self.assertEqual(len(cys), 2)
        # Nothing plotted at the zero baseline (374 = y of 0).
        for cy in cys:
            self.assertGreater(abs(cy - _CDD_Y1), 5.0)

    def test_gap_in_longer_series_splits_polyline(self):
        t = parse_table("Q\tR\n1\t10\n2\t12\n3\tn/a\n4\t14\n5\t16")
        svg = render_cdd_chart("line", t, {})
        self.assertEqual(svg.count("<polyline"), 2)

    def test_negative_line_values_stay_on_canvas(self):
        t = parse_table("Q\tV\nQ1\t10\nQ2\t-30\nQ3\t20")
        svg = render_cdd_chart("line", t, {})
        cys = [float(cy) for cy in
               re.findall(r'<circle cx="[\d.]+" cy="(-?[\d.]+)"', svg)]
        self.assertEqual(len(cys), 3)
        for cy in cys:
            self.assertGreaterEqual(cy, _CDD_Y0 - 0.5)
            self.assertLessEqual(cy, _CDD_Y1 + 0.5)
        # Solid zero line drawn when the scale is signed.
        self.assertIn('stroke-width="1.1"', svg)

    def test_single_row_line_centers_point_with_label(self):
        t = parse_table("Q\tV\n2024\t42")
        svg = render_cdd_chart("line", t, {})
        m = re.search(r'<circle cx="([\d.]+)"', svg)
        self.assertIsNotNone(m)
        # Centered in the plot (x0=60, x1=692 → 376), not top-left.
        self.assertAlmostEqual(float(m.group(1)), 376.0, delta=1.0)
        self.assertIn(">42<", svg)

    def test_line_points_carry_hover_titles(self):
        t = parse_table("Q\tRev\n2021\t100\n2022\t120")
        svg = render_cdd_chart("line", t, {})
        self.assertIn("<title>Rev · 2021: 100</title>", svg)


class CddSignedColumnTests(unittest.TestCase):
    def test_negative_columns_hang_below_zero_inside_plot(self):
        t = parse_table("Q\tV\nA\t10\nB\t-30\nC\t20")
        svg = render_cdd_chart("column", t, {})
        rects = re.findall(
            r'<rect x="(-?[\d.]+)" y="(-?[\d.]+)" width="([\d.]+)" '
            r'height="([\d.]+)" rx="1.5" fill="#0b2341"', svg)
        self.assertEqual(len(rects), 3)
        for _x, y, _w, h in rects:
            y, h = float(y), float(h)
            self.assertGreaterEqual(y, _CDD_Y0 - 0.5)
            self.assertLessEqual(y + h, _CDD_Y1 + 0.5)
        self.assertIn("<title>B: -30</title>", svg)

    def test_missing_cell_is_skipped_not_zero_height(self):
        t = parse_table("Q\tA\tB\nX\t10\t20\nY\tn/a\t25")
        svg = render_cdd_chart("column", t, {})
        # 3 bars only — the missing (Y, A) cell draws nothing.
        self.assertEqual(
            svg.count('rx="1.5" fill="#0b2341"')
            + svg.count('rx="1.5" fill="#1F7A75"'), 3)
        self.assertNotIn("<title>A · Y", svg)

    def test_horizontal_bar_negative_extends_left_of_zero(self):
        t = parse_table("Seg\tV\nUp\t30\nDown\t-12")
        svg = render_cdd_chart("bar", t, {})
        # Both bars render with real width.
        widths = [float(w) for w in re.findall(
            r'<rect x="[\d.-]+" y="[\d.]+" width="([\d.]+)" '
            r'height="[\d.]+" rx="1.5" fill="#0b2341"', svg)]
        self.assertEqual(len(widths), 2)
        for w in widths:
            self.assertGreater(w, 5.0)
        self.assertIn("<title>Down: -12</title>", svg)

    def test_grouped_column_bars_have_hover_titles(self):
        t = parse_table("Y\tRev\tEBITDA\n2021\t100\t22\n2022\t130\t31")
        svg = render_cdd_chart("column", t, {})
        self.assertIn("<title>Rev · 2021: 100</title>", svg)
        self.assertIn("<title>EBITDA · 2022: 31</title>", svg)


class CddScatterSignedTests(unittest.TestCase):
    def test_negative_y_points_stay_on_canvas(self):
        t = parse_table("Co\tX\tY\nA\t1\t-10\nB\t2\t20")
        svg = render_cdd_chart("scatter", t, {})
        cys = [float(cy) for cy in re.findall(
            r'<circle cx="[\d.]+" cy="(-?[\d.]+)"', svg)]
        self.assertEqual(len(cys), 2)
        for cy in cys:
            self.assertGreaterEqual(cy, _CDD_Y0 - 0.5)
            self.assertLessEqual(cy, _CDD_Y1 + 0.5)


# ── cdd: pie honesty ────────────────────────────────────────────────

class CddPieTests(unittest.TestCase):
    def test_negative_slice_dropped_with_disclosure(self):
        t = parse_table("S\tV\nX\t50\nY\t-20\nZ\t70")
        svg = render_cdd_chart("pie", t, {})
        self.assertEqual(svg.count("<path"), 2)
        self.assertIn("non-positive row excluded", svg)
        # Percentages recomputed over the POSITIVE total (120), not
        # the netted 100.
        self.assertIn(">42%<", svg)
        self.assertIn(">58%<", svg)

    def test_all_nonpositive_pie_shows_hint(self):
        t = parse_table("S\tV\nX\t-5\nY\t0")
        svg = render_cdd_chart("pie", t, {})
        self.assertIn("Pie needs at least one positive value", svg)
        self.assertNotIn("<path", svg)


# ── cdd: combo right axis ───────────────────────────────────────────

class CddComboTests(unittest.TestCase):
    def test_line_scale_disclosed_on_right_axis(self):
        t = parse_table("Year\tRev\tEBITDA\n2021\t100\t22\n"
                        "2022\t130\t31\n2023\t165\t43")
        svg = render_cdd_chart("combo", t, {})
        ticks = re.findall(
            r'text-anchor="start" font-family="[^"]*" '
            r'font-size="9.5" fill="(#[0-9A-Fa-f]+)">([\d.]+)<', svg)
        self.assertEqual(len(ticks), 6)
        # Right-axis labels wear the LINE series' color (Chartis #2).
        self.assertTrue(all(c == "#1F7A75" for c, _ in ticks))
        self.assertEqual(ticks[-1][1], "50")   # _nice_max(43)

    def test_combo_line_gap_not_plotted_as_zero(self):
        t = parse_table("Y\tRev\tEB\n2021\t100\t22\n2022\t130\tn/a\n"
                        "2023\t165\t43")
        svg = render_cdd_chart("combo", t, {})
        # Line circles: only 2 (the gap cell draws nothing).
        self.assertEqual(svg.count('r="3"'), 2)


# ── cdd: degenerate hints ───────────────────────────────────────────

class CddDegenerateHintTests(unittest.TestCase):
    def test_each_degenerate_shape_explains_itself(self):
        cases = [
            ("slope", "M\tV\nA\t1\nB\t2", "Slope needs 2 value"),
            ("radar", "Ax\tA\nP\t1\nQ\t2", "Radar needs 3+"),
            ("dumbbell", "M\tV\nA\t1", "Dumbbell needs 2 value"),
            ("gantt", "T\tS\nA\tx", "Gantt needs numeric"),
            ("histogram", "A\tV\nx\tn/a", "Histogram needs numeric"),
            ("boxplot", "S\tV\nx\tn/a", "Box plot needs numeric"),
        ]
        for ctype, data, needle in cases:
            svg = render_cdd_chart(ctype, parse_table(data), {})
            self.assertIn(needle, svg, ctype)
            self.assertTrue(svg.rstrip().endswith("</svg>"), ctype)
            self.assertNotIn("None", svg, ctype)


# ── cdd: label truncation + parse hardening + export JS ─────────────

class CddLabelTests(unittest.TestCase):
    def test_long_rotated_x_labels_truncate_with_title(self):
        rows = "\n".join(
            f"Very Long County Name Number {i:02d}\t{i + 1}"
            for i in range(15))
        t = parse_table("County\tV\n" + rows)
        svg = render_cdd_chart("column", t, {})
        self.assertIn("…", svg)
        self.assertIn("<title>Very Long County Name Number 00</title>",
                      svg)

    def test_long_legend_names_truncate_with_title(self):
        t = parse_table(
            "Y\tMedicare Advantage Penetration Rate\t"
            "Commercial Insurance Utilization Index\n"
            "2021\t10\t20\n2022\t12\t22")
        svg = render_cdd_chart("line", t, {})
        self.assertIn("…", svg)
        self.assertIn(
            "<title>Medicare Advantage Penetration Rate</title>", svg)

    def test_short_labels_untouched(self):
        t = parse_table("Y\tRev\tEBITDA\n2021\t100\t22\n2022\t130\t31")
        svg = render_cdd_chart("column", t, {})
        self.assertIn(">Rev<", svg)
        self.assertIn(">EBITDA<", svg)


class CddParseTableTests(unittest.TestCase):
    def test_quoted_csv_label_with_comma_stays_one_cell(self):
        t = parse_table('City,Pop\n"Los Angeles, CA",5\nDallas,3')
        self.assertEqual(t["rows"][0], ("Los Angeles, CA", [5.0]))
        self.assertEqual(t["rows"][1], ("Dallas", [3.0]))

    def test_accounting_negatives_parse(self):
        t = parse_table(
            "Step\tV\nRebates\t(1,234)\nFees\t($2,500.50)\nOK\t10")
        self.assertEqual(t["rows"][0], ("Rebates", [-1234.0]))
        self.assertEqual(t["rows"][1], ("Fees", [-2500.5]))
        self.assertEqual(t["rows"][2], ("OK", [10.0]))

    def test_non_numeric_paren_text_still_none(self):
        t = parse_table("A\tB\nx\t(n/a)")
        self.assertEqual(t["rows"][0], ("x", [None]))

    def test_accounting_bridge_reaches_waterfall_as_negative(self):
        t = parse_table("Step\tV\nStart\t100\nAdj\t(30)\nNet\t70")
        svg = render_cdd_chart("waterfall", t, {})
        # The (30) row renders as a red (negative) delta bar.
        self.assertEqual(svg.count('fill="#b5321e" filter'), 1)


class CddExportToolbarTests(unittest.TestCase):
    def test_helpers_installed_once_behind_window_guard(self):
        tb = chart_export_toolbar("out", "file")
        self.assertIn("__cdChartExport", tb)
        self.assertIn("window.ckDlSvg", tb)
        self.assertIn("window.ckDlPng", tb)
        self.assertIn("window.ckCopySvg", tb)

    def test_house_palette_registered(self):
        self.assertIn("House data", PALETTES)
        self.assertEqual(PALETTES["House data"][:5], DATA_SERIES)
        self.assertGreaterEqual(len(PALETTES["House data"]), 6)


# ── _chart_kit: palette tokens, negatives, ticks, exports ───────────

class ChartKitDataSeriesTests(unittest.TestCase):
    def test_data_series_mirrors_css_tokens(self):
        css_path = os.path.join(
            os.path.dirname(__file__), "..", "rcm_mc", "ui",
            "static", "chartis_tokens.css")
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
        tokens = dict(re.findall(
            r"--sc-data-(\d):\s*(#[0-9a-fA-F]{6})", css))
        self.assertEqual(
            [tokens[str(i)] for i in range(1, 6)], DATA_SERIES)
        self.assertEqual(DATA_SERIES_EXTENDED[:5], DATA_SERIES)

    def test_three_plus_series_use_house_palette(self):
        out = ck_grouped_bar(
            "T", ["A", "B"],
            [("s1", [1, 2], None), ("s2", [2, 3], None),
             ("s3", [3, 4], None), ("s4", [4, 5], None)])
        for color in DATA_SERIES[:4]:
            self.assertIn(color, out)
        # No semantic negative-red categorical in a 4-series chart.
        self.assertNotIn("#b5321e", out)

    def test_two_series_keep_teal_navy_continuity(self):
        out = ck_grouped_bar(
            "T", ["A"], [("s1", [1], None), ("s2", [2], None)])
        self.assertIn("#155752", out)
        self.assertIn("#0b2341", out)

    def test_explicit_colors_still_win(self):
        out = ck_grouped_bar(
            "T", ["A"],
            [("s1", [1], "#123456"), ("s2", [2], None),
             ("s3", [3], None)])
        self.assertIn("#123456", out)


class ChartKitNegativeVisibilityTests(unittest.TestCase):
    def test_bar_chart_negative_renders_red_tick_and_label(self):
        out = ck_bar_chart(
            "Delta", [("A", 5, "teal"), ("B", -3, "teal")])
        # Below-baseline tick + value label in negative tone.
        self.assertIn('fill="#b5321e"', out)
        self.assertIn(">-3.0<", out)
        self.assertIn("<title>B: -3.0</title>", out)

    def test_grouped_bar_negative_cell_gets_tick_with_title(self):
        out = ck_grouped_bar(
            "T", ["A"], [("s1", [4], None), ("s2", [-2], None)])
        self.assertIn('fill="#b5321e"', out)
        self.assertIn("<title>s2 · A: -2.0</title>", out)

    def test_all_positive_unchanged_no_red(self):
        out = ck_bar_chart("T", [("A", 5, "teal"), ("B", 3, "teal")])
        self.assertNotIn("#b5321e", out)


class ChartKitNiceTicksTests(unittest.TestCase):
    def test_round_steps(self):
        self.assertEqual(ck_nice_ticks(0, 100, 6),
                         [0.0, 20.0, 40.0, 60.0, 80.0, 100.0])
        self.assertEqual(ck_nice_ticks(29.6, 38.4, 5),
                         [30.0, 32.0, 34.0, 36.0, 38.0])

    def test_negative_range_includes_zero(self):
        ticks = ck_nice_ticks(-10.75, 5.75, 5)
        self.assertIn(0.0, ticks)
        self.assertEqual(ticks, sorted(ticks))

    def test_degenerate_inputs_safe(self):
        self.assertTrue(ck_nice_ticks(5, 5, 5))     # lo == hi
        self.assertEqual(ck_nice_ticks(float("nan"), 1, 5), [])

    def test_no_negative_zero_label(self):
        for t in ck_nice_ticks(-1, 1, 5):
            if t == 0:
                self.assertFalse(str(t).startswith("-"))


class ChartKitDivergingDefaultTests(unittest.TestCase):
    def test_default_pct_format_is_house_1dp(self):
        out = ck_diverging_bar("T", [("A", 2.0), ("B", -1.25)])
        self.assertIn("+2.0%", out)
        self.assertIn("-1.2%", out)

    def test_custom_fmt_still_wins(self):
        out = ck_diverging_bar(
            "T", [("A", 2.0)], value_fmt=lambda v: f"{v:+.0f}pp")
        self.assertIn("+2pp", out)


class ChartKitSvgExportTests(unittest.TestCase):
    def test_svg_button_opt_in(self):
        card = ck_chart_card("T", "<svg></svg>", svg_button=True)
        self.assertIn('data-format="svg"', card)
        self.assertIn("ck-chart-dl-svg", card)
        self.assertEqual(card.count("ck-chart-dl"), 3)  # 2 btns + cls
        # Default stays single-button.
        plain = ck_chart_card("T", "<svg></svg>")
        self.assertNotIn('data-format="svg"', plain)

    def test_assets_js_dispatches_on_format(self):
        assets = ck_chart_assets()
        self.assertIn("data-format", assets)
        self.assertIn("image/svg+xml", assets)
        self.assertIn("__ckChartDL", assets)   # still idempotent


if __name__ == "__main__":
    unittest.main()
