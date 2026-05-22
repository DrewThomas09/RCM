"""The /rollup-economics page leads with the computed return.

The page used to open with a 9-up KPI strip and eight charts/tables,
leaving the headline return (base MOIC / IRR + value created) buried
as KPIs #7-8 and in the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.rollup_economics_page import render_rollup_economics


class RollupEconomicsLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_rollup_economics({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("ROLL-UP RETURN", html)
        self.assertIn("MOIC", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ROLL-UP RETURN"),
            html.index("Platform EBITDA Walk"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Roll-Up Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
