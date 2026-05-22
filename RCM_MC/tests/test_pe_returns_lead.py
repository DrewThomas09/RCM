"""The PE returns page leads with the computed return takeaway.

The page used to open with a dense 6-up KPI grid; the headline
(MOIC/IRR + the dollar gain to LPs) was only readable by scanning the
grid and the Returns Assessment card. This pins that a ck_value_anchor
band now surfaces it at the top, toned by the IRR hurdle.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.pe_returns_page import render_returns_page


class PeReturnsLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        returns = {
            "irr": 0.24, "moic": 2.6, "entry_equity": 120e6,
            "exit_proceeds": 300e6, "hold_years": 5,
            "total_distributions": 312e6,
        }
        covenant = {
            "ebitda": 50e6, "debt": 300e6, "actual_leverage": 6.0,
            "covenant_max_leverage": 7.0, "covenant_headroom_turns": 1.0,
            "ebitda_cushion_pct": 0.14, "covenant_trips_at_ebitda": 43e6,
            "interest_coverage": 2.1,
        }
        return render_returns_page("d1", "Test Deal", returns, covenant)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("PE RETURNS", html)
        self.assertIn("total gain", html)

    def test_anchor_leads_before_assessment_card(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Returns Assessment"),
        )


if __name__ == "__main__":
    unittest.main()
