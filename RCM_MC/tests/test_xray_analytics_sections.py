"""The CMS X-Ray report surfaces the analytic-depth sections for the six
cross-sector verticals (and omits them for Hospital), in the X-Ray kit.

Covers the UI wiring of the correlation (#646) and expected-vs-actual (#647)
data layers: section presence, honest framing, the coefficient bar, and the
Hospital guard.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.cross_sector import SECTOR_BY_ID
from rcm_mc.data.provider_xray import _hospital_rows
from rcm_mc.ui.provider_xray_page import render_provider_xray

_VERTICALS = ("home-health", "hospice", "nursing-homes", "dialysis",
              "inpatient-rehab", "long-term-care-hospital")

_SECTION_TITLES = ("Performs vs. expectation", "What moves the headline",
                   "Measure correlations")


def _first_ccn(sid: str) -> str:
    return next(iter(SECTOR_BY_ID[sid].providers_loader()))


class AnalyticSectionsPresentTests(unittest.TestCase):
    def test_all_six_verticals_render_three_sections(self):
        for sid in _VERTICALS:
            h = render_provider_xray({"ccn": _first_ccn(sid), "vertical": sid})
            with self.subTest(sid=sid):
                for title in _SECTION_TITLES:
                    self.assertIn(title, h)

    def test_sections_use_the_xray_kit_chrome(self):
        h = render_provider_xray({"ccn": _first_ccn("nursing-homes"),
                                  "vertical": "nursing-homes"})
        self.assertIn('class="xr"', h)         # body opted into the kit
        self.assertIn("xr-ribbon", h)          # navy ribbon section headers
        self.assertIn("ck-xr-coefbar", h)      # standardized-coefficient bar
        self.assertIn("vs. its own measure profile", h)
        self.assertIn("vs. structural peers", h)

    def test_honest_framing_present(self):
        h = render_provider_xray({"ccn": _first_ccn("dialysis"),
                                  "vertical": "dialysis"}).lower()
        self.assertIn("association, not causation", h)
        self.assertIn("not a forecast", h)
        # R-squared and n are exposed for the model
        self.assertIn("r&sup2;=", h)
        self.assertIn("in-sample", h)

    def test_pearson_and_spearman_columns_shown(self):
        h = render_provider_xray({"ccn": _first_ccn("home-health"),
                                  "vertical": "home-health"})
        self.assertIn("Pearson", h)
        self.assertIn("Spearman", h)


class HospitalGuardTests(unittest.TestCase):
    def test_hospital_omits_cross_sector_analytics(self):
        rows = _hospital_rows()
        if not rows:
            self.skipTest("no hospital rows vendored")
        ccn = rows[0].get("ccn") or rows[0].get("provider_id") or ""
        h = render_provider_xray({"ccn": ccn, "vertical": "hospital"})
        for title in _SECTION_TITLES:
            self.assertNotIn(title, h)


if __name__ == "__main__":
    unittest.main()
