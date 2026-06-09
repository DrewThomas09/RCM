"""Regression: 837 parsers attribute the billing provider (NM1*85) to EVERY
claim it governs, so revenue-leakage analytics resolve by_provider correctly.

NM1*85 (loop 2010AA) is a HL-level header: one billing provider governs all
claims beneath it. Two bugs dropped it:
  • the fallback segment reader never captured NM1*85 at all (billing_npi
    stayed None → by_provider empty);
  • the x12-python adapter captured it but reset pending_npi after each CLM,
    so only the FIRST claim under a provider kept the NPI.
Both are fixed: the NPI persists across claims until a new NM1*85 replaces it.
"""
from __future__ import annotations

import unittest
from pathlib import Path

_FIX = Path(__file__).parent / "fixtures" / "edi"


class FallbackBillingProviderTests(unittest.TestCase):
    def test_both_claims_carry_billing_npi(self):
        from rcm_mc.diligence.snapshot import run_snapshot
        res = run_snapshot([_FIX / "clean_837p.edi", _FIX / "clean_835.edi"],
                           deal_name="Atlas", salt="s")
        # The fixture has ONE NM1*85 (1234567893) governing BOTH claims.
        npis = {c.billing_npi for c in res.ccd.claims}
        self.assertEqual(npis, {"1234567893"})
        self.assertEqual([(p.key, p.claim_count) for p in res.analytics.by_provider],
                         [("1234567893", 2)])


class _Seg:
    """Minimal stand-in for an x12-python segment (segment_id + elements)."""
    def __init__(self, sid, *vals):
        self.segment_id = sid
        self.elements = list(vals)


class X12BillingProviderPersistTests(unittest.TestCase):
    def test_billing_npi_persists_across_claims(self):
        # One NM1*85, then two CLMs — both must inherit the billing NPI.
        from rcm_mc.diligence.parsers.x12_python_adapter import _claims_from_837
        segs = [
            _Seg("NM1", "85", "2", "RIVERSIDE", "", "", "", "", "XX", "1234567893"),
            _Seg("NM1", "PR", "2", "MEDICARE"),
            _Seg("CLM", "C1", "250"),
            _Seg("CLM", "C2", "480"),
        ]
        claims = _claims_from_837(segs)
        self.assertEqual([c["claim_id"] for c in claims], ["C1", "C2"])
        self.assertEqual([c["billing_npi"] for c in claims],
                         ["1234567893", "1234567893"])

    def test_new_billing_provider_overrides(self):
        from rcm_mc.diligence.parsers.x12_python_adapter import _claims_from_837
        segs = [
            _Seg("NM1", "85", "2", "A", "", "", "", "", "XX", "1111111111"),
            _Seg("CLM", "C1", "100"),
            _Seg("NM1", "85", "2", "B", "", "", "", "", "XX", "2222222222"),
            _Seg("CLM", "C2", "200"),
        ]
        claims = _claims_from_837(segs)
        self.assertEqual([c["billing_npi"] for c in claims],
                         ["1111111111", "2222222222"])


if __name__ == "__main__":
    unittest.main()
