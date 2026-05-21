"""Pin for the lever-contribution chart in the EBITDA bridge section.

The bridge table lists per-lever EBITDA $ in row order. The lead chart
ranks levers by absolute impact and draws a proportional bar each, so
the partner reads which RCM levers carry the value creation at a glance.
Green = uplift, red = drag; the full signed table stays below.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace as NS


class BridgeLeverChartTests(unittest.TestCase):
    def _chart(self, impacts):
        from rcm_mc.ui.deal_profile_v2 import _bridge_lever_chart
        return _bridge_lever_chart(impacts)

    def test_one_bar_per_nonzero_lever_sorted(self):
        html = self._chart([
            NS(metric_key="clean_dar", ebitda_impact=2.4e6),
            NS(metric_key="initial_denial_rate", ebitda_impact=1.1e6),
            NS(metric_key="final_writeoff", ebitda_impact=-0.3e6),
        ])
        self.assertIn("Lever contribution", html)
        self.assertEqual(html.count("display:block;width:"), 3)

    def test_sign_colors_uplift_green_drag_red(self):
        html = self._chart([
            NS(metric_key="up", ebitda_impact=2.0e6),
            NS(metric_key="down", ebitda_impact=-1.0e6),
        ])
        self.assertIn("#3F7D4D", html)  # editorial green
        self.assertIn("#A53A2D", html)  # editorial red

    def test_largest_lever_full_width(self):
        # The dominant lever bar should be ~100% width; a tiny one floors
        # at 2% so it still reads as a row.
        html = self._chart([
            NS(metric_key="big", ebitda_impact=10.0e6),
            NS(metric_key="tiny", ebitda_impact=0.05e6),
        ])
        self.assertIn("width:100.0%", html)
        self.assertIn("width:2.0%", html)

    def test_zero_impacts_dropped(self):
        html = self._chart([
            NS(metric_key="real", ebitda_impact=1.0e6),
            NS(metric_key="zero", ebitda_impact=0),
            NS(metric_key="also", ebitda_impact=0.5e6),
        ])
        self.assertEqual(html.count("display:block;width:"), 2)

    def test_empty_below_two_levers(self):
        self.assertEqual(self._chart([NS(metric_key="solo", ebitda_impact=1.0e6)]), "")


if __name__ == "__main__":
    unittest.main()
