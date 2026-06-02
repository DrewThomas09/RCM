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


if __name__ == "__main__":
    unittest.main()
