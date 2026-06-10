"""Regression: the red gap dot is applied CONSISTENTLY beyond the X-Ray.

Loop step 3 — the same subtle marker on the IC memo (gated occupancy /
net-to-gross) and hospital profile (unreported payer mix / missing beds), so a
partner sees gaps flagged the same way on every page. See ic_memo_page._pct_gap
and hospital_profile.
"""
from __future__ import annotations

import unittest

import pandas as pd

_ARTIFACT = {
    "ccn": "999999", "state": "TX", "name": "ARTIFACT GENERAL",
    "net_patient_revenue": 3e8, "operating_expenses": 2.7e8,
    "gross_patient_revenue": 2e8,            # gross < net → n2g gated → gap
    "beds": 100, "total_patient_days": 85000,
    "bed_days_available": 36600,             # occ ≈ 232% → gated → gap
    "medicare_day_pct": 0.4, "medicaid_day_pct": 0.15,
}
_CLEAN = {**_ARTIFACT, "ccn": "999998", "name": "CLEAN GENERAL",
          "gross_patient_revenue": 7e8, "total_patient_days": 26000}


class IcMemoPctGapTests(unittest.TestCase):
    def test_pct_gap_marks_none(self):
        from rcm_mc.ui.ic_memo_page import _pct_gap
        out = _pct_gap(None)
        self.assertIn("—", out)
        self.assertIn("ck-gap-dot", out)

    def test_pct_gap_clean_value_has_no_dot(self):
        from rcm_mc.ui.ic_memo_page import _pct_gap
        out = _pct_gap(0.42)
        self.assertIn("42.0%", out)
        self.assertNotIn("ck-gap-dot", out)

    def test_ic_memo_marks_gated_occupancy_and_n2g(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        html = render_ic_memo("999999", pd.DataFrame([_ARTIFACT, _CLEAN]))
        # occupancy + net-to-gross both gated to None → two gap dots minimum.
        self.assertGreaterEqual(html.count("ck-gap-dot"), 2)


class HospitalProfilePayerGapTests(unittest.TestCase):
    def test_unreported_payer_mix_is_flagged(self):
        from rcm_mc.ui.hospital_profile import render_hospital_profile
        # A hospital with NaN payer-day mix (not reported on S-3).
        hosp = {
            "ccn": "999000", "name": "NO PAYER MIX HOSP", "state": "TX",
            "city": "Austin", "beds": 120, "net_patient_revenue": 2e8,
            "operating_expenses": 1.9e8, "gross_patient_revenue": 5e8,
            "medicare_day_pct": float("nan"), "medicaid_day_pct": float("nan"),
            "total_patient_days": 30000, "bed_days_available": 43800,
        }
        html = render_hospital_profile(hosp, None, hcris_df=pd.DataFrame([hosp]))
        self.assertIn("not reported", html)
        self.assertIn("ck-gap-dot", html)


if __name__ == "__main__":
    unittest.main()
