"""The per-deal dashboard hub leads with a deal snapshot.

The hub opened with a 4-up KPI grid; the deal's scale (EV) and the
recoverable-EBITDA opportunity were KPIs #3-4, and EV otherwise only
appeared inline on a model tile. This pins that a ck_value_anchor band
now orients the partner with EV + recoverable EBITDA at the very top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.deal_dashboard import render_deal_dashboard


class DealDashboardLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        profile = {
            "name": "Test Deal", "state": "TX", "net_revenue": 4.0e8,
            "ebitda_margin": 0.12, "bed_count": 300, "denial_rate": 14.0,
        }
        return render_deal_dashboard("d1", profile)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DEAL SNAPSHOT", html)
        self.assertIn("recoverable EBITDA", html)

    def test_anchor_leads_before_explainer(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Every analysis on this deal"),
        )


if __name__ == "__main__":
    unittest.main()
