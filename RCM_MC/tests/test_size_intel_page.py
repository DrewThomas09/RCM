"""Tests for size analytics and /size-intel page."""
from __future__ import annotations

import unittest


class TestSizeAnalytics(unittest.TestCase):
    def _corpus(self):
        return [
            {"source_id": f"t{i:02}", "deal_name": f"Deal {i}", "buyer": "B", "seller": "S",
             "hold_years": 5.0, "realized_moic": 1.5 + (i % 5) * 0.4,
             "realized_irr": 0.15, "payer_mix": {},
             "ev_mm": [50, 150, 250, 500, 1500][i % 5] + i}
            for i in range(25)
        ]

    def test_compute_profile(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        profile = compute_size_analytics(self._corpus())
        self.assertGreater(profile.n_total, 0)
        self.assertGreater(len(profile.buckets), 0)

    def test_ev_percentiles_ordered(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        profile = compute_size_analytics(self._corpus())
        self.assertLessEqual(profile.ev_p25, profile.ev_p50)
        self.assertLessEqual(profile.ev_p50, profile.ev_p75)

    def test_bucket_percentiles_ordered(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        for b in compute_size_analytics(self._corpus()).buckets:
            self.assertLessEqual(b.moic_p25, b.moic_p50)
            self.assertLessEqual(b.moic_p50, b.moic_p75)

    def test_corr_range(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        profile = compute_size_analytics(self._corpus())
        self.assertGreaterEqual(profile.size_moic_corr, -1.0)
        self.assertLessEqual(profile.size_moic_corr, 1.0)

    def test_points_populated(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        profile = compute_size_analytics(self._corpus())
        self.assertGreater(len(profile.ev_moic_points), 0)

    def test_full_corpus(self):
        from rcm_mc.data_public.size_analytics import compute_size_analytics
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        profile = compute_size_analytics(list(_SEED_DEALS))
        self.assertGreater(profile.n_total, 0)


class TestRenderSizeIntel(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 25_000)

    def test_scatter_present(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertIn("EV vs MOIC", html)
        self.assertIn("<svg", html)

    def test_histogram_present(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertIn("EV Distribution", html)

    def test_bucket_table_present(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertIn("Performance by Deal Size", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertIn("EV P50", html)
        self.assertIn("Size", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        # Page renders with its title "Size Intelligence" in the
        # shell title bar.  /size-intel was the legacy-nav self-
        # reference check; legacy-nav is no longer rendered into
        # the active sidebar, so we verify page identity instead.
        self.assertIn("Size Intelligence", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.size_intel_page import render_size_intel
        html = render_size_intel()
        self.assertNotIn("background:#ffffff", html.lower())


if __name__ == "__main__":
    unittest.main()
