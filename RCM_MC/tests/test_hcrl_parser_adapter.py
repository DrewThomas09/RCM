"""Healthcare Revenue Leakage V2 — parser adapter boundary tests.

Proves the decision gate from the plan: the fallback adapter produces
CCD-compatible output (claims with ids/amounts/cpt), ISA-aware
detection recovers transaction type + delimiters, and malformed files
are flagged rather than silently dropped.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from rcm_mc.diligence.parsers import (
    FallbackSegmentAdapter,
    available_adapters,
    detect_file,
)

_FIX = Path(__file__).parent / "fixtures" / "edi"


class TestDetection(unittest.TestCase):
    def test_detect_837p(self):
        det = detect_file(_FIX / "clean_837p.edi")
        self.assertEqual(det.file_type, "edi")
        self.assertTrue(det.is_x12)
        self.assertIn("837P", det.detected_transaction_types)
        self.assertIsNotNone(det.detected_delimiters)
        self.assertEqual(det.detected_delimiters.element, "*")
        self.assertEqual(det.detected_delimiters.component, ":")
        self.assertEqual(det.detected_delimiters.segment, "~")
        self.assertGreater(det.confidence, 0.9)

    def test_detect_835(self):
        det = detect_file(_FIX / "clean_835.edi")
        self.assertTrue(det.is_x12)
        self.assertIn("835", det.detected_transaction_types)

    def test_detect_unknown_suffix(self):
        # A tabular file is not X12.
        det = detect_file(Path("/tmp/nonexistent_report.csv"))
        self.assertEqual(det.file_type, "csv")
        self.assertFalse(det.is_x12)


class TestFallbackAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = FallbackSegmentAdapter()

    def test_parse_837p_extracts_claims(self):
        sets = self.adapter.parse(_FIX / "clean_837p.edi")
        self.assertEqual(len(sets), 1)
        ts = sets[0]
        self.assertEqual(ts.transaction_type, "837P")
        ids = {c["claim_id"] for c in ts.parsed_payload}
        self.assertEqual(ids, {"CLAIM1001", "CLAIM1002"})
        by_id = {c["claim_id"]: c for c in ts.parsed_payload}
        self.assertEqual(by_id["CLAIM1001"]["charge_amount"], 250.0)
        self.assertEqual(by_id["CLAIM1001"]["cpt_code"], "99213")
        self.assertEqual(by_id["CLAIM1001"]["payer"], "MEDICARE")

    def test_parse_835_extracts_payments(self):
        sets = self.adapter.parse(_FIX / "clean_835.edi")
        self.assertEqual(len(sets), 1)
        ts = sets[0]
        self.assertEqual(ts.transaction_type, "835")
        by_id = {c["claim_id"]: c for c in ts.parsed_payload}
        self.assertEqual(by_id["CLAIM1001"]["charge_amount"], 250.0)
        self.assertEqual(by_id["CLAIM1001"]["paid_amount"], 200.0)
        self.assertEqual(by_id["CLAIM1001"]["status_code"], "1")
        # Patient MRN captured from NM1*QC (to be tokenized downstream).
        self.assertEqual(by_id["CLAIM1001"]["patient_id"], "MRN0001")

    def test_validate_clean_is_valid(self):
        rep = self.adapter.validate(_FIX / "clean_835.edi")
        self.assertTrue(rep.is_valid)
        self.assertEqual(rep.parser_name, "fallback_segment")
        self.assertEqual(rep.errors, [])

    def test_validate_malformed_flags_envelope(self):
        rep = self.adapter.validate(_FIX / "malformed_837.edi")
        self.assertFalse(rep.is_valid)
        self.assertTrue(rep.envelope_issues)

    def test_metadata_has_delimiters_and_counts(self):
        meta = self.adapter.extract_metadata(_FIX / "clean_837p.edi")
        self.assertEqual(meta.parser_name, "fallback_segment")
        self.assertIsNotNone(meta.delimiters)
        self.assertGreaterEqual(meta.segment_count, 2)


class TestAdapterRegistry(unittest.TestCase):
    def test_fallback_always_available_and_last(self):
        adapters = available_adapters()
        self.assertTrue(adapters)
        # Fallback must be present and must be the last (lowest-priority)
        # so a library adapter wins ordering when one is installed.
        self.assertEqual(adapters[-1].name, "fallback_segment")


def _x12_available() -> bool:
    try:
        import x12  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_x12_available(), "x12-python not installed")
class TestX12PythonAdapter(unittest.TestCase):
    def setUp(self):
        from rcm_mc.diligence.parsers.x12_python_adapter import X12PythonAdapter
        self.adapter = X12PythonAdapter()

    def test_835_captures_cas_adjustments_and_patient(self):
        ts = self.adapter.parse(_FIX / "clean_835.edi")[0]
        by_id = {c["claim_id"]: c for c in ts.parsed_payload}
        c1 = by_id["CLAIM1001"]
        self.assertEqual(c1["paid_amount"], 200.0)
        self.assertIn("45", c1["adjustment_reason_codes"])   # CO-45 contractual
        self.assertEqual(c1["patient_id"], "MRN0001")
        self.assertEqual(c1["payer"], "MEDICARE")
        # CLAIM1002 has two CAS lines (45 contractual + PR-1 patient resp)
        self.assertEqual(
            set(by_id["CLAIM1002"]["adjustment_reason_codes"]), {"45", "1"})

    def test_837_captures_member_and_cpt(self):
        ts = self.adapter.parse(_FIX / "clean_837p.edi")[0]
        by_id = {c["claim_id"]: c for c in ts.parsed_payload}
        self.assertEqual(by_id["CLAIM1001"]["patient_id"], "MRN0001")
        self.assertEqual(by_id["CLAIM1001"]["cpt_code"], "99213")

    def test_metadata_recovers_envelope(self):
        meta = self.adapter.extract_metadata(_FIX / "clean_835.edi")
        self.assertEqual(meta.sender_id, "MEDICARE")
        self.assertEqual(meta.receiver_id, "ACMEBILL")
        self.assertEqual(meta.delimiters.element, "*")

    def test_primary_when_available(self):
        # When x12-python is installed it must rank ahead of fallback.
        names = [a.name for a in available_adapters()]
        self.assertEqual(names[0], "x12_python")
        self.assertEqual(names[-1], "fallback_segment")


class TestHarness(unittest.TestCase):
    def test_harness_runs_over_fixtures(self):
        from rcm_mc.diligence.parsers.harness import run_harness
        rep = run_harness(_FIX)
        self.assertIn("fallback_segment", rep.availability)
        # At least the fallback produced results for every fixture.
        fb = [r for r in rep.results if r.adapter == "fallback_segment"]
        self.assertGreaterEqual(len(fb), 3)
        clean = [r for r in fb if r.fixture == "clean_835.edi"][0]
        self.assertTrue(clean.is_valid)
        self.assertEqual(clean.claims_extracted, 2)


if __name__ == "__main__":
    unittest.main()
