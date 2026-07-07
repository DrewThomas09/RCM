"""Engine-case coverage for the NPI cleaner — survey-driven gaps.

Each class exercises one shipped case end-to-end through the REAL engine
path (clean_bytes / bigfile.clean_path / x12), per the repo's no-mocks
convention: silent-lossy ingest (ragged rows, UTF-16/32, EU money,
scientific-notation NPIs), half-done normalizers (compact/datetime dates,
date-unparseable), duplicate-billing worklists, streaming honesty +
cross-chunk near-duplicates + merged panels, value-based NPI column sniff,
native-837 referring/ordering/operating extraction, preamble/headerless
shaping, zip-batch skip accounting, the NPI↔name / DRG-on-professional
scrubber checks, modifier content preservation, the ISA-CSV misroute,
accented-name mojibake, registry↔engine dimension consistency, and the
extended wishlist auto-file loop.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from rcm_mc.npi_cleaner import bigfile, engine, rules, x12

# Luhn-valid NPIs (80840 + first 9) used across the existing suite.
GOOD_A = "1234567893"
GOOD_B = "1679576722"
# Luhn-valid but IMPLAUSIBLE first digit — CMS never issues 9xx NPIs.
LUHN_OK_BAD_PREFIX = "9234567896"


def _wipe_auto(title: str) -> None:
    """Remove pre-existing auto-filed wishlist rows with this title so the
    dedupe-by-title contract can't mask (or fake) a fresh auto-file."""
    from rcm_mc.npi_cleaner import wishlist
    for r in wishlist.list_requests():
        if r.get("source") == "auto" and r["title"] == title:
            wishlist.delete_request(r["id"])


def _auto_titles() -> list:
    from rcm_mc.npi_cleaner import wishlist
    return [r["title"] for r in wishlist.list_requests()
            if r.get("source") == "auto"]


class TestRaggedRows(unittest.TestCase):
    """P0: pads/trims used to happen with zero signal — now flagged,
    counted, worklisted, and warned about when data was dropped."""

    def test_truncated_and_padded_flagged(self):
        data = (b"ClaimID,BillingNPI,ChargeAmt\n"
                b"1," + GOOD_B.encode() + b",100,EXTRA,MORE\n"   # truncated
                b"2," + GOOD_A.encode() + b"\n"                  # padded
                b"3," + GOOD_B.encode() + b",50\n")              # clean
        res = engine.clean_bytes(data, "rag.csv")
        self.assertEqual(res.sanity.get("ragged-row"), 2)
        self.assertEqual(res.structure.get("ragged_rows"),
                         {"padded": 1, "truncated": 1})
        self.assertEqual(res.flag_rows.get("ragged-row"), [1, 2])
        self.assertTrue(any("MORE cells" in w for w in res.warnings),
                        res.warnings)
        # The truncated row lost its overflow — the output must not lie.
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertNotIn("EXTRA", out)
        # Scorecard surfaces both the counter and the structure entry.
        sc = res.as_scorecard()
        self.assertEqual(sc["sanity"].get("ragged-row"), 2)
        self.assertIn("ragged_rows", sc["structure"])

    def test_clean_file_never_flags(self):
        res = engine.clean_bytes(
            f"A,B\n1,{GOOD_A}\n2,{GOOD_B}\n".encode(), "ok.csv")
        self.assertNotIn("ragged-row", res.sanity)
        self.assertNotIn("ragged_rows", res.structure)

    def test_xlsx_variable_width_rows_not_flagged(self):
        # openpyxl rows are naturally variable-width — padding an xlsx row
        # is structure, not data loss, and must not tank the grade.
        openpyxl = __import__("openpyxl")
        from io import BytesIO
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ClaimID", "BillingNPI", "Note"])
        ws.append([1, GOOD_A, "full row"])
        ws.append([2, GOOD_B])            # short row — normal in xlsx
        buf = BytesIO()
        wb.save(buf)
        res = engine.clean_bytes(buf.getvalue(), "w.xlsx")
        self.assertNotIn("ragged-row", res.sanity)

    def test_streaming_merges_ragged_counts(self):
        rows = ["ClaimID,BillingNPI,ChargeAmt"]
        for i in range(1, 200):
            rows.append(f"{i},{GOOD_B},100")
        rows[5] = rows[5] + ",OVERFLOW"       # truncated, chunk 1
        rows.append(f"200,{GOOD_A}")          # padded, last chunk
        data = ("\n".join(rows) + "\n").encode()
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "rag.csv")
            with open(p, "wb") as fh:
                fh.write(data)
            with patch.object(bigfile, "STREAM_THRESHOLD_BYTES", 512), \
                    patch.object(bigfile, "CHUNK_TARGET_BYTES", 1024):
                res = bigfile.clean_path(p, "rag.csv")
        self.assertEqual(res.structure.get("ragged_rows"),
                         {"padded": 1, "truncated": 1})
        self.assertEqual(res.sanity.get("ragged-row"), 2)
        self.assertTrue(any("MORE cells" in w for w in res.warnings))


