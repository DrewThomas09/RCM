"""Editorial chart kit — inline-SVG charts + PNG export assets.

The geo analysis pages (State Comparison/Profile, County Explorer) were
table-only; this kit gives them the "easy visuals" partners expect. The
charts must be self-contained SVG (resolved hex, no bare CSS vars) so the
one-time SVG→canvas→PNG export helper rasterizes them cleanly.

Guards:
  - bar / grouped / diverging charts emit an <svg> inside an export card.
  - empty / all-non-finite input returns '' (caller falls back to table).
  - the export card carries a PNG button + targetable id; ck_chart_assets
    ships the idempotent download script once.
  - ck_chart_grid drops empty cards so a missing-data chart leaves no hole.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chart_kit import (
    ck_bar_chart,
    ck_chart_assets,
    ck_chart_grid,
    ck_diverging_bar,
    ck_grouped_bar,
    ck_hbar_chart,
)


class BarChartTests(unittest.TestCase):
    def test_renders_svg_in_export_card(self) -> None:
        out = ck_bar_chart(
            "Median HH income",
            [("CA", 93824, "positive"), ("TX", 73832, "teal"), ("FL", 69898, "warning")],
            reference=("U.S.", 73045),
        )
        self.assertIn("<svg", out)
        self.assertIn("ck-chart-card", out)
        self.assertIn("ck-chart-dl", out)              # export button
        self.assertIn('data-chart-id="ckc-median-hh-income"', out)
        self.assertIn("Median HH income", out)
        # reference line label present
        self.assertIn("U.S.", out)

    def test_empty_returns_blank(self) -> None:
        self.assertEqual(ck_bar_chart("X", []), "")
        self.assertEqual(ck_bar_chart("X", [("A", float("nan"), "teal")]), "")

    def test_custom_value_formatter_used(self) -> None:
        out = ck_bar_chart(
            "Uninsured", [("CA", 0.081, "teal")],
            value_fmt=lambda v: f"{v*100:.1f}%",
        )
        self.assertIn("8.1%", out)


class GroupedBarTests(unittest.TestCase):
    def test_grouped_renders_legend_and_bars(self) -> None:
        out = ck_grouped_bar(
            "Coverage",
            ["CA", "TX", "FL"],
            [("Uninsured", [8.1, 20.3, 15.1], None),
             ("Child poverty", [14.9, 18.9, 17.3], None)],
        )
        self.assertIn("<svg", out)
        self.assertIn("Uninsured", out)
        self.assertIn("Child poverty", out)

    def test_grouped_empty_returns_blank(self) -> None:
        self.assertEqual(ck_grouped_bar("X", [], []), "")
        self.assertEqual(
            ck_grouped_bar("X", ["A"], [("s", [None], None)]), ""
        )


class HBarChartTests(unittest.TestCase):
    def test_hbar_renders_card_with_long_labels(self) -> None:
        out = ck_hbar_chart(
            "Top counties — Population",
            [("Los Angeles County", 9829544, "teal"),
             ("San Diego County", 3286069, "teal")],
            reference=("State wtd-mean", 500000),
        )
        self.assertIn("<svg", out)
        self.assertIn("ck-chart-card", out)
        self.assertIn("ck-chart-dl", out)
        self.assertIn("State wtd-mean", out)

    def test_hbar_empty_returns_blank(self) -> None:
        self.assertEqual(ck_hbar_chart("X", []), "")


class DivergingBarTests(unittest.TestCase):
    def test_diverging_signs_and_card(self) -> None:
        out = ck_diverging_bar(
            "Median income — vs U.S. median",
            [("CA", 28.4, "teal"), ("MS", -22.1, "teal")],
        )
        self.assertIn("<svg", out)
        self.assertIn("ck-chart-card", out)
        self.assertIn("U.S. median", out)   # center label

    def test_diverging_empty_returns_blank(self) -> None:
        self.assertEqual(ck_diverging_bar("X", []), "")


class GridAndAssetsTests(unittest.TestCase):
    def test_grid_drops_empty_cards(self) -> None:
        a = ck_bar_chart("A", [("x", 1, "teal")])
        grid = ck_chart_grid(a, "", "")
        self.assertIn("ck-chart-grid", grid)
        self.assertEqual(grid.count("ck-chart-card"), 1)
        # all-empty grid collapses to nothing
        self.assertEqual(ck_chart_grid("", ""), "")

    def test_assets_ship_idempotent_png_helper(self) -> None:
        assets = ck_chart_assets()
        self.assertIn("<style>", assets)
        self.assertIn("<script>", assets)
        self.assertIn("__ckChartDL", assets)      # idempotency guard
        self.assertIn("toBlob", assets)           # canvas → PNG
        self.assertIn(".ck-chart-dl", assets)

    def test_charts_use_hex_not_bare_css_vars(self) -> None:
        # PNG export needs resolved colors — a serialized SVG can't resolve
        # var(--x). Ensure fills are concrete hex, not bare custom properties.
        out = ck_bar_chart("A", [("x", 5, "teal")])
        svg = out[out.index("<svg"):out.index("</svg>")]
        self.assertIn('fill="#', svg)
        self.assertNotIn("var(--", svg)


class LabelTruncationTests(unittest.TestCase):
    LONG = "Operating Margin (EBITDA %)"   # 26 chars — exceeds the 22 cap

    def test_hbar_truncates_with_ellipsis_and_full_title(self) -> None:
        out = ck_hbar_chart("T", [(self.LONG, 2.5, "teal")])
        self.assertIn("…", out)                              # clipped, visibly
        self.assertIn(f"<title>{self.LONG}", out)            # full text on hover
        # never the silent mid-word cut that reads like the real label
        self.assertNotIn("Operating Margin (EBIT<", out)

    def test_diverging_truncates_with_ellipsis_and_full_title(self) -> None:
        out = ck_diverging_bar("T", [(self.LONG, 1.5), ("Short", -0.4)])
        self.assertIn("…", out)
        self.assertIn(f"<title>{self.LONG}", out)

    def test_grouped_legend_truncates_with_tooltip(self) -> None:
        out = ck_grouped_bar(
            "T", ["A", "B"],
            [("Medicare Advantage Penetration", [1, 2], "teal")])
        self.assertIn("…", out)
        self.assertIn("<title>Medicare Advantage Penetration</title>", out)

    def test_short_label_is_untouched(self) -> None:
        out = ck_hbar_chart("T", [("Revenue", 5, "teal")])
        self.assertIn(">Revenue</text>", out)
        self.assertNotIn("…", out)

    def test_vertical_bar_labels_adapt_to_band_width(self) -> None:
        # Many bars → each category label truncates to fit its band so
        # adjacent labels don't overlap; full text stays in the bar <title>.
        items = [(f"CategoryNumber{i}XYZ", i + 1, "teal") for i in range(10)]
        out = ck_bar_chart("T", items)
        self.assertIn("…", out)
        self.assertIn("<title>CategoryNumber0XYZ:", out)


if __name__ == "__main__":
    unittest.main()
