"""Pin for the Return-vs-Consistency lead scatter on /sponsor-league.

The league table ranks on one sort key at a time, hiding the joint
return/consistency read in adjacent columns. The lead scatter (P50 MOIC
y, consistency score x, dashed refs at median consistency + 2.0× MOIC)
surfaces the quadrant a partner screens for — high-return AND consistent.

Mirrors the sister scatter on /sponsor-track-record. consistency_score
is the 0–100 composite scale (per data_public/sponsor_track_record.py),
not 0–1.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _rec(**kwargs):
    return SimpleNamespace(
        sponsor=kwargs.get("sponsor", "X"),
        median_moic=kwargs.get("median_moic"),
        consistency_score=kwargs.get("consistency_score"),
        loss_rate=kwargs.get("loss_rate", 0.0),
        deal_count=kwargs.get("deal_count", 5),
    )


class LeagueScatterTests(unittest.TestCase):
    def _scatter(self, records):
        from rcm_mc.ui.data_public.sponsor_league_page import _league_scatter
        return _league_scatter(records)

    def test_renders_svg_with_quadrant_refs_and_labels(self):
        html = self._scatter([
            _rec(sponsor="A", median_moic=2.8, consistency_score=78),
            _rec(sponsor="B", median_moic=1.6, consistency_score=45),
            _rec(sponsor="C", median_moic=1.1, consistency_score=30,
                 loss_rate=0.25),
        ])
        self.assertIn("<svg", html)
        self.assertIn("Return vs Consistency", html)
        self.assertIn("Consistency score", html)
        self.assertIn("P50 MOIC", html)
        # 2.0× MOIC reference + median-consistency reference are dashed.
        self.assertIn("stroke-dasharray", html)

    def test_one_dot_per_eligible_sponsor(self):
        html = self._scatter([
            _rec(sponsor="A", median_moic=2.8, consistency_score=78),
            _rec(sponsor="B", median_moic=1.6, consistency_score=45),
        ])
        self.assertEqual(html.count("<circle"), 2)

    def test_skips_sponsors_without_realized_moic(self):
        # Unrealized sponsors (median_moic None) are excluded from the
        # scatter — same as the table's MOIC stats.
        html = self._scatter([
            _rec(sponsor="A", median_moic=2.5, consistency_score=70),
            _rec(sponsor="B", median_moic=None, consistency_score=55),
            _rec(sponsor="C", median_moic=2.1, consistency_score=66),
        ])
        self.assertEqual(html.count("<circle"), 2)

    def test_empty_when_fewer_than_two_points(self):
        # ck_scatter returns '' below 2 finite points; the helper passes
        # that through so the caller falls back to the table alone.
        self.assertEqual(
            self._scatter([_rec(median_moic=2.0, consistency_score=60)]), "")

    def test_tone_encodes_loss_and_elite_return(self):
        # Lossy (>=20%) sponsor → negative tone; >=2.0x zero-loss →
        # positive tone. Assert both palette colors appear.
        html = self._scatter([
            _rec(sponsor="Elite", median_moic=2.6, consistency_score=80,
                 loss_rate=0.0),
            _rec(sponsor="Lossy", median_moic=1.4, consistency_score=40,
                 loss_rate=0.30),
        ])
        self.assertIn("--sc-positive", html)
        self.assertIn("--sc-negative", html)


if __name__ == "__main__":
    unittest.main()
