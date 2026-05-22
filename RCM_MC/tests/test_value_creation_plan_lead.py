"""The /value-creation-plan page leads with the computed plan value.

The page used to open with an 8-up KPI strip and six charts/tables,
leaving the headline (plan net value + the EV it translates to at
exit) buried as KPI #6 and in the bottom VCP thesis. This pins that a
ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.value_creation_plan_page import (
    render_value_creation_plan,
)


class ValueCreationPlanLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_value_creation_plan({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("net value", html)
        self.assertIn("EV at 11x", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("EBITDA Bridge: Entry"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("VCP Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
