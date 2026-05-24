"""PR 6 — Diligence Checklist honesty pass.

The /diligence-checklist page mixes real corpus data (MOIC/IRR/leverage
benchmarks + corpus-deal count) with a heuristic per-item risk weight.
A prior version mislabeled the heuristic column "Corpus Fail%", implying a
measured failure frequency. These tests lock in the honest labeling.
"""
import unittest

from rcm_mc.ui.data_public.diligence_checklist_page import render_diligence_checklist


class TestDiligenceChecklistHonesty(unittest.TestCase):
    def setUp(self):
        self.html = render_diligence_checklist({"sector": "Physician Group"})

    def test_no_misleading_corpus_fail_column(self):
        # The old, misleading header must be gone.
        self.assertNotIn("Corpus Fail%", self.html)

    def test_risk_weight_column_present(self):
        self.assertIn("Risk Wt.", self.html)

    def test_source_purpose_header_present(self):
        # Honest source-and-purpose band must render.
        self.assertIn("ck-sp", self.html)
        self.assertIn("rule engine", self.html)

    def test_caveat_distinguishes_heuristic_from_measured(self):
        self.assertIn("not a measured corpus", self.html)

    def test_renders_for_every_sector_without_error(self):
        for sector in ("Dental", "Behavioral Health", "Urgent Care"):
            html = render_diligence_checklist({"sector": sector})
            self.assertIn("ck-sp", html)
            self.assertNotIn("Corpus Fail%", html)


if __name__ == "__main__":
    unittest.main()
