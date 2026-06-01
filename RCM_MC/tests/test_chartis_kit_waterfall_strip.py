"""Tests for ``ck_waterfall_strip`` — risk-adjusted EBITDA-bridge
waterfall.

Iter-9 foundation: a horizontal stacked bar where each segment's
width = planned dollar impact and opacity = realization probability,
with an optional 5px footer bar encoding letter grade (A/B/C/D).

Not yet wired to /diligence/bridge-audit or /portfolio/monitor.
Tests lock the visual + behavior contract before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_waterfall_strip


_GRADE_COLORS = {
    "A": "#0a8a5f",
    "B": "#5ba383",
    "C": "#b8732a",
    "D": "#b5321e",
}


# Stable fixture used across multiple tests.
_BRIDGE = [
    {"name": "denial_reduction", "impact": 2_000_000,
     "realization": 0.85, "grade": "A"},
    {"name": "dso_compression",  "impact": 1_500_000,
     "realization": 0.60, "grade": "C"},
    {"name": "underpay_recovery", "impact": 500_000,
     "realization": 0.40, "grade": "D"},
]


class EmptyCasesTests(unittest.TestCase):
    """Helper must degrade silently — no defensible width allocation
    when no positive-impact segments exist."""

    def test_empty_segments_returns_empty(self):
        self.assertEqual(ck_waterfall_strip([]), "")

    def test_none_segments_returns_empty(self):
        self.assertEqual(ck_waterfall_strip(None), "")  # type: ignore

    def test_all_negative_impact_returns_empty(self):
        # Positive-impact only filter (negative levers belong in a
        # separate strip per the spec).
        out = ck_waterfall_strip([
            {"name": "x", "impact": -100_000},
            {"name": "y", "impact": -50_000},
        ])
        self.assertEqual(out, "")

    def test_zero_impact_filtered_out(self):
        out = ck_waterfall_strip([
            {"name": "zero", "impact": 0},
        ])
        self.assertEqual(out, "")

    def test_non_numeric_impact_filtered(self):
        # Mixed list: 1 valid + 3 invalid → renders the 1 valid
        out = ck_waterfall_strip([
            {"name": "good", "impact": 100_000},
            {"name": "bad", "impact": "junk"},
            {"name": "naninf", "impact": float("nan")},
            {"name": "inf", "impact": float("inf")},
        ])
        # Only the 'good' segment renders.
        self.assertIn('<svg', out)
        # Count <g> wrappers — one per rendered segment
        self.assertEqual(out.count('<g>'), 1)

    def test_non_mapping_items_safely_skipped(self):
        # Defensive against bad caller data.
        out = ck_waterfall_strip([
            "junk", None, {"name": "valid", "impact": 100_000},
            42,
        ])
        self.assertIn('<svg', out)
        self.assertEqual(out.count('<g>'), 1)


class BasicRenderTests(unittest.TestCase):

    def test_returns_svg_for_valid_bridge(self):
        out = ck_waterfall_strip(_BRIDGE)
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions(self):
        out = ck_waterfall_strip(_BRIDGE)
        self.assertIn('width="600"', out)
        self.assertIn('height="24"', out)

    def test_custom_dimensions(self):
        out = ck_waterfall_strip(_BRIDGE, width=900, height=32)
        self.assertIn('width="900"', out)
        self.assertIn('height="32"', out)

    def test_class_and_accessibility(self):
        out = ck_waterfall_strip(_BRIDGE)
        self.assertIn('class="ck-waterfall"', out)
        self.assertIn('role="img"', out)
        self.assertIn(
            'aria-label="risk-adjusted bridge waterfall"', out)

    def test_renders_one_g_wrapper_per_segment(self):
        out = ck_waterfall_strip(_BRIDGE)
        self.assertEqual(out.count('<g>'), 3)

    def test_renders_white_separators_between_segments(self):
        # Each segment <rect> has stroke="#ffffff" stroke-width="0.5"
        # so adjacent segments appear visually separated.
        out = ck_waterfall_strip(_BRIDGE)
        self.assertIn('stroke="#ffffff"', out)


class SegmentWidthTests(unittest.TestCase):
    """Width allocation must be proportional to impact."""

    def test_widths_sum_to_full_canvas(self):
        out = ck_waterfall_strip(_BRIDGE, width=600)
        import re
        # Pull rect widths for the segment rects (the body rects
        # have y="0" — distinct from the footer rects at y="bar_h").
        rect_pattern = re.compile(
            r'<rect x="[\d.]+" y="0" width="([\d.]+)"')
        widths = [float(w) for w in rect_pattern.findall(out)]
        # Per-segment body rect + optional hatched overlay → multiple
        # rects per segment with y="0". De-dup by uniquing on width
        # (each segment has a unique width given our fixture).
        unique_widths = sorted(set(widths))
        self.assertAlmostEqual(
            sum(unique_widths), 600.0, places=0,
            msg=f"widths: {unique_widths}")

    def test_proportional_to_impact(self):
        # Bridge totals to $4M; denial=2M → 50% of width, etc.
        out = ck_waterfall_strip(_BRIDGE, width=600)
        import re
        rect_pattern = re.compile(
            r'<rect x="([\d.]+)" y="0" width="([\d.]+)"')
        rects = [(float(x), float(w))
                 for x, w in rect_pattern.findall(out)]
        # First segment: x=0, w should be 50% of 600 = 300
        first_w = rects[0][1]
        self.assertAlmostEqual(first_w, 300.0, places=0)


class OpacityFromRealizationTests(unittest.TestCase):
    """Opacity must encode realization probability — full = 1.0,
    failed = floored at 0.20 (so segment never fully disappears)."""

    def test_full_realization_full_opacity(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 1.0},
        ])
        self.assertIn('fill-opacity="1.00"', out)

    def test_low_realization_floored_at_0_20(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 0.05},
        ])
        self.assertIn('fill-opacity="0.20"', out)

    def test_realization_above_one_clamped(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 5.0},
        ])
        self.assertIn('fill-opacity="1.00"', out)

    def test_negative_realization_clamped_to_zero_then_floored(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": -0.5},
        ])
        self.assertIn('fill-opacity="0.20"', out)

    def test_default_realization_is_one(self):
        # No 'realization' key → defaults to 1.0
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100},
        ])
        self.assertIn('fill-opacity="1.00"', out)

    def test_non_numeric_realization_falls_back_to_one(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": "junk"},
        ])
        self.assertIn('fill-opacity="1.00"', out)


class HatchOverlayTests(unittest.TestCase):
    """Low-realization segments get a hatched overlay as a second
    visual cue beyond opacity (per Iter-9 critic note: opacity alone
    doesn't read clearly when magnitudes vary)."""

    def test_low_realization_gets_hatch_overlay(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 0.50},
        ])
        # The hatch pattern + the url(#) ref both present
        self.assertIn('id="ck-wf-hatch"', out)
        self.assertIn('url(#ck-wf-hatch)', out)

    def test_high_realization_no_hatch_overlay(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 0.95},
        ])
        # Pattern still defined (cheap), but no segment references it
        self.assertIn('id="ck-wf-hatch"', out)
        self.assertNotIn('url(#ck-wf-hatch)', out)

    def test_threshold_at_70_pct(self):
        # 0.70 → no hatch; 0.69 → hatch (strict less-than)
        out_below = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 0.69},
        ])
        out_at = ck_waterfall_strip([
            {"name": "x", "impact": 100, "realization": 0.70},
        ])
        self.assertIn('url(#ck-wf-hatch)', out_below)
        self.assertNotIn('url(#ck-wf-hatch)', out_at)


