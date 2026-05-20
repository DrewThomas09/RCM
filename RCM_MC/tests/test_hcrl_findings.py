"""Healthcare Revenue Leakage V2 — findings + follow-up tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.analytics import compute_analytics
from rcm_mc.diligence.findings import generate_findings, generate_follow_ups
from rcm_mc.diligence.ingest.ccd import (
    CanonicalClaim,
    CanonicalClaimsDataset,
    ClaimStatus,
    PayerClass,
)
from rcm_mc.diligence.reconciliation import compute_data_confidence

# Affirmative overstatements we must never make. Note "not guaranteed
# EBITDA" is the *desired* disclaimer, so we forbid only un-negated
# affirmative claims of certainty.
_FORBIDDEN = [
    "guaranteed ebitda upside", "guaranteed recovery", "guaranteed savings",
    "will be recovered", "certain recovery",
]


def _c(i, payer, pc, cpt, npi, charge, paid, adj, codes, status):
    return CanonicalClaim(
        claim_id=f"C{i}", line_number=1, source_system="edi", source_file="f.edi",
        source_row=i, ccd_row_id=str(i), patient_id=f"PT-{i}",
        payer_canonical=payer, payer_class=pc, cpt_code=cpt, billing_npi=npi,
        charge_amount=charge, paid_amount=paid, adjustment_amount=adj,
        adjustment_reason_codes=codes, status=status,
        service_date_from=None,
    )


def _big_ccd():
    claims = []
    # 20 Medicare paid w/ contractual write-down (not leakage).
    for i in range(20):
        claims.append(_c(i, "Medicare", PayerClass.MEDICARE, "99213", "N1",
                         250, 200, 50, ("45",), ClaimStatus.PAID))
    # 20 Aetna prior-auth (CLINICAL) denials — preventable + concentrated.
    for i in range(20, 40):
        claims.append(_c(i, "Aetna", PayerClass.COMMERCIAL, "99214", "N2",
                         480, 0, 480, ("197",), ClaimStatus.DENIED))
    return CanonicalClaimsDataset(claims=claims)


class TestFindings(unittest.TestCase):
    def setUp(self):
        ccd = _big_ccd()
        self.analytics = compute_analytics(ccd)
        self.conf = compute_data_confidence(ccd)
        self.findings = generate_findings(self.analytics, self.conf)

    def test_surfaces_preventable_and_concentration(self):
        types = {f.finding_type for f in self.findings}
        self.assertIn("potentially_preventable_leakage", types)
        self.assertIn("payer_denial_concentration", types)

    def test_preventable_impact_is_aetna_denials(self):
        f = next(f for f in self.findings
                 if f.finding_type == "potentially_preventable_leakage")
        self.assertEqual(f.estimated_impact_amount, 20 * 480.0)
        self.assertTrue(f.limitations)

    def test_no_guaranteed_ebitda_language(self):
        blob = " ".join(
            (f.summary + " " + " ".join(f.limitations)).lower()
            for f in self.findings)
        for phrase in _FORBIDDEN:
            self.assertNotIn(phrase, blob)
        # The conservative caveat must be present on impact findings.
        self.assertIn("not guaranteed ebitda", blob)

    def test_every_finding_has_evidence_and_confidence(self):
        for f in self.findings:
            self.assertTrue(f.evidence)
            self.assertIn(f.confidence, ("high", "medium", "low"))


class TestFollowUps(unittest.TestCase):
    def test_dedupes_and_includes_baseline(self):
        ccd = _big_ccd()
        findings = generate_findings(
            compute_analytics(ccd), compute_data_confidence(ccd))
        pkg = generate_follow_ups(findings)
        # No duplicate questions / documents.
        self.assertEqual(len(pkg.questions), len(set(q.lower() for q in pkg.questions)))
        self.assertEqual(
            len(pkg.document_requests),
            len(set(d.lower() for d in pkg.document_requests)))
        # Baseline always present.
        self.assertTrue(any("net collection rate" in q.lower() for q in pkg.questions))
        self.assertTrue(any("ar aging" in d.lower() for d in pkg.document_requests))


if __name__ == "__main__":
    unittest.main()
