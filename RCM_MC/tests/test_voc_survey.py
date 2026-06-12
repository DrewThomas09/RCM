"""Tests for the Voice-of-Customer survey evidence surface
(/voc-survey): classification thresholds, respondent-weighted NPS,
and page/nav registration."""
from __future__ import annotations

import unittest

from rcm_mc.data_public.voc_survey import (
    SECTORS, _classify, compute_voc,
)
from rcm_mc.ui.data_public.voc_survey_page import render_voc_survey


class ClassificationTests(unittest.TestCase):
    def test_differentiator_needs_importance_and_gap(self):
        self.assertEqual(_classify(4.0, 0.5), "DIFFERENTIATOR")
        self.assertEqual(_classify(4.0, -0.5), "VULNERABILITY")
        # Low-importance criteria never classify as either, whatever
        # the gap — gaps customers don't weight can't move a decision.
        self.assertEqual(_classify(3.0, 2.0), "TABLE_STAKES")
        self.assertEqual(_classify(3.0, -2.0), "TABLE_STAKES")
        # Parity inside the ±0.3 noise band is table stakes.
        self.assertEqual(_classify(5.0, 0.2), "TABLE_STAKES")


class ComputeVocTests(unittest.TestCase):
    def test_blended_nps_is_respondent_weighted(self):
        r = compute_voc(SECTORS[0])
        expected = round(
            sum(s.nps * s.n_respondents for s in r.segments) /
            sum(s.n_respondents for s in r.segments))
        self.assertEqual(r.blended_nps, expected)

    def test_n_total_sums_segments(self):
        r = compute_voc(SECTORS[0])
        self.assertEqual(r.n_total,
                         sum(s.n_respondents for s in r.segments))

    def test_kpc_rows_sorted_by_importance_desc(self):
        r = compute_voc(SECTORS[0])
        importances = [k.importance for k in r.kpc_rows]
        self.assertEqual(importances, sorted(importances, reverse=True))

    def test_gap_matches_scores(self):
        for sector in SECTORS:
            for k in compute_voc(sector).kpc_rows:
                self.assertAlmostEqual(
                    k.gap, round(k.target_score - k.best_competitor_score, 2))

    def test_unknown_sector_falls_back(self):
        r = compute_voc("Not A Sector")
        self.assertEqual(r.sector, SECTORS[0])

    def test_every_sector_has_wtp_and_headline(self):
        for sector in SECTORS:
            r = compute_voc(sector)
            self.assertTrue(r.wtp_bands)
            self.assertTrue(r.headline)


class VocPageTests(unittest.TestCase):
    def test_renders_with_identity_and_provenance(self):
        html = render_voc_survey({})
        self.assertIn("Voice of Customer", html)
        self.assertIn("ck-illus-note", html)
        self.assertIn("KPC gap matrix", html)

    def test_sector_param_switches_panel(self):
        html = render_voc_survey({"sector": "HCIT / SaaS"})
        self.assertIn("EHR integration depth", html)

    def test_malicious_sector_param_is_neutralized(self):
        html = render_voc_survey({"sector": "<script>x()</script>"})
        self.assertNotIn("<script>x()</script>", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/voc-survey", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/voc-survey"), "diligence")


if __name__ == "__main__":
    unittest.main()
