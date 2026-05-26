"""Geo Map (/geo-map): a US choropleth cartogram of any real shared-registry
metric. Guards metric validation, that state values are real (never invented),
that the cartogram + drilldown render, and GREEN classification.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.geo_map_page import (
    _DEFAULT_METRIC,
    _parse_metric,
    _state_values,
    render_geo_map,
)


class GeoMapTests(unittest.TestCase):
    def test_parse_metric_validates(self):
        self.assertEqual(_parse_metric({"metric": ["population"]}), "population")
        self.assertEqual(_parse_metric({"metric": ["bogus"]}), _DEFAULT_METRIC)
        self.assertEqual(_parse_metric({}), _DEFAULT_METRIC)

    def test_state_values_are_real(self):
        vals = _state_values("population")
        self.assertGreater(len(vals), 40)            # most states report population
        self.assertIn("CA", vals)
        self.assertGreater(vals["CA"], 30_000_000)   # real CA population
        for v in vals.values():
            self.assertEqual(v, v)                   # no NaN

    def test_page_renders_cartogram_with_drilldown(self):
        h = render_geo_map({"metric": ["uninsured_acs"]})
        self.assertIn("Geo Map", h)
        self.assertIn("/state-profile?state=", h)    # click-through drilldown
        self.assertIn("invented", h)                 # honesty language
        self.assertIn("<svg", h)                     # the cartogram

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/geo-map")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
