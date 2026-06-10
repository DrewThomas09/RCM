"""Workstream H — composite demo deals anchored to real, named facilities.

The fictional demo deals carry a facility_anchor naming a REAL CCN whose
filed HCRIS financials (ACTUAL, sourced, X-Ray-linked) ground the deal,
while the RCM metrics stay labeled illustrative (HCRIS files no
denial/collection fields). Quick view must render both honestly, and must
flatten nested observed_metrics instead of claiming "no metrics".
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.deal_quick_view import render_deal_quick_view

_PROFILE = {
    "name": "Cypress Crossing Health",
    "ccn": "240004", "state": "MN",
    "rcm_metrics_basis": "illustrative-demo",
    "observed_metrics": {
        "denial_rate": {"value": 14.2, "quality_flags": []},
        "days_in_ar": {"value": 58.4, "quality_flags": []},
    },
    "facility_anchor": {
        "ccn": "240004", "name": "HENNEPIN COUNTY MEDICAL CENTER",
        "state": "MN", "fiscal_year": 2022, "beds": 335.0,
        "net_patient_revenue": 1.194e9, "operating_margin": -0.112,
        "source": "CMS HCRIS (latest authoritative filing)",
    },
}


class AnchorPanelTests(unittest.TestCase):
    def test_anchor_renders_actual_and_links_xray(self):
        h = render_deal_quick_view("ccf", _PROFILE)
        self.assertIn("Composite demo deal", h)
        self.assertIn("HENNEPIN COUNTY MEDICAL CENTER", h)
        self.assertIn("hcris-xray?ccn=240004", h)
        self.assertIn(">ACTUAL</span>", h)
        self.assertIn("-11.2% operating margin", h)

    def test_rcm_metrics_labeled_illustrative(self):
        h = render_deal_quick_view("ccf", _PROFILE)
        self.assertIn("illustrative demo values", h)
        self.assertIn("ENTERED", h)        # the profile-metrics basis badge

    def test_nested_observed_metrics_flattened(self):
        # Used to render "No profile metrics yet" while the nested values
        # sat right there.
        h = render_deal_quick_view("ccf", _PROFILE)
        self.assertIn("14.2%", h)
        self.assertNotIn("No profile metrics yet", h)

    def test_no_anchor_no_panel(self):
        prof = {k: v for k, v in _PROFILE.items() if k != "facility_anchor"}
        h = render_deal_quick_view("ccf", prof)
        self.assertNotIn("Composite demo deal", h)


class SeederAnchorTests(unittest.TestCase):
    def test_demo_seeder_carries_anchor_map(self):
        # The seeder names its real anchors in code with the selection
        # rationale — pin the map so a rename/retag is a conscious act.
        src = open("demo.py").read()
        for ccn in ("240004", "050039", "330182", "500129", "330304"):
            self.assertIn(ccn, src)
        self.assertIn("facility_anchor", src)
        self.assertIn("illustrative-demo", src)


if __name__ == "__main__":
    unittest.main()
