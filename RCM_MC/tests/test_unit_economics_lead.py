"""The /unit-economics page leads with the computed de-novo return.

The page used to open with an 8-up KPI strip and six charts/tables,
leaving the headline new-site return (de novo IRR + payback) buried
as KPIs #5-6 and in the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.unit_economics_page import render_unit_economics


class UnitEconomicsLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_unit_economics({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DE NOVO RETURN", html)
        self.assertIn("IRR", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("DE NOVO RETURN"),
            html.index("New Site Ramp Curve"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Unit Economics Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
