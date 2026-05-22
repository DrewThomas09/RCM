"""The denial-driver page leads with the computed recovery opportunity.

The page used to open with a 4-up KPI grid; the headline (recoverable
EBITDA from moving the denial rate to target) was buried as KPI #3 and
in the "What This Means" card. This pins that a ck_value_anchor band
now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.denial_page import render_denial_page


class DenialLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        analysis = {
            "summary": {
                "total_annual_impact": 4_500_000,
                "current_denial_rate": 14.0,
                "target_denial_rate": 9.0,
            },
            "drivers": [
                {"driver": "Eligibility", "contribution_pct": 30,
                 "annual_impact": 1.5e6, "severity": "high"},
            ],
            "recommendations": [],
        }
        return render_denial_page("d1", "Test Deal", analysis)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DENIAL RECOVERY", html)
        self.assertIn("recoverable EBITDA", html)

    def test_anchor_leads_before_root_causes(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Denial Root Causes"),
        )


if __name__ == "__main__":
    unittest.main()
