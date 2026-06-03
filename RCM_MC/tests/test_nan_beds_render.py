"""Regression: pages that list hospitals must not crash on filings with
no reported bed count (beds = NaN).

HCRIS has 104 of ~6,123 filings with no bed count. Several renderers did
``int(row["beds"])`` directly, which raises ``ValueError: cannot convert
float NaN to integer`` — a live 500. Found by crawling internal links:
``/market-data/state/HI`` (a HI hospital reports no beds) and any
``/hospital/<ccn>`` for one of the 104 (or whose comparables include one).

These tests use synthetic NaN-beds rows so they don't depend on which
specific CCNs happen to have NaN beds in the shipped data. The fixed
renderers keep beds numeric (0) for the rev/bed math but display an
em-dash, never a false "0 beds".
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ui.hospital_profile import render_hospital_profile
from rcm_mc.ui.market_data_page import render_state_detail


def _hosp(ccn: str, beds, *, state: str = "TX", name: str = "Sample Regional"):
    return {
        "ccn": ccn, "name": name, "state": state, "city": "Somewhere",
        "beds": beds, "net_patient_revenue": 1.8e8,
        "operating_expenses": 1.7e8, "net_income": 1e7,
        "medicare_day_pct": 0.45, "medicaid_day_pct": 0.18,
        "gross_patient_revenue": 5.2e8,
    }


class TestHospitalProfileNaNBeds(unittest.TestCase):
    def test_target_with_nan_beds_renders(self):
        # The crashing path: the profile's own hospital reports no beds.
        html = render_hospital_profile(_hosp("010001", float("nan")), None)
        self.assertIn("—", html)               # em-dash, not a crash
        self.assertNotIn(">0 beds", html.replace(" ", ""))  # no false "0 beds"

    def test_comparable_with_nan_beds_renders(self):
        # The other crashing path: a comparable in the peer table has no beds.
        html = render_hospital_profile(
            _hosp("010001", 220.0), None,
            comparables=[{"ccn": "010002", "name": "Peer", "beds": float("nan"),
                          "revenue": 1.4e8}],
        )
        self.assertIn("—", html)

    def test_known_beds_still_render_as_number(self):
        html = render_hospital_profile(_hosp("010001", 240.0), None)
        self.assertIn("240", html)


class TestStateDetailNaNBeds(unittest.TestCase):
    def test_state_with_nan_beds_hospital_renders(self):
        df = pd.DataFrame([
            _hosp("010001", 180.0, state="HI", name="Island Med"),
            _hosp("010002", np.nan, state="HI", name="No-Beds Reported"),
        ])
        html = render_state_detail("HI", df)
        self.assertIn("—", html)               # em-dash for the NaN-beds row
        self.assertIn("Island Med", html)      # the known-beds row still lists


if __name__ == "__main__":
    unittest.main()
