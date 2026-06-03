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

    def test_comparable_revenue_uses_net_patient_revenue_key(self):
        # Real comps come from an HCRIS row to_dict(), keyed
        # "net_patient_revenue" (not "revenue") — the peer table must show
        # that, not a false "$0M" from a missed key lookup.
        html = render_hospital_profile(
            _hosp("010001", 220.0), None,
            comparables=[{"ccn": "010002", "name": "Peer Med", "beds": 200.0,
                          "net_patient_revenue": 1.5e8}])
        self.assertIn("Peer Med", html)
        self.assertIn("$150M", html)
        self.assertNotIn("$0M", html)


class TestCaduceusScoreNaN(unittest.TestCase):
    def test_score_with_nan_beds_does_not_crash(self):
        # compute_caduceus_score runs in the /hospital route BEFORE the
        # renderer; int(beds) on a NaN crashed it (the real source of the
        # /hospital/<ccn> 500 for no-beds filings).
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
        s = compute_caduceus_score(_hosp("010001", float("nan")))
        self.assertIsNotNone(s)

    def test_score_with_nan_revenue_does_not_render_nan(self):
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
        s = compute_caduceus_score(
            {"ccn": "010001", "beds": float("nan"),
             "net_patient_revenue": float("nan")})
        # the breakdown strings must not contain a literal "nan"
        for v in (getattr(s, "breakdown", {}) or {}).values():
            self.assertNotIn("nan", str(v).lower())


class TestPayerMixNaN(unittest.TestCase):
    def test_unreported_payer_mix_shows_not_reported_not_nan(self):
        # A filing with revenue but no payer-day mix must not render "nan%"
        # (and must not assert a false "100% commercial" by coercing to 0).
        h = _hosp("010001", 220.0)
        h["medicare_day_pct"] = float("nan")
        h["medicaid_day_pct"] = float("nan")
        html = render_hospital_profile(h, None)
        self.assertNotIn("nan%", html.lower())
        self.assertIn("not reported", html.lower())


class TestPartialFilingFullRender(unittest.TestCase):
    def test_real_partial_filing_has_no_formatted_nan(self):
        # A real HCRIS filing with revenue but no bed count drives the full
        # /hospital render path — caduceus score + thesis-card signal bars,
        # where distress_prob came out NaN and rendered "Safety nan%". Assert
        # no *formatted* nan ($nanM / nan% / nanM); plain-word "nan" inside
        # covenant/finance/etc. is fine.
        import re
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
        df = _get_latest_per_ccn()
        partial = df[df["beds"].isna() & df["net_patient_revenue"].notna()]
        if partial.empty:
            self.skipTest("no partial (NaN-beds, real-NPR) filing in current data")
        h = partial.iloc[0].to_dict()
        html = render_hospital_profile(h, compute_caduceus_score(h), hcris_df=df)
        self.assertEqual(
            re.findall(r"\$nan|nan%|nanM|>nan<", html, re.I), [],
            "partial-filing profile must not render a formatted NaN")


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
