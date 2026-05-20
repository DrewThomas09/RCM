"""Healthcare Revenue Leakage V2 — Data Confidence Score tests."""
from __future__ import annotations

import unittest
from datetime import date

from rcm_mc.diligence.ingest.ccd import (
    CanonicalClaim,
    CanonicalClaimsDataset,
    PayerClass,
)
from rcm_mc.diligence.matching import match_claims
from rcm_mc.diligence.reconciliation import compute_data_confidence


def _claim(i: int, **kw) -> CanonicalClaim:
    base = dict(
        claim_id=f"C{i}", line_number=1, source_system="edi",
        source_file="f.edi", source_row=i, ccd_row_id=str(i),
        patient_id=f"PT-{i}",
        payer_class=PayerClass.MEDICARE,
        billing_npi="1234567893",
        service_date_from=date(2024, 5, 15),
        charge_amount=100.0,
    )
    base.update(kw)
    return CanonicalClaim(**base)


def _ccd(claims) -> CanonicalClaimsDataset:
    return CanonicalClaimsDataset(claims=claims)


class TestCleanData(unittest.TestCase):
    def test_clean_scores_high(self):
        ccd = _ccd([_claim(i) for i in range(10)])
        rep = compute_data_confidence(ccd)
        self.assertGreaterEqual(rep.score, 95)
        self.assertEqual([i for i in rep.issues if i.severity == "ERROR"], [])
        self.assertTrue(any("charge amount" in s for s in rep.summaries))

    def test_empty_scores_zero(self):
        rep = compute_data_confidence(_ccd([]))
        self.assertEqual(rep.score, 0)
        self.assertTrue(any(i.issue_type == "no_claims" for i in rep.issues))


class TestDeficiencies(unittest.TestCase):
    def test_missing_payer_and_charge_deducts(self):
        claims = [_claim(i) for i in range(10)]
        for c in claims[:5]:
            c.payer_class = PayerClass.UNKNOWN
            c.charge_amount = None
        rep = compute_data_confidence(_ccd(claims))
        self.assertLess(rep.score, 90)
        types = {i.issue_type for i in rep.issues}
        self.assertIn("unresolved_payer", types)
        self.assertIn("missing_charge", types)

    def test_unmapped_adjustment_codes_flagged(self):
        claims = [_claim(i) for i in range(4)]
        claims[0].adjustment_reason_codes = ("45",)      # mapped (contractual)
        claims[1].adjustment_reason_codes = ("ZZZ9",)    # unmapped
        rep = compute_data_confidence(_ccd(claims))
        self.assertIn("adjustment_codes_mapped_pct", rep.metrics)
        self.assertTrue(any(i.issue_type == "unmapped_adjustment_codes"
                            for i in rep.issues))

    def test_duplicate_claim_ids_flagged(self):
        claims = [_claim(1), _claim(1), _claim(2)]
        rep = compute_data_confidence(_ccd(claims))
        self.assertTrue(any(i.issue_type == "duplicate_claims" for i in rep.issues))
        self.assertEqual(rep.metrics["duplicate_claim_rows"], 1)


class TestMatchIntegration(unittest.TestCase):
    def test_unmatched_reduces_score_and_reports_dollars(self):
        submitted = [
            {"claim_id": "C1", "charge_amount": 100.0},
            {"claim_id": "C2", "charge_amount": 400.0},
        ]
        remittance = [{"claim_id": "C1", "paid_amount": 80.0}]
        mr = match_claims(submitted, remittance)
        ccd = _ccd([_claim(1), _claim(2)])
        rep = compute_data_confidence(
            ccd, match_result=mr, submitted=submitted, remittance=remittance)
        self.assertLess(rep.score, 100)
        self.assertIn("submitted_matched_pct", rep.metrics)
        # 50% of submitted claims matched; $400 unreconciled.
        self.assertTrue(any("could not be reconciled" in s for s in rep.summaries))
        self.assertTrue(any(i.issue_type == "unmatched_submitted" for i in rep.issues))


if __name__ == "__main__":
    unittest.main()
