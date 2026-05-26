"""Reimbursement Cliff Calendar page (/diligence/cliff-calendar).

Guards a once-dark pe_intelligence module brought to life as a Chartis page:
it must render the real curated calendar, scan a hold window correctly, carry
the honest illustrative label, and be wired into the route/nav/tier system so
the ranking crossover picks it up.
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.ui.cliff_calendar_page import render_cliff_calendar_page
from rcm_mc.pe_intelligence.reimbursement_cliff_calendar_2026_2029 import (
    CLIFF_CALENDAR,
    scan_cliff_calendar_for_deal,
)

_SERVER = (pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py")


class CliffCalendarPageTests(unittest.TestCase):
    def test_renders_real_events(self):
        h = render_cliff_calendar_page("hospital_general", 2026, 5)
        # Real named regulatory events from the curated calendar appear.
        self.assertIn("OBBBA", h)
        self.assertIn("Site-neutral", h)
        # Every modeled event is in the full table.
        for ev in CLIFF_CALENDAR:
            self.assertIn(ev.name, h)

    def test_honest_illustrative_label(self):
        # No-fake-data discipline: the page must declare it is curated /
        # partner-judgment, not a live CMS feed.
        h = render_cliff_calendar_page()
        self.assertIn("Illustrative template", h)
        self.assertIn("partner-judgment", h.lower())

    def test_hold_window_scan_matches_module(self):
        # The page leads with the module's computed in-hold exposure — it must
        # not invent numbers, only surface what scan_cliff_calendar_for_deal
        # returns.
        report = scan_cliff_calendar_for_deal("hospital_general", 2026, 5)
        h = render_cliff_calendar_page("hospital_general", 2026, 5)
        self.assertIn(f"{report.total_bps_in_hold / 100.0:+.1f}%", h)
        self.assertIn(str(len(report.hits)), h)

    def test_bad_inputs_fall_back_safely(self):
        # Unknown subsector / out-of-range hold must not raise.
        h = render_cliff_calendar_page("not_a_subsector", 1999, 99)
        self.assertIn("Reimbursement Cliff Calendar", h)

    def test_route_wired(self):
        src = _SERVER.read_text()
        self.assertIn('path == "/diligence/cliff-calendar"', src)
        self.assertIn("render_cliff_calendar_page", src)

    def test_classified_navy(self):
        from rcm_mc.diligence.surface_status import classify_surface
        self.assertEqual(
            classify_surface("/diligence/cliff-calendar")["tier"], "navy")

    def test_in_nav_and_palette(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _DEFAULT_PALETTE_MODULES
        hrefs = {it["href"] for it in _SUB_NAV["diligence"]}
        self.assertIn("/diligence/cliff-calendar", hrefs)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/cliff-calendar", routes)

    def test_ranked_crossover(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        routes = {r["route"] for r in RANKINGS.get("diligence", [])}
        self.assertIn("/diligence/cliff-calendar", routes)


if __name__ == "__main__":
    unittest.main()
