"""Home Health + Hospice screener pages (Sector Intelligence Phase 2B)."""
from __future__ import annotations

import unittest

from rcm_mc.ui.home_health_page import render_home_health
from rcm_mc.ui.hospice_page import render_hospice


class HomeHealthPageTests(unittest.TestCase):
    def test_national_view_has_map_summary_provenance(self):
        h = render_home_health({})
        self.assertIn("ck-page-title", h)
        self.assertIn("usgeo-state", h)                     # real US state map
        self.assertIn("by state", h)                       # per-state summary table
        self.assertIn("6jpm-sxkc", h)                      # provenance
        self.assertIn("Medicare-certified agencies only", h)  # limitation
        self.assertIn("/home-health?state=", h)            # drilldown links

    def test_state_view_lists_providers(self):
        h = render_home_health({"state": ["CA"]})
        for col in ("Agency", "CCN", "Star", "Discharge to community"):
            self.assertIn(col, h)
        self.assertIn('<a href="/home-health"', h)         # back to all states

    def test_no_external_calls(self):
        low = render_home_health({}).lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet"):
            self.assertNotIn(bad, low)


class HospicePageTests(unittest.TestCase):
    def test_national_view(self):
        h = render_hospice({})
        self.assertIn("ck-page-title", h)
        self.assertIn("usgeo-state", h)
        self.assertIn("yc9t-dgbk", h)                      # provenance
        self.assertIn("Medicare-certified hospices only", h)
        self.assertIn("/hospice?state=", h)

    def test_state_view_lists_hospices(self):
        h = render_hospice({"state": ["TX"]})
        for col in ("Hospice", "CCN", "Care Index", "Composite process"):
            self.assertIn(col, h)
        self.assertIn('<a href="/hospice"', h)

    def test_not_a_final_recommendation_framing(self):
        # Honest: diligence context, not an investment call.
        self.assertIn("not a final investment recommendation",
                      render_hospice({}).lower())


if __name__ == "__main__":
    unittest.main()
