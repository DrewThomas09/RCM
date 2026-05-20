"""Healthcare Revenue Leakage V2 — 837<->835 matching tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from rcm_mc.diligence.matching import match_claims
from rcm_mc.diligence.parsers import FallbackSegmentAdapter

_FIX = Path(__file__).parent / "fixtures" / "edi"


class TestExactMatch(unittest.TestCase):
    def test_exact_claim_id_high(self):
        sub = [{"claim_id": "C1", "charge_amount": 100.0}]
        rem = [{"claim_id": "C1", "paid_amount": 80.0}]
        res = match_claims(sub, rem)
        self.assertEqual(len(res.matches), 1)
        m = res.matches[0]
        self.assertEqual(m.match_confidence, "high")
        self.assertEqual(m.match_score, 1.0)
        self.assertEqual(m.review_status, "auto")
        self.assertEqual(res.unmatched_submitted, [])
        self.assertEqual(res.unmatched_remittance, [])

    def test_one_remittance_per_submission(self):
        sub = [{"claim_id": "C1"}, {"claim_id": "C1"}]
        rem = [{"claim_id": "C1"}]
        res = match_claims(sub, rem)
        # Only one of the two submissions can claim the single remittance.
        self.assertEqual(res.counts()["high"], 1)
        self.assertEqual(len(res.unmatched_submitted), 1)


class TestCompositeMatch(unittest.TestCase):
    def test_strong_composite_medium(self):
        sub = [{"claim_id": "AAA", "patient_id": "PT-x", "service_date_from": "20240515",
                "charge_amount": 250.0, "cpt_code": "99213", "billing_npi": "1234567893",
                "payer": "MEDICARE"}]
        # Different claim_id (payer re-numbered it) but same everything else.
        rem = [{"claim_id": "ZZZ", "patient_id": "PT-x", "service_date_from": "20240515",
                "charge_amount": 250.0, "cpt_code": "99213", "billing_npi": "1234567893",
                "payer": "MEDICARE", "paid_amount": 200.0}]
        res = match_claims(sub, rem)
        self.assertEqual(len(res.matches), 1)
        self.assertEqual(res.matches[0].match_confidence, "medium")
        self.assertEqual(res.matches[0].review_status, "auto")

    def test_weak_composite_low_needs_review(self):
        sub = [{"claim_id": "AAA", "patient_id": "PT-x", "service_date_from": "20240515"}]
        rem = [{"claim_id": "ZZZ", "patient_id": "PT-x", "service_date_from": "20240601"}]
        res = match_claims(sub, rem)
        self.assertEqual(len(res.matches), 1)
        self.assertEqual(res.matches[0].match_confidence, "low")
        self.assertEqual(res.matches[0].review_status, "needs_review")

    def test_no_overlap_unmatched(self):
        sub = [{"claim_id": "AAA", "patient_id": "PT-x", "cpt_code": "99213"}]
        rem = [{"claim_id": "ZZZ", "patient_id": "PT-y", "cpt_code": "00000"}]
        res = match_claims(sub, rem)
        self.assertEqual(res.matches, [])
        self.assertEqual(res.unmatched_submitted, ["AAA"])
        self.assertEqual(res.unmatched_remittance, ["ZZZ"])


class TestEndToEndFixtures(unittest.TestCase):
    def test_matched_pair_via_adapter(self):
        adapter = FallbackSegmentAdapter()
        submitted = adapter.parse(_FIX / "clean_837p.edi")[0].parsed_payload
        remittance = adapter.parse(_FIX / "clean_835.edi")[0].parsed_payload
        res = match_claims(submitted, remittance)
        # CLAIM1001 + CLAIM1002 share ids across the 837 and 835 fixtures.
        self.assertEqual(res.counts()["high"], 2)
        self.assertEqual(res.unmatched_submitted, [])
        self.assertEqual(res.unmatched_remittance, [])


if __name__ == "__main__":
    unittest.main()
