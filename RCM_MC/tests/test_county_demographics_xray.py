"""Service-area demographics — county ACS join on the HCRIS X-Ray.

The commercial context a target's own filings can't give: payer-mix demand
(65+, income), bad-debt risk (uninsured), access (rural). Joined via the
facility's geocoded county; EXACT name-match only — an ungeocoded/unmatched
facility shows no panel (never a guessed county).
"""
from __future__ import annotations

import unittest

from rcm_mc.data.county_demographics import (
    _norm_county, demographics_for_ccn,
)


class ResolverTests(unittest.TestCase):
    def test_methodist_resolves_to_harris_county(self):
        d = demographics_for_ccn("450358")
        self.assertTrue(d)
        self.assertEqual(d["state"], "TX")
        self.assertIn("Harris", d["county_name"])
        # plausible big-metro figures
        self.assertGreater(d["population"], 1_000_000)
        self.assertTrue(0 < d["pct_age_65_plus"] < 1)

    def test_unknown_ccn_returns_empty(self):
        self.assertEqual(demographics_for_ccn("000000"), {})

    def test_norm_county_bridges_label_gaps(self):
        self.assertEqual(_norm_county("DeKalb County"), _norm_county("DE KALB"))
        self.assertEqual(_norm_county("Harris County"), "HARRIS")
        self.assertEqual(_norm_county("St. Louis City"), "ST.LOUISCITY")


class XrayPanelTests(unittest.TestCase):
    def test_panel_renders_with_cdd_lens_and_source(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})
        self.assertIn("Service-area demographics", h)
        self.assertIn("Harris County", h)
        self.assertIn("Medicare-demand proxy", h)   # CDD lens
        self.assertIn("bad-debt", h)
        self.assertIn("Census/ACS", h)               # sourced
        # honesty: service-area, not the target's patients
        self.assertIn("not the target", h.replace("\n", " "))


if __name__ == "__main__":
    unittest.main()


class HealthBurdenLineTests(unittest.TestCase):
    """The demographics panel adds a state-level CDC PLACES chronic-disease
    burden line (a real acute-demand signal), labeled state-level and
    skipping NaN measures."""

    def test_burden_line_renders_with_disease_prevalence(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})
        self.assertIn("Community health burden", h)
        self.assertIn("diabetes", h)
        self.assertIn("obesity", h)
        self.assertIn("CDC PLACES", h)
        self.assertIn("state-level", h)   # granularity stated
