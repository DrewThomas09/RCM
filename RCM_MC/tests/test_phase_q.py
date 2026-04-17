"""Tests for Phase Q: EDI parsing, claim analytics, PMS connectors (Prompts 75-76).

25 tests covering:
  - EDI 837 / 835 parsing with synthetic content strings
  - Claim matching (837 <-> 835)
  - SQLite round-trip for claim records
  - Denial rate analytics by payer / CARC / status
  - Top denial reasons ranking
  - Payer AR aging buckets
  - PMSConnector ABC enforcement
  - EpicConnector stub behaviour
  - Credential storage round-trip (base64 placeholder encryption)

All external API / network calls are mocked where applicable.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data.edi_parser import (
    ClaimSubmission,
    RemittanceAdvice,
    parse_837,
    parse_835,
    match_837_835,
    save_claims,
    load_claims,
)
from rcm_mc.data.claim_analytics import (
    denial_rate_by_dimension,
    top_denial_reasons,
    payer_aging,
)
from rcm_mc.integrations.pms.base import (
    PMSConnector,
    save_credentials,
    load_credentials,
)
from rcm_mc.integrations.pms.epic import EpicConnector


# ── Synthetic EDI content ─────────────────────────────────────────────

SAMPLE_837 = (
    "ISA*00*          *00*          *ZZ*SENDER         *ZZ*BCBS           *230101*1200*^*00501*000000001*0*P*:~"
    "GS*HC*SENDER*BCBS*20230101*1200*1*X*005010X222A1~"
    "ST*837*0001~"
    "NM1*85*1*SMITH*JOHN*****XX*1234567890~"
    "NM1*PR*2*BLUE CROSS*****PI*54321~"
    "CLM*CLM123*1500***11:B:1~"
    "DTP*472*D8*20250115~"
    "HI*ABK:J069*ABF:E119~"
    "DRG*470~"
    "SV1*HC:99213*150*UN*1~"
    "CLM*CLM456*2200***11:B:1~"
    "DTP*472*D8*20250120~"
    "HI*ABK:M545~"
    "NM1*PR*2*AETNA*****PI*99999~"
    "SE*14*0001~"
    "GE*1*1~"
    "IEA*1*000000001~"
)

SAMPLE_835 = (
    "ISA*00*          *00*          *ZZ*PAYER          *ZZ*PROVIDER       *230201*0800*^*00501*000000002*0*P*:~"
    "GS*HP*PAYER*PROVIDER*20230201*0800*2*X*005010X221A1~"
    "ST*835*0002~"
    "CLP*CLM123*1*1500*1200*300~"
    "CAS*CO*45*300~"
    "DTM*036*20250201~"
    "CLP*CLM456*1*2200*0*2200~"
    "CAS*CO*29*1500*CR*16*700~"
    "DTM*036*20250210~"
    "SE*8*0002~"
    "GE*1*2~"
    "IEA*1*000000002~"
)


def _make_store():
    """Create a temp-file-backed PortfolioStore for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    store = PortfolioStore(tmp.name)
    store.init_db()
    return store


# ── EDI 837 Tests ─────────────────────────────────────────────────────

class TestParse837(unittest.TestCase):
    def test_extracts_claims_with_correct_ids_and_charges(self):
        claims = parse_837(SAMPLE_837)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0].claim_id, "CLM123")
        self.assertAlmostEqual(claims[0].total_charge, 1500.0)
        self.assertEqual(claims[1].claim_id, "CLM456")
        self.assertAlmostEqual(claims[1].total_charge, 2200.0)

    def test_dx_codes_and_drg(self):
        claims = parse_837(SAMPLE_837)
        self.assertIn("J069", claims[0].dx_codes)
        self.assertIn("E119", claims[0].dx_codes)
        self.assertEqual(claims[0].drg_code, "470")
        self.assertIn("M545", claims[1].dx_codes)

    def test_service_date_and_provider_npi(self):
        claims = parse_837(SAMPLE_837)
        self.assertEqual(claims[0].service_date, "20250115")
        self.assertEqual(claims[0].provider_npi, "1234567890")

    def test_payer_from_nm1(self):
        """NM1*PR segment overrides ISA-level payer."""
        claims = parse_837(SAMPLE_837)
        self.assertEqual(claims[0].payer, "BLUE CROSS")
        self.assertEqual(claims[1].payer, "AETNA")

    def test_empty_content(self):
        claims = parse_837("")
        self.assertEqual(claims, [])


# ── EDI 835 Tests ─────────────────────────────────────────────────────

class TestParse835(unittest.TestCase):
    def test_extracts_remittances_with_amounts(self):
        ras = parse_835(SAMPLE_835)
        self.assertEqual(len(ras), 2)
        self.assertEqual(ras[0].claim_id, "CLM123")
        self.assertAlmostEqual(ras[0].paid_amount, 1200.0)

    def test_claim_status_classification(self):
        ras = parse_835(SAMPLE_835)
        self.assertEqual(ras[0].claim_status, "partial")
        self.assertEqual(ras[1].claim_status, "denied")

    def test_carc_codes_and_adjudication_date(self):
        ras = parse_835(SAMPLE_835)
        self.assertIn("45", ras[0].carc_codes)
        self.assertIn("29", ras[1].carc_codes)
        self.assertIn("16", ras[1].carc_codes)
        self.assertEqual(ras[0].adjudication_date, "20250201")


# ── Matching ──────────────────────────────────────────────────────────

