"""Tests for the price-transparency foundation: NPPES + Hospital
MRF + Payer TiC ingestion + normalization + read helpers.

Each layer has parser + loader + read tests against checked-in
fixtures. The fixtures are tiny (a handful of rows) but exercise
the full schema shape: payer-specific charges, cash prices, de-id
min/max, multi-NPI provider groups, multiple billing-code types.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


_FIXTURE_DIR = Path(__file__).resolve().parent.parent / (
    "rcm_mc/pricing/fixtures")


# ── Normalization unit tests ─────────────────────────────────────

class TestNormalizeCode(unittest.TestCase):
    def test_strips_punctuation_and_uppercases(self):
        from rcm_mc.pricing.normalize import normalize_code
        self.assertEqual(normalize_code(" 27447 "), "27447")
        self.assertEqual(normalize_code("27447.0"), "27447")
        self.assertEqual(normalize_code("MS-DRG 470"), "MSDRG470")

    def test_empty_inputs(self):
        from rcm_mc.pricing.normalize import normalize_code
        self.assertIsNone(normalize_code(None))
        self.assertIsNone(normalize_code(""))
        self.assertIsNone(normalize_code("Not Available"))

    def test_preserves_alpha_codes(self):
        """HCPCS codes start with a letter — that letter must
        survive normalization."""
        from rcm_mc.pricing.normalize import normalize_code
        self.assertEqual(normalize_code("J3490"), "J3490")
        self.assertEqual(normalize_code("g0008"), "G0008")


class TestNormalizePayer(unittest.TestCase):
    def test_canonicalizes_known_aliases(self):
        from rcm_mc.pricing.normalize import normalize_payer_name
        self.assertEqual(
            normalize_payer_name("BCBS-TX"), "BCBS Texas")
        self.assertEqual(
            normalize_payer_name("Blue Cross Blue Shield of Texas"),
            "BCBS Texas")
        self.assertEqual(
            normalize_payer_name("UHC"), "UnitedHealthcare")
        self.assertEqual(
            normalize_payer_name("Aetna Inc"), "Aetna (CVS)")

    def test_unmatched_returns_input(self):
        from rcm_mc.pricing.normalize import normalize_payer_name
        # Unrecognized payer falls through unchanged
        self.assertEqual(
            normalize_payer_name("Some Local Co-op"),
            "Some Local Co-op")

    def test_empty_returns_empty_string(self):
        from rcm_mc.pricing.normalize import normalize_payer_name
        self.assertEqual(normalize_payer_name(None), "")
        self.assertEqual(normalize_payer_name(""), "")


class TestZipToCBSA(unittest.TestCase):
    def test_known_zip_returns_metro(self):
        from rcm_mc.pricing.normalize import zip_to_cbsa
        # Houston metro
        self.assertEqual(zip_to_cbsa("77001"), "26420")
        # Strips ZIP+4 suffix
        self.assertEqual(zip_to_cbsa("77001-1234"), "26420")

    def test_unknown_zip_returns_none(self):
        from rcm_mc.pricing.normalize import zip_to_cbsa
        self.assertIsNone(zip_to_cbsa("99999"))


class TestServiceLine(unittest.TestCase):
    def test_classifies_cpt(self):
        from rcm_mc.pricing.normalize import classify_service_line
        # 27447 is total knee → ortho
        self.assertEqual(
            classify_service_line("27447", "CPT"),
            "Surgery — Musculoskeletal/Ortho",
        )
        # 70551 is MRI brain → imaging
        self.assertEqual(
            classify_service_line("70551", "CPT"),
            "Imaging — Radiology",
        )

    def test_classifies_drg(self):
        from rcm_mc.pricing.normalize import classify_service_line
        # MS-DRG 470 — major joint replacement
        self.assertEqual(
            classify_service_line("470", "MSDRG"),
            "Musculoskeletal / Joint",
        )


# ── NPPES parser + loader ───────────────────────────────────────

class TestNppesParser(unittest.TestCase):
    def test_parses_organizational_npis_only(self):
        from rcm_mc.pricing.nppes import parse_nppes_csv
        records = list(parse_nppes_csv(
            _FIXTURE_DIR / "sample_nppes.csv"))
        # Only Type-2 entities by default — fixture has 5 Type-2
        # and 1 Type-1
        self.assertEqual(len(records), 5)
        npis = {r.npi for r in records}
        self.assertIn("1003456789", npis)
        self.assertNotIn("1568901234", npis)  # individual

    def test_includes_type_1_when_requested(self):
        from rcm_mc.pricing.nppes import parse_nppes_csv
        records = list(parse_nppes_csv(
            _FIXTURE_DIR / "sample_nppes.csv",
            include_type_1=True))
        self.assertEqual(len(records), 6)

    def test_zip_normalized_and_cbsa_resolved(self):
        from rcm_mc.pricing.nppes import parse_nppes_csv
        records = list(parse_nppes_csv(
            _FIXTURE_DIR / "sample_nppes.csv"))
        baylor = next(r for r in records if r.npi == "1003456789")
        self.assertEqual(baylor.zip5, "75246")
        # Dallas → DFW CBSA 19100 not in default crosswalk for 75246;
        # only assertion: zip5 is exactly 5 chars
        self.assertEqual(len(baylor.zip5), 5)
        houston = next(r for r in records if r.npi == "1124567890")
        self.assertEqual(houston.cbsa, "26420")  # Houston


class TestNppesLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_then_get(self):
        from rcm_mc.pricing import (
            PricingStore, parse_nppes_csv, load_nppes,
            get_provider_npi,
        )
        store = PricingStore(self.db)
        records = list(parse_nppes_csv(
            _FIXTURE_DIR / "sample_nppes.csv"))
        n = load_nppes(store, records)
        self.assertEqual(n, 5)

        baylor = get_provider_npi(store, "1003456789")
        self.assertIsNotNone(baylor)
        self.assertIn("BAYLOR", baylor["organization_name"])
        self.assertEqual(baylor["state"], "TX")
        self.assertEqual(baylor["entity_type"], 2)

    def test_load_idempotent(self):
        from rcm_mc.pricing import (
            PricingStore, parse_nppes_csv, load_nppes,
        )
        store = PricingStore(self.db)
        records = list(parse_nppes_csv(
            _FIXTURE_DIR / "sample_nppes.csv"))
        load_nppes(store, records)
        load_nppes(store, records)  # second call should not duplicate
        with store.connect() as con:
            count = con.execute(
                "SELECT COUNT(*) FROM pricing_nppes").fetchone()[0]
        self.assertEqual(count, 5)


# ── Hospital MRF ────────────────────────────────────────────────

class TestHospitalMrfParser(unittest.TestCase):
    def test_parses_v2_json(self):
        from rcm_mc.pricing.hospital_mrf import parse_hospital_mrf
        records = list(parse_hospital_mrf(
            _FIXTURE_DIR / "sample_hospital_mrf.json"))
        # 4 BCBS/UHC/Aetna/Cigna for 27447 + Medicare/BCBS for DRG 470 + BCBS for 70551
        self.assertEqual(len(records), 7)

    def test_payer_names_normalized(self):
        from rcm_mc.pricing.hospital_mrf import parse_hospital_mrf
        records = list(parse_hospital_mrf(
            _FIXTURE_DIR / "sample_hospital_mrf.json"))
        payers = {r.payer_name for r in records}
        # "BCBS-TX" → "BCBS Texas", "Aetna" → "Aetna (CVS)"
        self.assertIn("BCBS Texas", payers)
        self.assertIn("Aetna (CVS)", payers)

    def test_carries_cash_price_and_minmax(self):
        from rcm_mc.pricing.hospital_mrf import parse_hospital_mrf
        records = list(parse_hospital_mrf(
            _FIXTURE_DIR / "sample_hospital_mrf.json"))
        knee = [r for r in records if r.code == "27447"]
        self.assertGreater(len(knee), 0)
        first = knee[0]
        self.assertEqual(first.gross_charge, 75000)
        self.assertEqual(first.discounted_cash_price, 30000)
        self.assertEqual(first.deidentified_min, 22000)
        self.assertEqual(first.deidentified_max, 56000)


class TestHospitalMrfLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_then_query_by_code(self):
        from rcm_mc.pricing import (
            PricingStore, parse_hospital_mrf, load_hospital_mrf,
            list_charges_by_code,
        )
        store = PricingStore(self.db)
        recs = list(parse_hospital_mrf(
            _FIXTURE_DIR / "sample_hospital_mrf.json"))
        n = load_hospital_mrf(store, recs)
        self.assertEqual(n, 7)

        # All charges for CPT 27447 — 4 payer rows
        knee = list_charges_by_code(store, "27447")
        self.assertEqual(len(knee), 4)

        # Filter by payer
        bcbs_only = list_charges_by_code(
            store, "27447", payer_name="BCBS Texas")
        self.assertEqual(len(bcbs_only), 1)
        self.assertEqual(bcbs_only[0]["payer_specific_charge"], 24500)


# ── Payer TiC ───────────────────────────────────────────────────

class TestPayerTicParser(unittest.TestCase):
    def test_parses_inn_blocks(self):
        from rcm_mc.pricing.payer_mrf import parse_payer_tic_mrf
        records = list(parse_payer_tic_mrf(
            _FIXTURE_DIR / "sample_payer_tic.json"))
        # 27447: 2 NPIs in first group + 1 NPI in second = 3 rows
        # 70551: 1 row
        # MS-DRG 470: 1 row
        # Total: 5
        self.assertEqual(len(records), 5)

    def test_attaches_service_line(self):
        from rcm_mc.pricing.payer_mrf import parse_payer_tic_mrf
        records = list(parse_payer_tic_mrf(
            _FIXTURE_DIR / "sample_payer_tic.json"))
        knee = next(r for r in records
                    if r.code == "27447")
        self.assertEqual(
            knee.service_line, "Surgery — Musculoskeletal/Ortho")

    def test_payer_name_normalized(self):
        from rcm_mc.pricing.payer_mrf import parse_payer_tic_mrf
        records = list(parse_payer_tic_mrf(
            _FIXTURE_DIR / "sample_payer_tic.json"))
        payers = {r.payer_name for r in records}
        self.assertEqual(payers, {"Aetna (CVS)"})


class TestPayerTicLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_outside_options_lookup_for_npi(self):
        """The simulator's bread-and-butter query: 'what does every
        payer pay this NPI for the same code?'"""
        from rcm_mc.pricing import (
            PricingStore, parse_payer_tic_mrf, load_payer_tic_mrf,
            list_negotiated_rates_by_npi,
        )
        store = PricingStore(self.db)
        load_payer_tic_mrf(
            store,
            list(parse_payer_tic_mrf(
                _FIXTURE_DIR / "sample_payer_tic.json")),
        )
        rates = list_negotiated_rates_by_npi(store, "1003456789")
        # 3 codes × 1 payer × 1 plan = 3 rates for Baylor's NPI
        self.assertEqual(len(rates), 3)

        knee_only = list_negotiated_rates_by_npi(
            store, "1003456789", code="27447")
        self.assertEqual(len(knee_only), 1)
        self.assertEqual(knee_only[0]["negotiated_rate"], 27200.00)

    def test_dispersion_lookup_for_code(self):
        """The simulator's bargaining-anchor query: 'what's the
        spread of negotiated rates across all NPIs for this code?'"""
        from rcm_mc.pricing import (
            PricingStore, parse_payer_tic_mrf, load_payer_tic_mrf,
            list_negotiated_rates_for_code,
        )
        store = PricingStore(self.db)
        load_payer_tic_mrf(
            store,
            list(parse_payer_tic_mrf(
                _FIXTURE_DIR / "sample_payer_tic.json")),
        )
        rates = list_negotiated_rates_for_code(store, "27447")
        self.assertEqual(len(rates), 3)
        # Cross-NPI dispersion: 23800 to 27200
        amounts = sorted(r["negotiated_rate"] for r in rates
                         if r["negotiated_rate"] is not None)
        self.assertEqual(amounts[0], 23800.00)
        self.assertEqual(amounts[-1], 27200.00)


class TestLoadLog(unittest.TestCase):
    """Every loader writes a row to pricing_load_log so the next
    refresh-orchestrator can tell what was loaded and when."""

    def test_log_rows_for_each_source(self):
        from rcm_mc.pricing import (
            PricingStore, parse_nppes_csv, load_nppes,
            parse_hospital_mrf, load_hospital_mrf,
            parse_payer_tic_mrf, load_payer_tic_mrf,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            load_nppes(store, list(parse_nppes_csv(
                _FIXTURE_DIR / "sample_nppes.csv")))
            load_hospital_mrf(store, list(parse_hospital_mrf(
                _FIXTURE_DIR / "sample_hospital_mrf.json")))
            load_payer_tic_mrf(store, list(parse_payer_tic_mrf(
                _FIXTURE_DIR / "sample_payer_tic.json")))
            with store.connect() as con:
                rows = con.execute(
                    "SELECT source, record_count "
                    "FROM pricing_load_log "
                    "ORDER BY source"
                ).fetchall()
            sources = [r["source"] for r in rows]
            self.assertIn("nppes", sources)
            self.assertIn("hospital_mrf", sources)
            self.assertIn("payer_tic", sources)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
