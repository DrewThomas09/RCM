"""Guards for the Diligence workspace audit docs (PR 0, docs only)."""
from __future__ import annotations

import pathlib
import unittest

_DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


class DiligenceAuditDocsTests(unittest.TestCase):
    def test_all_docs_exist(self):
        for rel in ("PEDESK_DILIGENCE_WORKSPACE_AUDIT.md",
                    "PEDESK_DILIGENCE_PAGE_TAXONOMY.md",
                    "PEDESK_DILIGENCE_DATA_SOURCE_MATRIX.md",
                    "PEDESK_DILIGENCE_REFORM_PLAN.md",
                    "loops/DILIGENCE_WORKSPACE_REFORM_LOOP.md"):
            self.assertTrue((_DOCS / rel).is_file(), f"missing {rel}")

    def test_audit_records_illustrative_finding(self):
        t = (_DOCS / "PEDESK_DILIGENCE_WORKSPACE_AUDIT.md").read_text()
        self.assertIn("ILLUSTRATIVE", t)
        self.assertIn("data_public", t)
        self.assertIn("HCRIS X-Ray", t)

    def test_matrix_defines_confidence_labels(self):
        t = (_DOCS / "PEDESK_DILIGENCE_DATA_SOURCE_MATRIX.md").read_text()
        for label in ("LIVE", "DERIVED", "ILLUSTRATIVE", "DATA REQUIRED",
                      "EXPERIMENTAL"):
            self.assertIn(label, t)

    def test_plan_has_pr_sequence_and_triage(self):
        t = (_DOCS / "PEDESK_DILIGENCE_REFORM_PLAN.md").read_text()
        self.assertIn("PR sequence", t)
        self.assertIn("Triage", t)


if __name__ == "__main__":
    unittest.main()