class TestWideEncodings(unittest.TestCase):
    """P0: UTF-16/32 uploads decoded to NUL-garbage and were 'cleaned'."""

    def test_utf16_le_bom_excel_unicode_text(self):
        # Excel "Unicode Text" = UTF-16-LE + BOM + tabs.
        text = f"ClaimID\tBillingNPI\n1\t{GOOD_B}\n2\t99999\n"
        res = engine.clean_bytes(text.encode("utf-16"), "u16.csv")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        st = res.column_stats["BillingNPI"]
        self.assertEqual((st["valid"], st["malformed"]), (1, 1))
        self.assertTrue(any("UTF-16" in w for w in res.warnings))
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertNotIn("\x00", out)

    def test_utf16_be_bom(self):
        text = f"ClaimID,BillingNPI\n1,{GOOD_A}\n"
        res = engine.clean_bytes(
            b"\xfe\xff" + text.encode("utf-16-be"), "u16be.csv")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 1)

    def test_utf16_le_without_bom_heuristic(self):
        text = f"ClaimID,BillingNPI\n1,{GOOD_A}\n2,{GOOD_B}\n"
        res = engine.clean_bytes(text.encode("utf-16-le"), "nobom.csv")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 2)

    def test_utf32_le_bom(self):
        text = f"ClaimID,BillingNPI\n1,{GOOD_A}\n"
        res = engine.clean_bytes(text.encode("utf-32"), "u32.csv")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 1)

    def test_utf8_sig_still_clean(self):
        # Pin the already-working BOM path so it can never regress.
        data = ("﻿ClaimID,BillingNPI\n1," + GOOD_A + "\n").encode("utf-8")
        res = engine.clean_bytes(data, "sig.csv")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertEqual(res.npi_columns, ["BillingNPI"])

    def test_streaming_utf16_transcodes(self):
        rows = ["ClaimID,BillingNPI,ChargeAmt"]
        for i in range(1, 300):
            rows.append(f"{i},{GOOD_B},100")
        data = ("\n".join(rows) + "\n").encode("utf-16")   # BOM + LE
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "u16big.csv")
            with open(p, "wb") as fh:
                fh.write(data)
            with patch.object(bigfile, "STREAM_THRESHOLD_BYTES", 512), \
                    patch.object(bigfile, "CHUNK_TARGET_BYTES", 1024), \
                    patch.object(bigfile, "_FORMAT_INMEM_MAX_BYTES", 1024):
                res = bigfile.clean_path(p, "u16big.csv")
        self.assertEqual(res.n_rows_in, 299)
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 299)
        self.assertTrue(any("transcoded to UTF-8" in w
                            for w in res.warnings), res.warnings[:3])


class TestDelimiterVariants(unittest.TestCase):
    """P3: only TSV had coverage; semicolon/pipe/quoted-newline pinned."""

    def test_semicolon_with_eu_money(self):
        # Semicolon delimiters are the EU-Excel signature — exactly where
        # comma-decimal money lives; the two must compose.
        data = (f"ClaimID;BillingNPI;ChargeAmt\n"
                f"1;{GOOD_B};1.234,56\n2;{GOOD_A};17,50\n").encode()
        res = engine.clean_bytes(data, "eu.csv")
        sc = res.as_scorecard()
        self.assertEqual(sc["delimiter"], "semicolon")
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 2)
        self.assertEqual(res.repairs.get("money-eu-decimal"), 2)
        self.assertNotIn("money-unparseable", res.sanity)
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("1234.56", out)
        self.assertIn("17.50", out)

    def test_pipe_delimiter(self):
        data = f"ClaimID|BillingNPI\n1|{GOOD_A}\n2|{GOOD_B}\n".encode()
        res = engine.clean_bytes(data, "p.csv")
        self.assertEqual(res.as_scorecard()["delimiter"], "pipe")
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 2)

    def test_quoted_newline_in_memory(self):
        data = ("ClaimID,Note,BillingNPI\n"
                '1,"line one\nline two, with comma",' + GOOD_A + "\n").encode()
        res = engine.clean_bytes(data, "q.csv")
        self.assertEqual(res.n_rows_in, 1)
        self.assertEqual(res.column_stats["BillingNPI"]["valid"], 1)
        self.assertNotIn("ragged-row", res.sanity)


class TestMoneyLocale(unittest.TestCase):
    """P0: '1.234,56' was corrupted to 1.23 and logged as a repair;
    P2: trailing-sign negatives flagged instead of parsed."""

    def test_eu_dotted_thousands(self):
        self.assertEqual(engine._clean_money_cell("1.234,56"),
                         ("1234.56", ["money-eu-decimal"]))
        self.assertEqual(engine._clean_money_cell("12.345.678,90"),
                         ("12345678.90", ["money-eu-decimal"]))

    def test_eu_plain_comma_decimal(self):
        self.assertEqual(engine._clean_money_cell("1234,56"),
                         ("1234.56", ["money-eu-decimal"]))

    def test_us_forms_unchanged(self):
        # Non-regression: everything that parsed before parses the same.
        self.assertEqual(engine._clean_money_cell("1,234.56"),
                         ("1234.56", ["money-normalize"]))
        self.assertEqual(engine._clean_money_cell("1,234"),
                         ("1234.00", ["money-normalize"]))
        self.assertEqual(engine._clean_money_cell("(123.45)"),
                         ("-123.45", ["money-normalize"]))
        self.assertEqual(engine._clean_money_cell("100.00"), ("100.00", []))

    def test_trailing_negative_and_cr(self):
        self.assertEqual(engine._clean_money_cell("500.00-"),
                         ("-500.00", ["money-trailing-negative"]))
        self.assertEqual(engine._clean_money_cell("500.00CR"),
                         ("-500.00", ["money-trailing-negative"]))
        self.assertEqual(engine._clean_money_cell("1,500.00-"),
                         ("-1500.00", ["money-trailing-negative"]))
        self.assertFalse(engine._money_unparseable("500.00-"))
        self.assertEqual(engine._to_number("500.00-"), -500.0)

    def test_still_unparseable_still_flags(self):
        self.assertTrue(engine._money_unparseable("pending"))
        self.assertTrue(engine._money_unparseable("1,2OO"))
        res = engine.clean_bytes(
            b"ChargeAmt\npending\n100.00\n", "bad.csv")
        self.assertEqual(res.sanity.get("money-unparseable"), 1)

    def test_full_run_regression_eu_corruption(self):
        # The exact corruption the survey verified live: 1.234,56 → $1.23.
        res = engine.clean_bytes(
            'ClaimID,ChargeAmt\n1,"1.234,56"\n'.encode(), "eu2.csv")
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("1234.56", out)
        self.assertNotIn("1.23\n", out)
        self.assertEqual(res.repairs.get("money-eu-decimal"), 1)


