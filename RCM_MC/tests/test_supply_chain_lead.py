"""The /supply-chain page leads with the computed savings opportunity.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (savings opportunity + EV uplift) buried as KPIs
#3-4 and in the bottom thesis. This pins that a ck_value_anchor band
now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.supply_chain_page import render_supply_chain


class SupplyChainLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_supply_chain({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("SUPPLY-CHAIN SAVINGS", html)
        self.assertIn("savings opp", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Spend by Category"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Supply Chain Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
