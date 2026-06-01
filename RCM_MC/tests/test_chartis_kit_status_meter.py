"""Tests for ``ck_status_meter`` — compact 0-100 score gauge.

Sibling to ``ck_threshold_gauge`` (which takes explicit warning/
breach thresholds) — this is the simpler 'score on a fixed scale'
visualization. Use anywhere a 0-100 score lives in a row and the
partner needs a color-coded gut-feel: health score per deal, MIPS
composite, HCAHPS percentile, data-confidence index, deal-readiness
rating.

Not yet wired to any partner-facing page. Tests lock the contract
+ tone thirds before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_status_meter


class EmptyCasesTests(unittest.TestCase):

    def test_none_score_returns_empty(self):
        self.assertEqual(ck_status_meter(None), "")

    def test_non_numeric_returns_empty(self):
        self.assertEqual(ck_status_meter("junk"), "")

    def test_nan_returns_empty(self):
        self.assertEqual(ck_status_meter(float("nan")), "")

    def test_inf_returns_empty(self):
        self.assertEqual(ck_status_meter(float("inf")), "")

    def test_degenerate_scale_returns_empty(self):
        # scale_max <= scale_min → cannot divide.
        self.assertEqual(
            ck_status_meter(50, scale_min=100, scale_max=100), "")
        self.assertEqual(
            ck_status_meter(50, scale_min=100, scale_max=50), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_html(self):
        out = ck_status_meter(75)
        self.assertIn("<svg", out)
        self.assertIn("ck-status-meter", out)

    def test_default_dimensions(self):
        out = ck_status_meter(75)
        self.assertIn('width="120"', out)
        self.assertIn('height="10"', out)

    def test_custom_dimensions(self):
        out = ck_status_meter(75, width=200, height=14)
        self.assertIn('width="200"', out)
        self.assertIn('height="14"', out)

    def test_minimum_dimensions_floor(self):
        # width floors at 40, height at 6.
        out = ck_status_meter(75, width=10, height=2)
        self.assertIn('width="40"', out)
        self.assertIn('height="6"', out)

    def test_renders_background_ribbon(self):
        out = ck_status_meter(75)
        self.assertIn('fill="#e8e1d3"', out)

    def test_renders_marker_line(self):
        out = ck_status_meter(75)
        self.assertIn("<line", out)
        self.assertIn('stroke-width="2"', out)

    def test_role_img(self):
        out = ck_status_meter(75)
        self.assertIn('role="img"', out)


class PositiveDirectionZoneTests(unittest.TestCase):
    """Higher is better — bottom third red, middle amber, top green."""

    def test_top_third_is_green(self):
        # 80/100 → top third (>=67) → green
        out = ck_status_meter(80, direction="positive")
        self.assertIn('stroke="#0a8a5f"', out)
        self.assertIn("green zone", out)

    def test_middle_third_is_amber(self):
        out = ck_status_meter(50, direction="positive")
        self.assertIn('stroke="#b8732a"', out)
        self.assertIn("amber zone", out)

    def test_bottom_third_is_red(self):
        out = ck_status_meter(20, direction="positive")
        self.assertIn('stroke="#b5321e"', out)
        self.assertIn("red zone", out)

    def test_at_two_thirds_boundary_is_green(self):
        # 200/3 = 66.67 → frac=0.667 → top third (>= 2/3)
        out = ck_status_meter(67, direction="positive")
        self.assertIn("green zone", out)

    def test_at_one_third_boundary_is_amber(self):
        # 100/3 = 33.33 → frac=0.333 → middle (>= 1/3)
        out = ck_status_meter(34, direction="positive")
        self.assertIn("amber zone", out)


class NegativeDirectionZoneTests(unittest.TestCase):
    """Lower is better (risk scores, denial rate, leakage index)."""

    def test_low_score_is_green_in_negative(self):
        out = ck_status_meter(20, direction="negative")
        self.assertIn("green zone", out)

    def test_middle_is_amber_in_negative(self):
        out = ck_status_meter(50, direction="negative")
        self.assertIn("amber zone", out)

    def test_high_is_red_in_negative(self):
        out = ck_status_meter(85, direction="negative")
        self.assertIn("red zone", out)


class DirectionFallbackTests(unittest.TestCase):

    def test_unknown_direction_falls_back_to_positive(self):
        # 80 → 'positive' → green
        out = ck_status_meter(80, direction="weird")
        self.assertIn("green zone", out)

    def test_none_direction_falls_back_to_positive(self):
        out = ck_status_meter(80, direction=None)  # type: ignore
        self.assertIn("green zone", out)

    def test_case_insensitive_direction(self):
        out = ck_status_meter(85, direction="NEGATIVE")
        self.assertIn("red zone", out)


class ClampingTests(unittest.TestCase):

    def test_score_above_scale_clamps_to_max(self):
        out = ck_status_meter(150, scale_min=0, scale_max=100)
        # Marker pinned to right edge.
        self.assertIn(">100/100<", out)  # caption shows clamped value

    def test_score_below_scale_clamps_to_min(self):
        out = ck_status_meter(-30, scale_min=0, scale_max=100)
        self.assertIn(">0/100<", out)


class CustomScaleTests(unittest.TestCase):

    def test_custom_scale_max(self):
        # 5-star scale: scale_min=0, scale_max=5
        out = ck_status_meter(4, scale_min=0, scale_max=5)
        self.assertIn(">4/5<", out)
        # 4/5 = 0.8 → top third → green
        self.assertIn("green zone", out)

    def test_custom_scale_negative_min(self):
        # Z-score-like scale: -3 to +3
        out = ck_status_meter(1, scale_min=-3, scale_max=3)
        # (1 - -3) / 6 = 0.667 → top third → green
        self.assertIn("green zone", out)


class CaptionTests(unittest.TestCase):

    def test_default_caption_is_score_slash_max(self):
        out = ck_status_meter(75)
        self.assertIn(">75/100<", out)

    def test_default_caption_uses_precision_zero(self):
        out = ck_status_meter(75.7)
        # precision=0 default → '76/100'
        self.assertIn(">76/100<", out)

    def test_precision_one(self):
        out = ck_status_meter(75.7, precision=1)
        self.assertIn(">75.7/100<", out)

    def test_hide_caption(self):
        out = ck_status_meter(75, show_caption=False)
        self.assertNotIn("ck-status-meter-caption", out)

    def test_custom_caption_template(self):
        out = ck_status_meter(
            75, caption_template="{score:.0f} out of {max:.0f}",
        )
        self.assertIn(">75 out of 100<", out)

    def test_caption_color_matches_zone(self):
        # Top-third score → green caption text
        out = ck_status_meter(80)
        self.assertIn("color:#0a8a5f", out)


class LabelAndTooltipTests(unittest.TestCase):

    def test_label_appears_in_tooltip_when_provided(self):
        out = ck_status_meter(75, label="Health Score")
        # Tooltip carries 'Health Score: 75/100'
        self.assertIn("Health Score: 75/100", out)

    def test_no_label_uses_caption_as_tooltip(self):
        out = ck_status_meter(75)
        self.assertIn('title="75/100"', out)

    def test_label_with_hidden_caption_still_renders_wrapper(self):
        # show_caption=False + label → wrapper span with aria-label
        out = ck_status_meter(75, show_caption=False, label="MIPS")
        self.assertIn("ck-status-meter-wrap", out)
        self.assertIn('aria-label="MIPS"', out)

    def test_label_html_escaped(self):
        out = ck_status_meter(75, label="<script>x</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class StylingTests(unittest.TestCase):

    def test_caption_uses_jetbrains_mono(self):
        out = ck_status_meter(75)
        self.assertIn("JetBrains Mono", out)

    def test_caption_uses_tabular_nums(self):
        out = ck_status_meter(75)
        self.assertIn("tabular-nums", out)


if __name__ == "__main__":
    unittest.main()
