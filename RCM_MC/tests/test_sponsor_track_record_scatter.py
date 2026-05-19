"""Pin for the consistency × MOIC scatter on /sponsor-track-record.

Adds visual structure on top of the existing sortable league table:
a 4-quadrant scatter (compounders / lottery / underperformers /
avoid) with each sponsor as a bubble sized by deal count.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _rec(**kwargs):
    """Minimal sponsor record stand-in matching the attributes the
    scatter helper reads."""
    return SimpleNamespace(
        sponsor=kwargs.get("sponsor", "X"),
        median_moic=kwargs.get("median_moic"),
        consistency_score=kwargs.get("consistency_score"),
        deal_count=kwargs.get("deal_count", 1),
        realized_count=kwargs.get("realized_count", 1),
    )


class ConsistencyMoicScatterTests(unittest.TestCase):
    def test_renders_one_bubble_per_sponsor(self):
        from rcm_mc.ui.chartis.sponsor_track_record_page import (
            _consistency_moic_scatter,
        )
        svg = _consistency_moic_scatter([
            _rec(sponsor="A", median_moic=2.8,
                 consistency_score=0.78, deal_count=24),
            _rec(sponsor="B", median_moic=1.6,
                 consistency_score=0.45, deal_count=10),
            _rec(sponsor="C", median_moic=1.0,
                 consistency_score=0.30, deal_count=5),
        ])
        self.assertTrue(svg.startswith("<svg"))
        self.assertEqual(svg.count("<circle"), 3)
        # Each sponsor name lands in a <title> tooltip
        self.assertIn(">A:", svg)
        self.assertIn(">B:", svg)
        self.assertIn(">C:", svg)

    def test_quadrant_labels_present(self):
        from rcm_mc.ui.chartis.sponsor_track_record_page import (
            _consistency_moic_scatter,
        )
        svg = _consistency_moic_scatter([
            _rec(sponsor="A", median_moic=2.5,
                 consistency_score=0.7, deal_count=12),
        ])
        # Reading-aid labels in the corners
        self.assertIn("COMPOUNDERS", svg)
        self.assertIn("LOTTERY", svg)

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.sponsor_track_record_page import (
            _consistency_moic_scatter,
        )
        self.assertEqual(_consistency_moic_scatter([]), "")

    def test_skips_records_with_no_consistency_or_moic(self):
        # Sponsors with missing consistency_score (e.g. only one deal)
        # would plot at x=None which is undefined — skip them.
        from rcm_mc.ui.chartis.sponsor_track_record_page import (
            _consistency_moic_scatter,
        )
        svg = _consistency_moic_scatter([
            _rec(sponsor="OK", median_moic=2.0,
                 consistency_score=0.5, deal_count=3),
            _rec(sponsor="NO_CON", median_moic=2.0,
                 consistency_score=None, deal_count=2),
            _rec(sponsor="NO_MOIC", median_moic=None,
                 consistency_score=0.5, deal_count=2),
        ])
        # Only the one with both metrics plots
        self.assertEqual(svg.count("<circle"), 1)

    def test_bubbles_color_by_moic_band(self):
        from rcm_mc.ui.chartis.sponsor_track_record_page import (
            _consistency_moic_scatter,
        )
        svg = _consistency_moic_scatter([
            _rec(sponsor="green", median_moic=3.0,
                 consistency_score=0.6, deal_count=10),
            _rec(sponsor="amber", median_moic=2.0,
                 consistency_score=0.6, deal_count=10),
            _rec(sponsor="red", median_moic=1.0,
                 consistency_score=0.6, deal_count=10),
        ])
        # Three canonical band colors all present
        self.assertIn("#0a8a5f", svg)
        self.assertIn("#b8732a", svg)
        self.assertIn("#b5321e", svg)


if __name__ == "__main__":
    unittest.main()
