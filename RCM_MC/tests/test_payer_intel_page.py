"""Tests for payer intelligence analytics and /payer-intel page."""
from __future__ import annotations

import unittest


class TestPayerIntelligence(unittest.TestCase):
    def _corpus(self):
        return [
            {"source_id": f"t{i:02}", "deal_name": f"D{i}", "buyer": "B", "seller": "S",
             "ev_mm": 150.0, "hold_years": 5.0, "realized_moic": 1.5 + i * 0.3,
             "realized_irr": 0.15, "payer_mix": {
                 "commercial": 0.20 + (i % 5) * 0.15,
                 "medicare": 0.40 - (i % 3) * 0.05,
                 "medicaid": 0.20,
                 "self_pay": 0.05,
             }}
            for i in range(20)
        ]

    def test_compute_profile(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        profile = compute_payer_intelligence(self._corpus())
        self.assertGreater(profile.avg_commercial, 0)
        self.assertGreater(profile.avg_medicare, 0)
        self.assertIsNotNone(profile.commercial_moic_corr)

    def test_regime_stats(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        profile = compute_payer_intelligence(self._corpus())
        self.assertGreater(len(profile.regime_stats), 0)
        for r in profile.regime_stats:
            self.assertGreater(r.n_deals, 0)
            self.assertLessEqual(r.moic_p25, r.moic_p50)
            self.assertLessEqual(r.moic_p50, r.moic_p75)

    def test_loss_rate_valid(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        profile = compute_payer_intelligence(self._corpus())
        for r in profile.regime_stats:
            self.assertGreaterEqual(r.loss_rate, 0.0)
            self.assertLessEqual(r.loss_rate, 1.0)

    def test_ignores_string_payer_mix(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        corpus = self._corpus() + [
            {"source_id": "bad", "deal_name": "Bad", "buyer": "B", "seller": "S",
             "ev_mm": 100.0, "hold_years": 4.0, "realized_moic": 2.0,
             "realized_irr": 0.18, "payer_mix": "commercial:0.6"}
        ]
        # Should not raise
        profile = compute_payer_intelligence(corpus)
        self.assertIsNotNone(profile)

    def test_corr_range(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        profile = compute_payer_intelligence(self._corpus())
        self.assertGreaterEqual(profile.commercial_moic_corr, -1.0)
        self.assertLessEqual(profile.commercial_moic_corr, 1.0)

    def test_full_corpus(self):
        from rcm_mc.data_public.payer_intelligence import compute_payer_intelligence
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        profile = compute_payer_intelligence(list(_SEED_DEALS))
        self.assertGreater(profile.avg_commercial, 0)


class TestRenderPayerIntel(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 20_000)

    def test_pie_svg_present(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        self.assertIn("<svg", html)
        self.assertIn("Payer Mix", html)

    def test_scatter_present(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        self.assertIn("Commercial % vs Realized MOIC", html)

    def test_regime_table_present(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        self.assertIn("Payer Regime", html)
        self.assertIn("Gov-heavy", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        self.assertIn("Avg Commercial %", html)
        self.assertIn("MOIC Corr", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        # Page identity check (legacy-nav self-link deprecated).
        self.assertIn("Payer Intelligence", html)

    def test_editorial_theme(self):
        from rcm_mc.ui.data_public.payer_intel_page import render_payer_intel
        html = render_payer_intel()
        # Editorial chartis is the canonical theme. PR #281 swept the
        # Bloomberg-era dark hexes (#0a0e17, #0f172a, #1e293b, #111827)
        # from this page; the previous assertion checked for state
        # the codebase explicitly rejects. Anchor on what editorial
        # mode actually emits: the chartis_tokens stylesheet and at
        # least one parchment-palette hex.
        self.assertIn("chartis_tokens.css", html)
        # Parchment / paper-pure / editorial ink — at least one of
        # the canonical editorial surface colors must be present.
        editorial_markers = ("#F2EDE3", "#FAF7F0", "#ECE5D6", "#1a2332")
        present = [m for m in editorial_markers if m in html or m.lower() in html.lower()]
        self.assertTrue(
            present,
            f"expected at least one editorial palette hex; got none of {editorial_markers}",
        )

    def test_payer_pie_helper(self):
        from rcm_mc.ui.data_public.payer_intel_page import _payer_pie_svg
        svg = _payer_pie_svg(0.45, 0.35, 0.15, 0.05)
        self.assertIn("<svg", svg)
        self.assertIn("<path", svg)


if __name__ == "__main__":
    unittest.main()
