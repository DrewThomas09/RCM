"""Tests for rcm_mc/ui/data_public/comparables_page.py."""
from __future__ import annotations

import unittest


class TestRenderComparables(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertGreater(len(html), 30_000)

    def test_renders_with_query(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables(sector="Cardiology", ev_mm=200.0, ebitda_mm=20.0, hold_years=5.0)
        self.assertIn("Comparable", html)

    def test_renders_sector_only(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables(sector="Physician Practice")
        self.assertIn("<!DOCTYPE html>", html)

    def test_contains_query_form(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables()
        self.assertIn("Find Comparables", html)
        self.assertIn("ev_mm", html)
        self.assertIn("ebitda_mm", html)

    def test_contains_table(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables()
        self.assertIn("comps-tbl", html)

    def test_peer_stats_with_query(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables(sector="Physician Practice", ev_mm=100.0, ebitda_mm=12.0)
        self.assertIn("Peer Group Statistics", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables()
        self.assertIn("/comparables", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.comparables_page import render_comparables
        html = render_comparables()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_payer_bars_svg(self):
        from rcm_mc.ui.data_public.comparables_page import _payer_bars
        pm = {"commercial": 0.6, "medicare": 0.3, "medicaid": 0.08, "self_pay": 0.02}
        svg = _payer_bars(pm)
        self.assertIn("<svg", svg)
        self.assertIn("60%C", svg)

    def test_payer_bars_none(self):
        from rcm_mc.ui.data_public.comparables_page import _payer_bars
        result = _payer_bars(None)
        self.assertNotIn("<svg", result)

    def test_sim_badge_green_for_high_score(self):
        from rcm_mc.ui.data_public.comparables_page import _sim_badge
        badge = _sim_badge(0.85)
        self.assertIn("22c55e", badge)
        self.assertIn("85%", badge)

    def test_sim_badge_red_for_low_score(self):
        from rcm_mc.ui.data_public.comparables_page import _sim_badge
        badge = _sim_badge(0.20)
        self.assertIn("20%", badge)

    def test_peer_stats_panel(self):
        from rcm_mc.ui.data_public.comparables_page import _peer_stats_panel
        comps = [
            {"realized_moic": 2.5, "ev_mm": 200},
            {"realized_moic": 1.8, "ev_mm": 150},
            {"realized_moic": 3.2, "ev_mm": 300},
        ]
        panel = _peer_stats_panel(comps, None)
        self.assertIn("Peer P50 MOIC", panel)

    def test_peer_stats_empty_no_crash(self):
        from rcm_mc.ui.data_public.comparables_page import _peer_stats_panel
        result = _peer_stats_panel([], None)
        self.assertEqual(result, "")

    def test_comps_table_no_similarity(self):
        from rcm_mc.ui.data_public.comparables_page import _comps_table
        comps = [
            {"deal_name": "Test Deal", "sector": "Cardiology", "year": 2019,
             "ev_mm": 100, "ebitda_at_entry_mm": 12, "realized_moic": 2.5,
             "realized_irr": 0.22, "hold_years": 4.5, "source_id": "test_1",
             "payer_mix": {"commercial": 0.65}},
        ]
        html = _comps_table(comps, show_similarity=False)
        self.assertIn("Test Deal", html)
        self.assertNotIn("Match", html)


if __name__ == "__main__":
    unittest.main()
