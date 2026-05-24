"""Portfolio Map dossier-fidelity guards (handoff: ~/Desktop/portfolio_map_redesign).

The map page was rebuilt into the handoff's editorial dossier layout: a
filter bar, a live 4-cell stats strip, a click-to-select state detail panel,
and a Top Exposures ranking — over the existing geographic tile-grid
cartogram. Every number is real (deal-derived); empty states are honest;
controls without backing data (Sector / Revenue / Headcount) are shown but
disabled, never faked. No external map APIs / CDNs / geocoding.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.portfolio_map import render_portfolio_map

_DEALS = [
    {"deal_id": "d1", "name": "Mercy ASC", "state": "TX", "stage": "diligence"},
    {"deal_id": "d2", "name": "Coastal Rehab", "state": "TX", "stage": "LOI"},
    {"deal_id": "d3", "name": "Gulf Dialysis", "state": "FL", "stage": "IC"},
]
_CON = {"TX": True, "FL": False, "GA": True}


class DossierLayoutTests(unittest.TestCase):
    def setUp(self):
        self.html = render_portfolio_map(_DEALS, con_states=_CON)

    def test_filter_bar_present(self):
        self.assertIn("ck-pm-filters", self.html)
        self.assertIn("CON only", self.html)
        self.assertIn("Search states", self.html)
        self.assertIn("Concentration", self.html)

    def test_controls_without_data_are_disabled_not_faked(self):
        # Sector / Revenue / Headcount have no backing field — rendered but
        # disabled, never wired to fabricated values.
        self.assertIn("no sector tag", self.html.lower())
        self.assertIn("no per-state revenue", self.html.lower())
        self.assertIn("no headcount field", self.html.lower())

    def test_live_stats_strip_real_numbers(self):
        self.assertIn("ck-pm-stats", self.html)
        self.assertIn("Deals mapped", self.html)
        self.assertIn("<em>3</em>", self.html)        # 3 deal-state pairs
        self.assertIn("States · presence", self.html)
        self.assertIn("CON states", self.html)

    def test_top_exposures_ranked_real(self):
        self.assertIn("Top exposures", self.html)
        self.assertIn('data-pm-exp="TX"', self.html)  # TX has 2 deals → rank 1
        self.assertIn(">01.<", self.html)

    def test_detail_panel_and_select_wiring(self):
        self.assertIn("data-pm-detail", self.html)
        self.assertIn("us-map-select", self.html)     # listens to map click
        self.assertIn("Mercy ASC", self.html)         # real deal in JS blob

    def test_actions_safe(self):
        # Add deal routes to the real pipeline; Export/Pivot disabled no-ops.
        self.assertIn('href="/pipeline"', self.html)
        self.assertIn("disabled", self.html)

    def test_copy_is_real_geographic_map_not_tile_grid(self):
        low = self.html.lower()
        # New real-geography language; old tile/cartogram copy must be gone.
        self.assertIn("real geographic shape", low)
        self.assertIn("albers", low)
        self.assertNotIn("equal-size", low)
        self.assertNotIn("cartogram", low)
        # Honest about projection limits.
        self.assertIn("facility-location map", low)

    def test_real_svg_state_paths_present(self):
        # Recognizable geography — actual per-state SVG paths, not square tiles.
        self.assertIn("usgeo-svg", self.html)
        self.assertNotIn("usm-cell", self.html)         # no tile-grid cells
        self.assertIn('<path class="usgeo-state"', self.html)
        for st in ("CA", "TX", "FL", "NY", "ME", "WA"):
            self.assertIn(f'data-state="{st}"', self.html)


class EmptyStateTests(unittest.TestCase):
    def setUp(self):
        self.html = render_portfolio_map([], con_states=_CON)

    def test_honest_empty_states(self):
        self.assertIn("usgeo-svg", self.html)         # map still draws
        self.assertIn("No state-level portfolio data yet", self.html)
        self.assertIn("No exposure to rank yet", self.html)
        self.assertIn("Click a state", self.html)
        # Stats read zero, not invented.
        self.assertIn("<em>0</em>", self.html)


class NoExternalDepsTests(unittest.TestCase):
    def test_no_external_scripts_or_map_apis(self):
        low = render_portfolio_map(_DEALS, con_states=_CON).lower()
        for bad in ("mapbox", "leaflet", "maps.googleapis", "tile.openstreetmap",
                    "unpkg", "react", "babel", "geojson", "portfolio-map.html"):
            self.assertNotIn(bad, low)


if __name__ == "__main__":
    unittest.main()
