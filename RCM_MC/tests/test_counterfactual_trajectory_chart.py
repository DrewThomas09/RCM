"""Pin for the actual-vs-counterfactual trajectory chart on
/models/counterfactual/<deal_id>.

Adds a line chart of the two EBITDA trajectories with the
attributable impact area shaded above the existing period-by-period
table. Partners see "the initiative's value-creation curve"
without reading the table.
"""
from __future__ import annotations

import unittest


class CounterfactualTrajectoryChartTests(unittest.TestCase):
    def test_renders_two_lines_and_shaded_area(self):
        from rcm_mc.ui.analytics_pages import (
            _counterfactual_trajectory_chart,
        )
        svg = _counterfactual_trajectory_chart(
            actual=[10e6, 12e6, 14e6, 16e6, 18e6],
            counter=[10e6, 10.5e6, 11e6, 11.5e6, 12e6],
        )
        self.assertTrue(svg.startswith("<svg"))
        # 2 lines (actual solid + counter dashed)
        self.assertEqual(svg.count("<path"), 2)
        # 1 shaded polygon
        self.assertEqual(svg.count("<polygon"), 1)
        # Legend
        self.assertIn(">Actual</text>", svg)
        self.assertIn(">Counterfactual</text>", svg)

    def test_positive_cumulative_renders_green(self):
        # Actual higher than counter → green
        from rcm_mc.ui.analytics_pages import (
            _counterfactual_trajectory_chart,
        )
        svg = _counterfactual_trajectory_chart(
            actual=[10e6, 12e6, 14e6],
            counter=[10e6, 10e6, 10e6],
        )
        self.assertIn("#0a8a5f", svg)

    def test_negative_cumulative_renders_red(self):
        # Actual below counter → red
        from rcm_mc.ui.analytics_pages import (
            _counterfactual_trajectory_chart,
        )
        svg = _counterfactual_trajectory_chart(
            actual=[10e6, 9e6, 8e6],
            counter=[10e6, 11e6, 12e6],
        )
        self.assertIn("#b5321e", svg)

    def test_returns_empty_for_mismatched_lengths(self):
        from rcm_mc.ui.analytics_pages import (
            _counterfactual_trajectory_chart,
        )
        self.assertEqual(
            _counterfactual_trajectory_chart([1.0, 2.0], [1.0]), "",
        )

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.analytics_pages import (
            _counterfactual_trajectory_chart,
        )
        self.assertEqual(_counterfactual_trajectory_chart([], []), "")


if __name__ == "__main__":
    unittest.main()
