"""The /working-capital page leads with the computed cash unlock.

The page used to open with an 8-up KPI strip and four charts/tables,
leaving the load-bearing number (the one-time AR cash unlock + ongoing
FCF uplift) buried as KPI #7 and in the bottom thesis callout. This
pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.working_capital_page import render_working_capital


class WorkingCapitalLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_working_capital({"sector": "Physician Services"})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("WORKING-CAPITAL UNLOCK", html)
        self.assertIn("ongoing FCF", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("WORKING-CAPITAL UNLOCK"),
            html.index("DSO Trajectory"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Working Capital Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
