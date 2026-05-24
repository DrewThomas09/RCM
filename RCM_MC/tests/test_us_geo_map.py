"""Real geographic US SVG map renderer + vendored Albers path asset.

Replaces the square tile-grid cartogram on the Portfolio Map. Pins: real
per-state SVG paths (not tiles), recognizable geography (state bounding boxes
in the right quadrant), accessibility (svg title/desc + per-state aria-labels),
shading + accent/selected outlines, the same `us-map-select` event the page
wires to, and the absence of any runtime map API.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._us_geo_paths import US_GEO_VIEWBOX, US_STATE_PATHS
from rcm_mc.ui.us_geo_map import render_us_geo_map


def _bbox(d: str):
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", d)]
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


class VendoredAssetTests(unittest.TestCase):
    def test_all_states_plus_dc_present(self):
        for st in ("CA", "TX", "FL", "NY", "ME", "WA", "AK", "HI", "DC"):
            self.assertIn(st, US_STATE_PATHS)
            self.assertTrue(US_STATE_PATHS[st]["d"].startswith("M"))

    def test_geography_is_recognizable(self):
        _, _, W, H = US_GEO_VIEWBOX
        # West coast left, east coast right.
        self.assertLess(_bbox(US_STATE_PATHS["CA"]["d"])[0], W * 0.25)
        self.assertGreater(_bbox(US_STATE_PATHS["ME"]["d"])[2], W * 0.70)
        # North at top (small y), south at bottom (large y).
        self.assertLess(_bbox(US_STATE_PATHS["WA"]["d"])[1], H * 0.30)   # WA north
        self.assertGreater(_bbox(US_STATE_PATHS["FL"]["d"])[3], H * 0.60)  # FL south
        # Florida is a southeast peninsula: right half, lower half.
        fx0, fy0, fx1, fy1 = _bbox(US_STATE_PATHS["FL"]["d"])
        self.assertGreater(fx0, W * 0.45)
        self.assertGreater(fy1, H * 0.55)

    def test_ak_hi_are_bottom_left_insets(self):
        _, _, W, H = US_GEO_VIEWBOX
        for st in ("AK", "HI"):
            x0, y0, x1, y1 = _bbox(US_STATE_PATHS[st]["d"])
            self.assertLess(x0, W * 0.35)        # left
            self.assertGreater(y1, H * 0.60)     # bottom
            self.assertLessEqual(y1, H + 1)      # within canvas


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.html = render_us_geo_map(
            {"TX": 3.0, "FL": 1.0, "WA": 2.0},
            metric_label="deals", accent_states={"FL"},
            accent_label="Certificate-of-Need (CON) state",
            selected_state="TX",
            empty_message="No state-level portfolio data yet.")

    def test_real_paths_not_tiles(self):
        self.assertIn("usgeo-svg", self.html)
        self.assertNotIn("usm-cell", self.html)
        self.assertIn('<path class="usgeo-state" data-state="CA"', self.html)

    def test_accessibility(self):
        self.assertIn('role="img"', self.html)
        self.assertIn("<title", self.html)
        self.assertIn("<desc", self.html)
        self.assertIn('aria-label="Texas — 3 deals"', self.html)
        self.assertIn("no deals data", self.html)   # honest for unrated states

    def test_accent_and_selected_outlines(self):
        self.assertIn("usgeo-accent", self.html)     # FL outlined (CON)
        self.assertIn("usgeo-selected", self.html)   # TX selected
        # The selected/accent classes attach to the right states.
        self.assertRegex(self.html, r'class="usgeo-state usgeo-selected" data-state="TX"')

    def test_legend_and_caveat(self):
        self.assertIn("usgeo-legend", self.html)
        self.assertIn("No data", self.html)
        self.assertIn("Selected state", self.html)
        self.assertIn("usgeo-caveat", self.html)
        self.assertIn("Albers projection", self.html)

    def test_emits_us_map_select_event(self):
        self.assertIn("us-map-select", self.html)

    def test_no_runtime_map_api(self):
        low = self.html.lower()
        for bad in ("mapbox", "leaflet", "maps.googleapis", "unpkg",
                    "jsdelivr", "tile.openstreetmap", "topojson"):
            self.assertNotIn(bad, low)

    def test_empty_state_still_draws_map(self):
        h = render_us_geo_map({}, empty_message="No state-level portfolio data yet.")
        self.assertIn("usgeo-svg", h)
        self.assertIn("No state-level portfolio data yet.", h)


if __name__ == "__main__":
    unittest.main()
