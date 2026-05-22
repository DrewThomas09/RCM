"""The /insurance-tracker page leads with the insurance cost exposure.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (annual insurance spend + the transaction deal-
tail cost) buried in the grid and the bottom thesis. This pins that a
ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.insurance_tracker_page import render_insurance


class InsuranceTrackerLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_insurance({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("INSURANCE EXPOSURE", html)
        self.assertIn("annual insurance", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Premium by Coverage Type"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Insurance Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
