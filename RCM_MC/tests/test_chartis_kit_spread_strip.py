"""Tests for ``ck_spread_strip`` — inline target vs benchmark
spread visualization.

Generalizes the 'FQHC per-visit cost vs PPS rate' pattern from the
Iter-7 design loop into a reusable comparison visual: two ticks
(target + benchmark) + a colored gap between them encoding
favorable/adverse direction-of-improvement.

Not yet wired to any partner-facing page. Tests lock the contract
before integration so consumers (HCRIS X-ray, FQHC screener,
bridge audit planned-vs-actual) get a stable surface.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_spread_strip


class EmptyCasesTests(unittest.TestCase):

    def test_none_target_returns_empty(self):
        self.assertEqual(ck_spread_strip(None, 100), "")

    def test_none_benchmark_returns_empty(self):
        self.assertEqual(ck_spread_strip(100, None), "")

    def test_both_none_returns_empty(self):
        self.assertEqual(ck_spread_strip(None, None), "")

    def test_non_numeric_target_returns_empty(self):
        self.assertEqual(ck_spread_strip("junk", 100), "")

    def test_non_numeric_benchmark_returns_empty(self):
        self.assertEqual(ck_spread_strip(100, "junk"), "")

    def test_nan_returns_empty(self):
        self.assertEqual(
            ck_spread_strip(float("nan"), 100), "")
        self.assertEqual(
            ck_spread_strip(100, float("nan")), "")

    def test_inf_returns_empty(self):
        self.assertEqual(
            ck_spread_strip(float("inf"), 100), "")
        self.assertEqual(
            ck_spread_strip(100, float("-inf")), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_svg_for_valid_input(self):
        out = ck_spread_strip(0.12, 0.08, direction="positive")
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_dimensions(self):
        out = ck_spread_strip(100, 80)
        self.assertIn('width="120"', out)
        self.assertIn('height="18"', out)

    def test_custom_dimensions(self):
        out = ck_spread_strip(100, 80, width=200, height=24)
        self.assertIn('width="200"', out)
        self.assertIn('height="24"', out)

    def test_class_and_accessibility(self):
        out = ck_spread_strip(100, 80)
        self.assertIn('class="ck-spread-strip"', out)
        self.assertIn('role="img"', out)
        self.assertIn(
            'aria-label="target vs benchmark spread strip"', out)

    def test_renders_background_axis_ribbon(self):
        out = ck_spread_strip(100, 80)
        self.assertIn('<rect', out)
        self.assertIn('fill="#e8e1d3"', out)

    def test_renders_two_ticks(self):
        # Target tick is solid (stroke-linecap="round"); benchmark
        # tick is dashed.
        out = ck_spread_strip(100, 80)
        self.assertIn('stroke-linecap="round"', out)
        self.assertIn('stroke-dasharray="2,1.5"', out)


class FavorableDirectionTests(unittest.TestCase):
    """Target on the favorable side of benchmark → green gap."""

    def test_higher_target_in_positive_direction_is_favorable(self):
        # operating_margin: 12% target > 8% bench → favorable
        out = ck_spread_strip(0.12, 0.08, direction="positive")
        # Positive-green appears (in target tick + gap fill)
        self.assertIn("#0a8a5f", out)

    def test_lower_target_in_negative_direction_is_favorable(self):
        # labor_cost_ratio: 30% target < 40% bench → favorable
        out = ck_spread_strip(0.30, 0.40, direction="negative")
        self.assertIn("#0a8a5f", out)


class AdverseDirectionTests(unittest.TestCase):
    """Target on the wrong side of benchmark → red gap."""

    def test_lower_target_in_positive_direction_is_adverse(self):
        # margin: 5% target < 10% bench → adverse
        out = ck_spread_strip(0.05, 0.10, direction="positive")
        self.assertIn("#b5321e", out)

    def test_higher_target_in_negative_direction_is_adverse(self):
        # cost: 150 target > 120 bench → adverse
        out = ck_spread_strip(150, 120, direction="negative")
        self.assertIn("#b5321e", out)


class EqualValuesTests(unittest.TestCase):

    def test_equal_values_use_neutral_tone(self):
        out = ck_spread_strip(100, 100, direction="positive")
        # Neutral teal anchor appears.
        self.assertIn("#155752", out)
        # No green/red gap fill.
        self.assertNotIn("#0a8a5f", out)
        self.assertNotIn("#b5321e", out)

    def test_equal_values_no_gap_rect_rendered(self):
        # When values match, gap_w = 0 → falls below the 0.5px floor
        # → the gap rect is OMITTED entirely (cleaner than rendering
        # an invisible zero-width rect). Only the background ribbon
        # and the two tick lines appear.
        out = ck_spread_strip(100, 100, direction="positive")
        # Background ribbon rect is the only <rect> in the output.
        self.assertEqual(out.count("<rect"), 1)
        # No gap fill-opacity attribute at all.
        self.assertNotIn("fill-opacity", out)


class DirectionFallbackTests(unittest.TestCase):

    def test_unknown_direction_falls_back_to_positive(self):
        # 'weird' → treat as positive → 12 > 8 favorable → green
        out = ck_spread_strip(0.12, 0.08, direction="weird")
        self.assertIn("#0a8a5f", out)

    def test_none_direction_falls_back_to_positive(self):
        out = ck_spread_strip(0.12, 0.08, direction=None)  # type: ignore
        self.assertIn("#0a8a5f", out)

    def test_case_insensitive_direction(self):
        out = ck_spread_strip(150, 120, direction="NEGATIVE")
        self.assertIn("#b5321e", out)


class AxisRangeTests(unittest.TestCase):
    """Default axis range derives from the two values + 15% padding;
    callers can override with range_min/range_max."""

    def test_default_axis_includes_padding(self):
        # 10 and 20 → 15% pad on a span of 10 = ±1.5
        # axis_min = 8.5, axis_max = 21.5
        # tick at 10 → x = (10-8.5)/(21.5-8.5) × 120 ≈ 13.8
        out = ck_spread_strip(10, 20, width=120)
        # Just sanity that tick is well INSIDE [0.5, 119.5]
        import re
        target_tick_x = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2"', out)
        self.assertIsNotNone(target_tick_x)
        x = float(target_tick_x.group(1))
        self.assertGreater(x, 5)
        self.assertLess(x, 25)

    def test_custom_axis_range_honored(self):
        # Force axis 0..100 → target 50 sits at x=60 (50% of 120)
        out = ck_spread_strip(
            50, 75, width=120,
            range_min=0, range_max=100,
        )
        import re
        # Target tick is the solid line (stroke-width=2)
        target_x = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2"', out)
        x = float(target_x.group(1))
        # 50/100 × 120 = 60
        self.assertAlmostEqual(x, 60.0, places=0)

    def test_out_of_range_target_clamps_to_edge(self):
        # Target way outside custom axis range → clamps to width-0.5
        out = ck_spread_strip(
            999, 50, width=120,
            range_min=0, range_max=100,
        )
        import re
        target_x = re.search(
            r'<line x1="([\d.]+)"[^>]*stroke-width="2"', out)
        x = float(target_x.group(1))
        self.assertAlmostEqual(x, 119.5, places=1)


class TooltipTests(unittest.TestCase):

    def test_tooltip_carries_both_values_and_diff(self):
        out = ck_spread_strip(0.12, 0.08,
                                direction="positive",
                                unit_suffix="%")
        self.assertIn("<title>", out)
        self.assertIn("Target: 0.12%", out)
        self.assertIn("Benchmark: 0.08%", out)
        self.assertIn("Δ +0.04", out)

    def test_tooltip_includes_pct_change(self):
        # 12% vs 8% → 50% above bench → '+50.0%'
        out = ck_spread_strip(0.12, 0.08, direction="positive",
                                unit_suffix="%")
        self.assertIn("+50.0%", out)

    def test_tooltip_handles_zero_benchmark(self):
        # Zero benchmark → pct undefined → dash placeholder
        out = ck_spread_strip(100, 0)
        self.assertIn("—", out)

    def test_custom_labels(self):
        out = ck_spread_strip(
            100, 80,
            target_label="Our hospital",
            benchmark_label="State median",
        )
        self.assertIn("Our hospital:", out)
        self.assertIn("State median:", out)

    def test_unit_prefix_and_suffix(self):
        out = ck_spread_strip(
            150, 120,
            unit_prefix="$",
            unit_suffix="M",
        )
        self.assertIn("$150.00M", out)
        self.assertIn("$120.00M", out)


class TickStyleTests(unittest.TestCase):
    """Target tick = solid bold; benchmark tick = dashed faint."""

    def test_target_tick_is_solid_bold(self):
        out = ck_spread_strip(100, 80)
        # The solid tick line carries stroke-width="2" + linecap round
        self.assertIn('stroke-width="2"', out)
        self.assertIn('stroke-linecap="round"', out)

    def test_benchmark_tick_is_dashed_thin(self):
        out = ck_spread_strip(100, 80)
        # Dashed pattern '2,1.5' is on the benchmark tick
        self.assertIn('stroke-dasharray="2,1.5"', out)
        self.assertIn('stroke-width="1"', out)


if __name__ == "__main__":
    unittest.main()