class TestDateCases(unittest.TestCase):
    """P1: compact/datetime dates unnormalized; no date-unparseable flag;
    chronology checks silently disabled."""

    def test_compact_ccyymmdd(self):
        self.assertEqual(engine._clean_date_cell("20240211"),
                         ("2024-02-11", ["date-compact-to-iso"]))
        # Implausible month/day never converts (flagged instead).
        self.assertEqual(engine._clean_date_cell("20241399"),
                         ("20241399", []))

    def test_us_datetime_variants(self):
        self.assertEqual(engine._clean_date_cell("01/02/2024 10:30"),
                         ("2024-01-02", ["date-us-to-iso"]))
        self.assertEqual(engine._clean_date_cell("1/2/24 3:45:00 PM"),
                         ("2024-01-02", ["date-us-to-iso"]))
        self.assertEqual(engine._clean_date_cell("03/04/2024"),
                         ("2024-03-04", ["date-us-to-iso"]))

    def test_date_unparseable_flag(self):
        res = engine.clean_bytes(
            b"DateOfService\nPENDING\n2024-01-01\nnot/a/date\n", "d.csv")
        self.assertEqual(res.sanity.get("date-unparseable"), 2)
        self.assertEqual(res.flag_rows.get("date-unparseable"), [1, 3])
        # Blank cells never flag (null tokens blank first).
        res2 = engine.clean_bytes(b"DateOfService\nN/A\n\n", "d2.csv")
        self.assertNotIn("date-unparseable", res2.sanity)

    def test_compact_dates_reenable_chronology(self):
        # Before the compact repair these rows escaped EVERY date screen.
        data = (b"AdmitDate,DischargeDate\n20240210,20240205\n")
        res = engine.clean_bytes(data, "chron.csv")
        self.assertEqual(res.sanity.get("discharge-before-admit"), 1)
        self.assertEqual(res.repairs.get("date-compact-to-iso"), 2)

    def test_registry_and_dimension(self):
        self.assertEqual(rules.describe("date-unparseable")["dimension"],
                         "validity")
        self.assertIn("date-unparseable",
                      engine.CleanResult._VALIDITY_RULES)
        self.assertEqual(rules.describe("date-compact-to-iso")["kind"],
                         "repair")


class TestNpiScientific(unittest.TestCase):
    """P1: sci-notation NPIs — exact recovery when possible, an honest
    lossy flag when not (previously: 12-digit junk, generic malformed)."""

    def test_recoverable_mantissa(self):
        self.assertEqual(engine._clean_npi_cell("1.679576722E+09"),
                         (GOOD_B, ["npi-scientific-notation"]))
        self.assertEqual(engine._clean_npi_cell("1.234567893e+09"),
                         (GOOD_A, ["npi-scientific-notation"]))

    def test_lossy_mantissa_left_alone(self):
        v, r = engine._clean_npi_cell("1.68E+09")
        self.assertEqual((v, r), ("1.68E+09", []))
        # 9 significant digits is still not 10 — could be any trailing digit.
        v2, r2 = engine._clean_npi_cell("1.6795767E+09")
        self.assertEqual((v2, r2), ("1.6795767E+09", []))

    def test_full_run_flags_lossy_and_repairs_recoverable(self):
        data = (f"BillingNPI\n1.679576722E+09\n1.68E+09\n{GOOD_A}\n"
                ).encode()
        res = engine.clean_bytes(data, "sci.csv")
        self.assertEqual(res.repairs.get("npi-scientific-notation"), 1)
        self.assertEqual(res.sanity.get("npi-scientific-lossy"), 1)
        self.assertEqual(res.flag_rows.get("npi-scientific-lossy"), [2])
        st = res.column_stats["BillingNPI"]
        self.assertEqual(st["valid"], 2)       # recovered + plain
        self.assertEqual(st["malformed"], 1)   # the lossy cell
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn(GOOD_B, out)             # recovered exactly
        self.assertNotIn("167957672209", out)  # no 12-digit junk


