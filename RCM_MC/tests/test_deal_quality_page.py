"""Tests for deal quality scorer and /deal-quality page."""
from __future__ import annotations

import unittest


class TestDealQualityScore(unittest.TestCase):
    def _sample_deal(self, **kwargs):
        base = {
            "source_id": "test_001",
            "deal_name": "Test Deal",
            "buyer": "PE Fund",
            "seller": "Seller Co",
            "ev_mm": 200.0,
            "ebitda_at_entry_mm": 20.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.20,
            "payer_mix": {"commercial": 0.6},
            "year": 2020,
            "sector": "Physician Practice",
        }
        base.update(kwargs)
        return base

    def test_score_basic(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = self._sample_deal()
        score = score_deal_quality(deal)
        self.assertGreater(score.quality_score, 0)
        self.assertLessEqual(score.quality_score, 100)
        self.assertIn(score.tier, ("A", "B", "C", "D"))

    def test_tier_a_for_complete_deal(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = self._sample_deal(
            ebitda_mm=20.0, ev_ebitda=10.0, deal_type="LBO",
            region="Southeast", revenue_mm=100.0, geography="Multi-state",
            state="FL", leverage_pct=0.55, notes="Well-documented",
        )
        score = score_deal_quality(deal)
        self.assertEqual(score.tier, "A")

    def test_moic_negative_flag(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = self._sample_deal(realized_moic=-0.5)
        score = score_deal_quality(deal)
        flag_keys = [f.key for f in score.flags]
        self.assertIn("moic_negative", flag_keys)
        self.assertLess(score.credibility_raw, 100)

    def test_irr_mismatch_flag(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        # 5-year 2.5x MOIC implies ~20% IRR; report 60% → mismatch
        deal = self._sample_deal(realized_moic=2.5, hold_years=5.0, realized_irr=0.60)
        score = score_deal_quality(deal)
        flag_keys = [f.key for f in score.flags]
        self.assertIn("moic_irr_mismatch", flag_keys)

    def test_ev_nonpositive_flag(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = self._sample_deal(ev_mm=-50.0)
        score = score_deal_quality(deal)
        flag_keys = [f.key for f in score.flags]
        self.assertIn("ev_nonpositive", flag_keys)

    def test_missing_fields_listed(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = {
            "source_id": "test_002", "deal_name": "Sparse Deal",
            "buyer": "X", "seller": "Y", "ev_mm": 100.0,
            "hold_years": 4.0, "realized_moic": 2.0, "realized_irr": 0.18,
            "payer_mix": {},
        }
        score = score_deal_quality(deal)
        self.assertIn("sector", score.missing_fields)
        self.assertIn("ebitda_at_entry_mm", score.missing_fields)

    def test_score_corpus(self):
        from rcm_mc.data_public.deal_quality_score import score_corpus_quality
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        corpus = list(_SEED_DEALS)[:20]
        scores = score_corpus_quality(corpus)
        self.assertEqual(len(scores), 20)
        self.assertTrue(all(0 <= s.quality_score <= 100 for s in scores))

    def test_tier_assignment(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality, DealQualityScore
        deal = self._sample_deal()
        s = score_deal_quality(deal)
        if s.quality_score >= 75:
            self.assertEqual(s.tier, "A")
        elif s.quality_score >= 55:
            self.assertEqual(s.tier, "B")
        elif s.quality_score >= 35:
            self.assertEqual(s.tier, "C")
        else:
            self.assertEqual(s.tier, "D")

    def test_ev_ebitda_out_of_range_flag(self):
        from rcm_mc.data_public.deal_quality_score import score_deal_quality
        deal = self._sample_deal(ev_ebitda=55.0)
        score = score_deal_quality(deal)
        flag_keys = [f.key for f in score.flags]
        self.assertIn("ev_ebitda_range", flag_keys)


class TestRenderDealQuality(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 30_000)

    def test_renders_with_tier_filter(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality(tier_filter="A")
        self.assertIn("<!doctype html>", html.lower())

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("Avg Quality", html)
        self.assertIn("Tier A", html)
        self.assertIn("Flagged", html)

    def test_distribution_svg_present(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("<svg", html)
        self.assertIn("Quality Distribution", html)

    def test_table_present(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("Per-Deal Quality Scores", html)
        self.assertIn("Completeness", html)
        self.assertIn("Credibility", html)

    def test_methodology_panel(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("Scoring Methodology", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertIn("/deal-quality", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_sort_by_completeness(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality(sort_by="completeness")
        self.assertIn("<!doctype html>", html.lower())

    def test_sort_by_deal_name(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality(sort_by="deal_name")
        self.assertIn("<!doctype html>", html.lower())

    def test_tier_d_filter(self):
        from rcm_mc.ui.data_public.deal_quality_page import render_deal_quality
        html = render_deal_quality(tier_filter="D")
        self.assertIn("<!doctype html>", html.lower())


if __name__ == "__main__":
    unittest.main()
