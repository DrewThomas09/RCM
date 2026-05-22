"""The /deal-origination page leads with the computed pipeline value.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (weighted + total active pipeline EV) buried as
KPIs #1-2 and in the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.deal_origination_page import (
    render_deal_origination,
)


class DealOriginationLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_deal_origination({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("ORIGINATION PIPELINE", html)
        self.assertIn("weighted pipeline", html)

    def test_anchor_leads_before_funnel_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Sourcing Funnel"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Origination Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
