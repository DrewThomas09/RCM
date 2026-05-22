"""The market-analysis page leads with the market-position read.

The page used to open with a 6-up KPI grid; the moat-verdict +
concentration synthesis was only readable from the grid and the
bottom "What This Means" card. This pins that a ck_value_anchor band
now surfaces it at the top, toned by the moat rating.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.market_analysis_page import render_market_analysis_page


class MarketAnalysisLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        analysis = {
            "target": {},
            "market_size": {
                "hospitals": 12, "total_beds": 3400, "total_revenue": 4.2e9,
            },
            "moat": {
                "hhi_index": 2800, "moat_rating": "wide", "moat_score": 8,
                "market_share_rank": 2,
            },
            "competitors": [], "payer_mix_region": {}, "market_trends": {},
        }
        return render_market_analysis_page("d1", "Test Deal", analysis)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("MARKET POSITION", html)
        self.assertIn("moat", html)

    def test_anchor_leads_before_moat_and_what_this_means(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Competitive Moat"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("What This Means"),
        )


if __name__ == "__main__":
    unittest.main()
