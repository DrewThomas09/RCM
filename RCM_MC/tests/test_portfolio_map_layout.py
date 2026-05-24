"""Portfolio Map cartogram layout (handoff visual fix).

The square-ish tile grid was re-coordinated to the design handoff's
geographic-ish layout so the cartogram reads as the US: Florida nests under
SC/GA in the SE (no "floating Florida"), Texas sits south under Oklahoma,
New England nests in the NE corner. Pure layout/visual fix — data plumbing
unchanged, no external map tiles/scripts.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.us_map import _TILE, render_us_state_map


class CartogramLayoutTests(unittest.TestCase):
    def test_all_states_plus_dc_present_and_unique(self):
        self.assertEqual(len(_TILE), 51)                 # 50 states + DC
        self.assertEqual(len(set(_TILE.values())), 51)   # no overlapping cells

    def test_florida_attached_southeast_not_floating(self):
        # FL must sit directly under SC/GA, not offset into open space.
        self.assertEqual(_TILE["FL"], (6, 8))
        self.assertEqual(_TILE["GA"], (6, 7))
        self.assertEqual(_TILE["SC"], (5, 7))
        fl_r, fl_c = _TILE["FL"]
        ga_r, ga_c = _TILE["GA"]
        sc_r, sc_c = _TILE["SC"]
        # FL is east-adjacent to GA on the same southern row (attached, not
        # floating) and sits one row below the SC tile.
        self.assertEqual(fl_r, ga_r)
        self.assertEqual(fl_c, ga_c + 1)
        self.assertEqual(fl_r, sc_r + 1)

    def test_texas_south_under_oklahoma(self):
        self.assertEqual(_TILE["OK"], (6, 3))
        self.assertEqual(_TILE["TX"], (7, 3))            # same column, row below
        # TX is in the southern band and west of the southeast cluster.
        self.assertGreater(_TILE["TX"][0], _TILE["GA"][0] - 1)
        self.assertLess(_TILE["TX"][1], _TILE["FL"][1])

    def test_new_england_nests_northeast(self):
        # NE corner: high column (east), low row (north).
        for st in ("ME", "NH", "VT", "MA"):
            r, c = _TILE[st]
            self.assertLessEqual(r, 2, f"{st} should be northern")
            self.assertGreaterEqual(c, 9, f"{st} should be eastern")

    def test_west_coast_steps_down_left_edge(self):
        # WA/OR/CA all in column 0, north→south.
        self.assertEqual(_TILE["WA"][1], 0)
        self.assertEqual(_TILE["OR"][1], 0)
        self.assertEqual(_TILE["CA"][1], 0)
        self.assertLess(_TILE["WA"][0], _TILE["OR"][0])
        self.assertLess(_TILE["OR"][0], _TILE["CA"][0])


class CartogramRenderTests(unittest.TestCase):
    def test_renders_cells_with_accessible_names(self):
        html = render_us_state_map({"TX": 5, "FL": 3, "CA": 2},
                                   metric_label="deals")
        self.assertIn("usm-cell", html)
        self.assertIn(">TX<", html)
        self.assertIn(">FL<", html)
        # State full names are available for accessibility (tooltips/aria).
        self.assertIn("Texas", html)

    def test_empty_map_blends_neutral(self):
        # No-data cells use the neutral cream so empty cells don't read as a
        # separate bright block.
        html = render_us_state_map({}, metric_label="deals")
        self.assertIn("#ece3cb", html)

    def test_no_external_map_tiles_or_cdn(self):
        html = render_us_state_map({"TX": 1}, metric_label="deals")
        low = html.lower()
        for bad in ("mapbox", "leaflet", "googleapis/maps", "maps.googleapis",
                    "tile.openstreetmap", "unpkg", "geojson", "portfolio-map.html"):
            self.assertNotIn(bad, low)


if __name__ == "__main__":
    unittest.main()
