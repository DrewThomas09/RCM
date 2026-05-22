"""The demand-analysis page leads with the demand-profile read.

The page used to open with a 4-up KPI grid; the demand-pull verdict
(structural density + stickiness + pricing power) was only readable
from the grid and the bottom "What This Means for Diligence" card.
This pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.demand_page import render_demand_analysis


class DemandLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        profile = {
            "ccn": "010001", "hospital_name": "Test", "county": "Cook",
            "state": "IL", "disease_density_index": 72,
            "stickiness_score": 68, "price_elasticity": -0.15,
            "tailwind_score": 14,
        }
        return render_demand_analysis(profile)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DEMAND PROFILE", html)
        self.assertIn("disease density", html)

    def test_anchor_leads_before_diligence_card(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("What This Means for Diligence"),
        )


if __name__ == "__main__":
    unittest.main()
