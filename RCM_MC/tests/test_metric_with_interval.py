"""tests for ``rcm_mc.ui._ui_kit.metric_with_interval``.

PROMPTS.md Phase 3 / Prompt 33: every predicted metric must show its
conformal P10/P90 interval. The platform has rigorous 85-96% coverage
intervals; this helper makes them visible.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui._ui_kit import metric_with_interval


class IntervalRendering(unittest.TestCase):

    def test_full_interval(self) -> None:
        out = metric_with_interval(
            2.80, p10=1.95, p90=3.85, kind="multiple",
        )
        self.assertIn("2.80x", out)
        self.assertIn("metric-interval", out)
        self.assertIn("P10 1.95x", out)
        self.assertIn("P90 3.85x", out)

    def test_money_kind_interval(self) -> None:
        out = metric_with_interval(
            13_000_000, p10=8_000_000, p90=21_000_000, kind="money",
        )
        self.assertIn("$13.00M", out)
        self.assertIn("P10 $8.00M", out)
        self.assertIn("P90 $21.00M", out)

    def test_percent_kind_interval(self) -> None:
        out = metric_with_interval(
            0.092, p10=0.075, p90=0.118, kind="percent",
        )
        self.assertIn("9.2%", out)
        self.assertIn("P10 7.5%", out)
        self.assertIn("P90 11.8%", out)


class MissingBandsFallback(unittest.TestCase):
    """Half-intervals must not render — fall back to the point only."""

    def test_p10_missing(self) -> None:
        out = metric_with_interval(
            2.8, p10=None, p90=3.85, kind="multiple",
        )
        self.assertIn("2.80x", out)
        self.assertNotIn("metric-interval", out)
        self.assertNotIn("P90", out)

    def test_p90_missing(self) -> None:
        out = metric_with_interval(
            2.8, p10=1.95, p90=None, kind="multiple",
        )
        self.assertNotIn("metric-interval", out)
        self.assertNotIn("P10", out)

    def test_both_missing(self) -> None:
        out = metric_with_interval(
            2.8, p10=None, p90=None, kind="multiple",
        )
        self.assertEqual(out, "2.80x")

    def test_nan_band_treated_as_missing(self) -> None:
        out = metric_with_interval(
            2.8, p10=math.nan, p90=3.85, kind="multiple",
        )
        self.assertNotIn("metric-interval", out)


class PointMissing(unittest.TestCase):

    def test_missing_point_renders_unpopulated_label(self) -> None:
        # If the point estimate itself is missing, the format_value
        # missing-aware span comes through. The interval is dropped.
        out = metric_with_interval(
            None, p10=1.95, p90=3.85, kind="multiple",
        )
        self.assertIn('class="muted unpopulated"', out)
        self.assertNotIn("metric-interval", out)


if __name__ == "__main__":
    unittest.main()
