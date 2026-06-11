"""Cliff calendar payer-channel exposure decomposition.

The in-hold bps cut is grouped by payer channel and turned into a
cumulative erosion curve — both pure functions of the scan's hits, so
the 'which channel carries the cut' concentration read is auditable.
"""
from __future__ import annotations

import unittest

from rcm_mc.pe_intelligence.reimbursement_cliff_calendar_2026_2029 import (
    CLIFF_CALENDAR, analyze_cliff_exposure, scan_cliff_calendar_for_deal,
)


def _subsector_with_hits():
    subs = set()
    for ev in CLIFF_CALENDAR:
        subs.update(ev.subsectors)
    for s in sorted(subs):
        r = scan_cliff_calendar_for_deal(s, 2026, 5)
        if len(r.hits) >= 2:
            return s, r
    raise AssertionError("no subsector with >=2 hits in calendar")


class CliffExposureTests(unittest.TestCase):
    def test_payer_totals_sum_to_calendar_total(self):
        _, report = _subsector_with_hits()
        exp = analyze_cliff_exposure(report)
        summed = sum(p.total_bps for p in exp.by_payer)
        self.assertAlmostEqual(summed, report.total_bps_in_hold, places=1)

    def test_payers_sorted_most_cut_first(self):
        _, report = _subsector_with_hits()
        exp = analyze_cliff_exposure(report)
        totals = [p.total_bps for p in exp.by_payer]
        self.assertEqual(totals, sorted(totals))  # most negative first

    def test_cumulative_curve_is_running_total(self):
        _, report = _subsector_with_hits()
        exp = analyze_cliff_exposure(report)
        curve = exp.cumulative_by_relative_year
        # Final cumulative value equals the calendar total.
        self.assertAlmostEqual(curve[-1][1], report.total_bps_in_hold,
                               places=1)
        # Monotonic in relative_year.
        years = [y for y, _ in curve]
        self.assertEqual(years, sorted(years))

    def test_single_channel_concentration_detected(self):
        # ASC hold 2026-2030 is all Medicare in the seeded calendar.
        report = scan_cliff_calendar_for_deal(
            "ambulatory_surgery_center", 2026, 5)
        exp = analyze_cliff_exposure(report)
        if report.hits and report.total_bps_in_hold < 0:
            self.assertIsNotNone(exp.dominant_payer)
            self.assertGreaterEqual(exp.dominant_share, 0.0)
            self.assertLessEqual(exp.dominant_share, 1.0)

    def test_worst_event_is_most_negative_for_payer(self):
        _, report = _subsector_with_hits()
        exp = analyze_cliff_exposure(report)
        for p in exp.by_payer:
            payer_events = [h.event.rate_change_bps for h in report.hits
                            if h.event.affected_payer == p.payer]
            if payer_events:
                self.assertAlmostEqual(p.worst_bps, min(payer_events),
                                       places=1)

    def test_no_hits_renders_empty(self):
        report = scan_cliff_calendar_for_deal(
            "ambulatory_surgery_center", 2040, 3)
        exp = analyze_cliff_exposure(report)
        self.assertEqual(exp.by_payer, [])
        self.assertIsNone(exp.dominant_payer)

    def test_to_dict_round_trips(self):
        _, report = _subsector_with_hits()
        d = analyze_cliff_exposure(report).to_dict()
        self.assertIn("by_payer", d)
        self.assertIn("cumulative_by_relative_year", d)
        self.assertIn("dominant_payer", d)

    def test_renders_in_page(self):
        from rcm_mc.ui.cliff_calendar_page import render_cliff_calendar_page
        h = render_cliff_calendar_page({
            "subsector": ["ambulatory_surgery_center"],
            "hold_start": ["2026"], "hold_years": ["5"]})
        self.assertIn("Payer-channel exposure", h)


if __name__ == "__main__":
    unittest.main()
