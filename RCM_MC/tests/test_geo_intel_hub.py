"""Geographic Intelligence hub (/geo-intel): the top-nav landing that ties the
real-data state trio together. Guards that the hub links all three modes, is a
GREEN surface, sits in the Source nav section, and stays in the palette.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui._chartis_kit import _SUB_SECTION_MAP, _resolve_sub_section
from rcm_mc.ui.data_public.geo_intel_page import render_geo_intel


class GeoIntelHubTests(unittest.TestCase):
    def test_hub_links_all_three_modes(self):
        h = render_geo_intel()
        self.assertIn("Geographic Intelligence", h)
        for route in ("/state-compare", "/state-rankings", "/state-profile"):
            self.assertIn(route, h)

    def test_hub_is_green(self):
        self.assertEqual(classify_surface("/geo-intel")["tier"], "green")

    def test_trio_routes_resolve_to_source_section(self):
        for route in ("/geo-intel", "/state-compare", "/state-rankings",
                      "/state-profile"):
            self.assertEqual(_SUB_SECTION_MAP.get(route), "source", route)
            self.assertEqual(_resolve_sub_section(route), "source", route)


if __name__ == "__main__":
    unittest.main()
