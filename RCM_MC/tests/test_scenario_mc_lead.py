"""The /scenario-mc page leads with the computed Monte Carlo outcome.

The page used to open with an 8-up KPI strip and six charts/tables,
leaving the headline (median MOIC, the P5->P95 band, and the
probability of clearing 2x) buried mid-strip and in the bottom thesis.
This pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.scenario_mc_page import render_scenario_mc


class ScenarioMcLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_scenario_mc({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("MONTE CARLO OUTCOME", html)
        self.assertIn("median MOIC", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("MOIC Outcome Distribution"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Monte Carlo Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
