"""Tests for the Win/Loss analyzer surface (/win-loss): conversion
math, loss-mix shape, and page/nav registration."""
from __future__ import annotations

import unittest

from rcm_mc.data_public.win_loss import SECTORS, compute_win_loss
from rcm_mc.ui.data_public.win_loss_page import render_win_loss


class ComputeWinLossTests(unittest.TestCase):
    def test_totals_sum_segments(self):
        r = compute_win_loss(SECTORS[0])
        self.assertEqual(r.total_opportunities,
                         sum(s.opportunities for s in r.segments))
        self.assertEqual(r.total_wins, sum(s.wins for s in r.segments))

    def test_overall_rate_matches_totals(self):
        r = compute_win_loss(SECTORS[0])
        self.assertAlmostEqual(
            r.overall_win_rate_pct,
            round(r.total_wins / r.total_opportunities * 100, 1))

    def test_competitor_rates_consistent(self):
        for sector in SECTORS:
            for c in compute_win_loss(sector).competitors:
                self.assertLessEqual(c.wins, c.contested)
                self.assertAlmostEqual(
                    c.win_rate_pct, round(c.wins / c.contested * 100, 1))

    def test_loss_mix_covers_taxonomy_and_sums_to_100(self):
        from rcm_mc.data_public.win_loss import LOSS_REASONS
        for sector in SECTORS:
            r = compute_win_loss(sector)
            self.assertEqual(set(r.loss_reason_mix), set(LOSS_REASONS))
            self.assertAlmostEqual(
                sum(r.loss_reason_mix.values()), 100.0, places=1)
            self.assertEqual(r.price_loss_share_pct,
                             r.loss_reason_mix["PRICE"])

    def test_unknown_sector_falls_back(self):
        r = compute_win_loss("Not A Sector")
        self.assertEqual(r.sector, SECTORS[0])

    def test_trend_quarters_present(self):
        r = compute_win_loss(SECTORS[0])
        self.assertGreaterEqual(len(r.trend), 4)
        self.assertTrue(r.headline)


class WinLossPageTests(unittest.TestCase):
    def test_renders_with_identity_and_provenance(self):
        html = render_win_loss({})
        self.assertIn("Win/Loss Analyzer", html)
        self.assertIn("ck-illus-note", html)
        self.assertIn("Loss-reason mix", html)

    def test_sector_param_switches_log(self):
        html = render_win_loss({"sector": "Home Health"})
        self.assertIn("MA plan network contracts", html)

    def test_malicious_sector_param_is_neutralized(self):
        html = render_win_loss({"sector": "<script>x()</script>"})
        self.assertNotIn("<script>x()</script>", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/win-loss", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/win-loss"), "diligence")


if __name__ == "__main__":
    unittest.main()
