"""The market-analysis page leads with the market-position read.

The page used to open with a 6-up KPI grid; the moat-verdict +
concentration synthesis was only readable from the grid and the
bottom "What This Means" card. This pins that a ck_value_anchor band
now surfaces it at the top, toned by the moat rating.
"""
from __future__ import annotations

import re
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


class MarketAnalysisNaNTests(unittest.TestCase):
    """Regression: a deal with no market geography yields an NaN HHI.

    ``moat.get('hhi_index', 0)`` did not catch it (the key exists, the
    value is nan), so the page rendered the literal 'HHI nan' / 'HHI: nan'
    in the KPI, badge, and the 'What This Means' prose. A non-finite HHI
    must read as unknown instead.
    """

    def _html(self) -> str:
        analysis = {
            "target": {},
            "market_size": {"hospitals": 0, "total_beds": 0},
            "moat": {"hhi_index": float("nan"), "moat_rating": "none",
                     "moat_score": 0},
            "competitors": [], "payer_mix_region": {}, "market_trends": {},
        }
        return render_market_analysis_page("d1", "Test Deal", analysis)

    def test_no_literal_nan_leaks(self):
        html = self._html()
        # Strip scripts/styles (isNaN(...) lives in the JS shim).
        body = re.sub(r"<script\b[^>]*>.*?</script>", " ", html,
                      flags=re.S | re.I)
        body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body,
                      flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", body)
        self.assertNotRegex(text, r"\bnan\b|NaN")

    def test_unknown_hhi_reads_as_na(self):
        html = self._html()
        self.assertIn("n/a", html)
        self.assertIn("Unknown", html)

    def test_finite_hhi_still_formats(self):
        analysis = {
            "target": {}, "market_size": {"hospitals": 5, "total_beds": 100},
            "moat": {"hhi_index": 2800, "moat_rating": "wide",
                     "moat_score": 8},
            "competitors": [], "payer_mix_region": {}, "market_trends": {},
        }
        html = render_market_analysis_page("d1", "T", analysis)
        self.assertIn("2,800", html)
        self.assertIn("Concentrated", html)


if __name__ == "__main__":
    unittest.main()
