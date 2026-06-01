"""Tests for ``ck_trajectory_strip`` + ``ck_dual_strip``.

Iter-8 foundation: trajectory micro-line (slope-colored by
improvement direction) plus a composite that bundles trajectory +
distribution side-by-side with a 1px separator.

Neither helper is wired to a partner page yet — these tests lock
the visual + behavior contracts before the HCRIS X-ray and
target-screener integrations land.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui._chartis_kit import (
    ck_distribution_strip,
    ck_dual_strip,
    ck_trajectory_strip,
)


_TONE_COLORS = {
    "positive": "#0a8a5f",
    "warning":  "#b8732a",
    "negative": "#b5321e",
    "neutral":  "#155752",
}


# ─────────────────────────────────────────────────────────────────
# ck_trajectory_strip
# ─────────────────────────────────────────────────────────────────


class TrajectoryEmptyCasesTests(unittest.TestCase):

    def test_empty_values_returns_empty(self):
        self.assertEqual(ck_trajectory_strip([]), "")

    def test_none_returns_empty(self):
        self.assertEqual(ck_trajectory_strip(None), "")  # type: ignore

    def test_single_value_returns_empty(self):
        # Can't draw a trajectory from one point.
        self.assertEqual(ck_trajectory_strip([1.0]), "")

    def test_all_non_numeric_returns_empty(self):
        self.assertEqual(ck_trajectory_strip(["a", "b", "c"]), "")

    def test_nan_values_filtered_below_floor(self):
        # 3 values but 2 NaN → only 1 valid → empty
        self.assertEqual(
            ck_trajectory_strip([1.0, float("nan"), float("nan")]),
            "")


class TrajectoryBasicRenderTests(unittest.TestCase):

    def test_returns_svg_for_valid_input(self):
        out = ck_trajectory_strip([0.05, 0.07, 0.09])
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions(self):
        out = ck_trajectory_strip([0.05, 0.07, 0.09])
        self.assertIn('width="80"', out)
        self.assertIn('height="18"', out)

    def test_custom_dimensions(self):
        out = ck_trajectory_strip(
            [1.0, 2.0, 3.0], width=120, height=24)
        self.assertIn('width="120"', out)
        self.assertIn('height="24"', out)

    def test_has_class_and_aria(self):
        out = ck_trajectory_strip([1.0, 2.0])
        self.assertIn('class="ck-traj-strip"', out)
        self.assertIn('role="img"', out)
        self.assertIn('aria-label="trajectory micro-chart"', out)

    def test_renders_polyline_with_n_points(self):
        out = ck_trajectory_strip([1, 2, 3, 4, 5])
        # 5 points → 5 comma-separated coords in points attr
        self.assertIn('<polyline', out)
        # Each point is "x.x,y.y" so 5 points = 4 spaces between
        # coords inside the points attr.
        import re
        m = re.search(r'points="([^"]+)"', out)
        self.assertIsNotNone(m)
        coords = m.group(1).split()
        self.assertEqual(len(coords), 5)

    def test_filters_nan_from_values(self):
        # 4 valid + 1 NaN → 4 points rendered
        out = ck_trajectory_strip([1.0, 2.0, float("nan"), 3.0, 4.0])
        import re
        m = re.search(r'points="([^"]+)"', out)
        coords = m.group(1).split()
        self.assertEqual(len(coords), 4)


class TrajectorySlopeToningPositiveDirectionTests(unittest.TestCase):
    """direction='positive' (e.g. operating_margin → higher is better)."""

    def test_improving_trend_is_positive_tone(self):
        # Values trending up → improving → positive tone (teal)
        out = ck_trajectory_strip([0.05, 0.07, 0.09],
                                    direction="positive")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_slight_decline_within_amber_threshold_is_neutral(self):
        # 100 → 97 = -3% decline; below 5% amber threshold → neutral
        out = ck_trajectory_strip([100.0, 99.0, 97.0],
                                    direction="positive")
        self.assertIn(_TONE_COLORS["neutral"], out)

    def test_moderate_decline_is_warning(self):
        # 100 → 90 = -10% → in amber band (5% < |pct| ≤ 15%)
        out = ck_trajectory_strip([100.0, 95.0, 90.0],
                                    direction="positive")
        self.assertIn(_TONE_COLORS["warning"], out)

    def test_significant_decline_is_negative_tone(self):
        # 100 → 70 = -30% → past red threshold
        out = ck_trajectory_strip([100.0, 85.0, 70.0],
                                    direction="positive")
        self.assertIn(_TONE_COLORS["negative"], out)


class TrajectorySlopeToningNegativeDirectionTests(unittest.TestCase):
    """direction='negative' (e.g. labor_cost_ratio → lower is better
    → trend going DOWN is improvement)."""

    def test_decreasing_trend_is_positive_tone(self):
        # 0.45 → 0.35: labor cost ratio dropping = good
        out = ck_trajectory_strip([0.45, 0.40, 0.35],
                                    direction="negative")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_increasing_trend_is_warning_or_negative(self):
        # 0.30 → 0.50 = +67% increase in a "lower-better" metric
        # → past red threshold
        out = ck_trajectory_strip([0.30, 0.40, 0.50],
                                    direction="negative")
        self.assertIn(_TONE_COLORS["negative"], out)


class TrajectoryEdgeCasesTests(unittest.TestCase):

    def test_first_value_zero_handled(self):
        # First value = 0 → can't compute %; falls back to absolute
        # sign comparison. Last > first → improving (in pos direction).
        out = ck_trajectory_strip([0.0, 0.05, 0.10],
                                    direction="positive")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_flat_trajectory_neutral(self):
        # All identical values → 0% change → neutral
        out = ck_trajectory_strip([0.5, 0.5, 0.5])
        self.assertIn(_TONE_COLORS["neutral"], out)

    def test_unknown_direction_falls_back_to_positive(self):
        out = ck_trajectory_strip([0.05, 0.07, 0.09],
                                    direction="weird")
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_none_direction_safe(self):
        out = ck_trajectory_strip([0.05, 0.07, 0.09],
                                    direction=None)  # type: ignore
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_custom_thresholds_honored(self):
        # 100 → 92 = -8% decline.
        # With default amber=5/red=15 → warning.
        out_default = ck_trajectory_strip([100.0, 96.0, 92.0],
                                            direction="positive")
        self.assertIn(_TONE_COLORS["warning"], out_default)
        # Tighten amber to 10: now -8% is BELOW amber → neutral
        out_strict = ck_trajectory_strip(
            [100.0, 96.0, 92.0], direction="positive",
            threshold_amber_pct=10.0,
        )
        self.assertIn(_TONE_COLORS["neutral"], out_strict)


class TrajectoryTooltipTests(unittest.TestCase):

    def test_tooltip_carries_first_last_pct(self):
        out = ck_trajectory_strip([0.05, 0.07, 0.10],
                                    direction="positive")
        self.assertIn("<title>", out)
        self.assertIn("0.05", out)
        self.assertIn("0.10", out)
        self.assertIn("%", out)

    def test_tooltip_labels_direction_word(self):
        # Improving in pos direction → 'improving'
        out_imp = ck_trajectory_strip([0.05, 0.10],
                                        direction="positive")
        self.assertIn("improving", out_imp)
        # Improving (labor ratio dropping) in neg direction →
        # 'improving' also (the word reflects the metric direction)
        out_neg = ck_trajectory_strip([0.50, 0.35],
                                        direction="negative")
        self.assertIn("improving", out_neg)

    def test_tooltip_carries_point_count(self):
        out = ck_trajectory_strip([1.0, 2.0, 3.0, 4.0])
        self.assertIn("n=4 pts", out)


# ─────────────────────────────────────────────────────────────────
# ck_dual_strip
# ─────────────────────────────────────────────────────────────────


class DualStripBasicTests(unittest.TestCase):

    def test_wraps_in_dual_strip_span(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
            direction="positive",
        )
        self.assertIn('class="ck-dual-strip"', out)
        self.assertIn('<span', out)
        # Both components present
        self.assertIn('ck-traj-strip', out)
        self.assertIn('ck-dist-strip', out)

    def test_separator_between_two_strips(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
        )
        self.assertIn('ck-dual-strip-sep', out)

    def test_inline_flex_layout(self):
        # display:inline-flex keeps the composite inline-flow so it
        # sits in a table cell without breaking row height.
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
        )
        self.assertIn('display:inline-flex', out)

    def test_default_widths(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
        )
        # Default: trajectory 80px + 1px sep + 4px margin + dist 50px
        # = total visible width ~135px
        self.assertIn('width="80"', out)
        self.assertIn('width="50"', out)


class DualStripPartialDegradationTests(unittest.TestCase):

    def test_no_trajectory_data_renders_distribution_only(self):
        # Trajectory empty → still get the distribution strip
        out = ck_dual_strip(
            trajectory_values=[],
            distribution_values=list(range(1, 101)),
            target_value=85,
        )
        self.assertTrue(out)
        self.assertIn('ck-dist-strip', out)
        # Separator only renders when BOTH strips present
        self.assertNotIn('ck-dual-strip-sep', out)
        self.assertNotIn('ck-traj-strip', out)

    def test_no_distribution_data_renders_trajectory_only(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=[],
            target_value=85,
        )
        self.assertTrue(out)
        self.assertIn('ck-traj-strip', out)
        self.assertNotIn('ck-dual-strip-sep', out)
        self.assertNotIn('ck-dist-strip', out)

    def test_no_target_value_drops_distribution(self):
        # None target → distribution helper returns empty → only
        # trajectory rendered.
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=None,
        )
        self.assertIn('ck-traj-strip', out)
        self.assertNotIn('ck-dist-strip', out)
        self.assertNotIn('ck-dual-strip-sep', out)

    def test_both_empty_returns_empty_string(self):
        # No data on either side → composite returns empty (table
        # cell stays clean, no bare separator).
        self.assertEqual(
            ck_dual_strip(
                trajectory_values=[],
                distribution_values=[],
                target_value=None,
            ),
            "",
        )

    def test_too_short_trajectory_drops_left(self):
        # 1-point trajectory → trajectory drops → distribution only
        out = ck_dual_strip(
            trajectory_values=[0.05],
            distribution_values=list(range(1, 101)),
            target_value=85,
        )
        self.assertIn('ck-dist-strip', out)
        self.assertNotIn('ck-traj-strip', out)


class DualStripDirectionPropagationTests(unittest.TestCase):
    """The direction arg flows through to BOTH constituent helpers
    — both must agree on the metric's improvement direction or the
    composite gives mixed signals."""

    def test_negative_direction_propagates_to_trajectory(self):
        # Labor ratio dropping is GOOD in 'negative' direction →
        # trajectory tone should be positive (teal).
        out = ck_dual_strip(
            trajectory_values=[0.50, 0.40, 0.35],
            distribution_values=list(range(1, 101)),
            target_value=20,
            direction="negative",
        )
        self.assertIn(_TONE_COLORS["positive"], out)

    def test_negative_direction_propagates_to_distribution(self):
        # Target=20 in [1..100] with negative direction → bottom
        # quartile is best → positive tone in dist tick.
        out = ck_dual_strip(
            trajectory_values=[],  # drop trajectory so we only see dist
            distribution_values=list(range(1, 101)),
            target_value=20,
            direction="negative",
        )
        self.assertIn(_TONE_COLORS["positive"], out)


class DualStripCustomDimensionsTests(unittest.TestCase):

    def test_custom_trajectory_width(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
            trajectory_width=100,
        )
        self.assertIn('width="100"', out)

    def test_custom_distribution_width(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
            distribution_width=70,
        )
        self.assertIn('width="70"', out)

    def test_shared_height_applied(self):
        out = ck_dual_strip(
            trajectory_values=[0.05, 0.07, 0.09],
            distribution_values=list(range(1, 101)),
            target_value=85,
            height=24,
        )
        # Both strips + separator share the height
        # Two SVG height="24" plus separator inline style
        self.assertEqual(out.count('height="24"'), 2)
        self.assertIn('height:24px', out)


if __name__ == "__main__":
    unittest.main()
