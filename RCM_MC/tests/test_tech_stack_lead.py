"""The /tech-stack page leads with the computed IT EV uplift.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (IT EV uplift + modernization investment) buried
as KPIs #7-8 and in the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.tech_stack_page import render_tech_stack


class TechStackLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_tech_stack({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("IT VALUE", html)
        self.assertIn("EV uplift", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("System Modernness Heatmap"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Tech Stack Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
