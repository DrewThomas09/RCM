"""Wave-31 visual: fund-learning planned-vs-realized chart.

The lever-bias table carried planned, actual, and realization % as
columns — the shortfall geometry ("we planned $4M and got $1.5M")
required mental arithmetic. Pins the dumbbell chart: dashed planned
track + filled realized bar, realization tones, planned-size sort,
zero-plan levers skipped, and the empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.fund_learning_page import _lever_realization_svg


def _b(lever, planned, actual):
    pct = (actual / planned) if planned else 0.0
    return SimpleNamespace(
        lever=lever, planned_total=planned, actual_total=actual,
        realization_pct=pct, bias_direction="accurate",
        adjustment_factor=1.0, n_deals=3,
    )


class LeverRealizationChartTests(unittest.TestCase):
    def test_renders_planned_track_and_realized_bar(self):
        svg = _lever_realization_svg([
            _b("Denial recovery", 4_000_000, 1_500_000),   # 38% → red
            _b("Coding uplift", 2_000_000, 1_900_000),     # 95% → green
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-lever-realization", svg)
        self.assertIn("stroke-dasharray", svg)             # planned track
        self.assertIn("#b5321e", svg)                       # red band
        self.assertIn("#0a8a5f", svg)                       # green band
        self.assertIn("38% of $4.0M", svg)
        self.assertIn("95% of $2.0M", svg)

    def test_sorted_by_planned_size(self):
        svg = _lever_realization_svg([
            _b("Small lever", 1_000_000, 900_000),
            _b("Big lever", 9_000_000, 5_000_000),
        ])
        self.assertLess(svg.index("Big lever"), svg.index("Small lever"))

    def test_zero_plan_levers_skipped(self):
        svg = _lever_realization_svg([
            _b("Real", 1_000_000, 800_000),
            _b("Ghost", 0, 100_000),
        ])
        self.assertIn("Real", svg)
        self.assertNotIn("Ghost", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_lever_realization_svg([]), "")
        self.assertEqual(
            _lever_realization_svg([_b("Ghost", 0, 0)]), "")


if __name__ == "__main__":
    unittest.main()
