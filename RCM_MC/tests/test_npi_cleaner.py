"""Tests for the NPI Claims Cleaner (/npi-cleaner).

Covers the stdlib engine (Luhn verdicts, dedup, trimming, missing-billing-NPI
detection) and the full HTTP loop: page render, raw-body upload, status poll,
and cleaned-file download.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import urllib.request as _u
import urllib.parse as _up
import urllib.error as _ue
from unittest.mock import patch

from rcm_mc.npi_cleaner import engine


# Two NPIs that pass the real CMS/NPPES Luhn check (80840 + first 9).
GOOD_A = "1234567893"
GOOD_B = "1679576722"


class TestEngine(unittest.TestCase):
    def test_luhn_matches_cms_rule(self):
        self.assertTrue(engine.luhn_npi_valid(GOOD_A))
        self.assertTrue(engine.luhn_npi_valid(GOOD_B))
        self.assertFalse(engine.luhn_npi_valid("1234567890"))  # bad check digit
        self.assertFalse(engine.luhn_npi_valid("123"))          # too short

    def test_classify(self):
        self.assertEqual(engine.classify_npi(""), "blank")
        self.assertEqual(engine.classify_npi("  "), "blank")
        self.assertEqual(engine.classify_npi("99999"), "malformed")
        self.assertEqual(engine.classify_npi("1234567890"), "checksum")
        self.assertEqual(engine.classify_npi(GOOD_A), "valid")

    def test_clean_bytes_full(self):
        data = (
            "ClaimID,BillingProviderNPI,RenderingNPI\n"
            f"1, {GOOD_A} ,{GOOD_B}\n"       # leading/trailing space → trimmed
            f"2,{GOOD_A},{GOOD_B}\n"          # distinct row (different ClaimID)
            f"2,{GOOD_A},{GOOD_B}\n"          # exact duplicate of row above
            f"3,,{GOOD_B}\n"                  # blank billing NPI
            f"4,99999,{GOOD_B}\n"             # malformed
            "5,1234567890," + GOOD_B + "\n"   # checksum fail
        ).encode()
        res = engine.clean_bytes(data, "sample claims.csv")
        sc = res.as_scorecard()

        self.assertEqual(sc["rows_in"], 6)
        self.assertEqual(sc["duplicates_removed"], 1)
        self.assertEqual(sc["rows_out"], 5)
        self.assertEqual(sc["cells_trimmed"], 1)
        self.assertEqual(sc["billing_column"], "BillingProviderNPI")
        self.assertIn("RenderingNPI", sc["npi_columns"])

        bill = sc["column_stats"]["BillingProviderNPI"]
        # rows 1,2,2(dup counted before dedup)=3 valid, plus blank/malformed/checksum
        self.assertEqual(bill["blank"], 1)
        self.assertEqual(bill["malformed"], 1)
        self.assertEqual(bill["checksum"], 1)
        self.assertEqual(sc["billing_issues"], 3)
        self.assertEqual(sc["out_name"], "sample_claims_cleaned.csv")

        # The cleaned file exists, keeps the header, and trims whitespace.
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("ClaimID,BillingProviderNPI,RenderingNPI", out)
        self.assertNotIn(f" {GOOD_A} ", out)

    def test_no_npi_column_still_cleans(self):
        data = b"a,b\n1, 2 \n1, 2 \n"
        res = engine.clean_bytes(data, "x.csv")
        sc = res.as_scorecard()
        self.assertEqual(sc["npi_columns"], [])
        self.assertEqual(sc["duplicates_removed"], 1)
        self.assertTrue(any("No NPI column" in w for w in sc["warnings"]))

    def test_tsv_delimiter(self):
        data = b"NPI\tAmount\n" + GOOD_A.encode() + b"\t10\n"
        res = engine.clean_bytes(data, "t.tsv")
        self.assertEqual(res.as_scorecard()["delimiter"], "tab")

    def test_normalization_fixes(self):
        # A deliberately messy file exercising each normalizer.
        data = (
            "ClaimID,BillingNPI,ProviderState,AllowedAmt,DateOfService,PatientZip,HCPCS\n"
            "1,'1234567893,Ohio,\"$1,234.50\",2024-01-15,1234,99213\n"
            "2,1234567893.0,TX,\"(50.00)\",45300,08540,g0008\n"
            "3,N/A,texas,\"1,000\",01/15/2024,00501,99214\n"
        ).encode()
        res = engine.clean_bytes(data, "messy.csv")
        rp = res.repairs
        self.assertGreater(res.as_scorecard()["repairs_total"], 5)
        self.assertIn("state-name-to-code", rp)        # Ohio→OH, texas→TX
        self.assertIn("npi-excel-float", rp)           # 1234567893.0
        self.assertIn("leading-apostrophe", rp)        # '1234567893
        self.assertIn("null-token", rp)                # N/A → blank
        self.assertIn("date-excel-serial", rp)         # 45300
        self.assertIn("date-us-to-iso", rp)            # 01/15/2024
        self.assertIn("hcpcs-upper", rp)               # g0008 → G0008
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("OH", out)
        self.assertIn("2024-01-15", out)
        # Negative money is NOT apostrophe-defanged (it is a plain number).
        self.assertIn("-50.00", out)
        self.assertNotIn("'-50.00", out)

    def test_sex_and_icd_normalization(self):
        data = ("ClaimID,PatientSex,Diagnosis\n"
                "1,Male,E1165\n2,F,I10\n3,2,e119\n").encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertIn("sex-normalize", res.repairs)
        self.assertIn("dx-decimal", res.repairs)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("E11.65", out)   # E1165 → decimal inserted
        self.assertIn("I10", out)      # 3-char code unchanged
        self.assertIn("1,M,", out)     # Male → M

    def test_modifier_phone_taxonomy_normalization(self):
        data = ("ClaimID,Modifiers,ProviderPhone,ProviderTaxonomy\n"
                "1,\"26|tc, 59\",5551234567,207q00000x\n"
                "2,25;25,1-555-987-6543,208d00000x\n").encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertIn("modifier-normalize", res.repairs)
        self.assertIn("phone-format", res.repairs)
        self.assertIn("taxonomy-upper", res.repairs)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("26,TC,59", out)          # split/upper/order
        self.assertIn("(555) 123-4567", out)     # 10-digit format
        self.assertIn("(555) 987-6543", out)     # 11-digit w/ leading 1
        self.assertIn("207Q00000X", out)         # taxonomy upper
        self.assertIn("2,25,", out)              # dedup 25;25 → 25

    def test_cross_field_sanity_flags(self):
        data = ("ClaimID,ChargeAmt,AllowedAmt,PaidAmt,Units\n"
                "1,50,90,40,2\n"       # allowed > billed
                "2,200,150,300,1\n"    # paid > allowed
                "3,100,80,-5,0\n"      # negative paid + units<=0
                "4,100,80,60,1.5\n").encode()  # fractional units
        res = engine.clean_bytes(data, "x.csv")
        sf = res.sanity
        self.assertEqual(sf.get("allowed-exceeds-billed"), 1)
        self.assertEqual(sf.get("paid-exceeds-allowed"), 1)
        self.assertEqual(sf.get("negative-paid"), 1)
        self.assertEqual(sf.get("nonpositive-units"), 1)
        self.assertEqual(sf.get("fractional-units"), 1)

    def test_ndc_11digit_normalization(self):
        # Segment-aware padding must match the vendored normalize_ndc11 rule.
        data = ("ClaimID,NDC\n"
                "1,1234-5678-90\n"    # 4-4-2 → pad seg1
                "2,12345-678-90\n"    # 5-3-2 → pad seg2
                "3,00069015001\n"     # already 11 digits → unchanged
                "4,1234567890\n").encode()  # 10-digit unhyphenated → ambiguous
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.repairs.get("ndc-pad-11"), 2)
        self.assertEqual(res.sanity.get("ndc-ambiguous-10digit"), 1)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("01234567890", out)  # 1234-5678-90 padded
        self.assertIn("12345067890", out)  # 12345-678-90 padded

    def test_ndc_matches_package_rule(self):
        try:
            from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import field_validators as FV
        except Exception:
            self.skipTest("vendored field_validators unavailable")
        for c in ("1234-5678-90", "12345-678-90", "12345-6789-0",
                  "0069-0150-01", "00069015001"):
            mine, _ = engine._clean_ndc_cell(c)
            pkg, _st = FV.normalize_ndc11(c)
            self.assertEqual(mine, pkg, f"mismatch on {c}")

    def test_suspected_duplicate_claims(self):
        # Rows 1&2 share provider/patient/DOS/HCPCS/amount (diff ClaimID) → dup.
        # A 3rd row is an exact dup of row 1 (removed by exact dedup, not
        # double-counted). A 4th row differs only by patient → not a dup.
        data = (
            "ClaimID,BillingNPI,PatientID,DateOfService,HCPCS,AllowedAmt\n"
            f"1,{GOOD_B},P100,2024-03-01,99213,80\n"
            f"2,{GOOD_B},P100,2024-03-01,99213,80\n"
            f"1,{GOOD_B},P100,2024-03-01,99213,80\n"
            f"9,{GOOD_B},P200,2024-03-01,99213,80\n"
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.n_dupes_removed, 1)                    # exact dup
        self.assertEqual(res.sanity.get("suspected-duplicate-claim"), 1)

    def test_duplicate_claims_needs_key_columns(self):
        # Without provider/date/code columns the check must not run.
        data = ("ClaimID,Note\n1,a\n2,a\n").encode()
        res = engine.clean_bytes(data, "y.csv")
        self.assertNotIn("suspected-duplicate-claim", res.sanity)

    def test_future_date_flagged(self):
        # A service date or DOB after today is impossible → flagged. Uses a
        # far-future year so the assertion is stable regardless of run date.
        # A US-format future date must flag too (normalized to ISO first), and
        # a legitimately-future column (coverage end) must NOT flag.
        data = (
            "ClaimID,DateOfService,PatientDOB,CoverageEndDate\n"
            "1,2999-01-01,1980-05-14,2999-12-31\n"   # future DOS → flag
            "2,03/04/2999,1975-02-02,2999-12-31\n"   # future DOS (US fmt) → flag
            "3,2020-06-15,2999-05-05,2999-12-31\n"   # future DOB → flag
            "4,2021-01-01,1990-01-01,2999-12-31\n"   # all past svc/dob → clear
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        # Three rows have a future service/birth date; the coverage-end column
        # is in the future on every row but must never trigger the flag.
        self.assertEqual(res.sanity.get("date-in-future"), 3)

    def test_future_date_needs_service_or_dob_column(self):
        # Without a service/birth date column the check must not run even if a
        # generic future date is present.
        data = ("ClaimID,CoverageEndDate\n1,2999-01-01\n").encode()
        res = engine.clean_bytes(data, "y.csv")
        self.assertNotIn("date-in-future", res.sanity)

    def test_zip_state_mismatch_flagged(self):
        # A ZIP whose 3-digit prefix resolves to a different state than the
        # state cell is flagged. 902xx→CA, 331xx→FL, 100xx→NY.
        data = (
            "ClaimID,ProviderState,ProviderZip\n"
            "1,CA,90210\n"        # 902→CA, matches → clear
            "2,NY,90210\n"        # 902→CA but state says NY → mismatch
            "3,FL,33101\n"        # 331→FL, matches → clear
            "4,TX,10001\n"        # 100→NY but state says TX → mismatch
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("zip-state-mismatch"), 2)

    def test_zip_state_pairs_same_entity_only(self):
        # PatientState must not be compared against ProviderZip (different
        # entities) — that pairing would false-positive. Only same-entity
        # provider columns are compared, and here they agree → no flag.
        data = (
            "ClaimID,PatientState,ProviderState,ProviderZip\n"
            "1,NY,CA,90210\n"     # provider CA↔902 agree; patient NY ignored
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertNotIn("zip-state-mismatch", res.sanity)

    def test_zip_state_skips_territories(self):
        # Territory/military prefixes are approximate in the crosswalk, so a
        # PR/VI mismatch is never flagged.
        data = ("ClaimID,ProviderState,ProviderZip\n1,VI,00801\n").encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertNotIn("zip-state-mismatch", res.sanity)

    def test_hcpcs_malformed_flagged(self):
        # Valid: 5-digit CPT, letter+4 HCPCS, 4+letter Cat II; a valid code with
        # an appended modifier must NOT flag. Malformed: 4 digits, 5 letters.
        data = (
            "ClaimID,HCPCS\n"
            "1,99213\n"        # CPT Cat I → valid
            "2,J1885\n"        # HCPCS Level II → valid
            "3,0001F\n"        # CPT Cat II → valid
            "4,99213-25\n"     # valid + modifier → valid (modifier stripped)
            "5,9921\n"         # only 4 digits → malformed
            "6,ABCDE\n"        # 5 letters → malformed
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("hcpcs-malformed"), 2)

    def test_icd10_malformed_flagged(self):
        # Valid: E11.65, I10 (3-char), U07.1 (COVID). Malformed: leading digit,
        # too short.
        data = (
            "ClaimID,DiagnosisCode\n"
            "1,E11.65\n"       # valid
            "2,I10\n"          # valid 3-char
            "3,U07.1\n"        # valid
            "4,123.45\n"       # starts with a digit → malformed
            "5,E1\n"           # too short → malformed
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("icd10-malformed"), 2)

    def test_code_shape_checks_need_columns(self):
        # Without HCPCS/diagnosis columns the checks must not run.
        data = ("ClaimID,Note\n1,hello\n").encode()
        res = engine.clean_bytes(data, "y.csv")
        self.assertNotIn("hcpcs-malformed", res.sanity)
        self.assertNotIn("icd10-malformed", res.sanity)

    def test_money_unparseable_flagged(self):
        # An amount cell that survives cleaning but isn't a number is flagged;
        # normal / accounting-negative / $-and-comma values are not. A null
        # token ("N/A") is blanked by generic cleaning first, so it never flags.
        data = (
            "ClaimID,AllowedAmt\n"
            "1,100.00\n"       # clean number → ok
            "2,\"$1,250.50\"\n"  # $ + comma → parses → ok
            "3,(75.00)\n"      # accounting negative → parses → ok
            "4,N/A\n"          # null token → blanked → not flagged
            "5,pending\n"      # text in $ field → flagged
            "6,\"1,2OO\"\n"    # letter O instead of zero → flagged
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("money-unparseable"), 2)

    def test_money_unparseable_needs_money_column(self):
        data = ("ClaimID,Note\n1,hello world\n").encode()
        res = engine.clean_bytes(data, "y.csv")
        self.assertNotIn("money-unparseable", res.sanity)

    def test_sex_invalid_flagged(self):
        # Values that don't resolve to M/F/U via _clean_sex_cell are flagged;
        # mapped variants (Male, 2, blank) are not.
        data = (
            "ClaimID,PatientSex\n"
            "1,M\n"        # valid
            "2,Male\n"     # → M → valid
            "3,2\n"        # → F → valid
            "4,\n"         # blank → not flagged
            "5,X\n"        # unmapped → flagged
            "6,3\n"        # unmapped digit → flagged
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("sex-invalid"), 2)

    def test_taxonomy_malformed_flagged(self):
        # NUCC taxonomy must be 10 alphanumeric chars; anything else flags.
        data = (
            "ClaimID,ProviderTaxonomy\n"
            "1,207Q00000X\n"   # valid 10-char
            "2,2085R0202X\n"   # valid 10-char
            "3,207Q\n"         # too short → flagged
            "4,207Q00000XX\n"  # 11 chars → flagged
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("taxonomy-malformed"), 2)

    def test_value_domain_checks_need_columns(self):
        data = ("ClaimID,Note\n1,hi\n").encode()
        res = engine.clean_bytes(data, "y.csv")
        self.assertNotIn("sex-invalid", res.sanity)
        self.assertNotIn("taxonomy-malformed", res.sanity)

    def test_quality_report_card(self):
        # A clean file grades high; a dirty file grades lower, and every
        # dimension is a recomputable 0-100 ratio.
        clean = ("ClaimID,BillingNPI,AllowedAmt\n"
                 f"1,{GOOD_B},100.00\n2,{GOOD_B},110.00\n").encode()
        rc = engine.clean_bytes(clean, "clean.csv")
        qc = rc.as_scorecard()["quality"]
        self.assertGreaterEqual(qc["score"], 93)
        self.assertEqual(qc["letter"], "A")
        for dim in ("completeness", "validity", "consistency",
                    "uniqueness", "conformity"):
            self.assertIn(dim, qc["dimensions"])
        dirty = ("ClaimID,BillingNPI,AllowedAmt,PatientSex\n"
                 "1,123,garbage,X\n1,123,garbage,X\n2,,,\n").encode()
        rd = engine.clean_bytes(dirty, "dirty.csv")
        qd = rd.as_scorecard()["quality"]
        self.assertLess(qd["score"], qc["score"])

    def test_changelog_audit_trail(self):
        # Every change lands in the change-log CSV as before → after + rule.
        data = ("NPI,ChargeAmt,ServiceDate\n"
                f"  {GOOD_A}  ,\"$1,250.50\",03/04/2024\n").encode()
        res = engine.clean_bytes(data, "log.csv")
        self.assertGreaterEqual(res.n_changes, 3)
        self.assertIsNotNone(res.changelog_path)
        with open(res.changelog_path, encoding="utf-8") as fh:
            log = fh.read()
        self.assertIn("before", log.splitlines()[0])
        self.assertIn("1250.50", log)          # money after-value
        self.assertIn("2024-03-04", log)       # date after-value
        self.assertIn("date-us-to-iso", log)   # rule provenance

    def test_changelog_never_contains_phi(self):
        # De-id masking must NOT be recorded — originals would leak into the
        # log. Only the pre-deid cleaning changes appear.
        data = ("BillingNPI,PatientName,SSN\n"
                f"  {GOOD_B} ,John Q Public,123-45-6789\n").encode()
        res = engine.clean_bytes(data, "phi.csv", deid=True)
        if res.changelog_path:
            with open(res.changelog_path, encoding="utf-8") as fh:
                log = fh.read()
            self.assertNotIn("John Q Public", log)
            self.assertNotIn("123-45-6789", log)

    def test_payer_variant_clustering(self):
        data = ("ClaimID,Payer\n"
                "1,BCBS of Texas\n2,Blue Cross Blue Shield TX\n"
                "3,B.C.B.S.\n4,Aetna\n5,AETNA INC\n6,Cigna\n").encode()
        res = engine.clean_bytes(data, "p.csv")
        pv = res.payer_variants
        self.assertIsNotNone(pv)
        self.assertEqual(pv["column"], "Payer")
        self.assertEqual(pv["distinct_raw"], 6)
        canon = {c["canonical"]: c for c in pv["multi_spelling"]}
        self.assertIn("BLUE CROSS BLUE SHIELD", canon)
        self.assertEqual(canon["BLUE CROSS BLUE SHIELD"]["n_variants"], 3)
        self.assertIn("AETNA", canon)

    def test_chronology_flags(self):
        data = (
            "ClaimID,PatientDOB,DateOfService,AdmitDate,DischargeDate\n"
            "1,1990-01-01,1989-06-15,2024-03-01,2024-02-27\n"  # both wrong
            "2,1980-05-14,2024-03-01,2024-03-01,2024-03-04\n"  # both fine
        ).encode()
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("service-before-birth"), 1)
        self.assertEqual(res.sanity.get("discharge-before-admit"), 1)

    def test_paid_exceeds_billed_and_stale_date(self):
        data = ("ClaimID,BilledAmt,PaidAmt,DateOfService\n"
                "1,100,120,2024-03-01\n"      # paid > billed
                "2,100,80,2001-05-05\n").encode()  # stale DOS
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.sanity.get("paid-exceeds-billed"), 1)
        self.assertEqual(res.sanity.get("date-stale"), 1)

    def test_pos_and_revenue_code(self):
        data = ("ClaimID,POS,RevenueCode\n"
                "1,11,450\n"      # POS valid; revcode padded to 0450
                "2,1,0450\n"      # POS padded to 01 → valid
                "3,77,ABC\n").encode()  # POS invalid; revcode malformed
        res = engine.clean_bytes(data, "x.csv")
        self.assertEqual(res.repairs.get("revcode-pad"), 1)
        self.assertEqual(res.repairs.get("pos-pad"), 1)
        self.assertEqual(res.sanity.get("pos-invalid"), 1)
        self.assertEqual(res.sanity.get("revenue-code-malformed"), 1)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("0450", out)

    def test_charge_outliers_per_code(self):
        rows = [f"{i},{GOOD_B},99213,{100 + i}" for i in range(12)]
        rows.append(f"99,{GOOD_B},99213,9000")   # far-out charge
        data = ("ClaimID,BillingNPI,HCPCS,BilledAmt\n"
                + "\n".join(rows) + "\n").encode()
        res = engine.clean_bytes(data, "o.csv")
        self.assertEqual(res.sanity.get("charge-outlier"), 1)
        self.assertEqual(res.outliers[0]["code"], "99213")
        self.assertEqual(res.outliers[0]["outliers"], 1)

    def test_structure_findings(self):
        data = ("ClaimID,Note,Note,Empty\n"
                "1,a,b,\n2,c,d,\n").encode()
        res = engine.clean_bytes(data, "s.csv")
        self.assertEqual(res.structure.get("duplicate_headers"), ["Note"])
        self.assertEqual(res.structure.get("empty_columns"), ["Empty"])

    def test_discharge_date_not_money(self):
        # Regression: "DischargeDate" contains the substring "charge" and was
        # routed to the money cleaner — never date-normalized and false-flagged
        # as unparseable money. Date role must win.
        data = ("ClaimID,DischargeDate\n1,03/04/2024\n").encode()
        res = engine.clean_bytes(data, "d.csv")
        self.assertNotIn("money-unparseable", res.sanity)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("2024-03-04", out)   # date cleaner ran on it

    def test_column_fill_rates(self):
        # Per-column completeness profile: Note filled 1 of 4 rows = 25%.
        # Denominator is rows IN, so pct never exceeds 100 even when exact
        # duplicates are removed from the output.
        data = ("ClaimID,Note\n1,a\n2,\n3,\n4,\n").encode()
        res = engine.clean_bytes(data, "f.csv")
        fills = {f["column"]: f for f in res.column_fill}
        self.assertEqual(fills["ClaimID"]["pct"], 100.0)
        self.assertEqual(fills["Note"]["pct"], 25.0)
        dup = ("ClaimID,Note\n1,a\n1,a\n").encode()   # dedupe drops one row
        rd = engine.clean_bytes(dup, "d.csv")
        fd = {f["column"]: f for f in rd.column_fill}
        self.assertLessEqual(fd["Note"]["pct"], 100.0)

    def test_modifier_units_edits(self):
        # JW (discarded drug) with 0 units and bilateral 50 with 2 units are
        # both flagged; correct pairings are not.
        data = ("ClaimID,HCPCS,Modifier,Units\n"
                "1,J1885,JW,0\n"       # JW needs positive units → flag
                "2,J1885,JW,2\n"       # fine
                "3,99213,50,2\n"       # bilateral bills 1 unit → flag
                "4,99213,50,1\n"       # fine
                "5,99213,25,3\n").encode()  # unrelated modifier → fine
        res = engine.clean_bytes(data, "m.csv")
        self.assertEqual(res.sanity.get("jw-zero-units"), 1)
        self.assertEqual(res.sanity.get("bilateral-units"), 1)

    def test_workbook_quality_sheet(self):
        data = ("ClaimID,BillingNPI,AllowedAmt\n"
                f"1,{GOOD_B},100\n").encode()
        res = engine.clean_bytes(data, "q.csv")
        openpyxl = __import__("openpyxl")
        from io import BytesIO
        with open(res.workbook_path, "rb") as fh:
            wb = openpyxl.load_workbook(BytesIO(fh.read()))
        self.assertIn("Quality", wb.sheetnames)
        ws = wb["Quality"]
        cells = [str(c.value) for row in ws.iter_rows() for c in row if c.value]
        self.assertTrue(any("Overall grade" in c for c in cells))
        self.assertTrue(any("Completeness" in c for c in cells))

    def test_conflicting_amount_claims(self):
        # Same who·when·what key billed at two different amounts → flagged.
        # Equal-amount repeats are the suspected-duplicate signal, not this.
        data = (
            "ClaimID,BillingNPI,PatientID,DateOfService,HCPCS,BilledAmt\n"
            f"1,{GOOD_B},P1,2024-03-01,99213,100\n"
            f"2,{GOOD_B},P1,2024-03-01,99213,250\n"   # conflict with row 1
            f"3,{GOOD_B},P2,2024-03-01,99213,100\n"   # different patient
            f"4,{GOOD_B},P2,2024-03-01,99213,100\n"   # equal repeat, no conflict
        ).encode()
        res = engine.clean_bytes(data, "c.csv")
        self.assertEqual(res.sanity.get("conflicting-amount-claim"), 1)

    def test_carc_domain_and_top_denials(self):
        # Valid CARCs (numeric, letter+digits, multi-code cells) pass; a
        # non-CARC value flags. Top denial reasons are summarized.
        data = ("ClaimID,DenialCode\n"
                "1,16\n2,16\n3,\"16, 97\"\n4,B7\n5,PENDING\n").encode()
        res = engine.clean_bytes(data, "d.csv")
        self.assertEqual(res.sanity.get("carc-invalid"), 1)
        self.assertIsNotNone(res.denials)
        top = {d["code"]: d["count"] for d in res.denials["top"]}
        self.assertEqual(top.get("16"), 3)
        self.assertEqual(top.get("97"), 1)
        self.assertEqual(top.get("B7"), 1)

    def test_refdata_catalogs(self):
        from rcm_mc.npi_cleaner import refdata as rd
        self.assertEqual(rd.pos_name("11"), "Office")
        self.assertEqual(rd.pos_name("1"), "Pharmacy")     # 1-digit keying
        self.assertIn("Blood", rd.revenue_category("0380") or "")
        self.assertIsNotNone(rd.carc_description("197"))
        self.assertIsNotNone(rd.rarc_description("N115"))
        self.assertEqual(rd.modifier_meaning("JW"),
                         "Drug amount discarded / not administered")
        self.assertFalse(rd.tob_invalid("0111"))   # hospital, final claim
        self.assertFalse(rd.tob_invalid("131"))    # 3-digit keying
        self.assertTrue(rd.tob_invalid("999"))     # facility type 9 invalid
        self.assertTrue(rd.tob_invalid("11"))      # too short
        self.assertFalse(rd.discharge_status_invalid("01"))
        self.assertFalse(rd.discharge_status_invalid("1"))  # zero-stripped
        self.assertTrue(rd.discharge_status_invalid("XX"))
        self.assertTrue(rd.modifier_unknown("ZQ"))
        self.assertFalse(rd.modifier_unknown("25"))

    def test_rule_registry(self):
        from rcm_mc.npi_cleaner import rules
        cat = rules.catalog()
        self.assertGreater(len(cat), 50)
        ids = {r["id"] for r in cat}
        # Every engine sanity/repair key that exists today must be described.
        for must in ("hcpcs-malformed", "money-unparseable", "charge-outlier",
                     "revcode-pad", "tob-malformed", "timely-filing-risk",
                     "service-before-birth", "conflicting-amount-claim"):
            self.assertIn(must, ids)
        d = rules.describe("pos-invalid")
        self.assertEqual(d["severity"], "critical")
        self.assertTrue(d["remediation"])
        # Unknown rules degrade gracefully (renderer never breaks).
        self.assertEqual(rules.describe("brand-new-rule")["title"],
                         "brand-new-rule")

    def test_institutional_domain_flags(self):
        data = (
            "ClaimID,TypeOfBill,DischargeStatus,AdmissionType\n"
            "1,0111,01,1\n"       # all valid
            "2,999,XX,7\n"        # all invalid
        ).encode()
        res = engine.clean_bytes(data, "inst.csv")
        self.assertEqual(res.sanity.get("tob-malformed"), 1)
        self.assertEqual(res.sanity.get("discharge-status-invalid"), 1)
        self.assertEqual(res.sanity.get("admission-type-invalid"), 1)

    def test_discharge_status_not_money(self):
        # "DischargeStatus" contains "charge" — must not be routed to the
        # money cleaner ("01" → "1.00") and false-flagged. Sibling of the
        # DischargeDate/date-role regression.
        data = ("ClaimID,DischargeStatus\n1,01\n2,30\n").encode()
        res = engine.clean_bytes(data, "ds.csv")
        self.assertNotIn("discharge-status-invalid", res.sanity)
        self.assertNotIn("money-unparseable", res.sanity)
        with open(res.out_path, encoding="utf-8") as fh:
            self.assertIn("01", fh.read())

    def test_modifier_unknown_and_timely_filing(self):
        data = (
            "ClaimID,Modifier,Units,DateOfService,ReceivedDate\n"
            "1,ZQ,1,2024-01-01,2024-02-01\n"     # unknown modifier
            "2,25,1,2024-01-01,2025-06-01\n"     # 517 days → filing risk
            "3,50,1,2024-01-01,2024-06-01\n"     # fine
        ).encode()
        res = engine.clean_bytes(data, "mt.csv")
        self.assertEqual(res.sanity.get("modifier-unknown"), 1)
        self.assertEqual(res.sanity.get("timely-filing-risk"), 1)

    def test_drg_pad_and_malformed(self):
        # Excel-stripped DRG zeros restored (87 → 087); bad shapes flagged.
        data = ("ClaimID,MSDRG\n"
                "1,87\n"        # → 087 (pad repair)
                "2,470\n"       # valid, untouched
                "3,1234\n"      # 4 digits → malformed
                "4,ABC\n"       # non-numeric → malformed
                "5,000\n").encode()   # 000 is never assigned → malformed
        res = engine.clean_bytes(data, "drg.csv")
        self.assertEqual(res.repairs.get("drg-pad"), 1)
        self.assertEqual(res.sanity.get("drg-malformed"), 3)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("087", out)
        self.assertIn("470", out)
        # A header merely CONTAINING "drg" must not be treated as a DRG
        # column ("DrGroup" was the false-match risk).
        data2 = ("ClaimID,DrGroupNote\n1,87\n").encode()
        res2 = engine.clean_bytes(data2, "drg2.csv")
        self.assertIsNone(res2.repairs.get("drg-pad"))
        self.assertIsNone(res2.sanity.get("drg-malformed"))

    def test_anesthesia_units_implausible(self):
        data = ("ClaimID,HCPCS,Units\n"
                "1,00840,1500\n"     # anesthesia, >1440 → flag
                "2,00840,90\n"       # anesthesia, plausible
                "3,99213,2000\n").encode()   # not anesthesia → no flag
        res = engine.clean_bytes(data, "anes.csv")
        self.assertEqual(res.sanity.get("anesthesia-units-implausible"), 1)

    def test_timely_filing_per_payer_limit(self):
        # 120 days DOS→received: over UnitedHealthcare's 90-day limit,
        # inside Medicare's 365 — the payer on the ROW decides.
        data = ("ClaimID,PayerName,DateOfService,ReceivedDate\n"
                "1,UnitedHealthcare,2024-01-01,2024-04-30\n"
                "2,Medicare,2024-01-01,2024-04-30\n"
                "3,Some Tiny TPA,2024-01-01,2024-04-30\n").encode()
        res = engine.clean_bytes(data, "tf.csv")
        # Only the UHC row breaches: unknown payer falls back to 365.
        self.assertEqual(res.sanity.get("timely-filing-risk"), 1)
        from rcm_mc.npi_cleaner import refdata
        self.assertEqual(refdata.timely_filing_days("MEDICARE"), 365)
        self.assertIsNone(refdata.timely_filing_days("SOME TINY TPA"))

    def test_revenue_tob_mismatch(self):
        # Room & board (0120) on hospital OUTPATIENT 0131 → flag; the same
        # revenue on inpatient 0111 is fine; ancillary 0450 on outpatient
        # is fine. Row 4: clinic TOB (0731) with ICU revenue → flag.
        data = ("ClaimID,TypeOfBill,RevenueCode\n"
                "1,0131,0120\n"
                "2,0111,0120\n"
                "3,0131,0450\n"
                "4,0731,0200\n").encode()
        res = engine.clean_bytes(data, "tobrev.csv")
        self.assertEqual(res.sanity.get("revenue-tob-mismatch"), 2)
        from rcm_mc.npi_cleaner import refdata
        self.assertEqual(refdata.tob_facility_class("0131"), ("1", "3"))
        self.assertEqual(refdata.tob_facility_class("131"), ("1", "3"))
        self.assertIsNone(refdata.tob_facility_class("13"))

    def test_specialty_mix_from_taxonomy(self):
        data = ("ClaimID,TaxonomyCode\n"
                "1,207q00000x\n"          # lower-case → upper repair, counted
                "2,207Q00000X\n"
                "3,363L00000X\n"
                "4,BADCODE\n").encode()   # malformed → not counted
        res = engine.clean_bytes(data, "tax.csv")
        sc = res.as_scorecard()
        specs = {s["code"]: s for s in (sc["specialties"] or [])}
        self.assertEqual(specs["207Q00000X"]["n"], 2)
        self.assertEqual(specs["207Q00000X"]["name"], "Family Medicine")
        self.assertEqual(specs["363L00000X"]["name"], "Nurse Practitioner")
        self.assertNotIn("BADCODE", specs)

    def test_exec_report_credential_and_specialty_sections(self):
        data = ("RenderingProviderName,TaxonomyCode\n"
                "\"SMITH, JOHN, MD\",207Q00000X\n").encode()
        res = engine.clean_bytes(data, "er.csv")
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        html_out = build_exec_report(res.as_scorecard(), "er.csv",
                                     "2026-01-01T00:00:00+00:00")
        self.assertIn("Credential mix", html_out)
        self.assertIn("Doctor of Medicine", html_out)
        self.assertIn("Specialty mix", html_out)
        self.assertIn("Family Medicine", html_out)

    def test_worklist_row_capture(self):
        data = ("ClaimID,HCPCS\n"
                "1,99213\n2,BAD!!\n3,99214\n4,WRONG\n").encode()
        res = engine.clean_bytes(data, "wl.csv")
        # Output rows 2 and 4 carry the malformed codes.
        self.assertEqual(res.flag_rows.get("hcpcs-malformed"), [2, 4])
        sc = res.as_scorecard()
        self.assertEqual(sc["worklists"]["hcpcs-malformed"], 2)
        self.assertGreaterEqual(len(sc["rule_catalog"]), 58)

    def test_run_history_record_and_compare(self):
        from rcm_mc.npi_cleaner import history
        good = ("ClaimID,BillingNPI\n" f"1,{GOOD_B}\n").encode()
        bad = ("ClaimID,BillingNPI,HCPCS\n1,123,BAD!!\n").encode()
        r1 = engine.clean_bytes(good, "hist_good.csv")
        r2 = engine.clean_bytes(bad, "hist_bad.csv")
        runs = history.list_runs(10)
        names = [r["file_name"] for r in runs]
        self.assertIn("hist_good.csv", names)
        self.assertIn("hist_bad.csv", names)
        a = next(r for r in runs if r["file_name"] == "hist_good.csv")
        b = next(r for r in runs if r["file_name"] == "hist_bad.csv")
        cmp_ = history.compare_runs(a["run_id"], b["run_id"])
        self.assertIsNotNone(cmp_)
        self.assertLess(cmp_["score_delta"], 0)   # bad file scores lower
        rules_moved = {d["rule"] for d in cmp_["rule_delta"]}
        self.assertIn("hcpcs-malformed", rules_moved)

    def test_exec_report_builds(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        res = engine.clean_bytes(engine.sample_csv().encode(), "s.csv")
        html_doc = build_exec_report(res.as_scorecard(), "s.csv",
                                     "2026-01-01 00:00 UTC")
        self.assertIn("Claims data-quality report", html_doc)
        self.assertIn("Quality dimensions", html_doc)
        self.assertIn("Findings", html_doc)

    def test_cli_batch_mode(self):
        from rcm_mc.npi_cleaner.cli import main as cli_main
        with tempfile.TemporaryDirectory() as tmp:
            srcp = os.path.join(tmp, "in.csv")
            with open(srcp, "w", encoding="utf-8") as fh:
                fh.write(f"ClaimID,BillingNPI\n1, {GOOD_B} \n")
            rc = cli_main([srcp, "--outdir", tmp])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(
                os.path.join(tmp, "in_cleaned.csv")))
            # Quality gate: a clean file passes 90, nothing passes 101.
            self.assertEqual(cli_main([srcp, "--outdir", tmp,
                                       "--min-score", "90"]), 0)
            self.assertEqual(cli_main([srcp, "--outdir", tmp,
                                       "--min-score", "101"]), 1)

    def test_profiles_module(self):
        from rcm_mc.npi_cleaner import profiles
        cfg = profiles.save_profile("t-suite", {
            "disabled_rules": ["modifier-unknown", "not-a-real-rule"],
            "accepted_rules": ["date-stale"],
            "thresholds": {"timely_filing_days": 5,      # clamped to 30
                           "stale_years": 2,
                           "outlier_iqr_mult": 99}})     # clamped to 10
        self.assertEqual(cfg["disabled_rules"], ["modifier-unknown"])
        self.assertEqual(cfg["thresholds"]["timely_filing_days"], 30)
        self.assertEqual(cfg["thresholds"]["outlier_iqr_mult"], 10.0)
        loaded = profiles.get_profile("t-suite")
        self.assertEqual(loaded["name"], "t-suite")
        names = [p["name"] for p in profiles.list_profiles()]
        self.assertIn("t-suite", names)
        self.assertTrue(profiles.delete_profile("t-suite"))
        self.assertIsNone(profiles.get_profile("t-suite"))

    def test_profile_applied_to_run(self):
        # Thresholds honored, disabled rule absent, accepted rule reported
        # but excluded from the grade.
        prof = {"name": "px",
                "disabled_rules": ["modifier-unknown"],
                "accepted_rules": ["date-stale"],
                "thresholds": {"timely_filing_days": 30, "stale_years": 2,
                               "outlier_iqr_mult": 3.0}}
        data = ("ClaimID,Modifier,Units,DateOfService,ReceivedDate\n"
                "1,ZQ,1,2023-01-01,2024-03-01\n").encode()
        res = engine.clean_bytes(data, "prof.csv", profile=prof)
        sc = res.as_scorecard()
        self.assertNotIn("modifier-unknown", sc["sanity"])   # disabled
        self.assertIn("date-stale", sc["sanity"])            # 2y horizon hit
        self.assertIn("timely-filing-risk", sc["sanity"])    # 30d limit hit
        self.assertEqual(sc["accepted_rules"], ["date-stale"])
        self.assertEqual(sc["profile"], "px")
        # Without the acceptance the same file grades lower on consistency.
        res2 = engine.clean_bytes(data, "prof2.csv", profile={
            "thresholds": prof["thresholds"]})
        c_acc = res.quality()["dimensions"]["consistency"]
        c_raw = res2.quality()["dimensions"]["consistency"]
        self.assertGreater(c_acc, c_raw)

    def test_workbook_worklist_sheets(self):
        data = ("ClaimID,HCPCS\n1,99213\n2,BAD!!\n").encode()
        res = engine.clean_bytes(data, "wlx.csv")
        openpyxl = __import__("openpyxl")
        from io import BytesIO
        with open(res.workbook_path, "rb") as fh:
            wb = openpyxl.load_workbook(BytesIO(fh.read()))
        wl_sheets = [s for s in wb.sheetnames if s.startswith("WL ")]
        self.assertTrue(wl_sheets)
        ws = wb[wl_sheets[0]]
        cells = [str(c.value) for row in ws.iter_rows() for c in row if c.value]
        self.assertIn("BAD!!", cells)
        self.assertNotIn("99213", cells)   # unflagged row not in worklist tab

    def test_mbi_validation(self):
        from rcm_mc.npi_cleaner import refdata as rd
        self.assertFalse(rd.mbi_malformed("1EG4-TE5-MK73"))  # valid, hyphens ok
        self.assertTrue(rd.mbi_malformed("1SG4TE5MK73"))     # S excluded
        self.assertTrue(rd.mbi_malformed("0EG4TE5MK73"))     # can't start 0
        self.assertTrue(rd.mbi_malformed("1EG4TE5MK7"))      # 10 chars
        # Engine: fires only on Medicare rows, never under de-id.
        data = ("ClaimID,Payer,MemberID\n"
                "1,Medicare,1EG4-TE5-MK73\n"   # valid MBI
                "2,Medicare,BADMBI\n"          # malformed → flag
                "3,Aetna,BADMBI\n").encode()   # non-Medicare → no check
        res = engine.clean_bytes(data, "mbi.csv")
        self.assertEqual(res.sanity.get("mbi-malformed"), 1)
        res_deid = engine.clean_bytes(data, "mbi2.csv", deid=True)
        self.assertNotIn("mbi-malformed", res_deid.sanity)

    def test_ub_code_catalogs_and_shape(self):
        from rcm_mc.npi_cleaner import refdata as rd
        self.assertEqual(rd.condition_code_meaning("44"),
                         "Inpatient admission changed to outpatient")
        self.assertIsNotNone(rd.occurrence_code_meaning("24"))
        self.assertIsNotNone(rd.value_code_meaning("80"))
        data = ("ClaimID,ConditionCode,OccurrenceCode,ValueCode\n"
                "1,44,24,80\n"          # valid
                "2,\"44, A1\",05,B1\n"  # multi-code cell valid
                "3,4,ABC,8!\n").encode()  # all malformed shapes
        res = engine.clean_bytes(data, "ub.csv")
        self.assertEqual(res.sanity.get("condition-code-malformed"), 1)
        self.assertEqual(res.sanity.get("occurrence-code-malformed"), 1)
        self.assertEqual(res.sanity.get("value-code-malformed"), 1)

    def test_near_duplicate_rows(self):
        # Same content differing only by case/extra spaces → near-dup flag
        # (row kept); an exact repeat is removed by dedupe, not double-flagged.
        data = ("ID,Name\n1,Hello World\n1,HELLO   world\n"
                "1,Hello World\n2,Other\n").encode()
        res = engine.clean_bytes(data, "nd.csv")
        self.assertEqual(res.sanity.get("near-duplicate-row"), 1)
        self.assertEqual(res.n_dupes_removed, 1)
        self.assertEqual(res.n_rows_out, 3)   # near-dup row is KEPT

    def test_provider_name_recase_unit(self):
        # Shouting person names get standard casing with Mc/O'/hyphen
        # handling; credentials stay uppercase; suffixes keep canon form.
        c = engine._clean_provider_name_cell
        for src, want, creds in (
            ("SMITH, JOHN A, MD", "Smith, John A, MD", ["MD"]),
            ("O'BRIEN-SMITH, MARY, NP", "O'Brien-Smith, Mary, NP", ["NP"]),
            ("MCDONALD, RONALD, DO", "McDonald, Ronald, DO", ["DO"]),
            # No Mac- rule on purpose: Macias must NOT become MacIas.
            ("MACIAS, JOSE, M.D.", "Macias, Jose, MD", ["MD"]),
            ("smith, jane, pa-c", "Smith, Jane, PA-C", ["PA-C"]),
            ("SMITH JR, WILLIAM, DDS", "Smith Jr, William, DDS", ["DDS"]),
        ):
            got, hits, seen = c(src)
            self.assertEqual(got, want)
            self.assertEqual(hits, ["provider-name-format"])
            self.assertEqual(seen, creds)
        # Mixed case = already curated → untouched, credentials still parsed.
        got, hits, seen = c("Smith, John, MD")
        self.assertEqual((got, hits, seen), ("Smith, John, MD", [], ["MD"]))
        # An org name in a provider-name column must pass through untouched.
        for org in ("SMITH FAMILY CLINIC LLC", "MERCY HOSPITAL",
                    "ACME MEDICAL GROUP INC"):
            got, hits, seen = c(org)
            self.assertEqual((got, hits, seen), (org, [], []))
        # Digits mean an ID crept in — never re-case those.
        self.assertEqual(c("SMITH 12345"), ("SMITH 12345", [], []))

    def test_provider_name_engine_and_credentials(self):
        # End to end: the provider-name column is re-cased, the org-name
        # column is untouched, and the credential mix lands in the scorecard.
        data = ("RenderingProviderName,OrganizationName,BilledAmt\n"
                "\"SMITH, JOHN A, MD\",MERCY HOSPITAL INC,100\n"
                "\"O'BRIEN, MARY, NP\",MERCY HOSPITAL INC,200\n").encode()
        res = engine.clean_bytes(data, "prov.csv")
        self.assertEqual(res.repairs.get("provider-name-format"), 2)
        sc = res.as_scorecard()
        self.assertEqual(sc["credentials"], {"MD": 1, "NP": 1})
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("Smith, John A, MD", out)
        self.assertIn("O'Brien, Mary, NP", out)
        self.assertIn("MERCY HOSPITAL INC", out)   # org column untouched
        from rcm_mc.npi_cleaner import rules
        self.assertEqual(rules.describe("provider-name-format")["kind"],
                         "repair")

    def test_credential_catalog_in_sync(self):
        # Every credential the engine can parse must have a display meaning
        # in refdata (and vice versa) — the two sets are maintained together.
        from rcm_mc.npi_cleaner import refdata
        self.assertEqual(set(engine._CREDENTIALS), set(refdata.CREDENTIALS))
        self.assertEqual(refdata.credential_meaning("m.d."),
                         "Doctor of Medicine")
        self.assertIsNone(refdata.credential_meaning("XYZ"))

    def test_formula_injection_defanged(self):
        # A cell that would start an Excel formula must be neutralized in CSV.
        data = ("NPI,Note\n" + GOOD_A + ",=SUM(A1:A9)\n").encode()
        res = engine.clean_bytes(data, "x.csv")
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("'=SUM(A1:A9)", out)

    def test_phi_deid_masks_patient_keeps_provider(self):
        # De-id must mask ONLY patient identifiers — provider NPI/name stay
        # intact (NPPES recovery relies on them). Off by default.
        data = (
            "BillingNPI,ProviderName,PatientName,PatientDOB,PatientZip,"
            "MRN,SSN,PatientAcct\n"
            f"{GOOD_B},Dr Jane Smith,John Q Public,1980-05-14,90210,"
            "MR12345,123-45-6789,ACCT-778\n"
            f"{GOOD_B},Dr Jane Smith,Mary Roe,1975-11-02,90210,"
            "MR99999,987-65-4321,ACCT-778\n"
        ).encode()
        res = engine.clean_bytes(data, "phi.csv", deid=True)
        sc = res.as_scorecard()
        self.assertIsNotNone(sc.get("deid"))
        self.assertGreater(sc["deid"]["cells"], 0)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        # Provider identifiers preserved.
        self.assertIn(GOOD_B, out)
        self.assertIn("Dr Jane Smith", out)
        # Patient identifiers masked.
        self.assertNotIn("John Q Public", out)
        self.assertNotIn("Mary Roe", out)
        self.assertNotIn("123-45-6789", out)
        self.assertNotIn("1980-05-14", out)   # DOB reduced to year
        self.assertIn("1980", out)
        self.assertIn("902XX", out)            # ZIP truncated to 3 digits
        # MRN/account tokenized, and the SAME source value → SAME token so
        # rows still link (both rows share PatientAcct ACCT-778).
        self.assertNotIn("MR12345", out)
        self.assertNotIn("ACCT-778", out)
        lines = [ln for ln in out.splitlines() if ln.strip()][1:]
        acct_tokens = [ln.split(",")[-1] for ln in lines]
        self.assertEqual(acct_tokens[0], acct_tokens[1])   # stable token
        self.assertTrue(acct_tokens[0].startswith("PT-"))

    def test_phi_deid_off_by_default(self):
        # Without the flag, patient data passes through untouched.
        data = ("BillingNPI,PatientName,SSN\n"
                f"{GOOD_B},John Q Public,123-45-6789\n").encode()
        res = engine.clean_bytes(data, "phi.csv")
        self.assertIsNone(res.as_scorecard().get("deid"))
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("John Q Public", out)
        self.assertIn("123-45-6789", out)

    def test_xlsx_upload_roundtrip(self):
        openpyxl = __import__("openpyxl")
        from io import BytesIO
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ClaimID", "BillingNPI"])
        ws.append([1, GOOD_A])
        ws.append([2, "99999"])
        buf = BytesIO()
        wb.save(buf)
        res = engine.clean_bytes(buf.getvalue(), "claims.xlsx")
        sc = res.as_scorecard()
        self.assertEqual(sc["delimiter"], "xlsx (Excel)")
        self.assertEqual(sc["rows_in"], 2)
        self.assertEqual(sc["billing_column"], "BillingNPI")

    def test_workbook_generated(self):
        data = (f"BillingNPI,AllowedAmt\n{GOOD_A},80\n").encode()
        res = engine.clean_bytes(data, "c.csv")
        self.assertTrue(res.workbook_path)
        openpyxl = __import__("openpyxl")
        wb = openpyxl.load_workbook(res.workbook_path)
        self.assertIn("Scorecard", wb.sheetnames)
        self.assertIn("Cleaned data", wb.sheetnames)

    def test_sample_csv_cleans(self):
        res = engine.clean_bytes(engine.sample_csv().encode(), "sample.csv")
        sc = res.as_scorecard()
        self.assertEqual(sc["duplicates_removed"], 1)   # rows 1001/1002
        self.assertGreater(sc["billing_issues"], 0)


class TestVendorAdapter(unittest.TestCase):
    """The real, complete v49 deterministic engine (schema.standardize_any +
    clean_orchestrator.clean_all), driven through vendor_adapter."""

    def setUp(self):
        from rcm_mc.npi_cleaner import vendor_adapter as va
        if not va.available():
            self.skipTest("pandas / vendored v49 engine unavailable")
        self.va = va

    def test_v49_engine_runs_and_sizes_issues(self):
        data = (
            "ClaimID,BillingProviderNPI,ReferringNPI,ChargeAmt,AllowedAmt,"
            "PaidAmt,DateOfService,PaidDate,HCPCS\n"
            f"1,{GOOD_A},{GOOD_B},100,80,60,2024-01-15,2024-02-01,99213\n"
            # allowed>billed + paid>allowed (money), referring==billing (role)
            f"2,{GOOD_A},{GOOD_A},50,90,40,2024-03-10,2024-03-01,99214\n"
            f"3,99999,{GOOD_B},200,150,120,2024-05-01,2024-06-01,99215\n"
        ).encode()
        res = self.va.run(data)
        self.assertIsNotNone(res)
        self.assertIn("clean_all", res["engine"])
        # Real screens fire; issues are sized with a systematic verdict.
        self.assertIn("money_ordering", res["screens"])
        self.assertGreaterEqual(res["screens"]["money_ordering"], 1)
        self.assertGreaterEqual(res["screens"].get("npi_role_coherence", 0), 1)
        issues = {i["issue"] for i in res["issues"]}
        self.assertIn("money_ordering", issues)
        # A corrections companion is produced for the consistency violations.
        self.assertGreater(res["suggestions_n"], 0)
        self.assertTrue(res["suggestions_records"])
        self.assertIn("suggested_value", res["suggestions_records"][0])

    def test_engine_attaches_v49_advanced_and_companion(self):
        data = (
            "BillingNPI,ChargeAmt,AllowedAmt,PaidAmt\n"
            f"{GOOD_A},50,90,40\n"   # allowed>billed + paid>allowed
        ).encode()
        res = engine.clean_bytes(data, "c.csv")
        self.assertIsNotNone(res.advanced)
        self.assertIn("clean_all", res.advanced["engine"])
        # Suggestions companion is written to its own CSV.
        self.assertTrue(res.companion_path)
        with open(res.companion_path, encoding="utf-8") as fh:
            head = fh.readline()
        self.assertIn("suggested_value", head)

    def test_extended_anomaly_screens(self):
        # Enough rows for the Benford screen (needs >=100 amounts).
        lines = ["BillingNPI,Payer,AllowedAmt"]
        for i in range(150):
            amt = 100 + (i * 37) % 900
            lines.append(f"16799999{i%80:02d},PayerA,{amt}")
        data = ("\n".join(lines) + "\n").encode()
        res = self.va.run(data)
        self.assertIsNotNone(res)
        ext = res.get("extended", [])
        keys = {e["key"] for e in ext}
        # Benford + HHI should always be computable on this data.
        self.assertIn("benford", keys)
        self.assertIn("hhi", keys)

    def test_bundled_v49_sample_runs(self):
        from pathlib import Path
        sample = (Path(__import__("rcm_mc").__file__).parent / "npi_cleaner"
                  / "vendor_v49" / "examples" / "sample_claims.xlsx")
        if not sample.exists():
            self.skipTest("bundled sample missing")
        res = engine.clean_bytes(sample.read_bytes(), "sample_claims.xlsx")
        self.assertEqual(res.as_scorecard()["delimiter"], "xlsx (Excel)")
        self.assertIsNotNone(res.advanced)
        # 20 deterministic repairs + the JW/JZ wastage issue on the sample.
        self.assertGreater(res.advanced["repairs"], 0)
        self.assertTrue(res.advanced["issues"])


class TestConnectors(unittest.TestCase):
    """Live drug connectors (RxNorm / openFDA) with an injected opener."""

    def setUp(self):
        from rcm_mc.npi_cleaner import connectors as C
        if not C.available():
            self.skipTest("public_api_clients unavailable")
        self.C = C

    def _opener(self, url, headers, timeout_s):
        if "rxcui.json" in url and "idtype=NDC" in url:
            return json.dumps({"idGroup": {"rxnormId": ["1049502"]}}).encode()
        if "rxcui.json" in url:
            return json.dumps({"idGroup": {"rxnormId": ["860975"]}}).encode()
        if "/properties.json" in url:
            return json.dumps({"properties": {"name": "metformin", "tty": "IN"}}).encode()
        if "/ndcs.json" in url:
            return json.dumps({"ndcGroup": {"ndcList": {"ndc": ["00093-1049"]}}}).encode()
        if "api.fda.gov" in url:
            return json.dumps({"results": [{"brand_name": "GLUCOPHAGE",
                                            "generic_name": "METFORMIN",
                                            "labeler_name": "BMS"}]}).encode()
        return b"{}"

    def test_catalog_lists_sources(self):
        cat = self.C.catalog()
        self.assertGreaterEqual(len(cat), 15)
        ids = {c["id"] for c in cat}
        self.assertIn("rxnorm", ids)
        self.assertIn("nppes", ids)
        self.assertIn("openfda", ids)

    def test_resolve_drugs_rxnorm_and_openfda(self):
        res = self.C.resolve_drugs(
            ["0093-1049-01"], ["metformin"], opener=self._opener)
        by_id = {r["id"]: r for r in res}
        self.assertIn("rxnorm", by_id)
        self.assertEqual(by_id["rxnorm"]["resolved"], 2)  # 1 NDC + 1 name
        self.assertTrue(by_id["rxnorm"]["sample"][0]["rxcui"])
        self.assertIn("openfda", by_id)
        self.assertEqual(by_id["openfda"]["resolved"], 1)
        self.assertEqual(by_id["openfda"]["sample"][0]["brand"], "GLUCOPHAGE")

    def test_engine_online_wires_connectors_and_catalog(self):
        from rcm_mc.npi_cleaner import connectors as C

        def fake_resolve(ndcs, drugs, **kw):
            return [{"id": "rxnorm", "label": "RxNorm / RxNav", "queried": 1,
                     "resolved": 1, "unresolved": 0, "sample": [], "note": "ok"}]

        def fake_fetch(npi, **kw):
            return None

        data = ("BillingNPI,NDC,DrugName\n"
                f"{GOOD_A},0093-1049-01,Metformin\n").encode()
        with patch.object(C, "resolve_drugs", fake_resolve), \
             patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi", fake_fetch):
            res = engine.clean_bytes(data, "c.csv", enrich=True)
        sc = res.as_scorecard()
        self.assertTrue(sc["connectors"])
        self.assertEqual(sc["connectors"][0]["id"], "rxnorm")
        self.assertGreaterEqual(len(sc["catalog"]), 15)


class TestCompliance(unittest.TestCase):
    """OIG LEIE (offline) + Medicare PECOS (mocked client) screening."""

    def test_leie_offline_flags_excluded(self):
        from rcm_mc.npi_cleaner import compliance as C
        p = os.path.join(tempfile.mkdtemp(), "leie.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("LASTNAME,NPI,EXCLTYPE\n"
                     f"BADDOC,{GOOD_B},1128a1\n")
        r = C.screen_leie([GOOD_B, GOOD_A, "99999"], leie_path=p)
        self.assertTrue(r["available"])
        self.assertEqual(r["excluded"], 1)
        self.assertEqual(r["matches"][0]["npi"], GOOD_B)

    def test_leie_no_dataset_note(self):
        from rcm_mc.npi_cleaner import compliance as C
        r = C.screen_leie([GOOD_A], leie_path="/nonexistent/leie.csv")
        self.assertFalse(r["available"])
        self.assertIn("LEIE", r["note"])

    def test_pecos_with_mock_client(self):
        from rcm_mc.npi_cleaner import compliance as C

        class FakeCMS:
            def enrollment_lookup(self, npi):
                return {"enrolled": npi != GOOD_A}

            def opt_out_lookup(self, npi):
                return {"opted_out": npi == GOOD_B}

        r = C.screen_cms([GOOD_A, GOOD_B], cms_client=FakeCMS())
        self.assertTrue(r["available"])
        self.assertEqual(r["checked"], 2)
        self.assertEqual(r["not_enrolled"], 1)   # GOOD_A
        self.assertEqual(r["opted_out"], 1)      # GOOD_B

    def test_engine_online_attaches_compliance(self):
        from rcm_mc.npi_cleaner import compliance as C, connectors as CN

        def fake_screen(npis, **kw):
            return [{"id": "oig_leie", "label": "OIG LEIE (excluded providers)",
                     "available": True, "checked": len(npis), "excluded": 0,
                     "matches": [], "note": "clean"}]

        def fake_fetch(npi, **kw):
            return None

        data = (f"BillingNPI\n{GOOD_A}\n99999\n").encode()
        with patch.object(C, "screen", fake_screen), \
             patch.object(CN, "resolve_drugs", lambda *a, **k: []), \
             patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi", fake_fetch):
            res = engine.clean_bytes(data, "c.csv", enrich=True)
        sc = res.as_scorecard()
        self.assertTrue(sc["compliance"])
        self.assertEqual(sc["compliance"][0]["id"], "oig_leie")


class TestDeepPipeline(unittest.TestCase):
    """Deep recovery (full v49 run_pipeline) wiring — timeout + graceful fail."""

    def test_available(self):
        from rcm_mc.npi_cleaner import deep_pipeline as D
        # Boolean either way; just exercise the guard.
        self.assertIn(D.available(), (True, False))

    def test_timeout_is_graceful_not_a_hang(self):
        from rcm_mc.npi_cleaner import deep_pipeline as D
        if not D.available():
            self.skipTest("deep pipeline unavailable")
        from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import pipeline as P

        def _hang(*a, **k):
            time.sleep(10)

        with patch.object(P, "run_pipeline", _hang):
            out = D.run(b"BillingNPI\n" + GOOD_A.encode(),
                        "x.csv", timeout_s=1)
        self.assertFalse(out["ok"])
        self.assertIn("timed out", out["error"])

    def test_engine_attaches_deep_result(self):
        from rcm_mc.npi_cleaner import deep_pipeline, engine as eng
        import tempfile
        import os

        wb = os.path.join(tempfile.mkdtemp(), "x_recovered.xlsx")
        with open(wb, "wb") as fh:
            fh.write(b"PK\x03\x04stub")

        def fake_run(data, name, **kw):
            return {"ok": True, "error": None, "stats": {"npis_recovered": 5},
                    "workbook_path": wb, "workbook_name": "x_recovered.xlsx"}

        data = ("BillingNPI\n" + GOOD_A + "\n").encode()
        with patch.object(deep_pipeline, "run", fake_run):
            res = eng.clean_bytes(data, "x.csv", deep=True)
        self.assertIsNotNone(res.deep)
        self.assertTrue(res.deep["ok"])
        self.assertEqual(res.deep_workbook_path, wb)
        self.assertEqual(res.as_scorecard()["deep_workbook_name"],
                         "x_recovered.xlsx")


class TestNppesBridge(unittest.TestCase):
    """Live NPPES verify/recover, cross-using the shared CMS client (mocked)."""

    def _providers(self):
        from rcm_mc.data_public.nppes_api_client import NppesProvider
        return NppesProvider

    def test_verify_active_and_not_found(self):
        from rcm_mc.npi_cleaner import nppes_bridge
        NppesProvider = self._providers()

        def fake_fetch(npi, **kw):
            if npi == GOOD_B:
                return NppesProvider(npi=npi, entity_type=2,
                                     name="MERCY HOSPITAL", state="OH")
            return None

        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi", fake_fetch):
            out = nppes_bridge.verify_npis([GOOD_B, GOOD_A, GOOD_B, "123"])
        self.assertEqual(out["checked"], 2)     # GOOD_B + GOOD_A (distinct, 10-digit)
        self.assertEqual(out["active"], 1)      # GOOD_B resolves
        self.assertEqual(out["not_found"], 1)   # GOOD_A returns None
        self.assertEqual(out["records"][GOOD_B]["status"], "active")

    def test_recover_candidates(self):
        from rcm_mc.npi_cleaner import nppes_bridge
        NppesProvider = self._providers()

        def fake_search(name, state="", **kw):
            return [NppesProvider(npi=GOOD_A, entity_type=2,
                                  name="ACME CLINIC LLC", state=state or "TX")]

        with patch("rcm_mc.data_public.nppes_api_client.search_by_organization",
                   fake_search):
            out = nppes_bridge.recover_candidates([
                {"row": "2", "name": "Acme Clinic", "state": "TX"},
                {"row": "3", "name": "Acme Clinic", "state": "TX"},  # deduped
            ])
        self.assertEqual(out["searched"], 1)
        self.assertEqual(out["resolved"], 1)
        self.assertEqual(out["matches"][0]["candidates"][0]["npi"], GOOD_A)

    def test_engine_enrich_end_to_end(self):
        NppesProvider = self._providers()

        def fake_fetch(npi, **kw):
            if npi == GOOD_B:
                return NppesProvider(npi=npi, entity_type=2,
                                     name="MERCY HOSPITAL", state="OH")
            return None

        def fake_search(name, state="", **kw):
            return [NppesProvider(npi=GOOD_A, entity_type=2,
                                  name="ACME CLINIC LLC", state=state or "TX")]

        data = (
            "ClaimID,BillingProviderNPI,OrganizationName,ProviderState\n"
            f"1,{GOOD_B},Mercy Hospital,OH\n"
            "2,,Acme Clinic,TX\n"
        ).encode()
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi", fake_fetch), \
             patch("rcm_mc.data_public.nppes_api_client.search_by_organization",
                   fake_search):
            res = engine.clean_bytes(data, "c.csv", enrich=True)
        self.assertIsNotNone(res.nppes)
        self.assertEqual(res.nppes["verify"]["active"], 1)
        matches = res.nppes["recover"]["matches"]
        self.assertTrue(any(m["candidates"] for m in matches))

    def test_enrich_off_by_default(self):
        data = f"NPI\n{GOOD_A}\n".encode()
        res = engine.clean_bytes(data, "c.csv")
        self.assertIsNone(res.nppes)

    def test_recovery_written_to_cleaned_file(self):
        NppesProvider = self._providers()

        def fake_fetch(npi, **kw):
            return None  # nothing verifies; forces recovery path

        def fake_search(name, state="", **kw):
            return [NppesProvider(npi=GOOD_A, entity_type=2,
                                  name="ACME CLINIC LLC", state=state or "TX")]

        data = (
            "BillingNPI,OrganizationName,ProviderState\n"
            ",Acme Clinic,TX\n"
            "99999,Acme Clinic,TX\n"
        ).encode()
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi", fake_fetch), \
             patch("rcm_mc.data_public.nppes_api_client.search_by_organization",
                   fake_search):
            res = engine.clean_bytes(data, "c.csv", enrich=True)
        # Both Acme rows get the recovered NPI written to a new column.
        self.assertEqual(len(res.recovered_rows), 2)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("recovered_billing_npi", out)
        self.assertEqual(out.count(GOOD_A), 2)


class TestNpiCleanerHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket
        import threading
        from rcm_mc.server import build_server
        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_page_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/npi-cleaner") as r:
                    body = r.read().decode()
                self.assertIn("NPI Claims Cleaner", body)
                self.assertIn("/npi-cleaner/upload", body)
                self.assertIn("npi-drop", body)
                # Tabbed results + live-connector affordances present.
                self.assertIn("npi-tabs", body)
                self.assertIn('data-panel="connectors"', body)
                self.assertIn("Connections available", body)
                self.assertIn("Go online", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_changelog_download_route(self):
        # ?fmt=changelog streams the audit trail once a job with changes ran.
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv_b = ("NPI,ChargeAmt\n"
                         f"  {GOOD_A}  ,\"$1,250.50\"\n").encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv_b, method="POST",
                    headers={"X-Filename": "c.csv"})
                with _u.urlopen(req) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        j = json.loads(r.read().decode())
                        if j.get("done"):
                            break
                    time.sleep(0.05)
                self.assertTrue(j["scorecard"]["changelog_name"])
                self.assertIn("quality", j["scorecard"])
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/download/{job_id}"
                    "?fmt=changelog"
                ) as r:
                    body = r.read().decode()
                self.assertIn("before", body.splitlines()[0])
                self.assertIn("1250.50", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_worklist_exec_history_rules_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv_b = ("ClaimID,HCPCS\n1,99213\n2,BAD!!\n").encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv_b, method="POST",
                    headers={"X-Filename": "w.csv"})
                with _u.urlopen(req) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        j = json.loads(r.read().decode())
                        if j.get("done"):
                            break
                    time.sleep(0.05)
                # Worklist: just the flagged row, with a _row column.
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/download/{job_id}"
                    "?fmt=worklist&rule=hcpcs-malformed"
                ) as r:
                    wl = r.read().decode()
                self.assertIn("_row", wl.splitlines()[0])
                self.assertIn("BAD!!", wl)
                self.assertNotIn("99213", wl)      # unflagged row excluded
                # Executive report renders.
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/download/{job_id}"
                    "?fmt=exec"
                ) as r:
                    self.assertIn("Claims data-quality report",
                                  r.read().decode())
                # History page + API + rules API.
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/history") as r:
                    _hist_html = r.read().decode()
                self.assertIn("Quality-score trend", _hist_html)
                self.assertIn("Per-rule trend", _hist_html)
                self.assertIn("nh-rule-box", _hist_html)
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/history") as r:
                    runs = json.loads(r.read().decode())["runs"]
                self.assertTrue(any(x["file_name"] == "w.csv" for x in runs))
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/rules") as r:
                    self.assertGreater(
                        len(json.loads(r.read().decode())["rules"]), 50)
            finally:
                server.shutdown()
                server.server_close()

    def test_profiles_api_and_sync_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                # Save a profile over the API.
                body = json.dumps({"name": "http-prof", "config": {
                    "accepted_rules": ["date-stale"],
                    "thresholds": {"stale_years": 2}}}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/profiles",
                    data=body, method="POST",
                    headers={"Content-Type": "application/json"})
                with _u.urlopen(req) as r:
                    self.assertTrue(json.loads(r.read().decode())["ok"])
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/profiles") as r:
                    names = [p["name"] for p in
                             json.loads(r.read().decode())["profiles"]]
                self.assertIn("http-prof", names)
                # Async upload honors X-Profile.
                csv_b = ("ClaimID,DateOfService\n1,2023-01-01\n").encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv_b, method="POST",
                    headers={"X-Filename": "p.csv", "X-Profile": "http-prof"})
                with _u.urlopen(req) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        j = json.loads(r.read().decode())
                        if j.get("done"):
                            break
                    time.sleep(0.05)
                self.assertEqual(j["scorecard"]["profile"], "http-prof")
                self.assertIn("date-stale", j["scorecard"]["sanity"])
                self.assertIn("date-stale", j["scorecard"]["accepted_rules"])
                # Synchronous API clean with the same profile.
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/clean"
                    "?profile=http-prof",
                    data=csv_b, method="POST",
                    headers={"X-Filename": "sync.csv"})
                with _u.urlopen(req) as r:
                    sc = json.loads(r.read().decode())
                self.assertIn("quality", sc)
                self.assertEqual(sc["profile"], "http-prof")
                # Cleanup.
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/api/profiles/delete",
                    data=json.dumps({"name": "http-prof"}).encode(),
                    method="POST",
                    headers={"Content-Type": "application/json"})
                with _u.urlopen(req) as r:
                    self.assertTrue(json.loads(r.read().decode())["ok"])
            finally:
                server.shutdown()
                server.server_close()

    def test_large_upload_accepted_others_capped(self):
        # Claims uploads above the 10 MB global POST cap are accepted on the
        # cleaner upload route (200 MB ceiling); every other POST stays capped.
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                header = b"ClaimID,BillingNPI\n"
                row = b"1," + GOOD_B.encode() + b"\n"
                big = header + row * ((11 * 1024 * 1024) // len(row) + 1)
                self.assertGreater(len(big), 10_000_000)  # above the old cap
                # Upload route accepts it → returns a job id.
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=big, method="POST", headers={"X-Filename": "big.csv"})
                with _u.urlopen(req) as r:
                    self.assertIn("job_id", json.loads(r.read().decode()))
                # An ordinary POST path still rejects the same oversized body.
                # The guard rejects early on Content-Length and closes the
                # socket, so the client sees either a clean 413 or a broken
                # pipe mid-upload — both prove the body was refused (and the
                # broken pipe is the desired don't-drain-the-body behavior).
                req2 = _u.Request(
                    f"http://127.0.0.1:{port}/__cap_probe__",
                    data=big, method="POST")
                try:
                    _u.urlopen(req2)
                    self.fail("expected rejection on a non-upload POST path")
                except _u.HTTPError as exc:  # type: ignore[attr-defined]
                    self.assertEqual(exc.code, 413)
                except (_ue.URLError, ConnectionError):
                    pass  # server closed the connection early — refused
            finally:
                server.shutdown()
                server.server_close()

    def test_upload_status_download_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv = (
                    "ClaimID,BillingNPI\n"
                    f"1,{GOOD_A}\n"
                    "2,\n"
                    "3,badnpi\n"
                ).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv, method="POST",
                    headers={"X-Filename": "claims%20file.csv"},
                )
                with _u.urlopen(req) as r:
                    up = json.loads(r.read().decode())
                job_id = up["job_id"]
                self.assertTrue(job_id)

                # Poll to completion.
                sc = None
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        st = json.loads(r.read().decode())
                    if st.get("done"):
                        sc = st.get("scorecard")
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(sc, "job never completed")
                self.assertEqual(sc["rows_in"], 3)
                self.assertEqual(sc["billing_column"], "BillingNPI")
                self.assertEqual(sc["billing_issues"], 2)  # blank + malformed
                self.assertEqual(sc["out_name"], "claims_file_cleaned.csv")

                # Download the cleaned file.
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/download/{job_id}"
                ) as r:
                    self.assertIn("attachment", r.headers.get("Content-Disposition", ""))
                    out = r.read().decode()
                self.assertIn("ClaimID,BillingNPI", out)
            finally:
                server.shutdown()
                server.server_close()

    def test_detect_and_override_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv = (
                    "Claim,ProvID,OrgNm,St,AllowedAmt\n"
                    f"1,{GOOD_A},Mercy,OH,80\n"
                    "2,99999,Mercy,OH,40\n"
                ).encode()
                # detect returns headers + a role mapping
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/detect",
                    data=csv, method="POST",
                    headers={"X-Filename": "c.csv"})
                with _u.urlopen(req) as r:
                    det = json.loads(r.read().decode())
                if not det.get("available"):
                    self.skipTest("detector unavailable")
                self.assertIn("ProvID", det["headers"])
                self.assertTrue(any(role["key"] == "billing_npi"
                                    for role in det["roles"]))

                # upload with an explicit override → billing column honored
                ov = json.dumps({"billing_npi": "ProvID", "state": "St"})
                req2 = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv, method="POST",
                    headers={"X-Filename": "c.csv",
                             "X-Overrides": _up.quote(ov)})
                with _u.urlopen(req2) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                sc = None
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        st = json.loads(r.read().decode())
                    if st.get("done"):
                        sc = st["scorecard"]
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(sc)
                self.assertEqual(sc["billing_column"], "ProvID")
                self.assertEqual(sc["billing_issues"], 1)  # the 99999
            finally:
                server.shutdown()
                server.server_close()

    def test_sample_and_xlsx_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                # The sample endpoint returns a usable CSV.
                with _u.urlopen(f"http://127.0.0.1:{port}/npi-cleaner/sample") as r:
                    sample = r.read()
                self.assertIn(b"BillingProviderNPI", sample)

                # Upload it and pull the .xlsx workbook back.
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=sample, method="POST",
                    headers={"X-Filename": "sample_claims.csv"})
                with _u.urlopen(req) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                sc = None
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        st = json.loads(r.read().decode())
                    if st.get("done"):
                        sc = st["scorecard"]
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(sc)
                self.assertTrue(sc["workbook_name"].endswith(".xlsx"))
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/download/{job_id}?fmt=xlsx"
                ) as r:
                    body = r.read()
                    self.assertEqual(body[:4], b"PK\x03\x04")  # a real zip/xlsx
                    self.assertIn("spreadsheetml",
                                  r.headers.get("Content-Type", ""))
            finally:
                server.shutdown()
                server.server_close()

    def test_pivot_analysis_page_and_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv = (
                    "ClaimID,ProviderState,AllowedAmt\n"
                    f"1,OH,100\n2,TX,200\n3,OH,50\n"
                ).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=csv, method="POST", headers={"X-Filename": "c.csv"})
                with _u.urlopen(req) as r:
                    job_id = json.loads(r.read().decode())["job_id"]
                for _ in range(50):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/npi-cleaner/status/{job_id}"
                    ) as r:
                        if json.loads(r.read().decode()).get("done"):
                            break
                    time.sleep(0.05)
                # data endpoint returns the cleaned rows as JSON
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/data/{job_id}"
                ) as r:
                    data = json.loads(r.read().decode())
                self.assertIn("ProviderState", data["columns"])
                self.assertEqual(len(data["rows"]), 3)
                # analysis page renders with the pivot builder
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/analyze/{job_id}"
                ) as r:
                    page = r.read().decode()
                self.assertIn("an-fieldlist", page)
                self.assertIn(f"/npi-cleaner/data/", page)
                # enhanced analytics: stat tiles, quick views, chart modes
                self.assertIn("an-tiles", page)
                self.assertIn("Quick views", page)
                self.assertIn('value="heatmap"', page)
                self.assertIn('value="scatter"', page)
                self.assertIn('value="correlation"', page)
                self.assertIn("renderCorrelation", page)
                self.assertIn("Pearson correlation", page)
                self.assertIn('value="box"', page)
                self.assertIn("renderBoxplot", page)
                self.assertIn('value="histogram"', page)
                self.assertIn("renderHistogram", page)
                self.assertIn("% of total", page)
                # unknown job → graceful "expired" page (still 200)
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/npi-cleaner/analyze/deadbeef"
                ) as r:
                    self.assertIn("expired", r.read().decode())
            finally:
                server.shutdown()
                server.server_close()

    def test_empty_upload_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/npi-cleaner/upload",
                    data=b"", method="POST",
                    headers={"X-Filename": "x.csv", "Content-Length": "0"},
                )
                try:
                    _u.urlopen(req)
                    self.fail("expected 400")
                except _u.HTTPError as e:  # type: ignore[attr-defined]
                    self.assertEqual(e.code, 400)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
