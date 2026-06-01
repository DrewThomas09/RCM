"""Tests for ``ck_threshold_gauge`` — value vs threshold strip.

Generalizes the 'covenant cushion' / 'margin headroom' / 'A/R aging
risk' pattern into a reusable 3-zone strip (safe / warning / breach).
Sibling to ``ck_spread_strip``: where spread compares two values,
this places one value against a pair of editorial gates.

Designed for partner-facing cells where a single number needs
context against a known threshold without spending a full chart —
covenant cushion, operating margin vs PE target, days_in_AR vs
aging gate, denial_rate vs payer SLA.

Not yet wired to a partner-facing page. Tests lock the contract
before integration so consumers get a stable surface.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_threshold_gauge


class EmptyCasesTests(unittest.TestCase):

    def test_none_value_returns_empty(self):
        self.assertEqual(
            ck_threshold_gauge(
                None, warning_threshold=1.5, breach_threshold=1.2),
            "",
        )

    def test_none_warning_returns_empty(self):
        self.assertEqual(
            ck_threshold_gauge(
                2.0, warning_threshold=None, breach_threshold=1.2),
            "",
        )

    def test_none_breach_returns_empty(self):
        self.assertEqual(
            ck_threshold_gauge(
                2.0, warning_threshold=1.5, breach_threshold=None),
            "",
        )

    def test_non_numeric_returns_empty(self):
        self.assertEqual(
            ck_threshold_gauge(
                "junk", warning_threshold=1.5, breach_threshold=1.2),
            "",
        )

    def test_nan_or_inf_returns_empty(self):
        self.assertEqual(
            ck_threshold_gauge(
                float("nan"), warning_threshold=1.5, breach_threshold=1.2),
            "",
        )
        self.assertEqual(
            ck_threshold_gauge(
                2.0, warning_threshold=float("inf"), breach_threshold=1.2),
            "",
        )


class ThresholdOrderingTests(unittest.TestCase):
    """Misordered thresholds for the stated direction → empty string
    (no guessing the operator's intent)."""

    def test_positive_requires_warning_above_breach(self):
        # warning < breach in positive direction → empty
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.0, breach_threshold=1.5,
            direction="positive",
        )
        self.assertEqual(out, "")

    def test_positive_equal_thresholds_returns_empty(self):
        # Equal thresholds → zero-width warning band → ambiguous → empty
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.5,
            direction="positive",
        )
        self.assertEqual(out, "")

    def test_negative_requires_breach_above_warning(self):
        # breach < warning in negative direction → empty
        out = ck_threshold_gauge(
            55, warning_threshold=70, breach_threshold=50,
            direction="negative",
        )
        self.assertEqual(out, "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_svg(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        self.assertIn('width="140"', out)
        self.assertIn('height="18"', out)

    def test_custom_dimensions(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2,
            width=200, height=24,
        )
        self.assertIn('width="200"', out)
        self.assertIn('height="24"', out)

    def test_minimum_dimensions_enforced(self):
        # Floor at 40×10 so the strip stays visible.
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2,
            width=10, height=4,
        )
        self.assertIn('width="40"', out)
        self.assertIn('height="10"', out)

    def test_class_and_accessibility(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        self.assertIn('class="ck-threshold-gauge"', out)
        self.assertIn('role="img"', out)
        self.assertIn('aria-label="value vs threshold gauge', out)

    def test_renders_background_ribbon(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        self.assertIn('fill="#e8e1d3"', out)

    def test_renders_threshold_ticks_dashed(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        # Both warning + breach ticks share the 2,1.5 dasharray
        self.assertEqual(out.count('stroke-dasharray="2,1.5"'), 2)

    def test_renders_value_tick_solid_bold(self):
        out = ck_threshold_gauge(
            2.0, warning_threshold=1.5, breach_threshold=1.2)
        # Value tick: stroke-width=2.5 + linecap round
        self.assertIn('stroke-width="2.5"', out)
        self.assertIn('stroke-linecap="round"', out)


class PositiveDirectionZoneTests(unittest.TestCase):
    """Higher is better (DSCR, margin, cushion). Value >= warning → safe;
    breach <= value < warning → warning; value < breach → breach."""

    def test_above_warning_is_safe_zone(self):
        # value=2.5 cushion, warning=1.5x, breach=1.2x → safe (green)
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('safe zone', out)
        # Aria label includes zone name
        self.assertIn('(safe zone)', out)

    def test_between_warning_and_breach_is_warning_zone(self):
        # value=1.35 → between 1.5 and 1.2 → warning amber
        out = ck_threshold_gauge(
            1.35, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('(warning zone)', out)

    def test_at_breach_threshold_is_warning(self):
        # value == breach → still in warning (>= breach is warning)
        out = ck_threshold_gauge(
            1.2, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('(warning zone)', out)

    def test_below_breach_is_breach_zone(self):
        # value=1.0 < breach=1.2 → breach (red)
        out = ck_threshold_gauge(
            1.0, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('(breach zone)', out)

    def test_at_warning_threshold_is_safe(self):
        # value == warning → safe (>= warning is safe)
        out = ck_threshold_gauge(
            1.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('(safe zone)', out)


class NegativeDirectionZoneTests(unittest.TestCase):
    """Higher is worse (days_in_AR, denial_rate, leverage_ratio).
    Zones invert — low = safe, high = breach."""

    def test_below_warning_is_safe(self):
        # A/R aging: value=45 days < warning=50 → safe
        out = ck_threshold_gauge(
            45, warning_threshold=50, breach_threshold=70,
            direction="negative",
        )
        self.assertIn('(safe zone)', out)

    def test_between_thresholds_is_warning(self):
        # A/R aging: value=60 → between warning=50 and breach=70 → warning
        out = ck_threshold_gauge(
            60, warning_threshold=50, breach_threshold=70,
            direction="negative",
        )
        self.assertIn('(warning zone)', out)

    def test_above_breach_is_breach(self):
        # A/R aging: value=85 > breach=70 → breach
        out = ck_threshold_gauge(
            85, warning_threshold=50, breach_threshold=70,
            direction="negative",
        )
        self.assertIn('(breach zone)', out)

    def test_at_warning_is_safe(self):
        # value == warning → safe (<= warning is safe in negative)
        out = ck_threshold_gauge(
            50, warning_threshold=50, breach_threshold=70,
            direction="negative",
        )
        self.assertIn('(safe zone)', out)

    def test_at_breach_is_warning(self):
        # value == breach → warning (<= breach is warning in negative)
        out = ck_threshold_gauge(
            70, warning_threshold=50, breach_threshold=70,
            direction="negative",
        )
        self.assertIn('(warning zone)', out)


class DirectionFallbackTests(unittest.TestCase):

    def test_unknown_direction_falls_back_to_positive(self):
        # 'sideways' → treat as positive
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="sideways",
        )
        self.assertIn('(safe zone)', out)

    def test_none_direction_falls_back_to_positive(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction=None,  # type: ignore
        )
        self.assertIn('(safe zone)', out)

    def test_case_insensitive_direction(self):
        out = ck_threshold_gauge(
            85, warning_threshold=50, breach_threshold=70,
            direction="NEGATIVE",
        )
        self.assertIn('(breach zone)', out)


class ZoneColorTests(unittest.TestCase):
    """Each zone has a specific editorial color in the value-tick stroke."""

    def test_safe_zone_uses_positive_green(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        # Value tick stroke is the zone color.
        self.assertIn('stroke="#0a8a5f"', out)

    def test_warning_zone_uses_amber(self):
        out = ck_threshold_gauge(
            1.35, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('stroke="#b8732a"', out)

    def test_breach_zone_uses_red(self):
        out = ck_threshold_gauge(
            1.0, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
        )
        self.assertIn('stroke="#b5321e"', out)


class AxisRangeTests(unittest.TestCase):
    """Default axis range covers all three values with 20% padding;
    callers can pin with range_min/range_max."""

    def test_value_tick_within_strip_bounds(self):
        # value=2.5, warning=1.5, breach=1.2 → default range covers
        # all three with pad → value tick must be at x < width.
        import re
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            width=140,
        )
        # Value tick has stroke-width="2.5" — the only one.
        m = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        self.assertIsNotNone(m)
        x = float(m.group(1))
        self.assertGreater(x, 0.5)
        self.assertLess(x, 139.5)

    def test_custom_range_honored(self):
        # Pin axis 0..10; value=5 → x = 5/10 * 140 = 70
        import re
        out = ck_threshold_gauge(
            5.0, warning_threshold=3.0, breach_threshold=1.0,
            width=140, range_min=0, range_max=10,
        )
        m = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        self.assertIsNotNone(m)
        x = float(m.group(1))
        # 5/10 * (140 - 1) + 0.5 = 70.0 (approx)
        self.assertAlmostEqual(x, 70.0, delta=1.0)

    def test_value_above_custom_range_clamps_to_edge(self):
        import re
        out = ck_threshold_gauge(
            999, warning_threshold=3.0, breach_threshold=1.0,
            width=140, range_min=0, range_max=10,
        )
        m = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        x = float(m.group(1))
        # Clamped to right edge (width - 0.5)
        self.assertAlmostEqual(x, 139.5, places=1)

    def test_value_below_custom_range_clamps_to_left_edge(self):
        import re
        out = ck_threshold_gauge(
            -100, warning_threshold=3.0, breach_threshold=1.0,
            width=140, range_min=0, range_max=10,
        )
        m = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        x = float(m.group(1))
        self.assertAlmostEqual(x, 0.5, places=1)


class TooltipTests(unittest.TestCase):

    def test_tooltip_carries_value_and_thresholds(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            unit_suffix="x",
        )
        self.assertIn('<title>', out)
        self.assertIn('2.50x', out)
        self.assertIn('1.50x', out)
        self.assertIn('1.20x', out)
        self.assertIn('Zone: safe', out)

    def test_custom_labels(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            value_label="DSCR",
            threshold_label="Covenant",
        )
        self.assertIn('DSCR:', out)
        self.assertIn('Covenant', out)

    def test_unit_prefix_and_suffix(self):
        out = ck_threshold_gauge(
            150, warning_threshold=100, breach_threshold=50,
            unit_prefix="$",
            unit_suffix="M",
        )
        self.assertIn('$150.00M', out)
        self.assertIn('$100.00M', out)
        self.assertIn('$50.00M', out)

    def test_precision_arg(self):
        out = ck_threshold_gauge(
            0.1234, warning_threshold=0.10, breach_threshold=0.05,
            precision=4, unit_suffix="",
        )
        self.assertIn('0.1234', out)

    def test_tooltip_html_escaped(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            value_label="<script>",
        )
        # Escaped in the <title> body.
        self.assertNotIn('<script>', out.split('<title>')[1])
        self.assertIn('&lt;script&gt;', out)


class ZoneRectTests(unittest.TestCase):
    """Each zone band renders as a translucent rect; sub-pixel widths
    are omitted (no invisible noise)."""

    def test_three_zones_render_when_well_separated(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
            range_min=0, range_max=3,
        )
        # 1 background ribbon + 3 zone rects = 4 total
        self.assertEqual(out.count('<rect'), 4)

    def test_zone_rects_use_translucent_fill_opacity(self):
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5, breach_threshold=1.2,
            direction="positive",
            range_min=0, range_max=3,
        )
        # Each zone rect carries fill-opacity="0.22" (subdued).
        self.assertIn('fill-opacity="0.22"', out)

    def test_sub_pixel_zone_band_dropped(self):
        # With axis tightly bounded so the warning band shrinks below
        # the 0.5px floor, that zone rect is skipped.
        out = ck_threshold_gauge(
            2.5, warning_threshold=1.5,
            breach_threshold=1.4999,  # tiny gap, sub-pixel at width=10
            direction="positive",
            range_min=0, range_max=100,  # 1.5−1.4999 ≈ 0.0001 of axis span
            width=40,
        )
        # Background ribbon + at most 2 zone rects (warning is dropped).
        self.assertLessEqual(out.count('<rect'), 3)


if __name__ == "__main__":
    unittest.main()