class TestDuplicateWorklists(unittest.TestCase):
    """P1: the double-billing rules had counters but no downloadable rows."""

    def _res(self):
        data = (f"ClaimID,BillingNPI,PatientID,DateOfService,HCPCS,BilledAmt\n"
                f"1,{GOOD_A},P1,2024-01-01,99213,100\n"
                f"2,{GOOD_A},P1,2024-01-01,99213,100\n"    # dup of row 1
                f"3,{GOOD_A},P2,2024-01-02,99214,100\n"
                f"4,{GOOD_A},P2,2024-01-02,99214,150\n"    # amount conflict
                ).encode()
        return engine.clean_bytes(data, "dups.csv")

    def test_suspected_duplicate_rows_captured(self):
        res = self._res()
        self.assertGreaterEqual(res.sanity.get("suspected-duplicate-claim",
                                               0), 1)
        wl = res.flag_rows.get("suspected-duplicate-claim")
        # BOTH members of the colliding pair are in the worklist.
        self.assertIn(1, wl)
        self.assertIn(2, wl)

    def test_conflicting_amount_rows_captured(self):
        res = self._res()
        self.assertEqual(res.sanity.get("conflicting-amount-claim"), 1)
        self.assertEqual(res.flag_rows.get("conflicting-amount-claim"),
                         [3, 4])

    def test_charge_outlier_rows_captured(self):
        rows = [f"{i},99213,{100 + i % 2}" for i in range(11)]
        data = ("ClaimID,HCPCS,BilledAmt\n" + "\n".join(rows)
                + "\n99,99213,9000\n").encode()
        res = engine.clean_bytes(data, "out.csv")
        self.assertEqual(res.sanity.get("charge-outlier"), 1)
        self.assertEqual(res.flag_rows.get("charge-outlier"), [12])
        # The outlier detail panel still renders the same numbers.
        self.assertEqual(res.outliers[0]["outliers"], 1)
        # Scorecard worklists advertise the rows for all three rules.
        wl = res.as_scorecard()["worklists"]
        self.assertEqual(wl.get("charge-outlier"), 1)


class TestStreamingImprovements(unittest.TestCase):
    """P1: cross-chunk near-duplicates + merged payer/denial/specialty
    panels + an honest banner."""

    def _fixture(self):
        hdr = ("ClaimID,PayerName,HCPCS,DenialCode,ChargeAmt,"
               "ProviderTaxonomy")
        rows = [hdr]
        rows.append("NDP,UHC SPECIAL,99213,16,100,207Q00000X")
        for i in range(1, 380):
            rows.append(f"{i},UHC,99213,16,100,207Q00000X")
        rows.append("B1,UHC,BAD!!,16,100,207Q00000X")     # flagged row
        rows.append("ndp,uhc special,99213,16,100,207q00000x")  # case twin
        return ("\n".join(rows) + "\n").encode()

    def test_cross_chunk_near_duplicate_and_merged_panels(self):
        data = self._fixture()
        ref = engine.clean_bytes(data, "s.csv")
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "s.csv")
            with open(p, "wb") as fh:
                fh.write(data)
            with patch.object(bigfile, "STREAM_THRESHOLD_BYTES", 512), \
                    patch.object(bigfile, "CHUNK_TARGET_BYTES", 2048):
                res = bigfile.clean_path(p, "s.csv")
        # The folded twin straddles many chunk boundaries — still found,
        # matching the whole-file in-memory result.
        self.assertEqual(ref.sanity.get("near-duplicate-row"), 1)
        self.assertEqual(res.sanity.get("near-duplicate-row"), 1)
        # Merged payer-quality panel (previously empty on streamed runs).
        self.assertTrue(res.payer_quality)
        uhc = next(e for e in res.payer_quality
                   if e["payer"] == "UNITEDHEALTHCARE")
        self.assertEqual(uhc["rows"], res.n_rows_out)
        self.assertGreaterEqual(uhc["flagged"], 1)
        self.assertIn("clean_pct", uhc)
        # Merged denials panel with the CARC playbook fields intact.
        self.assertTrue(res.denials)
        self.assertEqual(res.denials["top"][0]["code"], "16")
        self.assertEqual(res.denials["column"], "DenialCode")
        # Merged specialty mix.
        self.assertTrue(res.specialties)
        self.assertEqual(res.specialties[0]["code"], "207Q00000X")

    def test_banner_is_honest_about_chunk_scans(self):
        data = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "s.csv")
            with open(p, "wb") as fh:
                fh.write(data)
            with patch.object(bigfile, "STREAM_THRESHOLD_BYTES", 512), \
                    patch.object(bigfile, "CHUNK_TARGET_BYTES", 2048):
                res = bigfile.clean_path(p, "s.csv")
        banner = next(w for w in res.warnings if w.startswith("Streaming"))
        self.assertIn("near-duplicates", banner)
        self.assertIn("reset at each chunk boundary", banner)
        # The old blanket claim is gone.
        self.assertNotIn("findings and worklists cover every row", banner)


