"""The value-creation playbook leads with the 100-day-plan value.

render_playbook used to open with a legacy 2-up KPI grid; the headline
(total EBITDA impact + the equity value it creates at exit) was only
readable from the grid and the bottom "What This Means" card. This
pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.diligence_page import render_playbook


class PlaybookLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        entries = [
            {"title": "Denial workflow", "category": "RCM",
             "priority": "high", "ebitda_impact": 2_000_000,
             "timeline": "Q1", "owner": "COO"},
            {"title": "Coding/CDI", "category": "RCM",
             "priority": "medium", "ebitda_impact": 1_200_000,
             "timeline": "Q2", "owner": "CFO"},
        ]
        return render_playbook("d1", "Test Deal", entries)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("100-DAY PLAN VALUE", html)
        self.assertIn("equity value at 11x", html)

    def test_anchor_leads_before_playbook_and_what_this_means(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Value Creation Playbook"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("What This Means"),
        )


if __name__ == "__main__":
    unittest.main()
