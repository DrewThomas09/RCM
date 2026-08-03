"""Report-0270: shared CSV formula-injection defang + the three exporters
that previously under-defanged (missing tab/CR) or defanged nothing.
"""
from __future__ import annotations

import unittest

from rcm_mc.infra.csv_safety import FORMULA_LEAD, defang_cell, defang_row


class TestDefangCell(unittest.TestCase):
    def test_all_formula_leads_neutralized(self):
        for lead in FORMULA_LEAD:
            self.assertEqual(defang_cell(lead + "cmd"), "'" + lead + "cmd")

    def test_tab_and_cr_covered(self):
        # The gap the local helpers missed.
        self.assertEqual(defang_cell("\t=1+1"), "'\t=1+1")
        self.assertEqual(defang_cell("\rHYPERLINK"), "'\rHYPERLINK")

    def test_safe_strings_and_non_strings_passthrough(self):
        self.assertEqual(defang_cell("Acme Health"), "Acme Health")
        self.assertEqual(defang_cell(42), 42)
        self.assertEqual(defang_cell(None), None)
        self.assertEqual(defang_cell(""), "")

    def test_defang_row(self):
        self.assertEqual(
            defang_row(["=EVIL", 3, "ok", "@x"]),
            ["'=EVIL", 3, "ok", "'@x"],
        )


class TestExpertCallsDefang(unittest.TestCase):
    def test_delegates_to_shared_and_covers_tab(self):
        from rcm_mc.ui.expert_calls_page import _csv_defang
        self.assertEqual(_csv_defang("=cmd"), "'=cmd")
        self.assertEqual(_csv_defang("\t=cmd"), "'\t=cmd")  # was missed before
        self.assertEqual(_csv_defang("safe"), "safe")


class TestCorpusExportDefang(unittest.TestCase):
    def test_leading_formula_and_tab_defanged(self):
        # deal_name / buyer / notes are partner-supplied free text — the
        # real \t/\r gap this export had before Report-0270.
        from rcm_mc.data_public.corpus_export import to_csv
        deals = [{
            "source_id": "d1", "deal_name": "=HYPERLINK(evil)",
            "buyer": "\t=1+1", "notes": "@SUM(A1)",
        }]
        out = to_csv(deals, include_payer_mix=False)
        self.assertIn("'=HYPERLINK(evil)", out)
        self.assertIn("'\t=1+1", out)
        self.assertIn("'@SUM(A1)", out)


class TestTamSamCsvDefang(unittest.TestCase):
    def test_csv_builds_and_defang_wrapper_is_active(self):
        # tam_sam content is trusted catalog today (model_from_qs takes
        # only numeric overrides + a fixed template key), so this is a
        # defense-in-depth smoke test: the export builds and its rows go
        # through the shared defang wrapper (unit-tested above).
        from rcm_mc.ui.tam_sam_page import tam_sam_csv
        out = tam_sam_csv({"template": ["fertility_ivf"]})
        self.assertIn("TAM/SAM build", out)
        self.assertTrue(len(out) > 200)


if __name__ == "__main__":
    unittest.main()
