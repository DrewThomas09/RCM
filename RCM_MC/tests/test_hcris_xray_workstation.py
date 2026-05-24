"""HCRIS X-Ray input redesign — B · Workstation (handoff design_handoff_xray).

The landing page is the two-up workstation built on the shared xray_kit:
intake form (Identify + Peer engine + Run X-Ray) on the left, a clearly-
LABELLED SAMPLE preview on the right. The search/CCN engine path is unchanged.
No fabricated values leak as real; the sample is explicitly marked sample.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page


class WorkstationLandingTests(unittest.TestCase):
    def setUp(self):
        self.html = render_hcris_xray_page(qs={})

    def test_two_up_intake(self):
        self.assertIn("xr-ws", self.html)            # two-up grid
        self.assertIn("① Identify", self.html)
        self.assertIn("② Peer engine", self.html)
        self.assertIn("▸ Run X-Ray", self.html)

    def test_fy_segmented_and_peer_engine_fields(self):
        self.assertIn('name="fiscal_year"', self.html)
        self.assertIn("FY2022", self.html)
        self.assertIn('name="peer_k"', self.html)
        self.assertIn('name="bed_band_pct"', self.html)
        # Identify field preserved (engine path unchanged).
        self.assertIn('name="q"', self.html)

    def test_sample_is_labelled_not_real(self):
        self.assertIn("Sample output", self.html)
        self.assertIn("Illustrative SAMPLE", self.html)
        self.assertIn("nothing here is your target", self.html)

    def test_uses_kit_and_no_external_scripts(self):
        self.assertIn("--xr-navy:#0d2336", self.html)   # xray_kit tokens
        self.assertIn("xr-band", self.html)             # peer-band visual
        low = self.html.lower()
        for bad in ("unpkg", "react", "babel", "cdn.jsdelivr"):
            self.assertNotIn(bad, low)


class ResultsPathPreservedTests(unittest.TestCase):
    def test_ccn_path_still_renders_engine_report(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        ccn = str(_get_latest_per_ccn().iloc[0]["ccn"])
        html = render_hcris_xray_page(qs={"ccn": [ccn]})
        # The real engine report still renders (target card markup present).
        self.assertIn("hx-", html)
        self.assertGreater(len(html), 5000)


if __name__ == "__main__":
    unittest.main()
