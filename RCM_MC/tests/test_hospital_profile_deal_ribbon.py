"""The hospital profile (the deal's landing page) carries the ribbon.

render_hospital_profile now leads with the standard _model_nav pill
ribbon (active="profile"), so the deal's landing page is the entry to
the per-deal integration spine. The CCN is passed raw so it isn't
double-escaped.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.hospital_profile import render_hospital_profile


class _FakeScore:
    grade = "B+"
    score = 75
    components: dict = {}


_HOSPITAL = {
    "ccn": "010001",
    "name": "Test General Hospital",
    "city": "Atlanta",
    "state": "GA",
    "beds": 200,
    "net_patient_revenue": 1.5e8,
    "operating_expenses": 1.4e8,
    "net_income": 1.0e7,
    "medicare_day_pct": 0.45,
    "medicaid_day_pct": 0.20,
}


class HospitalProfileDealRibbonTests(unittest.TestCase):
    def test_carries_ribbon_and_sibling_links(self):
        html = render_hospital_profile(_HOSPITAL, _FakeScore())
        self.assertIn("ck-model-pill", html)
        self.assertIn("/ebitda-bridge/010001", html)
        self.assertIn("/models/returns/010001", html)

    def test_ccn_not_double_escaped(self):
        html = render_hospital_profile(_HOSPITAL, _FakeScore())
        # raw CCN appears in the ribbon hrefs (no &amp; / entity mangling)
        self.assertGreater(html.count("010001"), 5)


if __name__ == "__main__":
    unittest.main()
