"""The returns-waterfall page leads with the computed split takeaway.

The page used to open with a 5-up KPI grid; the load-bearing read —
gross MOIC/IRR plus the dollars that actually reach LPs vs GP carry —
was only readable from the grid and the LP/GP split card. This pins
that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.waterfall_page import render_waterfall_page


class WaterfallLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        result = {
            "lp_total": 260e6, "gp_total": 40e6, "lp_moic": 2.4,
            "gp_moic": 3.0, "lp_irr": 0.21, "gross_moic": 2.6,
            "gross_irr": 0.24, "invested": 120e6, "exit_proceeds": 300e6,
            "hold_years": 5, "tiers": [],
        }
        return render_waterfall_page("d1", "Test Deal", result)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("RETURNS WATERFALL", html)
        self.assertIn("to LPs", html)

    def test_anchor_leads_before_split_card(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("LP / GP Split"),
        )


if __name__ == "__main__":
    unittest.main()
