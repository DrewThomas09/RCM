"""Tests for leverage analytics and /leverage-intel page."""
from __future__ import annotations

import unittest


class TestLeverageAnalytics(unittest.TestCase):
    def _corpus(self):
        deals = []
        for i in range(30):
            d = {
                "source_id": f"t{i:02}", "deal_name": f"Deal {i}",
                "buyer": "B", "seller": "S", "ev_mm": 200.0 + i * 10,
                "hold_years": 5.0, "realized_moic": 1.5 + (i % 5) * 0.4,
                "realized_irr": 0.15 + (i % 4) * 0.03, "payer_mix": {},
            }
            if i < 10:
                d["leverage_pct"] = 0.40 + (i % 4) * 0.08
            else:
                d["ev_ebitda"] = 8.0 + (i % 6)
            deals.append(d)
        return deals

    def test_compute_analytics(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        self.assertGreater(profile.n_direct, 0)
        self.assertGreater(profile.n_proxied, 0)

    def test_buckets_present(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        self.assertGreater(len(profile.buckets), 0)

    def test_bucket_percentiles_ordered(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        for b in profile.buckets:
            self.assertLessEqual(b.moic_p25, b.moic_p50)
            self.assertLessEqual(b.moic_p50, b.moic_p75)

    def test_loss_rate_valid(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        for b in profile.buckets:
            self.assertGreaterEqual(b.loss_rate, 0.0)
            self.assertLessEqual(b.loss_rate, 1.0)

    def test_corr_range(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        self.assertGreaterEqual(profile.lev_moic_corr, -1.0)
        self.assertLessEqual(profile.lev_moic_corr, 1.0)

    def test_optimal_bucket_valid(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        profile = compute_leverage_analytics(self._corpus())
        bucket_labels = [b.label for b in profile.buckets]
        self.assertIn(profile.optimal_bucket, bucket_labels)

    def test_proxy_implied(self):
        from rcm_mc.data_public.leverage_analytics import _implied_leverage
        lev = _implied_leverage(10.0)
        self.assertIsNotNone(lev)
        self.assertGreater(lev, 0)
        self.assertLessEqual(lev, 1.0)

    def test_full_corpus(self):
        from rcm_mc.data_public.leverage_analytics import compute_leverage_analytics
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        profile = compute_leverage_analytics(list(_SEED_DEALS))
        self.assertIsNotNone(profile)


class TestRenderLeverageIntel(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("<!doctype html>", html)
        self.assertGreater(len(html), 20_000)

    def test_histogram_present(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("Leverage Distribution", html)
        self.assertIn("<svg", html)

    def test_scatter_present(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("Leverage % vs Realized MOIC", html)

    def test_bucket_table_present(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("MOIC by Leverage Bucket", html)
        self.assertIn("Optimal", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("Avg Leverage", html)
        self.assertIn("Optimal Bucket", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertIn("/leverage-intel", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.leverage_intel_page import render_leverage_intel
        html = render_leverage_intel()
        self.assertNotIn("background:#ffffff", html.lower())


if __name__ == "__main__":
    unittest.main()
