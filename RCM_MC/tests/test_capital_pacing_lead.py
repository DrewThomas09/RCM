"""The /capital-pacing page leads with the computed fund return.

The page used to open with a 10-up KPI strip and several charts/tables,
leaving the headline fund return (TVPI / DPI / net IRR + NAV) buried
as KPIs #7-9 and in the bottom pacing thesis. This pins that a
ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.capital_pacing_page import render_capital_pacing


class CapitalPacingLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_capital_pacing({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("FUND PERFORMANCE", html)
        self.assertIn("TVPI", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Portfolio Investments"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Pacing Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
