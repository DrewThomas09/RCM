"""tests for ``metric_with_delta`` (P73)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import metric_with_delta


class IncreaseHigherIsBetter(unittest.TestCase):

    def test_moic_up_renders_positive_arrow(self) -> None:
        out = metric_with_delta(2.80, 2.65, kind="multiple")
        self.assertIn("2.80x", out)
        self.assertIn("▲", out)
        self.assertIn("+0.15x", out)
        self.assertIn("tone-positive", out)


class DecreaseHigherIsBetter(unittest.TestCase):

    def test_health_down_renders_negative_arrow(self) -> None:
        out = metric_with_delta(
            87, 90, kind="count", period_label="vs last month",
        )
        self.assertIn("▼", out)
        self.assertIn("-3", out)
        self.assertIn("tone-negative", out)
        self.assertIn("vs last month", out)


class HigherIsWorseFlag(unittest.TestCase):

    def test_denial_rate_increase_is_negative_tone(self) -> None:
        # Denial rate going up is bad — caller flips the flag.
        out = metric_with_delta(
            0.092, 0.085, kind="percent",
            higher_is_better=False,
        )
        self.assertIn("▲", out)
        self.assertIn("tone-negative", out)
        self.assertIn("+0.7pp", out)

    def test_denial_rate_decrease_is_positive_tone(self) -> None:
        out = metric_with_delta(
            0.085, 0.092, kind="percent",
            higher_is_better=False,
        )
        self.assertIn("▼", out)
        self.assertIn("tone-positive", out)


class MoneyDelta(unittest.TestCase):

    def test_money_delta_signed(self) -> None:
        out = metric_with_delta(
            120_000_000, 100_000_000, kind="money",
        )
        self.assertIn("$120.00M", out)
        self.assertIn("+$20.00M", out)


class MissingValuesGraceful(unittest.TestCase):

    def test_no_prior_renders_point_only(self) -> None:
        out = metric_with_delta(2.80, None, kind="multiple")
        self.assertEqual(out, "2.80x")

    def test_no_value_renders_unpopulated_span(self) -> None:
        out = metric_with_delta(None, 2.65, kind="multiple")
        self.assertIn("muted unpopulated", out)
        self.assertNotIn("metric-delta", out)


class ZeroDeltaDropsArrow(unittest.TestCase):

    def test_equal_values_render_point_only(self) -> None:
        out = metric_with_delta(2.80, 2.80, kind="multiple")
        self.assertEqual(out, "2.80x")


if __name__ == "__main__":
    unittest.main()
