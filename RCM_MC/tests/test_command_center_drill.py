"""Command-center hero KPIs carry drill-through links (PAGE_INVENTORY fix).

Every hero figure links to the surface where a partner acts on it —
screener (scoped), market data, distress scan, portfolio. Links are in
the KPI sub line; values stay clean numbers.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class CommandCenterDrillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.command_center import render_command_center
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "cc.db")
        cls.html = render_command_center(_get_latest_per_ccn(), db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_hero_kpi_has_a_drill_link(self):
        for href in (
            "/target-screener?vertical=hospitals",
            "/target-screener?vertical=hospitals&min_size=100",
            "/market-data",
            "/screening/bankruptcy-survivor",
            "/portfolio",
        ):
            self.assertIn(f'href="{href}"', self.html, href)

    def test_drill_targets_are_served_routes(self):
        # Guard against a drill link pointing at a route that was renamed
        # away — every target must be an exact-match route in server.py.
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        for route in ("/target-screener", "/market-data",
                      "/screening/bankruptcy-survivor", "/portfolio"):
            self.assertIn(f'"{route}"', src, route)


if __name__ == "__main__":
    unittest.main()
