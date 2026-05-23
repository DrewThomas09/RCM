"""/market-data/map reuses the local US state tile-grid (Phase 1B).

The page already aggregates real HCRIS data per state; the tile map shades
states by the selected metric while the existing heatmap table is kept.
The map renders only when state data exists — never forced/fabricated.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.market_data_page import render_market_data


def _hcris():
    return pd.DataFrame([
        {"state": "CA", "beds": 200, "net_patient_revenue": 5e8,
         "operating_expenses": 4.6e8, "medicare_day_pct": 0.40,
         "medicaid_day_pct": 0.20},
        {"state": "CA", "beds": 150, "net_patient_revenue": 3e8,
         "operating_expenses": 2.7e8, "medicare_day_pct": 0.45,
         "medicaid_day_pct": 0.18},
        {"state": "TX", "beds": 300, "net_patient_revenue": 7e8,
         "operating_expenses": 6.5e8, "medicare_day_pct": 0.50,
         "medicaid_day_pct": 0.15},
    ])


class MarketDataMapTests(unittest.TestCase):
    def test_state_map_renders_with_data(self):
        html = render_market_data(_hcris(), metric="avg_margin")
        self.assertIn("usm-cell", html)              # tile-grid present
        self.assertIn("State Map", html)             # map panel title
        self.assertIn("California:", html)           # real state shaded

    def test_existing_heatmap_table_preserved(self):
        html = render_market_data(_hcris(), metric="hospitals")
        self.assertIn("State Market Heatmap", html)  # table panel kept
        self.assertIn("usm-cell", html)

    def test_map_not_forced_when_no_state_data(self):
        html = render_market_data(pd.DataFrame(), metric="avg_margin")
        self.assertNotIn("State Map ·", html)        # no forced/empty map panel
        self.assertGreater(len(html), 500)           # page still renders

    def test_no_external_map_dependency(self):
        low = render_market_data(_hcris(), metric="hhi").lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet"):
            self.assertNotIn(bad, low)

    def test_state_cells_drill_into_state_detail(self):
        html = render_market_data(_hcris(), metric="hospitals")
        self.assertIn('data-href="/market-data/state/CA"', html)
        # honest tile-grid disclosure
        self.assertIn("cells represent states, not geographic area", html)


class StateDetailHospitalPointsTests(unittest.TestCase):
    """/market-data/state/<ST> plots geocoded hospital points (join by CCN)."""

    def _ca_hcris(self, n=4, with_uncoded=True):
        from rcm_mc.data.hospital_coords import coords_for_state
        rows = [{"state": "CA", "ccn": c.ccn, "name": c.facility_name,
                 "beds": 100, "net_patient_revenue": 2e8,
                 "operating_expenses": 1.8e8}
                for c in coords_for_state("CA")[:n]]
        if with_uncoded:
            rows.append({"state": "CA", "ccn": "999999", "name": "No-Coord",
                         "beds": 50, "net_patient_revenue": 1e8,
                         "operating_expenses": 9e7})
        return pd.DataFrame(rows)

    def test_geocoded_hospitals_are_plotted(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        html = render_state_detail("CA", self._ca_hcris(n=4))
        self.assertIn("Hospital locations in CA", html)        # map panel
        self.assertIn("Showing 4 geocoded hospital locations of 5 in CA", html)
        self.assertIn("Census", html)                          # provenance

    def test_uncoded_hospital_listed_not_plotted(self):
        from rcm_mc.ui.market_data_page import render_state_detail
        html = render_state_detail("CA", self._ca_hcris(n=4))
        self.assertIn("Hospitals in CA", html)                 # table preserved
        self.assertIn("not plotted", html)                     # honest note

    def test_no_forced_map_when_no_coordinates(self):
        import pandas as _pd
        from rcm_mc.ui.market_data_page import render_state_detail
        df = _pd.DataFrame([{"state": "CA", "ccn": "999999", "name": "X",
                             "beds": 10, "net_patient_revenue": 1e8,
                             "operating_expenses": 9e7}])
        html = render_state_detail("CA", df)
        self.assertNotIn("Hospital locations in CA", html)     # no forced map
        self.assertIn("Hospitals in CA", html)                 # table still there


if __name__ == "__main__":
    unittest.main()
