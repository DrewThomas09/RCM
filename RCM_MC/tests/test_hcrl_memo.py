"""Healthcare Revenue Leakage V2 — Markdown memo tests (full pipeline)."""
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
from rcm_mc.diligence.reporting import MemoContext, render_markdown_memo


def _c(i, payer, pc, cpt, npi, charge, paid, adj, codes, status):
    return CanonicalClaim(
        claim_id=f"C{i}", line_number=1, source_system="edi", source_file="f.edi",
        source_row=i, ccd_row_id=str(i), patient_id=f"PT-{i}",  # tokenized MRN
        payer_canonical=payer, payer_class=pc, cpt_code=cpt, billing_npi=npi,
        charge_amount=charge, paid_amount=paid, adjustment_amount=adj,
        adjustment_reason_codes=codes, status=status,
    )


def _ccd():
    claims = []
    for i in range(20):
        claims.append(_c(i, "Medicare", PayerClass.MEDICARE, "99213", "N1",
                         250, 200, 50, ("45",), ClaimStatus.PAID))
    for i in range(20, 40):
        claims.append(_c(i, "Aetna", PayerClass.COMMERCIAL, "99214", "N2",
                         480, 0, 480, ("197",), ClaimStatus.DENIED))
    return CanonicalClaimsDataset(claims=claims)


def _render():
    ccd = _ccd()
    analytics = compute_analytics(ccd)
    conf = compute_data_confidence(ccd)
    findings = generate_findings(analytics, conf)
    follow_ups = generate_follow_ups(findings)
    return render_markdown_memo(
        analytics=analytics, confidence=conf, findings=findings,
        follow_ups=follow_ups,
        context=MemoContext(deal_name="Project Atlas", source_file_count=2,
                            transaction_types=("837P", "835"),
                            prepared_on="2026-05-20"),
    )


class TestMemo(unittest.TestCase):
    def setUp(self):
        self.memo = _render()

    def test_has_all_eleven_sections(self):
        for n, title in [
            (1, "Executive summary"), (2, "Data reviewed"),
            (3, "Data quality and limitations"), (4, "Revenue leakage overview"),
            (5, "Payer-level findings"), (6, "Procedure / CPT-level findings"),
            (7, "Provider-level findings"), (8, "Potential EBITDA implications"),
            (9, "Follow-up diligence questions"), (10, "Additional data requests"),
            (11, "Methodology and caveats"),
        ]:
            self.assertIn(f"## {n}. {title}", self.memo)

    def test_phi_safe_no_tokens_or_mrn(self):
        # The memo consumes only aggregates — no patient tokens / MRNs.
        # Use a word boundary so "CPT-level" is not a false positive; real
        # tokens are "PT-<id>" at a word boundary.
        import re
        self.assertIsNone(re.search(r"\bPT-\w", self.memo))
        self.assertNotIn("MRN", self.memo)
        # None of the specific tokenized patient ids leak through.
        for i in range(40):
            self.assertNotIn(f"PT-{i} ", self.memo)

    def test_conservative_language(self):
        low = self.memo.lower()
        self.assertIn("not guaranteed ebitda", low)
        self.assertIn("subject to validation", low)
        self.assertNotIn("guaranteed ebitda upside", low)

    def test_key_numbers_present(self):
        # Gross charges = 20*250 + 20*480 = 14600; preventable = 20*480 = 9600.
        self.assertIn("$14,600", self.memo)
        self.assertIn("$9,600", self.memo)

    def test_includes_payer_and_caveats(self):
        self.assertIn("Aetna", self.memo)
        self.assertIn("tokenized", self.memo)
        self.assertIn("Contractual adjustments are excluded", self.memo)


if __name__ == "__main__":
    unittest.main()
