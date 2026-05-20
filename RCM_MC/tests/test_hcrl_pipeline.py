"""Healthcare Revenue Leakage V2 — end-to-end snapshot pipeline test.

Proves acceptance criteria 1-17 work together: EDI files → CCD →
tokenize → match → confidence → analytics → findings → memo.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from rcm_mc.diligence.snapshot import build_ccd_from_files, run_snapshot

_FIX = Path(__file__).parent / "fixtures" / "edi"


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.res = run_snapshot(
            [_FIX / "clean_837p.edi", _FIX / "clean_835.edi"],
            deal_name="Project Atlas", salt="testsalt")

    def test_builds_one_row_per_claim(self):
        # 835 remittance rows are the source of truth; 837 enriches.
        self.assertEqual(len(self.res.ccd.claims), 2)
        ids = {c.claim_id for c in self.res.ccd.claims}
        self.assertEqual(ids, {"CLAIM1001", "CLAIM1002"})

    def test_matches_pair_high_confidence(self):
        self.assertEqual(self.res.match.counts()["high"], 2)

    def test_patient_tokenized_no_raw_mrn(self):
        for c in self.res.ccd.claims:
            self.assertTrue(c.patient_id.startswith("PT-"))
            self.assertNotIn("MRN", c.patient_id)

    def test_financials_from_remittance(self):
        t = self.res.analytics.totals
        self.assertEqual(t.gross_charges, 730.0)   # 250 + 480
        self.assertEqual(t.paid_amount, 400.0)      # 200 + 200

    def test_provider_and_payer_resolved(self):
        # NM1*85 / N1*PE NPI captured; payer resolved to canonical.
        self.assertTrue(self.res.analytics.by_provider)
        self.assertEqual(self.res.analytics.by_provider[0].key, "1234567893")
        payers = {p.key for p in self.res.analytics.by_payer}
        self.assertIn("Medicare", payers)

    def test_memo_renders(self):
        self.assertIn("## 1. Executive summary", self.res.memo_markdown)
        self.assertIn("Project Atlas", self.res.memo_markdown)
        self.assertIn("not guaranteed EBITDA", self.res.memo_markdown)

    def test_confidence_score_in_range(self):
        self.assertIsInstance(self.res.confidence.score, int)
        self.assertGreaterEqual(self.res.confidence.score, 0)
        self.assertLessEqual(self.res.confidence.score, 100)

    def test_result_is_json_serialisable(self):
        import json
        json.dumps(self.res.to_dict())  # must not raise

    def test_parser_used_recorded(self):
        # x12-python is installed in dev; fallback otherwise. Either is fine.
        self.assertIn(self.res.parser_used, ("x12_python", "fallback_segment"))


class TestBuildOnly(unittest.TestCase):
    def test_build_partitions_transaction_types(self):
        build = build_ccd_from_files([_FIX / "clean_837p.edi", _FIX / "clean_835.edi"])
        self.assertIn("835", build.transaction_types)
        self.assertTrue(any(t.startswith("837") for t in build.transaction_types))
        self.assertEqual(len(build.submitted), 2)
        self.assertEqual(len(build.remittance), 2)


if __name__ == "__main__":
    unittest.main()
