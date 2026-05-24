"""The /sector-intelligence landing — honest coverage directory.

The six live CMS verticals (Hospitals, Home Health, Hospice, SNF, Dialysis,
IRF, LTCH) link to real routes; every other sector is a clearly-tagged
Roadmap entry with NO link to a not-yet-built page.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.sector_intelligence_page import render_sector_intelligence

_SERVER = Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"


class SectorIntelligencePageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_sector_intelligence()

    def test_renders_with_title(self):
        self.assertIn("ck-page-title", self.html)
        self.assertIn("Sector Intelligence", self.html)

    def test_hospitals_live_with_real_links(self):
        self.assertIn("Hospitals", self.html)
        for route in ("/market-data/map", "/portfolio/map", "/diligence/hcris-xray"):
            self.assertIn(route, self.html)

    def test_live_sectors_link_and_roadmap_sectors_do_not(self):
        # The six live CMS verticals link to real screeners...
        for sector in ("Home Health", "Hospice", "SNF / Nursing Home",
                       "Dialysis", "Inpatient Rehab / IRF",
                       "Long-Term Care Hospital / LTCH", "Dental / DSO"):
            self.assertIn(sector, self.html)
        for route in ('href="/home-health"', 'href="/hospice"',
                      'href="/nursing-homes"', 'href="/dialysis"',
                      'href="/inpatient-rehab"',
                      'href="/long-term-care-hospital"'):
            self.assertIn(route, self.html)
        # ...still-roadmap sectors carry NO link to an unbuilt route.
        self.assertIn("not yet built", self.html)
        for dead in ('href="/dental"', 'href="/outpatient"', 'href="/physician-groups"'):
            self.assertNotIn(dead, self.html)

    def test_data_honesty_labels_present(self):
        # Dental must disclose it's supply-only, not commercial revenue.
        self.assertIn("not observable in CMS data", self.html)
        # Outpatient must disclose Medicare-proxy framing.
        self.assertIn("Commercial volume unobserved", self.html)

    def test_route_wired_in_dispatch(self):
        text = _SERVER.read_text(encoding="utf-8")
        self.assertIn('path == "/sector-intelligence"', text)
        self.assertIn("render_sector_intelligence", text)

    def test_no_external_map_or_cdn(self):
        low = self.html.lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet"):
            self.assertNotIn(bad, low)


if __name__ == "__main__":
    unittest.main()