class TestMatch837835(unittest.TestCase):
    def test_matched_records_count_and_turnaround(self):
        subs = parse_837(SAMPLE_837)
        ras = parse_835(SAMPLE_835)
        matched = match_837_835(subs, ras)
        self.assertEqual(len(matched), 2)
        rec = [m for m in matched if m["claim_id"] == "CLM123"][0]
        # 20250115 -> 20250201 = 17 days
        self.assertEqual(rec["turnaround_days"], 17)

    def test_denial_reason_populated(self):
        subs = parse_837(SAMPLE_837)
        ras = parse_835(SAMPLE_835)
        matched = match_837_835(subs, ras)
        rec = [m for m in matched if m["claim_id"] == "CLM456"][0]
        self.assertEqual(rec["denial_reason"], "29")

    def test_unmatched_remittance(self):
        """Remittance without a matching submission still yields a record."""
        subs = []
        ras = parse_835(SAMPLE_835)
        matched = match_837_835(subs, ras)
        self.assertEqual(len(matched), 2)
        self.assertEqual(matched[0]["payer"], "")
        self.assertIsNone(matched[0]["turnaround_days"])


# ── SQLite round-trip ─────────────────────────────────────────────────

class TestClaimStorage(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        store = _make_store()
        subs = parse_837(SAMPLE_837)
        ras = parse_835(SAMPLE_835)
        matched = match_837_835(subs, ras)
        count = save_claims(store, "DEAL001", matched)
        self.assertEqual(count, 2)
        loaded = load_claims(store, "DEAL001")
        self.assertEqual(len(loaded), 2)
        ids = {r["claim_id"] for r in loaded}
        self.assertEqual(ids, {"CLM123", "CLM456"})

    def test_load_empty_deal(self):
        store = _make_store()
        loaded = load_claims(store, "NONEXISTENT")
        self.assertEqual(loaded, [])


# ── Claim analytics ──────────────────────────────────────────────────

class TestClaimAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = _make_store()
        subs = parse_837(SAMPLE_837)
        ras = parse_835(SAMPLE_835)
        matched = match_837_835(subs, ras)
        save_claims(cls.store, "DEAL_A", matched)

    def test_denial_rate_by_payer(self):
        result = denial_rate_by_dimension(self.store, "DEAL_A", dimension="payer")
        self.assertIn("BLUE CROSS", result)
        # BLUE CROSS has CLM123 which is partial, not denied
        self.assertEqual(result["BLUE CROSS"]["denied"], 0)

    def test_denial_rate_by_status(self):
        result = denial_rate_by_dimension(self.store, "DEAL_A", dimension="status")
        self.assertIn("denied", result)
        self.assertEqual(result["denied"]["total"], 1)

    def test_denial_rate_by_carc(self):
        result = denial_rate_by_dimension(self.store, "DEAL_A", dimension="carc")
        self.assertIsInstance(result, dict)
        # At least one CARC code bucket should exist
        self.assertGreater(len(result), 0)

    def test_denial_rate_invalid_dimension(self):
        with self.assertRaises(ValueError):
            denial_rate_by_dimension(self.store, "DEAL_A", dimension="invalid")

    def test_top_denial_reasons(self):
        reasons = top_denial_reasons(self.store, "DEAL_A", limit=5)
        self.assertIsInstance(reasons, list)
        carc_codes_found = {r["carc"] for r in reasons}
        self.assertGreater(len(carc_codes_found), 0)
        # Each entry has expected keys
        for r in reasons:
            self.assertIn("count", r)
            self.assertIn("total_denial_dollars", r)
            self.assertIn("pct_of_denials", r)

    @patch("rcm_mc.data.claim_analytics.datetime")
    def test_payer_aging(self, mock_dt):
        """Use a fixed 'today' so aging buckets are deterministic."""
        mock_dt.now.return_value = datetime(2025, 4, 15, tzinfo=timezone.utc)
        mock_dt.strptime = datetime.strptime
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = payer_aging(self.store, "DEAL_A")
        self.assertIsInstance(result, dict)
        total_outstanding = sum(
            v.get("total_outstanding", 0) for v in result.values()
        )
        self.assertGreater(total_outstanding, 0)


# ── PMS Connector ────────────────────────────────────────────────────

class TestPMSConnector(unittest.TestCase):
    def test_abc_cannot_instantiate(self):
        """PMSConnector is abstract -- direct instantiation must fail."""
        with self.assertRaises(TypeError):
            PMSConnector()

    def test_epic_is_subclass_and_stubs_return_defaults(self):
        self.assertTrue(issubclass(EpicConnector, PMSConnector))
        epic = EpicConnector(config={"base_url": "https://fhir.epic.com/R4"})
        self.assertFalse(epic.test_connection())
        self.assertEqual(epic.pull_encounters(("2025-01-01", "2025-01-31")), [])
        self.assertEqual(epic.pull_charges(("2025-01-01", "2025-01-31")), [])
        self.assertEqual(epic.pull_ar_aging(), {})

    def test_epic_no_url(self):
        epic = EpicConnector(config={})
        self.assertFalse(epic.test_connection())


# ── Credential storage ──────────────────────────────────────────────

class TestCredentialStorage(unittest.TestCase):
    def test_save_load_roundtrip(self):
        store = _make_store()
        creds = {
            "base_url": "https://fhir.epic.com/R4",
            "client_id": "abc123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        }
        save_credentials(store, "DEAL_X", "epic", creds)
        loaded = load_credentials(store, "DEAL_X", "epic")
        self.assertEqual(loaded, creds)

    def test_load_missing_returns_none(self):
        store = _make_store()
        result = load_credentials(store, "DEAL_X", "nonexistent")
        self.assertIsNone(result)

    def test_upsert_overwrites(self):
        store = _make_store()
        save_credentials(store, "DEAL_Y", "epic", {"key": "v1"})
        save_credentials(store, "DEAL_Y", "epic", {"key": "v2"})
        loaded = load_credentials(store, "DEAL_Y", "epic")
        self.assertEqual(loaded["key"], "v2")


if __name__ == "__main__":
    unittest.main()
