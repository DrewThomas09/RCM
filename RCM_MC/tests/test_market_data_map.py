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


if __name__ == "__main__":
    unittest.main()