class TestNpiValueSniff(unittest.TestCase):
    """P1: NPI columns under non-'npi' headers were invisible."""

    def _data(self, header="PROV_ID"):
        rows = [f"ClaimID,{header},ChargeAmt"]
        for i in range(1, 8):
            rows.append(f"{i},{GOOD_A if i % 2 else GOOD_B},100")
        return ("\n".join(rows) + "\n").encode()

    def test_sniffed_column_adopted(self):
        res = engine.clean_bytes(self._data(), "sniff.csv")
        self.assertEqual(res.npi_columns, ["PROV_ID"])
        self.assertEqual(res.billing_column, "PROV_ID")
        self.assertEqual(res.structure.get("npi_sniffed_columns"),
                         ["PROV_ID"])
        st = res.column_stats["PROV_ID"]
        self.assertEqual(st["valid"], 7)
        self.assertTrue(any("NPI-shaped values" in w for w in res.warnings))
        # No "no NPI column" warning — the sniff found one.
        self.assertFalse(any("No NPI column detected" in w
                             for w in res.warnings))

    def test_explicit_billing_header_never_displaced(self):
        rows = ["BillingNPI,REND_PROV_ID"]
        for i in range(6):
            rows.append(f"{GOOD_A},{GOOD_B}")
        res = engine.clean_bytes(("\n".join(rows) + "\n").encode(), "b.csv")
        self.assertEqual(res.billing_column, "BillingNPI")
        self.assertIn("REND_PROV_ID", res.npi_columns)

    def test_non_npi_values_never_adopted(self):
        rows = ["ClaimID,AccountRef,ChargeAmt"]
        for i in range(1, 8):
            rows.append(f"{i},{1000000000 + i},100")   # 10-digit, Luhn-bad
        res = engine.clean_bytes(("\n".join(rows) + "\n").encode(), "n.csv")
        self.assertEqual(res.npi_columns, [])
        self.assertTrue(any("No NPI column detected" in w
                            for w in res.warnings))

    def test_claimed_columns_never_sniffed(self):
        # A MemberID column of 10-digit values belongs to the member role.
        rows = ["MemberID,Note"]
        for i in range(6):
            rows.append(f"{GOOD_A},x")
        res = engine.clean_bytes(("\n".join(rows) + "\n").encode(), "m.csv")
        self.assertEqual(res.npi_columns, [])

    def test_autofiles_field_gap(self):
        title = "NPI column detected by value under a non-NPI header"
        _wipe_auto(title)
        engine.clean_bytes(self._data(), "sniff2.csv")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)


_X12_837P_PROVIDERS = (
    "ISA*00*          *00*          *ZZ*SUBMITTER      *ZZ*RECEIVER       "
    "*240110*1200*^*00501*000000001*0*P*:~"
    "GS*HC*SUB*REC*20240110*1200*1*X*005010X222A1~"
    "ST*837*0001*005010X222A1~"
    "BHT*0019*00*1*20240110*1200*CH~"
    "NM1*85*2*ACME FAMILY CLINIC*****XX*1497758544~"
    "NM1*IL*1*DOE*JANE****MI*MBR123~"
    "NM1*PR*2*UNITEDHEALTHCARE*****PI*87726~"
    "CLM*ACCT001*225***11:B:1*Y*A*Y*Y~"
    "HI*ABK:E1165~"
    "NM1*82*1*SMITH*JOHN****XX*1234567893~"        # 2310B claim rendering
    "NM1*DN*1*REFERRER*BOB****XX*1679576722~"      # 2310A referring
    "LX*1~"
    "SV1*HC:99213:25*100*UN*1*11~"
    "DTP*472*D8*20240110~"
    "NM1*82*1*LINEDOC*AMY****XX*1497758544~"       # 2420A line 1 ONLY
    "LX*2~"
    "SV1*HC:93000*125*UN*1~"
    "DTP*472*D8*20240110~"
    "NM1*DK*1*ORDERER*ANN****XX*1245319599~"       # 2420E ordering, line 2
    "SE*20*0001~GE*1*1~IEA*1*000000001~").encode()

_X12_837I_OPERATING = (
    "ISA*00*          *00*          *ZZ*S              *ZZ*R              "
    "*240110*1200*^*00501*000000002*0*P*:~"
    "GS*HC*S*R*20240110*1200*2*X*005010X223A2~"
    "ST*837*0002*005010X223A2~"
    "NM1*85*2*MERCY HOSPITAL*****XX*1497758544~"
    "CLM*STAY01*5000***13:A:1*Y*A*Y*Y~"
    "NM1*71*1*ATTEND*AL****XX*1234567893~"
    "NM1*72*1*OPER*OTTO****XX*1679576722~"
    "LX*1~"
    "SV2*0450*HC:99284*5000*UN*1~"
    "DTP*472*RD8*20240101-20240103~"
    "SE*10*0002~GE*1*2~IEA*1*000000002~").encode()


class TestX12Providers(unittest.TestCase):
    """P1: referring/ordering/operating NPIs never extracted from native
    837s; line-level 2420A rendering leaked onto later lines."""

    def test_837p_referring_ordering_and_2420a_scope(self):
        h, rows = x12.x12_to_table(_X12_837P_PROVIDERS)
        self.assertIn("ReferringNPI", h)
        self.assertIn("OrderingNPI", h)
        self.assertIn("OperatingNPI", h)
        r0 = dict(zip(h, rows[0]))
        r1 = dict(zip(h, rows[1]))
        # Claim-level referring reaches every line of the claim.
        self.assertEqual(r0["ReferringNPI"], GOOD_B)
        self.assertEqual(r1["ReferringNPI"], GOOD_B)
        # Line 1's 2420A rendering applies to line 1 ONLY; line 2 falls
        # back to the claim-level 2310B — the leak the survey verified.
        self.assertEqual(r0["RenderingNPI"], "1497758544")
        self.assertEqual(r1["RenderingNPI"], GOOD_A)
        # Line-level ordering lands on its own line only.
        self.assertEqual(r0["OrderingNPI"], "")
        self.assertEqual(r1["OrderingNPI"], "1245319599")

    def test_837i_operating(self):
        h, rows = x12.x12_to_table(_X12_837I_OPERATING)
        i0 = dict(zip(h, rows[0]))
        self.assertEqual(i0["OperatingNPI"], GOOD_B)
        self.assertEqual(i0["AttendingNPI"], GOOD_A)
        self.assertEqual(i0["TypeOfBill"], "131")

    def test_ordering_referring_screen_reachable_from_native_837(self):
        # The whole point: the ordering/referring screen can now fire on
        # native EDI, not just CSVs.
        res = engine.clean_bytes(_X12_837P_PROVIDERS, "claims.837")
        self.assertIn("ReferringNPI", res.order_referring_columns)
        self.assertIn("OrderingNPI", res.order_referring_columns)
        self.assertIn("ReferringNPI", res.npi_columns)
        st = res.column_stats["ReferringNPI"]
        self.assertEqual(st["valid"], 2)


