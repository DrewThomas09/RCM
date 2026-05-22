"""The /regulatory-risk page leads with the computed exposure.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (EV at risk + remediation cost) buried as KPIs
#6-7 and in the bottom thesis. This pins that a ck_value_anchor band
now surfaces it at the top, toned by the risk score.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.regulatory_risk_page import render_regulatory_risk


class RegulatoryRiskLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_regulatory_risk({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("REGULATORY EXPOSURE", html)
        self.assertIn("EV at risk", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Active Regulatory Events"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Regulatory Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
