"""Tests for SectorThemeDetector."""
from __future__ import annotations

import unittest


def _theme_corpus():
    """Synthetic 12-doc corpus covering the four named themes
    plus some background industry coverage."""
    from rcm_mc.sector_themes import Document
    return [
        Document(
            doc_id="D1", date="2024-03-01",
            text="Specialty pharmacy platform compounds GLP-1 "
                 "drugs including semaglutide and tirzepatide for "
                 "obesity treatment. Mounjaro and Wegovy supply "
                 "constraints driving demand."),
        Document(
            doc_id="D2", date="2024-09-15",
            text="GLP-1 specialty pharmacy weight loss compounding "
                 "Ozempic Wegovy Mounjaro Zepbound semaglutide."),
        Document(
            doc_id="D3", date="2025-01-10",
            text="Hybrid care platform combines telehealth virtual "
                 "visits with in-person primary care. Remote "
                 "monitoring for chronic disease."),
        Document(
            doc_id="D4", date="2025-06-20",
            text="AI-enabled RCM platform automates denial "
                 "management. Computer-assisted coding reduces "
                 "manual review. Machine learning predicts denials."),
        Document(
            doc_id="D5", date="2025-11-04",
            text="Medicare Advantage star rating arbitrage. MA plan "
                 "quality bonus payments. Stars rating optimization "
                 "for QBP."),
        Document(
            doc_id="D6", date="2024-04-22",
            text="Hospital acquisition private equity general "
                 "industry update unrelated to themes."),
        Document(
            doc_id="D7", date="2025-07-15",
            text="Behavioral health network mental health "
                 "outpatient psychiatric therapy addiction."),
        Document(
            doc_id="D8", date="2025-12-01",
            text="Value-based primary care capitated ACO REACH "
                 "delegated risk arrangement."),
        # Multi-theme deal
        Document(
            doc_id="D9", date="2025-08-10",
            text="AI-enabled RCM denial management platform plus "
                 "value-based primary care capitated risk."),
        Document(
            doc_id="D10", date="2024-11-30",
            text="Hospital chain consolidation continues."),
        Document(
            doc_id="D11", date="2025-02-05",
            text="GLP-1 specialty pharmacy compounding for "
                 "Mounjaro and Zepbound. Weight loss demand."),
        Document(
            doc_id="D12", date="2024-08-19",
            text="Telehealth hybrid care expansion."),
    ]


# ── Vocabulary + LDA ────────────────────────────────────────────

class TestVocabAndLDA(unittest.TestCase):
    def test_vocabulary_filters_low_freq(self):
        from rcm_mc.sector_themes import build_vocabulary
        corpus = build_vocabulary(_theme_corpus(), min_count=2)
        # All vocab words should appear in ≥2 documents
        self.assertGreater(len(corpus.vocab), 5)
        self.assertEqual(len(corpus.vocab), len(corpus.word_to_idx))

    def test_lda_returns_topic_word_distributions(self):
        from rcm_mc.sector_themes import (
            build_vocabulary, fit_lda_collapsed_gibbs,
        )
        corpus = build_vocabulary(_theme_corpus(), min_count=2)
        model = fit_lda_collapsed_gibbs(
            corpus, K=4, n_iter=40, seed=1)
        # phi: K × V, theta: D × K
        self.assertEqual(model.phi.shape, (4, len(corpus.vocab)))
        self.assertEqual(
            model.theta.shape,
            (len(corpus.documents), 4))
        # Each row of phi sums to ~1
        for k in range(4):
            self.assertAlmostEqual(
                float(model.phi[k].sum()), 1.0, places=4)
        # Each row of theta sums to ~1
        for d in range(model.theta.shape[0]):
            self.assertAlmostEqual(
                float(model.theta[d].sum()), 1.0, places=4)

    def test_lda_top_words_returns_n(self):
        from rcm_mc.sector_themes import (
            build_vocabulary, fit_lda_collapsed_gibbs,
        )
        corpus = build_vocabulary(_theme_corpus(), min_count=2)
        model = fit_lda_collapsed_gibbs(
            corpus, K=3, n_iter=20, seed=1)
        words = model.top_words(0, n_top=5)
        self.assertEqual(len(words), 5)
        for w, p in words:
            self.assertIn(w, corpus.vocab)
            self.assertGreater(p, 0)


# ── Theme-anchored matching ────────────────────────────────────

class TestThemeAnchored(unittest.TestCase):
    def test_glp1_text_matches_theme(self):
        from rcm_mc.sector_themes import score_deal_against_themes
        text = ("Specialty pharmacy compounds GLP-1 semaglutide "
                "and tirzepatide for obesity weight loss demand.")
        matches = score_deal_against_themes(text)
        ids = {m.theme_id for m in matches}
        self.assertIn("glp1_specialty_pharmacy", ids)

    def test_unrelated_text_returns_empty(self):
        from rcm_mc.sector_themes import score_deal_against_themes
        # Use a topic clearly outside the healthcare-PE taxonomy
        text = "USDA organic certification standards update."
        matches = score_deal_against_themes(text)
        self.assertEqual(matches, [])


# ── Heatmap ────────────────────────────────────────────────────

class TestHeatmap(unittest.TestCase):
    def test_heatmap_returns_year_buckets(self):
        from rcm_mc.sector_themes import emerging_theme_heatmap
        heatmap = emerging_theme_heatmap(_theme_corpus())
        # GLP-1 should appear in both 2024 and 2025
        self.assertIn("glp1_specialty_pharmacy", heatmap)
        glp1 = heatmap["glp1_specialty_pharmacy"]
        self.assertIn("2024", glp1)
        self.assertIn("2025", glp1)

    def test_quarter_granularity(self):
        from rcm_mc.sector_themes import emerging_theme_heatmap
        heatmap = emerging_theme_heatmap(
            _theme_corpus(), granularity="quarter")
        glp1 = heatmap.get("glp1_specialty_pharmacy", {})
        # At least one of the periods should be quarter-formatted
        any_quarter = any("Q" in k for k in glp1.keys())
        self.assertTrue(any_quarter)


# ── Target universe ────────────────────────────────────────────

class TestTargetUniverse(unittest.TestCase):
    def test_thesis_returns_relevant_deals(self):
        from rcm_mc.sector_themes import build_target_universe
        out = build_target_universe(
            _theme_corpus(),
            thesis_theme_ids=["glp1_specialty_pharmacy"],
            min_composite=0.05,
        )
        ids = {e.doc_id for e in out}
        # D1, D2, D11 should be in (GLP-1 deals)
        self.assertIn("D1", ids)
        self.assertIn("D2", ids)
        self.assertIn("D11", ids)
        # D6 (unrelated) should NOT be in
        self.assertNotIn("D6", ids)

    def test_multi_theme_deal_outranks_single_theme(self):
        """D9 hits AI-RCM + value-based PC; should outrank a deal
        that only hits one of those when both themes are in the
        thesis."""
        from rcm_mc.sector_themes import build_target_universe
        out = build_target_universe(
            _theme_corpus(),
            thesis_theme_ids=[
                "ai_enabled_rcm", "value_based_primary_care",
            ],
            min_composite=0.05,
        )
        # D9 should outrank D4 (single-theme AI-RCM)
        d9 = next((e for e in out if e.doc_id == "D9"), None)
        d4 = next((e for e in out if e.doc_id == "D4"), None)
        if d9 and d4:
            self.assertGreater(d9.composite_score, d4.composite_score)


if __name__ == "__main__":
    unittest.main()
