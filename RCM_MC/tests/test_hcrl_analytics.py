"""Healthcare Revenue Leakage V2 — analytics marts tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.analytics import compute_analytics
from rcm_mc.diligence.ingest.ccd import (
    CanonicalClaim,
    CanonicalClaimsDataset,
    ClaimStatus,
    PayerClass,
)


def _c(i, payer, pc, cpt, npi, charge, paid, adj, codes, status):
    return CanonicalClaim(
        claim_id=f"C{i}", line_number=1, source_system="edi", source_file="f.edi",
        source_row=i, ccd_row_id=str(i), patient_id=f"PT-{i}",
        payer_canonical=payer, payer_class=pc, cpt_code=cpt, billing_npi=npi,
        charge_amount=charge, paid_amount=paid, adjustment_amount=adj,
        adjustment_reason_codes=codes, status=status,
    )


def _ccd():
    return CanonicalClaimsDataset(claims=[
        # Contractual write-down — NOT leakage.
        _c(1, "Medicare", PayerClass.MEDICARE, "99213", "N1", 250, 200, 50,
           ("45",), ClaimStatus.PAID),
        # Prior-auth (CLINICAL) denial — likely preventable.
        _c(2, "Aetna", PayerClass.COMMERCIAL, "99214", "N1", 480, 0, 480,
           ("197",), ClaimStatus.DENIED),
        # Timely-filing (PAYER_BEHAVIOR) denial — possibly preventable.
        _c(3, "Aetna", PayerClass.COMMERCIAL, "99213", "N2", 300, 0, 300,
           ("29",), ClaimStatus.DENIED),
    ])


class TestTotals(unittest.TestCase):
    def setUp(self):
        self.r = compute_analytics(_ccd())

    def test_money_totals(self):
        t = self.r.totals
        self.assertEqual(t.gross_charges, 1030.0)
        self.assertEqual(t.paid_amount, 200.0)
        self.assertEqual(t.adjustment_amount, 830.0)

    def test_contractual_excluded_from_denial(self):
        t = self.r.totals
        self.assertEqual(t.contractual_adjustments, 50.0)
        self.assertEqual(t.denial_dollars, 780.0)        # 480 + 300, no contractual
        self.assertEqual(t.denied_claim_count, 2)

    def test_preventable_is_conservative(self):
        # CLINICAL (likely) + PAYER_BEHAVIOR (possibly) = 780; contractual excluded.
        self.assertEqual(self.r.totals.potentially_preventable_leakage, 780.0)

    def test_collection_rate(self):
        self.assertAlmostEqual(self.r.totals.gross_collection_rate, 200 / 1030, places=4)


class TestBreakdowns(unittest.TestCase):
    def setUp(self):
        self.r = compute_analytics(_ccd())

    def test_category_breakdown(self):
        by = {c.category: c for c in self.r.by_category}
        self.assertEqual(by["CONTRACTUAL"].dollars, 50.0)
        self.assertEqual(by["CONTRACTUAL"].ebitda_relevance, "not_applicable")
        self.assertEqual(by["CLINICAL"].dollars, 480.0)
        self.assertEqual(by["CLINICAL"].preventability, "likely_preventable")
        self.assertEqual(by["PAYER_BEHAVIOR"].dollars, 300.0)

    def test_payer_rollup_sorted_by_denial(self):
        self.assertEqual(self.r.by_payer[0].key, "Aetna")
        self.assertEqual(self.r.by_payer[0].denial_dollars, 780.0)

    def test_cpt_and_provider_rollups(self):
        cpt = {g.key: g for g in self.r.by_cpt}
        self.assertEqual(cpt["99214"].denial_dollars, 480.0)
        self.assertEqual(cpt["99213"].denial_dollars, 300.0)
        prov = {g.key: g for g in self.r.by_provider}
        self.assertEqual(prov["N1"].denial_dollars, 480.0)
        self.assertEqual(prov["N2"].denial_dollars, 300.0)

    def test_concentration(self):
        # All paid dollars sit with Medicare/N1/99213 in this fixture.
        self.assertEqual(self.r.payer_concentration_top1_pct, 1.0)


if __name__ == "__main__":
    unittest.main()
