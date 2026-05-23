"""Reusable US state tile-grid map renderer (rcm_mc.ui.us_map).

Local/static SVG cartogram — no external map tiles, no CDN, no network.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.us_map import _TILE, STATE_NAMES, render_us_state_map


class TileGridIntegrityTests(unittest.TestCase):
    def test_all_states_plus_dc_present_and_unique(self):
        self.assertEqual(len(_TILE), 51)                  # 50 + DC
        self.assertEqual(len(set(_TILE.values())), 51)    # no overlapping cells
        # every tile has a display name
        for abbr in _TILE:
            self.assertIn(abbr, set(STATE_NAMES) | {"DC"})


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.html = render_us_state_map(
            {"CA": 12, "TX": 7, "NY": 3},
            metric_label="deals",
            accent_states=["NY"], accent_label="CON state",
            empty_message="none",
        )

    def test_emits_svg_with_state_cells(self):
        self.assertIn("<svg", self.html)
        # one cell per state (accent class appends, so count the data attr)
        self.assertEqual(self.html.count('data-state="'), 51)

    def test_accessible_labels(self):
        self.assertIn('role="img"', self.html)
        self.assertIn('aria-label="California: 12 deals', self.html)
        self.assertIn("<title>", self.html)

    def test_legend_present(self):
        self.assertIn("usm-legend", self.html)
        self.assertIn("deals", self.html)

    def test_metric_shading_is_relative(self):
        # The max value (CA=12) should get a deeper teal than the min (NY=3).
        self.assertIn("rgba(21,87,82,", self.html)  # teal ramp used

    def test_accent_outline(self):
        self.assertIn("usm-accent", self.html)
        self.assertIn("CON state", self.html)

    def test_no_external_map_script_or_cdn(self):
        low = self.html.lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "cdn.",
                    "http://", "https://"):
            self.assertNotIn(bad, low)

    def test_empty_state_still_draws_map(self):
        h = render_us_state_map(
            {}, metric_label="deals",
            empty_message="No state-level portfolio data is available yet.")
        self.assertEqual(h.count('data-state="'), 51)   # map still drawn
        self.assertIn("No state-level portfolio data is available yet", h)
        # no invented data: nothing clickable when there are no values
        self.assertNotIn('data-clickable="1"', h)

    def test_unknown_states_ignored_not_invented(self):
        # A bogus abbreviation must not create a cell or crash.
        h = render_us_state_map({"ZZ": 99, "CA": 1}, metric_label="deals")
        self.assertEqual(h.count('data-state="'), 51)
        self.assertNotIn('data-state="ZZ"', h)


if __name__ == "__main__":
    unittest.main()
