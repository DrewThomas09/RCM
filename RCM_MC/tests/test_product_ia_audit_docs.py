"""Guards for the product-IA audit docs (PR A — docs only).

Asserts the three audit artifacts exist and carry the key sections, and that
this docs-only change introduced no code/route/UI edits (the audit must be
reviewed before anything is implemented).
"""
from __future__ import annotations

import pathlib
import unittest

_DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


class AuditDocsTests(unittest.TestCase):
    def test_three_docs_exist(self):
        for name in ("PEDESK_PRODUCT_IA_AUDIT.md",
                     "PEDESK_DEAL_WORKFLOW_MODEL.md",
                     "PEDESK_ROUTE_TAXONOMY.md"):
            self.assertTrue((_DOCS / name).is_file(), f"missing {name}")

    def test_ia_audit_has_key_sections(self):
        t = (_DOCS / "PEDESK_PRODUCT_IA_AUDIT.md").read_text()
        for marker in ("Route inventory", "Per-page audit",
                       "Duplicate / overlap analysis", "Proposed nav map",
                       "Route migration table", "implementation PRs",
                       "requires user approval"):
            self.assertIn(marker, t)

    def test_workflow_model_has_lifecycle_and_promotions(self):
        t = (_DOCS / "PEDESK_DEAL_WORKFLOW_MODEL.md").read_text()
        self.assertIn("Lifecycle stages", t)
        self.assertIn("Promotion actions", t)
        self.assertIn("New Deal", t)

    def test_taxonomy_defines_universes(self):
        t = (_DOCS / "PEDESK_ROUTE_TAXONOMY.md").read_text()
        for chip in ("USER DEALS", "USER PORTFOLIO", "CMS PUBLIC DATA",
                     "BENCHMARK CORPUS", "RESEARCH REFERENCE"):
            self.assertIn(chip, t)

    def test_corpus_as_portfolio_finding_recorded(self):
        # The headline data-semantics finding must be captured honestly.
        t = (_DOCS / "PEDESK_PRODUCT_IA_AUDIT.md").read_text()
        self.assertIn("655", t)
        self.assertIn("load_corpus_deals", t)


if __name__ == "__main__":
    unittest.main()
