"""Tests for ``ck_growth_arrow`` — compact arrow + %-change cell.

Universal 'vs prior period' indicator that sits in any table cell
without consuming a full column. Arrow direction follows raw delta;
arrow color follows the metric's improvement direction.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_growth_arrow


class EmptyCasesTests(unittest.TestCase):

    def test_none_current_returns_empty(self):
        self.assertEqual(ck_growth_arrow(None, 100), "")

    def test_none_prior_returns_empty(self):
        self.assertEqual(ck_growth_arrow(100, None), "")

    def test_non_numeric_returns_empty(self):
        self.assertEqual(ck_growth_arrow("junk", 100), "")
        self.assertEqual(ck_growth_arrow(100, "junk"), "")

    def test_nan_or_inf_returns_empty(self):
        self.assertEqual(ck_growth_arrow(float("nan"), 100), "")
        self.assertEqual(ck_growth_arrow(100, float("inf")), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_html_with_svg(self):
        out = ck_growth_arrow(125, 100)
        self.assertIn("<svg", out)
        self.assertIn("</svg>", out)

    def test_class_and_aria(self):
        out = ck_growth_arrow(125, 100)
        self.assertIn('class="ck-growth-arrow"', out)
        self.assertIn('role="img"', out)
        self.assertIn('aria-label="growth arrow"', out)

    def test_default_height(self):
        out = ck_growth_arrow(125, 100)
        self.assertIn('width="14"', out)
        self.assertIn('height="14"', out)

    def test_custom_height(self):
        out = ck_growth_arrow(125, 100, height=18)
        self.assertIn('width="18"', out)
        self.assertIn('height="18"', out)


class ToneFromDirectionTests(unittest.TestCase):

    def test_positive_direction_rising_is_green(self):
        # revenue up = good
        out = ck_growth_arrow(125, 100, direction="positive")
        self.assertIn("#0a8a5f", out)

    def test_positive_direction_falling_is_red(self):
        # revenue down = bad
        out = ck_growth_arrow(80, 100, direction="positive")
        self.assertIn("#b5321e", out)

    def test_negative_direction_rising_is_red(self):
        # denial_rate up = bad
        out = ck_growth_arrow(0.105, 0.10, direction="negative")
        self.assertIn("#b5321e", out)

    def test_negative_direction_falling_is_green(self):
        # denial_rate down = good
        out = ck_growth_arrow(0.095, 0.10, direction="negative")
        self.assertIn("#0a8a5f", out)

    def test_unknown_direction_falls_back_to_positive(self):
        out = ck_growth_arrow(125, 100, direction="weird")
        self.assertIn("#0a8a5f", out)

    def test_none_direction_safe(self):
        out = ck_growth_arrow(125, 100, direction=None)  # type: ignore
        self.assertIn("#0a8a5f", out)


class ArrowGlyphDirectionTests(unittest.TestCase):
    """Arrow points up for rising values regardless of direction
    arg — color (not glyph) carries the editorial good/bad signal."""

    def test_rising_renders_up_triangle(self):
        # Up triangle: vertex points UP → first path point is the
        # top of the triangle.
        out = ck_growth_arrow(125, 100, direction="positive")
        # "M 7.0 2.5 L ..." → first M coordinate y=2.5 (top of canvas)
        self.assertIn("M 7.0 2.5", out)

    def test_falling_renders_down_triangle(self):
        # Down triangle: vertex points DOWN → first path point is
        # the bottom (y > height/2).
        out = ck_growth_arrow(80, 100, direction="positive")
        # First M coordinate y near bottom (height-2.5 = 11.5)
        self.assertIn("M 7.0 11.5", out)

    def test_rising_in_negative_direction_still_up_glyph(self):
        # denial_rate increased → arrow still points UP (the number
        # actually went up); color says 'bad' but glyph reflects
        # raw direction.
        out = ck_growth_arrow(0.105, 0.10, direction="negative")
        self.assertIn("M 7.0 2.5", out)


class NeutralBandTests(unittest.TestCase):
    """Flat changes (< threshold) render as a horizontal dash —
    avoids '+0.04%' noise on basically-flat metrics."""

    def test_change_within_default_threshold_is_flat(self):
        # 100 → 100.1 = +0.1% < 0.5% threshold → flat dash
        out = ck_growth_arrow(100.1, 100.0)
        self.assertIn("<line", out)  # dash, not triangle
        self.assertNotIn("<path", out)
        self.assertIn("#7a7a7a", out)  # neutral gray

    def test_change_at_threshold_boundary_still_flat(self):
        # Exactly 0.5% change → still flat (strict less-than)
        out = ck_growth_arrow(100.4, 100.0)  # +0.4% < 0.5%
        self.assertIn("<line", out)
        self.assertNotIn("<path", out)

    def test_change_above_threshold_renders_arrow(self):
        out = ck_growth_arrow(101, 100)  # +1.0% > 0.5%
        self.assertIn("<path", out)
        self.assertNotIn(
            "stroke-linecap=\"round\"/></svg>", out)  # no dash line

    def test_custom_threshold(self):
        # Lower the threshold so +0.1% qualifies as a real change.
        out = ck_growth_arrow(
            100.1, 100.0, neutral_threshold_pct=0.05)
        self.assertIn("<path", out)


class PctCaptionTests(unittest.TestCase):

    def test_default_shows_pct(self):
        out = ck_growth_arrow(125, 100)
        self.assertIn(">+25.0%<", out)

    def test_show_pct_false_hides_caption(self):
        out = ck_growth_arrow(125, 100, show_pct=False)
        self.assertNotIn("ck-growth-pct", out)
        self.assertNotIn(">+25.0%<", out)

    def test_precision_arg(self):
        out = ck_growth_arrow(125.456, 100, precision=2)
        self.assertIn(">+25.46%<", out)

    def test_unit_suffix_override(self):
        # Useful for cells like 'change in MOIC' (no %).
        out = ck_growth_arrow(2.5, 2.0, unit_suffix="x")
        self.assertIn(">+25.0x<", out)

    def test_negative_pct_shows_minus_sign(self):
        out = ck_growth_arrow(80, 100)
        self.assertIn(">-20.0%<", out)

    def test_zero_prior_shows_dash(self):
        # Zero baseline → pct undefined → dash placeholder
        out = ck_growth_arrow(50, 0)
        self.assertIn("—", out)

    def test_zero_prior_arrow_still_shows(self):
        # Even though pct caption is dash, the arrow direction
        # should still render (50 > 0 = up).
        out = ck_growth_arrow(50, 0)
        self.assertIn("<path", out)


class TooltipTests(unittest.TestCase):

    def test_tooltip_carries_first_arrow_last(self):
        out = ck_growth_arrow(125, 100)
        self.assertIn("100.0 → 125.0", out)
        self.assertIn("+25.0%", out)

    def test_tooltip_labels_improving_or_degrading(self):
        out_pos = ck_growth_arrow(125, 100, direction="positive")
        self.assertIn("improving", out_pos)
        out_neg = ck_growth_arrow(0.105, 0.10, direction="negative")
        self.assertIn("degrading", out_neg)

    def test_tooltip_says_flat_for_within_threshold(self):
        out = ck_growth_arrow(100.1, 100.0)
        self.assertIn("flat", out)


class StylingTests(unittest.TestCase):

    def test_pct_uses_jetbrains_mono(self):
        # Numerical caption uses JetBrains Mono per chartis convention.
        out = ck_growth_arrow(125, 100)
        self.assertIn("JetBrains Mono", out)

    def test_pct_uses_tabular_nums(self):
        # Tabular nums so columns align across rows.
        out = ck_growth_arrow(125, 100)
        self.assertIn("tabular-nums", out)

    def test_inline_flex_layout(self):
        # Composite uses inline-flex so it sits in flow.
        out = ck_growth_arrow(125, 100)
        self.assertIn("display:inline-flex", out)

    def test_pct_color_matches_arrow(self):
        # Caption color matches arrow color (same editorial signal).
        out_pos = ck_growth_arrow(125, 100, direction="positive")
        # The caption span carries inline color:#0a8a5f
        self.assertIn("color:#0a8a5f", out_pos)


if __name__ == "__main__":
    unittest.main()