class TestPreambleAndHeaderless(unittest.TestCase):
    """P2: title rows became one-column headers; headerless files promoted
    NPIs to header text."""

    _BODY = (f"ClaimID,BillingNPI,ChargeAmt,DateOfService,HCPCS\n"
             f"1,{GOOD_B},100,2024-01-01,99213\n"
             f"2,{GOOD_A},50,2024-01-02,99214\n"
             f"3,{GOOD_B},75,2024-01-03,99215\n")

    def test_title_row_skipped(self):
        data = ("Claims Extract Q3 2025\n" + self._BODY).encode()
        res = engine.clean_bytes(data, "t.csv")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertEqual(res.n_rows_in, 3)
        self.assertTrue(any("title row" in w for w in res.warnings))

    def test_two_title_rows_skipped(self):
        data = ("ACME HEALTH\nConfidential,internal\n" + self._BODY).encode()
        res = engine.clean_bytes(data, "t2.csv")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertTrue(any("2 title row(s)" in w for w in res.warnings))

    def test_headerless_synthesizes_and_keeps_row_one(self):
        data = (f"1,{GOOD_B},100\n2,{GOOD_A},50\n3,{GOOD_B},75\n").encode()
        res = engine.clean_bytes(data, "nohdr.csv")
        self.assertEqual(res.headers, ["column_1", "column_2", "column_3"])
        self.assertEqual(res.n_rows_in, 3)      # row 1 kept as data
        self.assertTrue(any("no header row" in w for w in res.warnings))
        # And the value sniff rescues the NPI column despite the synthetic
        # headers — the two heuristics compose.
        self.assertEqual(res.npi_columns, ["column_2"])
        self.assertEqual(res.column_stats["column_2"]["valid"], 3)

    def test_ordinary_headers_untouched(self):
        res = engine.clean_bytes(self._BODY.encode(), "ok.csv")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertFalse(any("title row" in w or "no header row" in w
                             for w in res.warnings))

    def test_xlsx_cover_row_skipped(self):
        openpyxl = __import__("openpyxl")
        from io import BytesIO
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Claims Extract Q3 2025"])
        ws.append(["ClaimID", "BillingNPI", "ChargeAmt", "DOS", "HCPCS"])
        for i in range(1, 5):
            ws.append([i, GOOD_A, 100, "2024-01-01", "99213"])
        buf = BytesIO()
        wb.save(buf)
        res = engine.clean_bytes(buf.getvalue(), "cover.xlsx")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertTrue(any("title row" in w for w in res.warnings))

    def test_headerless_autofiles_format_gap(self):
        title = "Headerless file cleaned with synthesized column names"
        _wipe_auto(title)
        engine.clean_bytes(
            (f"1,{GOOD_B},100\n2,{GOOD_A},50\n3,{GOOD_B},75\n").encode(),
            "nohdr2.csv")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)


class TestZipBatchHonesty(unittest.TestCase):
    """P2: silent 50-member cap and silently ignored non-claim members."""

    def _zip(self, entries):
        import io as _io
        import zipfile as _zf
        buf = _io.BytesIO()
        with _zf.ZipFile(buf, "w") as z:
            for name, text in entries:
                z.writestr(name, text)
        return buf.getvalue()

    def test_skipped_members_named_and_cap_stated(self):
        data = self._zip([
            ("a.csv", f"NPI\n{GOOD_A}\n"),
            ("b.csv", f"NPI\n{GOOD_B}\n"),
            ("c.csv", f"NPI\n{GOOD_A}\n"),
            ("report.xlsx", "not-actually-xlsx"),
            ("notes.dat", "binary stuff")])
        with patch.object(engine, "_BATCH_MEMBER_CAP", 2):
            res = engine.clean_bytes(data, "sites.zip")
        blob = " ".join(res.warnings)
        self.assertIn("report.xlsx", blob)
        self.assertIn("notes.dat", blob)
        self.assertIn("2-file batch cap", blob)
        self.assertEqual(res.structure.get("batch_skipped"),
                         {"unsupported": 2, "over_cap": 1})
        # Only the first 2 members (alphabetical) were cleaned.
        self.assertEqual(len(res.batch), 2)

    def test_full_batch_has_no_skip_warning(self):
        data = self._zip([("a.csv", f"NPI\n{GOOD_A}\n"),
                          ("b.csv", f"NPI\n{GOOD_B}\n")])
        res = engine.clean_bytes(data, "ok.zip")
        self.assertFalse(any("not cleaned" in w for w in res.warnings))
        self.assertNotIn("batch_skipped", res.structure)

    def test_back_compat_wrapper(self):
        data = self._zip([("a.csv", "NPI\n1\n"), ("x.md", "skip")])
        members = engine.zip_batch_members(data)
        self.assertEqual([m[0] for m in members], ["a.csv"])
        members2, info = engine.zip_batch_members_ex(data)
        self.assertEqual([m[0] for m in members2], ["a.csv"])
        self.assertEqual(info["skipped_unsupported"], ["x.md"])
        self.assertEqual(info["over_cap"], 0)

    def test_skips_autofile_format_gap(self):
        title = "Zip batch members were skipped"
        _wipe_auto(title)
        data = self._zip([("a.csv", f"NPI\n{GOOD_A}\n"),
                          ("weird.dat", "x")])
        engine.clean_bytes(data, "mix.zip")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)


