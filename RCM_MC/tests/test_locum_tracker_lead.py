"""The /locum-tracker page leads with the locum exposure + opportunity.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (locum spend burden + the permanent-conversion
savings opportunity) split across the grid and the bottom thesis. This
pins that a ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.locum_tracker_page import render_locum_tracker


class LocumTrackerLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_locum_tracker({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("LOCUM EXPOSURE", html)
        self.assertIn("conversion savings/yr", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Coverage Gap Inventory"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Workforce Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
