"""The /drug-pricing-340b page leads with the computed program value.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (340B ceiling savings + program margin) buried as
KPIs #3-4 and in the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.drug_pricing_340b_page import (
    render_drug_pricing_340b,
)


class DrugPricing340bLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_drug_pricing_340b({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("340B PROGRAM VALUE", html)
        self.assertIn("ceiling savings", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Drug Category Savings Map"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("340B Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