class TestScrubberChecks(unittest.TestCase):
    """P2: the 6th/7th checks — NPI↔name conflict, DRG-on-professional —
    plus NPI first-digit plausibility."""

    def test_npi_name_conflict(self):
        data = (f"BillingNPI,OrganizationName\n"
                f"{GOOD_A},Mercy General\n"
                f"{GOOD_A},MERCY  GENERAL\n"       # case/space variant: OK
                f"{GOOD_A},Mercy General.\n"        # punctuation variant: OK
                f"{GOOD_A},Lakeside Imaging\n"      # real conflict
                f"{GOOD_B},Riverbend Clinic\n").encode()
        res = engine.clean_bytes(data, "nc.csv")
        self.assertEqual(res.sanity.get("npi-name-conflict"), 1)
        self.assertEqual(res.flag_rows.get("npi-name-conflict"), [4])

    def test_npi_name_conflict_needs_both_columns(self):
        res = engine.clean_bytes(
            f"BillingNPI\n{GOOD_A}\n{GOOD_A}\n".encode(), "n1.csv")
        self.assertNotIn("npi-name-conflict", res.sanity)

    def test_drg_on_professional(self):
        data = ("DRG,POS,HCPCS\n470,11,99213\n,11,99213\n").encode()
        res = engine.clean_bytes(data, "drg.csv")
        self.assertEqual(res.sanity.get("drg-on-professional"), 1)
        self.assertEqual(res.flag_rows.get("drg-on-professional"), [1])

    def test_drg_with_tob_is_institutional_and_fine(self):
        data = ("DRG,POS,TypeOfBill\n470,11,111\n").encode()
        res = engine.clean_bytes(data, "drg2.csv")
        self.assertNotIn("drg-on-professional", res.sanity)

    def test_classify_npi_prefix_plausibility(self):
        # Luhn-valid but starting with 9 — CMS never issued it.
        self.assertTrue(engine.luhn_npi_valid(LUHN_OK_BAD_PREFIX))
        self.assertEqual(engine.classify_npi(LUHN_OK_BAD_PREFIX),
                         "malformed")
        self.assertEqual(engine.classify_npi(GOOD_A), "valid")
        # 2-prefix NPIs are plausible: valid stays valid, Luhn-fail stays
        # checksum (not demoted to malformed).
        self.assertEqual(engine.classify_npi("2234567891"), "valid")
        self.assertEqual(engine.classify_npi("2234567892"), "checksum")
        self.assertEqual(engine.classify_npi("1234567890"), "checksum")

    def test_rules_registered(self):
        for rid in ("npi-name-conflict", "drg-on-professional"):
            self.assertEqual(rules.describe(rid)["kind"], "flag")
            self.assertIn(rid, engine.CleanResult._CONSISTENCY_RULES)


class TestModifierContent(unittest.TestCase):
    """P2: malformed modifier tokens were silently deleted."""

    def test_no_characters_lost(self):
        v, r = engine._clean_modifier_cell("25;LT4;GY")
        self.assertEqual(v, "25,GY,LT4")
        self.assertEqual(r, ["modifier-normalize"])
        self.assertTrue(engine._modifier_malformed(v))

    def test_valid_only_cell_unchanged_semantics(self):
        self.assertEqual(engine._clean_modifier_cell("26|tc, 59"),
                         ("26,TC,59", ["modifier-normalize"]))
        self.assertFalse(engine._modifier_malformed("26,TC,59"))

    def test_full_run_flags_and_keeps(self):
        data = ("ClaimID,Modifiers\n1,25;LT4;GY\n2,25\n").encode()
        res = engine.clean_bytes(data, "mod.csv")
        self.assertEqual(res.sanity.get("modifier-malformed"), 1)
        self.assertEqual(res.flag_rows.get("modifier-malformed"), [1])
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("LT4", out)              # content preserved
        self.assertIn("modifier-malformed",
                      engine.CleanResult._VALIDITY_RULES)


class TestIsaCsvProbe(unittest.TestCase):
    """P3: a CSV whose first header cell is 'ISA' was misrouted to X12."""

    def test_isa_headed_csv_cleans_as_csv(self):
        data = (f"ISA,BillingNPI\n1,{GOOD_A}\n2,{GOOD_B}\n").encode()
        self.assertFalse(x12.looks_like_x12(data))
        res = engine.clean_bytes(data, "isa.csv")
        self.assertEqual(res.npi_columns, ["BillingNPI"])
        self.assertEqual(res.n_rows_in, 2)
        self.assertFalse(any("X12" in w for w in res.warnings))

    def test_real_x12_still_detected(self):
        self.assertTrue(x12.looks_like_x12(_X12_837P_PROVIDERS))
        self.assertTrue(x12.looks_like_x12(_X12_837I_OPERATING))
        # And the alnum-separator rejection is unchanged.
        self.assertFalse(x12.looks_like_x12(b"ISAN,Other\n1,2\n"))


