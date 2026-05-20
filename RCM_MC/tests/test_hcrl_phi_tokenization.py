"""Healthcare Revenue Leakage V2 — PHI tokenization tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.ingest.ccd import CanonicalClaim, CanonicalClaimsDataset
from rcm_mc.diligence.security import PhiTokenizer, new_salt, tokenize_ccd


def _claim(row_id: str, mrn: str) -> CanonicalClaim:
    return CanonicalClaim(
        claim_id=f"C{row_id}", line_number=1, source_system="edi_837",
        source_file="f.edi", source_row=int(row_id), ccd_row_id=row_id,
        patient_id=mrn,
    )


def _ccd(*pairs: tuple[str, str]) -> CanonicalClaimsDataset:
    return CanonicalClaimsDataset(claims=[_claim(r, m) for r, m in pairs])


class TestPhiTokenizer(unittest.TestCase):
    def test_deterministic_for_salt(self):
        t = PhiTokenizer(salt="abc123")
        self.assertEqual(t.token("MRN0001"), t.token("MRN0001"))

    def test_distinct_salts_distinct_tokens(self):
        a, b = PhiTokenizer(salt="s1"), PhiTokenizer(salt="s2")
        self.assertNotEqual(a.token("MRN0001"), b.token("MRN0001"))

    def test_token_shape_and_no_raw(self):
        tok = PhiTokenizer(salt="x").token("MRN0001")
        self.assertTrue(tok.startswith("PT-"))
        self.assertNotIn("MRN0001", tok)

    def test_empty_returns_none(self):
        t = PhiTokenizer(salt="x")
        self.assertIsNone(t.token(""))
        self.assertIsNone(t.token(None))

    def test_idempotent(self):
        t = PhiTokenizer(salt="x")
        once = t.token("MRN0001")
        self.assertEqual(t.token(once), once)


class TestTokenizeCcd(unittest.TestCase):
    def test_replaces_raw_with_token(self):
        ccd = _ccd(("1", "MRN0001"), ("2", "MRN0002"))
        res = tokenize_ccd(ccd, PhiTokenizer(salt="x"))
        ids = [c.patient_id for c in res.ccd.claims]
        self.assertTrue(all(i.startswith("PT-") for i in ids))
        # raw MRNs no longer present anywhere on the CCD claims
        self.assertNotIn("MRN0001", ids)
        self.assertEqual(res.tokenized_rows, 2)
        self.assertEqual(len(res.tokens), 2)

    def test_same_mrn_same_token_preserves_matching(self):
        # An 837 row and its 835 row share an MRN -> must share a token
        # so 835<->837 matching by member still works post-tokenization.
        ccd = _ccd(("1", "MRN0001"), ("2", "MRN0001"))
        res = tokenize_ccd(ccd, PhiTokenizer(salt="x"))
        toks = {c.patient_id for c in res.ccd.claims}
        self.assertEqual(len(toks), 1)
        self.assertEqual(len(res.tokens), 1)

    def test_log_is_phi_free(self):
        ccd = _ccd(("1", "MRN0001"))
        res = tokenize_ccd(ccd, PhiTokenizer(salt="x"))
        entries = res.ccd.log.by_rule("phi_tokenize:patient")
        self.assertEqual(len(entries), 1)
        self.assertNotIn("MRN0001", entries[0].source_value or "")
        self.assertEqual(entries[0].source_value, "<redacted-phi>")

    def test_missing_patient_logged_warn(self):
        ccd = _ccd(("1", ""))
        res = tokenize_ccd(ccd, PhiTokenizer(salt="x"))
        self.assertEqual(res.empty_patient_rows, 1)
        self.assertTrue(res.ccd.log.by_rule("phi_tokenize:missing"))

    def test_idempotent_over_ccd(self):
        ccd = _ccd(("1", "MRN0001"))
        t = PhiTokenizer(salt="x")
        first = tokenize_ccd(ccd, t).ccd.claims[0].patient_id
        again = tokenize_ccd(ccd, t)  # second pass: already tokenized
        self.assertEqual(again.ccd.claims[0].patient_id, first)
        self.assertEqual(again.tokenized_rows, 0)

    def test_salt_factory_unique(self):
        self.assertNotEqual(new_salt(), new_salt())


if __name__ == "__main__":
    unittest.main()
