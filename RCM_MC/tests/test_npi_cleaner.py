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
