"""The /workforce-planning page leads with the computed labor value.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (labor EV impact + turnover cost) buried as KPIs
#7-8. This pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.workforce_planning_page import (
    render_workforce_planning,
)


class WorkforcePlanningLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_workforce_planning({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("LABOR VALUE", html)
        self.assertIn("EV impact", html)

    def test_anchor_leads_before_charts(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Labor Spend by Role"),
        )


if __name__ == "__main__":
    unittest.main()