class GradeFooterTests(unittest.TestCase):
    """Optional 5px footer bar below each segment encodes letter
    grade with the standard severity palette."""

    def test_grade_A_footer_is_positive_green(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "grade": "A"},
        ])
        self.assertIn(_GRADE_COLORS["A"], out)

    def test_grade_D_footer_is_negative_red(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "grade": "D"},
        ])
        self.assertIn(_GRADE_COLORS["D"], out)

    def test_missing_grade_no_footer(self):
        # No grade → no footer rect at y=bar_h
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100},
        ])
        # No grade-color hex appears
        for color in _GRADE_COLORS.values():
            self.assertNotIn(color, out)

    def test_show_grade_footer_false_disables_footers(self):
        out = ck_waterfall_strip(
            _BRIDGE, show_grade_footer=False,
        )
        for color in _GRADE_COLORS.values():
            self.assertNotIn(color, out)

    def test_grade_case_insensitive(self):
        # 'a' should be normalized to 'A'
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "grade": "a"},
        ])
        self.assertIn(_GRADE_COLORS["A"], out)

    def test_unknown_grade_no_footer(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "grade": "Z"},
        ])
        for color in _GRADE_COLORS.values():
            self.assertNotIn(color, out)


class TooltipTests(unittest.TestCase):

    def test_per_segment_tooltip_carries_name_and_realization(self):
        out = ck_waterfall_strip([
            {"name": "denial_reduction", "impact": 2_000_000,
             "realization": 0.85},
        ])
        # Per-segment <title> inside <g>
        self.assertIn("denial_reduction", out)
        self.assertIn("planned $2.00M", out)
        self.assertIn("realized 85%", out)
        self.assertIn("risk-adjusted $1.70M", out)

    def test_composite_total_tooltip(self):
        out = ck_waterfall_strip(_BRIDGE)
        # Composite <title> at the SVG level (not inside any <g>).
        # Total = 2M + 1.5M + 0.5M = 4M gross.
        # Risk-adjusted = 2*0.85 + 1.5*0.60 + 0.5*0.40 = 2.8M
        self.assertIn("$4.00M gross", out)
        self.assertIn("$2.80M risk-adjusted", out)

    def test_segment_name_html_escaped(self):
        out = ck_waterfall_strip([
            {"name": "<img src=x>", "impact": 100,
             "realization": 1.0},
        ])
        self.assertNotIn("<img src=x>", out)
        self.assertIn("&lt;img", out)

    def test_grade_appears_in_tooltip_when_set(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "grade": "B"},
        ])
        self.assertIn("grade B", out)


class CustomColorTests(unittest.TestCase):

    def test_custom_color_overrides_default(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100, "color": "#abcdef"},
        ])
        self.assertIn('fill="#abcdef"', out)

    def test_default_color_when_none(self):
        out = ck_waterfall_strip([
            {"name": "x", "impact": 100},
        ])
        # Default first-in-palette is teal-anchored '#155752'
        self.assertIn('fill="#155752"', out)


if __name__ == "__main__":
    unittest.main()
