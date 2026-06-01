"""Tests for ``ck_distribution_strip`` — the inline percentile-tick
visualization helper.

Spec'd in the Iter-7 design loop: a 120×18 inline SVG that puts the
distribution of a cohort behind a target-positioning tick. The
tick's color follows the severity palette based on which quartile
the target sits in, mirrored for ``direction='negative'`` metrics
(lower = better, e.g. labor_cost_ratio).

This helper is not yet wired to any partner-facing page. Tests lock
the contract before any page consumes it — when the HCRIS X-ray and
target-screener integrations land, they get a stable surface.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui._chartis_kit import ck_distribution_strip


# Reference palette (mirrors the helper's internal mapping).
_TONE_COLORS = {
    "positive": "#0a8a5f",
    "warning":  "#b8732a",
    "negative": "#b5321e",
    "neutral":  "#155752",
}


class EmptyCasesTests(unittest.TestCase):
    """Helpers must degrade silently — empty SVG, never a placeholder."""

    def test_none_target_returns_empty(self):
        self.assertEqual(
            ck_distribution_strip([1, 2, 3, 4, 5], None), "")

    def test_non_numeric_target_returns_empty(self):
        self.assertEqual(
            ck_distribution_strip([1, 2, 3, 4, 5], "not a number"),
            "")

    def test_nan_target_returns_empty(self):
        self.assertEqual(
            ck_distribution_strip([1, 2, 3, 4, 5], float("nan")), "")

    def test_inf_target_returns_empty(self):
        self.assertEqual(
            ck_distribution_strip([1, 2, 3, 4, 5], float("inf")), "")

    def test_too_few_cohort_values_returns_empty(self):
        # 4-value floor — fewer than that and any percentile is
        # undefendable.
        self.assertEqual(ck_distribution_strip([], 5), "")
        self.assertEqual(ck_distribution_strip([1], 5), "")
        self.assertEqual(ck_distribution_strip([1, 2, 3], 5), "")

    def test_none_values_returns_empty(self):
        self.assertEqual(ck_distribution_strip(None, 5), "")

    def test_all_non_numeric_values_returns_empty(self):
        # Non-numeric cohort values are filtered; if filtering leaves
        # fewer than 4 valid points, return empty.
        self.assertEqual(
            ck_distribution_strip(["a", "b", "c", "d"], 5), "")


class BasicRenderTests(unittest.TestCase):
    """Default render shape and required SVG attributes."""

    def test_returns_non_empty_svg_for_valid_input(self):
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertTrue(out)
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions_120x18(self):
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertIn('width="120"', out)
        self.assertIn('height="18"', out)
        self.assertIn('viewBox="0 0 120 18"', out)

    def test_custom_dimensions_honored(self):
        out = ck_distribution_strip(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5,
            width=200, height=24,
        )
        self.assertIn('width="200"', out)
        self.assertIn('height="24"', out)
        self.assertIn('viewBox="0 0 200 24"', out)

    def test_has_ck_dist_strip_class(self):
        # The class is the css hook the editorial shell uses to style
        # the strip within tables — lock it.
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertIn('class="ck-dist-strip"', out)

    def test_has_role_img_for_accessibility(self):
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertIn('role="img"', out)
        self.assertIn('aria-label="percentile distribution strip"', out)

    def test_contains_background_ribbon_rect(self):
        # The cohort-distribution background ribbon is a parchment-
        # toned rect — locks the visual scaffold.
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertIn('<rect', out)
        self.assertIn('fill="#e8e1d3"', out)

    def test_contains_tick_line(self):
        out = ck_distribution_strip([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        self.assertIn('<line', out)
        self.assertIn('stroke-width="2"', out)


class TickPositioningTests(unittest.TestCase):
    """Tick x-coordinate must map target value onto the cohort range."""

    def test_target_at_min_pins_tick_at_left(self):
        out = ck_distribution_strip(
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 10)
        # Tick should be at very small x (clamped to 0.5 floor).
        self.assertIn('x1="0.5"', out)

    def test_target_at_max_pins_tick_at_right(self):
        out = ck_distribution_strip(
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 100)
        # Default width 120 → tick clamped to 119.5
        self.assertIn('x1="119.5"', out)

    def test_target_at_midpoint_centers_tick(self):
        # Min=10, Max=100; target=55 → (55-10)/(100-10) × 120 = 60
        out = ck_distribution_strip(
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 55)
        self.assertIn('x1="60.0"', out)

    def test_out_of_range_target_clamped_to_edge(self):
        # Target far outside the cohort range — clamped to edge.
        out_hi = ck_distribution_strip(
            [10, 20, 30, 40, 50], 999_999)
        self.assertIn('x1="119.5"', out_hi)
        out_lo = ck_distribution_strip(
            [10, 20, 30, 40, 50], -999_999)
        self.assertIn('x1="0.5"', out_lo)

    def test_zero_range_cohort_safe(self):
        # All cohort values identical → rng falls back to 1.0 so we
        # don't divide-by-zero; tick position is well-defined.
        out = ck_distribution_strip([5, 5, 5, 5, 5, 5], 5)
        self.assertTrue(out)  # renders without crashing


class ToneByQuartilePositiveDirectionTests(unittest.TestCase):
    """direction='positive' (higher = better): top quartile is teal
    (positive tone), bottom is red."""

    _COHORT = list(range(1, 101))  # 1..100

    def test_top_quartile_is_positive_tone(self):
        # Target ≥ p75 (75) → positive tone (teal-positive)
        out = ck_distribution_strip(self._COHORT, 85, direction="positive")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_above_median_is_neutral_tone(self):
        # p50 < target < p75 → neutral tone
        out = ck_distribution_strip(self._COHORT, 60, direction="positive")
        self.assertIn(_TONE_COLORS["neutral"], out)

    def test_below_median_is_warning_tone(self):
        # p25 < target < p50 → warning tone
        out = ck_distribution_strip(self._COHORT, 35, direction="positive")
        self.assertIn(_TONE_COLORS["warning"], out)

    def test_bottom_quartile_is_negative_tone(self):
        # Target < p25 → negative tone
        out = ck_distribution_strip(self._COHORT, 10, direction="positive")
        self.assertIn(_TONE_COLORS["negative"], out)


class ToneByQuartileNegativeDirectionTests(unittest.TestCase):
    """direction='negative' (lower = better, e.g. labor_cost_ratio):
    bottom quartile is teal, top is red — mirrored."""

    _COHORT = list(range(1, 101))

    def test_bottom_quartile_is_positive_tone(self):
        out = ck_distribution_strip(self._COHORT, 10, direction="negative")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_below_median_is_neutral_tone(self):
        out = ck_distribution_strip(self._COHORT, 35, direction="negative")
        self.assertIn(_TONE_COLORS["neutral"], out)

    def test_above_median_is_warning_tone(self):
        out = ck_distribution_strip(self._COHORT, 60, direction="negative")
        self.assertIn(_TONE_COLORS["warning"], out)

    def test_top_quartile_is_negative_tone(self):
        out = ck_distribution_strip(self._COHORT, 85, direction="negative")
        self.assertIn(_TONE_COLORS["negative"], out)


class DirectionArgEdgeCasesTests(unittest.TestCase):

    def test_unknown_direction_falls_back_to_positive(self):
        # Defensive: an unexpected string defaults to 'positive'
        # rather than raising.
        out = ck_distribution_strip(
            list(range(1, 101)), 85, direction="weird")
        # 85 in positive direction → positive tone (teal-positive)
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_none_direction_falls_back_to_positive(self):
        out = ck_distribution_strip(
            list(range(1, 101)), 85, direction=None)  # type: ignore
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_case_insensitive_direction(self):
        # 'POSITIVE' and 'Positive' both work.
        out = ck_distribution_strip(
            list(range(1, 101)), 85, direction="POSITIVE")
        self.assertIn(_TONE_COLORS["positive"], out)


class TooltipTests(unittest.TestCase):
    """Native SVG <title> drives the hover tooltip — no JS required."""

    def test_tooltip_contains_percentile_and_n(self):
        out = ck_distribution_strip(
            list(range(1, 101)), 80, direction="positive")
        # Target=80 in [1..100] → rank=80 → p80 of n=100
        self.assertIn("<title>", out)
        self.assertIn("p80", out)
        self.assertIn("n=100", out)

    def test_tooltip_includes_direction_word(self):
        out_pos = ck_distribution_strip(
            list(range(1, 101)), 80, direction="positive")
        self.assertIn("higher=better", out_pos)
        out_neg = ck_distribution_strip(
            list(range(1, 101)), 80, direction="negative")
        self.assertIn("lower=better", out_neg)

    def test_tooltip_includes_label_when_provided(self):
        out = ck_distribution_strip(
            list(range(1, 101)), 50, label="Operating Margin")
        self.assertIn("Operating Margin", out)

    def test_tooltip_label_html_escaped(self):
        # The label flows through _esc — pre-empt any XSS in metric
        # names that may carry through.
        out = ck_distribution_strip(
            list(range(1, 101)), 50,
            label="<script>alert(1)</script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_percentile_clamped_to_0_100(self):
        # An out-of-range target still produces a percentile in [0,100].
        out_hi = ck_distribution_strip(list(range(1, 101)), 99999)
        self.assertIn("p100", out_hi)
        out_lo = ck_distribution_strip(list(range(1, 101)), -99999)
        # rank_below = 0 → p0
        self.assertIn("p0", out_lo)


class DataHygieneTests(unittest.TestCase):
    """Robustness against partial / dirty cohort data."""

    def test_filters_nan_from_cohort(self):
        # 5 valid + 5 NaN → 5 valid (>= 4 floor) → renders
        cohort = [1.0, 2.0, float("nan"), 3.0, float("nan"), 4.0,
                  float("nan"), 5.0, float("nan"), float("nan")]
        out = ck_distribution_strip(cohort, 3)
        self.assertTrue(out)

    def test_filters_inf_from_cohort(self):
        cohort = [1.0, 2.0, float("inf"), 3.0, float("-inf"),
                  4.0, 5.0, 6.0, 7.0]
        out = ck_distribution_strip(cohort, 4)
        self.assertTrue(out)

    def test_filters_non_numeric_from_cohort(self):
        cohort = [1, 2, "junk", 3, None, 4, 5, "bad", 6, 7]
        out = ck_distribution_strip(cohort, 4)
        self.assertTrue(out)

    def test_filtering_drops_below_floor_returns_empty(self):
        # 10 values but 8 are NaN → only 2 valid → below 4 floor
        cohort = [float("nan")] * 8 + [1.0, 2.0]
        self.assertEqual(ck_distribution_strip(cohort, 1.5), "")


if __name__ == "__main__":
    unittest.main()
