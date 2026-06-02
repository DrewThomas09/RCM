"""Dynamic editorial charts on the geographic analysis pages.

State Profile and County Explorer were table-only. They now lead with the
shared chart kit (PNG-exportable inline SVG) built from the SAME real values
as their tables: State Profile shows a diverging chart vs the U.S. median plus
a metric spotlight; County Explorer shows top-N counties on the sorted metric
plus a builder. Each page ships the export assets and a "+ build a chart"
control, and never invents data.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.county_explorer_page import render_county_explorer
from rcm_mc.ui.data_public.state_profile_page import render_state_profile


class StateProfileChartTests(unittest.TestCase):
    def test_headline_diverging_chart_and_assets(self) -> None:
        html = render_state_profile({"state": ["CA"]})
        self.assertIn("Visual summary", html)
        self.assertIn("ckc-profile-diverging", html)   # vs-median chart
        self.assertIn("ck-chart-dl", html)             # export button
        self.assertIn("__ckChartDL", html)             # export JS
        self.assertIn("Spotlight a metric", html)      # builder

    def test_metric_spotlight_builds_ranking_chart(self) -> None:
        html = render_state_profile({"state": ["MS"], "smetric": ["median_income"]})
        self.assertIn("ckc-spotlight-median_income", html)
        # builder pre-opens when a spotlight is active
        self.assertIn('sp-chart-builder" open', html)

    def test_bad_state_falls_back_without_crashing(self) -> None:
        # Unknown state → default; page still renders with the chart band.
        html = render_state_profile({"state": ["ZZ"]})
        self.assertIn("Visual summary", html)


class CountyExplorerChartTests(unittest.TestCase):
    def test_top_counties_chart_tracks_sort_and_ships_assets(self) -> None:
        html = render_county_explorer({"state": ["OH"]})
        self.assertIn("Visual summary", html)
        self.assertIn("ckc-county-population", html)    # default sort metric
        self.assertIn("Chart a metric", html)           # builder
        self.assertIn("__ckChartDL", html)

    def test_builder_charts_chosen_metric(self) -> None:
        html = render_county_explorer({
            "state": ["CA"], "sort": ["median_household_income"],
            "cmetric": ["uninsured_rate"],
        })
        self.assertIn("ckc-county-uninsured_rate", html)


if __name__ == "__main__":
    unittest.main()
