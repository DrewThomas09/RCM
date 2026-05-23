"""Vendored hospital CCN -> lat/lon crosswalk + point-map renderer.

Coordinates come from a ONE-TIME offline geocode (US Census) of public CMS
addresses; the app reads only the local file. Tests pin: real coordinates
load + join by CCN, no point is invented without a coordinate, provenance
is carried, and rendering makes no external map calls.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.hospital_coords import (
    HospitalCoord,
    coords_for_state,
    coords_provenance,
    load_hospital_coords,
)
from rcm_mc.ui.us_map import render_state_hospital_points


class CrosswalkLoaderTests(unittest.TestCase):
    def setUp(self):
        self.coords = load_hospital_coords()

    def test_crosswalk_loads_real_coordinates(self):
        self.assertGreater(len(self.coords), 3000)   # ~4,630 vendored
        any_c = next(iter(self.coords.values()))
        self.assertIsInstance(any_c, HospitalCoord)
        self.assertTrue(any_c.source)                 # provenance present
        self.assertTrue(any_c.source_date)

    def test_keyed_by_ccn_and_coordinates_are_floats(self):
        for ccn, c in list(self.coords.items())[:50]:
            self.assertEqual(ccn, c.ccn)
            self.assertIsInstance(c.lat, float)
            self.assertIsInstance(c.lon, float)
            # continental-US-ish + AK/HI sanity envelope
            self.assertTrue(17.0 <= c.lat <= 72.0, c.lat)
            self.assertTrue(-180.0 <= c.lon <= -64.0, c.lon)

    def test_coords_for_state_filters_and_is_in_range(self):
        ca = coords_for_state("CA")
        self.assertGreater(len(ca), 50)
        self.assertTrue(all(c.state == "CA" for c in ca))
        # every CA point sits inside California's lat/lon envelope
        self.assertTrue(all(32.0 <= c.lat <= 42.5 for c in ca))
        self.assertTrue(all(-125.0 <= c.lon <= -114.0 for c in ca))

    def test_provenance_string(self):
        prov = coords_provenance()
        self.assertIsNotNone(prov)
        self.assertIn("Census", prov)
        self.assertIn("as of", prov)


class PointRendererTests(unittest.TestCase):
    def _pts(self, n=3):
        return coords_for_state("TX")[:n]

    def test_emits_svg_points_with_provenance(self):
        pts = self._pts(5)
        h = render_state_hospital_points(
            pts, state="TX", total_in_state=10, provenance=coords_provenance())
        self.assertIn("<svg", h)
        self.assertEqual(h.count("<circle"), len(pts))   # one dot per point
        self.assertIn("Source:", h)
        self.assertIn("Census", h)

    def test_honest_count_note(self):
        pts = self._pts(3)
        h = render_state_hospital_points(pts, state="TX", total_in_state=9)
        self.assertIn("Showing 3 geocoded hospital locations of 9 in TX", h)
        self.assertIn("not plotted", h)   # names the hospitals it can't plot

    def test_no_points_without_coordinates_empty_state(self):
        h = render_state_hospital_points([], state="WY")
        self.assertNotIn("<circle", h)
        self.assertIn("No geocoded hospital locations available for WY", h)

    def test_no_external_map_calls(self):
        low = render_state_hospital_points(self._pts(4), state="TX").lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "http://", "https://"):
            self.assertNotIn(bad, low)

    def test_accessible_labels(self):
        h = render_state_hospital_points(self._pts(2), state="TX")
        self.assertIn('role="img"', h)
        self.assertIn("aria-label=", h)
        self.assertIn("<title>", h)


if __name__ == "__main__":
    unittest.main()