class TestMojibakeNames(unittest.TestCase):
    """P3: accented provider names stayed corrupted."""

    def test_common_accents_repaired(self):
        v, r = engine._clean_generic("JosÃ© PeÃ±a MD")
        self.assertEqual(v, "José Peña MD")
        self.assertIn("mojibake", r)
        v2, _ = engine._clean_generic("FranÃ§ois MÃ¼ller")
        self.assertEqual(v2, "François Müller")

    def test_full_run_output_contains_repaired_name(self):
        data = ("ProviderName,BillingNPI\n"
                "JosÃ© PeÃ±a MD," + GOOD_A + "\n").encode()
        res = engine.clean_bytes(data, "moj.csv")
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("José Peña MD", out)
        self.assertGreaterEqual(res.repairs.get("mojibake", 0), 1)


class TestRegistryEngineConsistency(unittest.TestCase):
    """P2: leie-excluded-npi said dimension=validity but affected nothing;
    now every registry flag dimension maps into the grade math."""

    def test_leie_counts_toward_validity(self):
        self.assertIn("leie-excluded-npi",
                      engine.CleanResult._VALIDITY_RULES)

    def test_every_flag_dimension_reaches_the_grade(self):
        uniq = {"suspected-duplicate-claim", "possible-duplicate-service",
                "near-duplicate-row"}
        for r in rules.all_rules():
            if r.kind != "flag" or not r.dimension:
                continue
            if r.dimension == "validity":
                self.assertIn(r.id, engine.CleanResult._VALIDITY_RULES,
                              f"{r.id} says validity but is not graded")
            elif r.dimension == "consistency":
                self.assertIn(r.id, engine.CleanResult._CONSISTENCY_RULES,
                              f"{r.id} says consistency but is not graded")
            elif r.dimension == "uniqueness":
                self.assertIn(r.id, uniq,
                              f"{r.id} says uniqueness but is not graded")

    def test_new_rules_registered_with_dimensions(self):
        expected = {
            "ragged-row": ("flag", "validity"),
            "date-unparseable": ("flag", "validity"),
            "npi-scientific-lossy": ("flag", "validity"),
            "modifier-malformed": ("flag", "validity"),
            "npi-name-conflict": ("flag", "consistency"),
            "drg-on-professional": ("flag", "consistency"),
            "money-eu-decimal": ("repair", "conformity"),
            "money-trailing-negative": ("repair", "conformity"),
            "date-compact-to-iso": ("repair", "conformity"),
            "npi-scientific-notation": ("repair", "validity"),
        }
        by_id = {r.id: r for r in rules.all_rules()}
        for rid, (kind, dim) in expected.items():
            self.assertIn(rid, by_id, rid)
            self.assertEqual(by_id[rid].kind, kind, rid)
            self.assertEqual(by_id[rid].dimension, dim, rid)
            self.assertTrue(by_id[rid].remediation, rid)

    def test_leie_flag_lowers_validity_dimension(self):
        # Synthesizing the counter directly (the pack path is exercised in
        # the main suite): a critical exclusion must now move the grade.
        res = engine.CleanResult(n_rows_in=10, n_rows_out=10,
                                 n_cells_total=10, n_cells_filled=10)
        base = res.quality()["dimensions"]["validity"]
        res.sanity["leie-excluded-npi"] = 5
        hit = res.quality()["dimensions"]["validity"]
        self.assertLess(hit, base)


class TestAutofileExtension(unittest.TestCase):
    """P2: the improvement loop was starved — only two gap classes filed."""

    def test_ragged_heavy_file_autofiles(self):
        title = "High ragged-row rate on an upload"
        _wipe_auto(title)
        rows = ["A,B,C"]
        for i in range(120):
            rows.append(f"{i},x,y" + (",z,extra" if i % 10 == 0 else ""))
        engine.clean_bytes(("\n".join(rows) + "\n").encode(), "rag.csv")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)

    def test_date_unparseable_heavy_file_autofiles(self):
        title = ("High date-unparseable rate — an unrecognized date format")
        _wipe_auto(title)
        rows = ["ClaimID,DateOfService"]
        for i in range(210):
            rows.append(f"{i},{i}-JAN-2024")     # DD-MON-YYYY: unsupported
        engine.clean_bytes(("\n".join(rows) + "\n").encode(), "dt.csv")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)

    def test_low_rates_do_not_autofile(self):
        for title in ("High ragged-row rate on an upload",
                      "High date-unparseable rate — an unrecognized "
                      "date format"):
            _wipe_auto(title)
        rows = ["ClaimID,DateOfService"]
        for i in range(210):
            rows.append(f"{i},2024-01-01")
        rows[7] = rows[7] + ",extra"             # one ragged row: below 5%
        engine.clean_bytes(("\n".join(rows) + "\n").encode(), "ok.csv")
        autos = _auto_titles()
        self.assertNotIn("High ragged-row rate on an upload", autos)
        self.assertNotIn("High date-unparseable rate — an unrecognized "
                         "date format", autos)

    def test_x12_without_claims_autofiles(self):
        title = "X12 upload carried no 837/835 claims"
        _wipe_auto(title)
        ack = (_X12_837P_PROVIDERS[:106]
               + b"GS*FA*S*R*20240110*1200*3*X*005010X231A1~"
                 b"ST*999*0001~AK1*HC*1~SE*3*0001~")
        engine.clean_bytes(ack, "ack.999")
        self.assertIn(title, _auto_titles())
        _wipe_auto(title)


if __name__ == "__main__":
    unittest.main()
