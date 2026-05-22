"""The corpus /competitive-intel page leads with a computed takeaway.

The page used to open with an 8-up KPI strip and six charts/tables,
leaving the decision-critical synthesis (roll-up thesis + the dollar
share-shift opportunity) buried in a callout at the very bottom. This
pins that a ck_value_anchor band now surfaces that opportunity at the
top, ahead of the charts and the bottom thesis.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.competitive_intel_page import render_competitive_intel


class CompetitiveIntelLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_competitive_intel(
            {"sector": "Physician Services", "revenue": "80", "share": "0.8"}
        )

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("ROLL-UP OPPORTUNITY", html)
        self.assertIn("addressable", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ROLL-UP OPPORTUNITY"),
            html.index("Competitive Share Landscape"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Competitive Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
