"""The /patient-experience page leads with the computed experience value.

The page used to open with an 8-up KPI strip and several charts/tables,
splitting the headline (PEX composite + EV uplift from improvement)
across KPIs #1/#7 and the bottom thesis. This pins that a
ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.patient_experience_page import (
    render_patient_experience,
)


class PatientExperienceLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_patient_experience({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("EXPERIENCE VALUE", html)
        self.assertIn("EV uplift", html)

    def test_anchor_leads_before_charts_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("NPS Position"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Experience Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
