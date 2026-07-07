"""Catchment-radius rings on the state-detail pin map (BACKLOG #31 nub).

Pins: the ?radius= value is validated against fixed presets (bogus input
degrades safely to off), rings render ONLY around real-coordinate pins
(one ring per plotted pin — the no-fake-points rule extends to rings),
ring pixel geometry re-derives from the projection's ACTUAL scale (a
hand-computed case at a known latitude is asserted), the control is off
by default (no active ring without the parameter), and the degenerate
single-point view omits rings honestly instead of drawing them at a
fabricated size.
"""
from __future__ import annotations

import math
import re
import unittest
from types import SimpleNamespace

from rcm_mc.data.hospital_coords import coords_for_state
from rcm_mc.ui.us_map import (
    CATCHMENT_RADIUS_PRESETS_MI,
    _fit_projection,
    catchment_ring_px,
    parse_catchment_radius,
    render_state_hospital_points,
)


def _fake(lat, lon, name="Fake General"):
    return SimpleNamespace(lat=lat, lon=lon, facility_name=name, city="")


class ParseCatchmentRadiusTests(unittest.TestCase):
    def test_valid_presets_parse(self):
        self.assertEqual(parse_catchment_radius("15"), 15)
        self.assertEqual(parse_catchment_radius("30"), 30)
        self.assertEqual(parse_catchment_radius(15), 15)
        self.assertEqual(parse_catchment_radius(" 30 "), 30)

    def test_bogus_values_rejected_safely(self):
        for bad in (None, "", "abc", "-15", "15.5", "1e2", "9999", "0",
                    "15;DROP TABLE deals", "15 mi", True, False, 47,
                    10**20, [15], "∞"):
            self.assertIsNone(parse_catchment_radius(bad), repr(bad))

    def test_custom_presets_respected(self):
        self.assertEqual(parse_catchment_radius("60", presets=(60,)), 60)
        self.assertIsNone(parse_catchment_radius("15", presets=(60,)))
        self.assertIsNone(parse_catchment_radius("15", presets=()))


class PixelRadiusMathTests(unittest.TestCase):
    """Hand-computed geometry at a known latitude (central Texas)."""

    P1 = _fake(30.0, -98.0, "South Pin")
    P2 = _fake(32.0, -96.0, "North Pin")

    def test_projection_scale_hand_computed(self):
        # Viewport 480x360, pad 18 -> avail 444x324. Lat span 2 deg binds
        # the height axis: scale = 324 / 2 = 162 px per degree (the width
        # axis would have allowed 444 / (2 * cos 31 deg) ~ 259 px/deg).
        fit = _fit_projection([self.P1, self.P2])
        self.assertAlmostEqual(fit["scale"], 162.0, places=9)
        self.assertAlmostEqual(fit["mean_lat"], 31.0, places=9)
        self.assertFalse(fit["degenerate"])

    def test_ring_px_hand_computed_at_known_latitude(self):
        # 15 statute miles at pin latitude 30N under the equirectangular
        # fit (x compressed by cos of the mean latitude, 31N):
        #   ry = scale * mi / 69.055               (miles per degree lat)
        #   rx = scale * mi / (69.172*cos30) * cos31
        rx, ry = catchment_ring_px(
            15, scale=162.0, mean_lat_deg=31.0, pin_lat_deg=30.0)
        self.assertAlmostEqual(ry, 162.0 * 15 / 69.055, places=9)  # ~35.19 px
        exp_rx = (162.0 * 15 / (69.172 * math.cos(math.radians(30.0)))
                  * math.cos(math.radians(31.0)))
        self.assertAlmostEqual(rx, exp_rx, places=9)               # ~34.77 px
        # Near-circular at mid latitudes — an honest ellipse, not a
        # forced circle (rx != ry because a longitude degree at the pin's
        # own latitude differs slightly from the fit's mean-lat scale).
        self.assertNotAlmostEqual(rx, ry, places=3)
        self.assertLess(abs(rx - ry) / ry, 0.03)

    def test_rendered_ellipse_carries_projection_derived_radii(self):
        pts = [self.P1, self.P2]
        h = render_state_hospital_points(pts, state="TX",
                                         catchment_radius_mi=15)
        fit = _fit_projection(pts)
        rx, ry = catchment_ring_px(
            15, scale=fit["scale"], mean_lat_deg=fit["mean_lat"],
            pin_lat_deg=self.P1.lat)
        self.assertIn(f'rx="{rx:.1f}" ry="{ry:.1f}"', h)


