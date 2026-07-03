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

    def test_formula_injection_defanged(self):
        # A cell that would start an Excel formula must be neutralized in CSV.
        data = ("NPI,Note\n" + GOOD_A + ",=SUM(A1:A9)\n").encode()
        res = engine.clean_bytes(data, "x.csv")
        with open(res.out_path, encoding="utf-8") as fh:
            out = fh.read()
        self.assertIn("'=SUM(A1:A9)", out)

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
    """The real vendored v48 screens, driven through vendor_adapter."""

    def setUp(self):
        from rcm_mc.npi_cleaner import vendor_adapter as va
        if not va.available():
            self.skipTest("pandas / vendored modules unavailable")
        self.va = va

    def test_header_mapping(self):
        m = self.va.build_mapping(
            ["ClaimID", "BillingProviderNPI", "ReferringNPI", "ChargeAmt",
             "AllowedAmt", "PaidAmt", "DateOfService", "PaidDate", "HCPCS"])
        self.assertEqual(m["billing_npi"], "BillingProviderNPI")
        self.assertEqual(m["referring_npi"], "ReferringNPI")
        self.assertEqual(m["billed_amt"], "ChargeAmt")
        self.assertEqual(m["allowed_amt"], "AllowedAmt")
        self.assertEqual(m["date"], "DateOfService")
        self.assertEqual(m["hcpcs"], "HCPCS")

    def test_real_screens_catch_violations(self):
        data = (
            "ClaimID,BillingProviderNPI,ReferringNPI,ChargeAmt,AllowedAmt,"
            "PaidAmt,DateOfService,PaidDate,HCPCS\n"
            f"1,{GOOD_A},{GOOD_B},100,80,60,2024-01-15,2024-02-01,99213\n"
            # paid>allowed (money), referring==billing (role), future date
            f"2,{GOOD_A},{GOOD_A},50,90,40,2099-03-10,2024-03-01,ABCDE\n"
            f"3,99999,{GOOD_B},200,150,120,2024-05-01,2024-06-01,99214\n"
        ).encode()
        res = self.va.run(data)
        self.assertIsNotNone(res)
        self.assertIn("field_validators", res["engine"])

        # money ordering flags row 2 (paid 40 > allowed 90? no; allowed 90 >
        # billed 50 yes) and row-2 paid>allowed etc. — at least one violation.
        money = [c for c in res["consistency"] if c["screen"] == "money_ordering"][0]
        self.assertGreaterEqual(money["flagged"], 1)
        role = [c for c in res["consistency"]
                if c["screen"] == "npi_role_coherence"][0]
        self.assertEqual(role["flagged"], 1)  # row 2 referring == billing

        rule_ids = {r["rule_id"] for r in res["field_rules"]}
        self.assertIn("NPI-LEN", rule_ids)       # 99999 billing NPI
        self.assertIn("DATE-FUTURE", rule_ids)   # 2099 service date
        self.assertIn("HCPCS-FMT", rule_ids)     # ABCDE

    def test_engine_attaches_advanced(self):
        data = (
            "BillingNPI,AllowedAmt,PaidAmt\n"
            f"{GOOD_A},80,200\n"   # paid > allowed
        ).encode()
        res = engine.clean_bytes(data, "c.csv")
        self.assertIsNotNone(res.advanced)
        self.assertIn("field_validators", res.advanced["engine"])


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
