"""The /clinical-outcomes page leads with the computed clinical value.

The page used to open with an 8-up KPI strip and several charts/tables,
splitting the headline (composite quality score + EV impact) across
KPIs #1/#8 and the bottom thesis. This pins that a ck_value_anchor
band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.clinical_outcomes_page import (
    render_clinical_outcomes,
)


class ClinicalOutcomesLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_clinical_outcomes({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("CLINICAL VALUE", html)
        self.assertIn("EV impact", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("MA Star Trajectory"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Clinical Outcomes Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