class RingRenderTests(unittest.TestCase):
    def _pts(self, n=4):
        return coords_for_state("TX")[:n]

    def test_default_off_no_active_ring_without_param(self):
        h = render_state_hospital_points(self._pts(), state="TX")
        self.assertIn('value="off" checked>', h)          # Off pre-selected
        self.assertIn('value="15">', h)                   # presets offered...
        self.assertIn('value="30">', h)
        self.assertNotIn('value="15" checked', h)         # ...but not active
        self.assertNotIn('value="30" checked', h)
        self.assertIn(".usm-ring-g{display:none;}", h)    # rings hidden by CSS

    def test_ring_count_equals_real_pin_count_per_preset(self):
        pts = self._pts(5)
        h = render_state_hospital_points(pts, state="TX",
                                         catchment_radius_mi=30)
        for mi in CATCHMENT_RADIUS_PRESETS_MI:
            m = re.search(
                rf'<g class="usm-ring-g" data-mi="{mi}"[^>]*>(.*?)</g>',
                h, re.S)
            self.assertIsNotNone(m, f"missing ring group for {mi} mi")
            self.assertEqual(m.group(1).count("<ellipse"), len(pts))

    def test_no_fake_points_no_fake_rings(self):
        # A facility without a real coordinate gets neither a dot NOR a
        # ring — the no-fake-points rule extends to catchment rings.
        pts = [*self._pts(3), _fake(None, None, "No-Coord Hospital")]
        h = render_state_hospital_points(pts, state="TX",
                                         catchment_radius_mi=15)
        self.assertEqual(h.count("<circle"), 3)           # dots: real pins only
        for mi in CATCHMENT_RADIUS_PRESETS_MI:
            m = re.search(
                rf'<g class="usm-ring-g" data-mi="{mi}"[^>]*>(.*?)</g>',
                h, re.S)
            self.assertEqual(m.group(1).count("<ellipse"), 3)

    def test_pin_dot_count_unchanged_by_rings(self):
        # Rings are <ellipse> elements; the one-<circle>-per-pin invariant
        # (test_hospital_coords) must keep holding with rings enabled.
        pts = self._pts(4)
        h = render_state_hospital_points(pts, state="TX",
                                         catchment_radius_mi=15)
        self.assertEqual(h.count("<circle"), 4)

    def test_active_radius_checks_matching_preset(self):
        h = render_state_hospital_points(self._pts(), state="TX",
                                         catchment_radius_mi=15)
        self.assertIn('value="15" checked>', h)
        self.assertNotIn('value="off" checked', h)

    def test_invalid_active_radius_degrades_to_off(self):
        # 47 is not a preset — the renderer must not invent a 47-mi ring.
        h = render_state_hospital_points(self._pts(), state="TX",
                                         catchment_radius_mi=47)
        self.assertIn('value="off" checked>', h)
        self.assertNotIn('data-mi="47"', h)

    def test_legend_states_radius_and_approximation_caveat(self):
        h = render_state_hospital_points(self._pts(), state="TX",
                                         catchment_radius_mi=15)
        self.assertIn("15-mile straight-line radius", h)
        self.assertIn("30-mile straight-line radius", h)
        self.assertIn("equirectangular approximation", h)
        self.assertIn("not drive time", h)

    def test_degenerate_single_point_omits_rings_honestly(self):
        # One distinct point -> the fit has no real distance scale; a ring
        # would be drawn at a fabricated size. Omit it and say why.
        h = render_state_hospital_points([self._pts(1)[0]], state="TX",
                                         catchment_radius_mi=15)
        self.assertNotIn("<ellipse", h)
        self.assertNotIn("usm-rsel", h)
        self.assertIn("no distance scale", h)
        self.assertEqual(h.count("<circle"), 1)           # pin still plotted

    def test_presets_opt_out_restores_legacy_output(self):
        h = render_state_hospital_points(self._pts(), state="TX",
                                         catchment_presets=())
        self.assertNotIn("usm-rsel", h)
        self.assertNotIn("<ellipse", h)
        self.assertNotIn("Catchment radius", h)

    def test_no_external_calls_with_rings_on(self):
        low = render_state_hospital_points(
            self._pts(), state="TX", catchment_radius_mi=30).lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet",
                    "http://", "https://"):
            self.assertNotIn(bad, low)

    def test_query_param_sync_js_present_and_scoped(self):
        h = render_state_hospital_points(self._pts(), state="TX")
        self.assertIn("URLSearchParams", h)               # ?radius= sync shim
        self.assertIn("replaceState", h)                  # shareable URL
        self.assertNotIn("fetch(", h)                     # no network calls


class StateDetailRadiusParamTests(unittest.TestCase):
    """render_state_detail plumbs the raw ?radius= value through parsing."""

    def test_radius_param_activates_ring_preset(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        h = render_state_detail("TX", radius="15")
        self.assertIn('value="15" checked>', h)
        self.assertIn("<ellipse", h)

    def test_default_render_has_no_active_ring(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        h = render_state_detail("TX")
        self.assertIn('value="off" checked>', h)
        self.assertNotIn('value="15" checked', h)
        self.assertNotIn('value="30" checked', h)

    def test_bogus_radius_degrades_to_off(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        for bad in ("abc", "-15", "99999", "15.5"):
            h = render_state_detail("TX", radius=bad)
            self.assertIn('value="off" checked>', h, repr(bad))
            self.assertNotIn('value="15" checked', h, repr(bad))


if __name__ == "__main__":
    unittest.main()
