"""The /tax-structure page leads with the computed tax optimization.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (tax savings + recommended structure) buried as
KPIs #3-4. This pins that a ck_value_anchor band now surfaces it at
the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.tax_structure_page import render_tax_structure


class TaxStructureLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_tax_structure({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("TAX OPTIMIZATION", html)
        self.assertIn("tax savings", html)

    def test_anchor_leads_before_charts(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Purchase Price Allocation"),
        )


if __name__ == "__main__":
    unittest.main()
