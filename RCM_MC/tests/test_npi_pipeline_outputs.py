"""Pipeline/report-layer output tests for the NPI Claims Cleaner.

Covers the improvements shipped on the pipeline-report front:

  * exec one-pager carries compliance, dollar exposure, NPPES, trend
    alerts, de-id, charge outliers, honest prevalence captions, and the
    national E&M context;
  * workbook gains Denials / Compliance / Charge outliers / Dictionary
    sheets, honest Summary labels + trend rows, and dollar-ranked
    worklist tabs with why-flagged / what-to-do banners;
  * reconcile reports the headline unmatched dollars, normalizes the
    claim-id join and CARC group-code prefixes, and explains near-zero
    match rates;
  * compliance NPI dedupe is linear-time and LEIE matches are enriched
    with name / exclusion type / date / billed exposure;
  * history supports population deltas, streaks, recovery alerts, and a
    persistent store root (RCM_MC_NPI_WORKDIR);
  * wishlist mutations are guarded, source-filterable, persistent-root
    aware, and support the improvement loop's "shipped" transition;
  * deep mode fails a no-egress run in seconds via a preflight probe.

New file only — the 239-test contract in test_npi_cleaner.py is untouched.
"""
from __future__ import annotations

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from rcm_mc.npi_cleaner import engine

# NPIs that pass the real CMS/NPPES Luhn check (80840 + first 9).
GOOD_A = "1234567893"
GOOD_B = "1679576722"


def _load_workbook(data: bytes):
    openpyxl = __import__("openpyxl")
    return openpyxl.load_workbook(io.BytesIO(data))


def _cleaned_table(res):
    import csv
    with open(res.out_path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def _base_scorecard():
    res = engine.clean_bytes(
        f"ClaimID,BillingNPI\n1,{GOOD_A}\n".encode(), "base.csv")
    return res.as_scorecard()


# ---------------------------------------------------------------- compliance --
class TestComplianceScreens(unittest.TestCase):
    def test_distinct_npis_linear_and_same_semantics(self):
        from rcm_mc.npi_cleaner import compliance as C
        # Small case: order preserved, non-NPIs dropped, cap + truncation.
        vals = [GOOD_A, "  " + GOOD_A + " ", GOOD_B, "123", GOOD_A,
                "1093718892"]
        out, trunc = C._distinct_npis(vals, 10)
        self.assertEqual(out, [GOOD_A, GOOD_B, "1093718892"])
        self.assertFalse(trunc)
        out2, trunc2 = C._distinct_npis(vals, 2)
        self.assertEqual(out2, [GOOD_A, GOOD_B])
        self.assertTrue(trunc2)
        # Scale case: 200k values / 100k distinct completes in seconds —
        # the old list-membership scan was quadratic and effectively hung.
        big = [f"1{i:09d}" for i in range(100_000)] * 2
        t0 = time.monotonic()
        out3, _ = C._distinct_npis(big, 10_000)
        elapsed = time.monotonic() - t0
        self.assertEqual(len(out3), 10_000)
        self.assertLess(elapsed, 5.0)

    def _leie_csv(self, tmp):
        p = os.path.join(tmp, "UPDATED.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(
                "LASTNAME,FIRSTNAME,BUSNAME,NPI,EXCLTYPE,EXCLDATE\n"
                f"DOE,JANE,,{GOOD_A},1128a1,20220315\n"
                f",,ACME HOME HEALTH LLC,{GOOD_B},1128b7,20230601\n")
        return p

    def test_leie_matches_enriched_and_dollar_sized(self):
        from rcm_mc.npi_cleaner import compliance as C
        with tempfile.TemporaryDirectory() as tmp:
            path = self._leie_csv(tmp)
            out = C.screen_leie(
                [GOOD_A, GOOD_B, "1093718892"], leie_path=path,
                dollars_by_npi={GOOD_A: 1500.559, "1093718892": 50.0})
        self.assertTrue(out["available"])
        self.assertEqual(out["excluded"], 2)
        by_npi = {m["npi"]: m for m in out["matches"]}
        self.assertEqual(by_npi[GOOD_A]["name"], "JANE DOE")
        self.assertEqual(by_npi[GOOD_A]["excl_type"], "1128a1")
        self.assertEqual(by_npi[GOOD_A]["excl_date"], "20220315")
        self.assertEqual(by_npi[GOOD_A]["billed"], 1500.56)  # 2dp
        self.assertEqual(by_npi[GOOD_B]["name"], "ACME HOME HEALTH LLC")
        self.assertNotIn("billed", by_npi[GOOD_B])  # no dollars known
        self.assertEqual(out["excluded_billed_total"], 1500.56)
        self.assertIn("$1,500.56", out["note"])

    def test_leie_unreadable_csv_degrades_honestly(self):
        from rcm_mc.npi_cleaner import compliance as C
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "bad.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("A,B\n1,2\n")   # no NPI column
            out = C.screen_leie([GOOD_A], leie_path=p)
        self.assertFalse(out["available"])
        self.assertIn("could not be read", out["note"])

    def test_screen_passes_dollars_through(self):
        from rcm_mc.npi_cleaner import compliance as C
        with tempfile.TemporaryDirectory() as tmp:
            path = self._leie_csv(tmp)
            results = C.screen([GOOD_A], leie_path=path, run_cms=False,
                               dollars_by_npi={GOOD_A: 10.0})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["excluded_billed_total"], 10.0)


# ----------------------------------------------------------------- reconcile --
class TestReconcileOutputs(unittest.TestCase):
    def test_headline_unmatched_dollar_totals(self):
        from rcm_mc.npi_cleaner.reconcile import reconcile
        ha = ["ClaimID", "BilledAmt"]
        # 30 unpaid claims (top-25 cap truncates) + 1 matched claim.
        ra = [[f"U{i:02d}", "10"] for i in range(30)] + [["M1", "100"]]
        hb = ["ClaimID", "PaidAmt"]
        rb = [["M1", "40"], ["O1", "5"], ["O2", "7"]]
        rep = reconcile(ha, ra, hb, rb)
        self.assertEqual(rep["unpaid_count"], 30)
        self.assertEqual(len(rep["unpaid"]), 25)          # capped list
        self.assertEqual(rep["unpaid_billed_total"], 300.0)  # ALL unmatched
        self.assertEqual(rep["unpaid_lines_total"], 30)
        self.assertEqual(rep["orphan_paid_total"], 12.0)
        # Dollar-weighted match rate: 100 matched of 400 billed → 25.0%.
        self.assertEqual(rep["matched_pct_of_billed"], 25.0)

    def test_claim_id_normalization_joins_padded_and_cased_ids(self):
        from rcm_mc.npi_cleaner.reconcile import reconcile
        ha = ["ClaimID", "BilledAmt"]
        ra = [["0001234", "50"], ["abc9", "60"]]
        hb = ["ClaimID", "PaidAmt"]
        rb = [["1234", "10"], ["ABC9", "20"]]
        rep = reconcile(ha, ra, hb, rb)
        self.assertEqual(rep["matched"], 2)
        self.assertEqual(rep["unpaid_count"], 0)
        self.assertEqual(rep["orphan_remits_count"], 0)
        # The join was fuzzy-on-padding/case — the report must say so.
        self.assertIn("note", rep)
        self.assertIn("normalization", rep["note"])
        # Display values keep the side-A spelling.
        claims = {e["claim"] for e in rep["top_variance"]}
        self.assertIn("0001234", claims)

    def test_carc_group_prefix_normalized_in_denial_mix(self):
        from rcm_mc.npi_cleaner.reconcile import reconcile
        ha = ["ClaimID", "BilledAmt"]
        ra = [["C1", "100"], ["C2", "100"]]
        hb = ["ClaimID", "PaidAmt", "DenialCodes"]
        rb = [["C1", "0", "CO-45"], ["C2", "0", "PR1;CO45"]]
        rep = reconcile(ha, ra, hb, rb)
        den = {d["code"]: d for d in rep["denials"]}
        self.assertIn("45", den)                    # CO-45 + CO45 → 45
        self.assertEqual(den["45"]["claims"], 2)
        self.assertEqual(den["45"]["category"], "contractual")
        self.assertIn("1", den)                     # PR1 → 1 (deductible)
        self.assertEqual(den["1"]["category"], "patient-responsibility")
        # A genuine letter code must NOT be stripped.
        rb2 = [["C1", "0", "P1"]]
        rep2 = reconcile(ha, ra, hb, rb2)
        self.assertIn("P1", {d["code"] for d in rep2["denials"]})

    def test_low_match_diagnostic_shows_id_shapes(self):
        from rcm_mc.npi_cleaner.reconcile import reconcile
        ha = ["ClaimID", "BilledAmt"]
        ra = [[f"A{i}", "10"] for i in range(6)]
        hb = ["ClaimID", "PaidAmt"]
        rb = [[f"90000{i}", "5"] for i in range(6)]
        rep = reconcile(ha, ra, hb, rb)
        self.assertEqual(rep["matched"], 0)
        self.assertIn("id_shapes", rep)
        shapes_a = {s["shape"] for s in rep["id_shapes"]["a"]}
        shapes_b = {s["shape"] for s in rep["id_shapes"]["b"]}
        self.assertIn("alnum(2)", shapes_a)
        self.assertIn("digits(6)", shapes_b)
        # Healthy match → no diagnostic noise.
        rep2 = reconcile(ha, ra, ha, ra)
        self.assertNotIn("id_shapes", rep2)


# ------------------------------------------------------------------- history --
def _sc(score, dims, sanity=None, pop=None):
    """Minimal scorecard shape record_run consumes."""
    sc = {"rows_in": 10, "rows_out": 10, "duplicates_removed": 0,
          "quality": {"score": score, "letter": "B", "dimensions": dims},
          "repairs": {}, "sanity": sanity or {}, "changes_logged": 0}
    if pop is not None:
        sc["population"] = pop
    return sc


_POP_A = {"encounters": {"n_encounters": 5,
                         "readmissions": {"rate_pct": 10.0}},
          "volume": {"median_observed_pmpm": 100.0},
          "service_mix": {"categories": [{"category": "Office",
                                          "pct": 50.0}]},
          "coding_intensity": {"file_avg_level": 3.2}}
_POP_B = {"encounters": {"n_encounters": 8,
                         "readmissions": {"rate_pct": 9.0}},
          "volume": {"median_observed_pmpm": 125.5},
          "service_mix": {"categories": [{"category": "Office",
                                          "pct": 60.0}]},
          "coding_intensity": {"file_avg_level": 3.5}}


class TestHistoryDeltasAndStreaks(unittest.TestCase):
    def test_compare_runs_dimension_and_population_deltas(self):
        import rcm_mc.npi_cleaner.history as h
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(h, "_DB_PATH", Path(tmp) / "hist.sqlite3"):
                a = h.record_run(_sc(70, {"completeness": 90.0,
                                          "validity": 80.0},
                                     sanity={"r1": 5}, pop=_POP_A), "f.csv")
                b = h.record_run(_sc(80, {"completeness": 95.5,
                                          "validity": 78.0},
                                     sanity={"r1": 2}, pop=_POP_B), "f.csv")
                cmpd = h.compare_runs(a, b)
        self.assertEqual(cmpd["score_delta"], 10)
        self.assertEqual(cmpd["dimension_delta"]["completeness"], 5.5)
        self.assertEqual(cmpd["dimension_delta"]["validity"], -2.0)
        pd = cmpd["population_delta"]
        self.assertEqual(pd["median_observed_pmpm"], 25.5)
        self.assertEqual(pd["readmit_rate_pct"], -1.0)
        self.assertEqual(pd["n_encounters"], 3)
        self.assertNotIn("top_setting", pd)      # strings don't delta
        # get_run now carries the population payload.
        self.assertEqual(cmpd["b"]["population"]["n_encounters"], 8)

    def test_streaks_improving_then_decline(self):
        import rcm_mc.npi_cleaner.history as h
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(h, "_DB_PATH", Path(tmp) / "hist.sqlite3"):
                for s in (70, 80, 90):
                    h.record_run(_sc(s, {}), "feed.csv")
                    time.sleep(0.01)   # distinct ts ordering
                st = h.streaks("feed.csv")
                self.assertEqual(st["runs"], 3)
                self.assertEqual(st["improving_streak"], 2)
                self.assertEqual(st["declining_streak"], 0)
                self.assertEqual(st["best_score"], 90)
                self.assertEqual(st["worst_score"], 70)
                self.assertEqual(st["latest_delta"], 10)
                h.record_run(_sc(85, {}), "feed.csv")
                st2 = h.streaks("feed.csv")
                self.assertEqual(st2["improving_streak"], 0)
                self.assertEqual(st2["declining_streak"], 1)
                self.assertEqual(st2["latest_delta"], -5)
                # Unknown file → None, not a crash.
                self.assertIsNone(h.streaks("never-seen.csv"))

    def test_trend_alert_reports_recovery_not_just_regression(self):
        import rcm_mc.npi_cleaner.history as h
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(h, "_DB_PATH", Path(tmp) / "hist.sqlite3"):
                h.record_run(_sc(70, {}), "r.csv")
                alerts = h.trend_alerts(_sc(80, {}), "r.csv")
        self.assertTrue(any("recovered 70 → 80" in a for a in alerts))

    def test_env_workdir_persists_history_store(self):
        import rcm_mc.npi_cleaner.history as h
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"RCM_MC_NPI_WORKDIR": tmp}):
                rid = h.record_run(_sc(75, {"completeness": 99.0}),
                                   "envtest.csv")
                self.assertTrue(rid)
                self.assertTrue(
                    (Path(tmp) / "npi_cleaner_history.sqlite3").exists())
                names = [r["file_name"] for r in h.list_runs()]
                self.assertIn("envtest.csv", names)


# ------------------------------------------------------------------ wishlist --
class TestWishlistLoop(unittest.TestCase):
    def test_env_workdir_persists_wishlist_store(self):
        import rcm_mc.npi_cleaner.wishlist as w
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"RCM_MC_NPI_WORKDIR": tmp}):
                w.add_request("payer", "Support ACME Health family")
                self.assertTrue(
                    (Path(tmp) / "npi_cleaner_wishlist.sqlite3").exists())
                titles = [r["title"] for r in w.list_requests()]
                self.assertIn("Support ACME Health family", titles)

    def test_source_filter_and_shipped_transition(self):
        import rcm_mc.npi_cleaner.wishlist as w
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(w, "_DB_PATH", Path(tmp) / "wl.sqlite3"):
                w.add_request("field",
                              "Detector found no NPI column in an upload")
                w.auto_file("field",
                            "Detector found no NPI column in an upload",
                            "auto-filed")
                w.auto_file("format", "High ragged-row rate on an upload")
                autos = w.list_requests(source="auto")
                self.assertEqual(len(autos), 2)
                self.assertTrue(all(r["source"] == "auto" for r in autos))
                # Ship the auto-filed gap; the identically-titled HUMAN
                # request stays open (a human decides about human asks).
                n = w.mark_shipped("no NPI column")
                self.assertEqual(n, 1)
                shipped = w.list_requests(status="shipped")
                self.assertEqual(len(shipped), 1)
                self.assertEqual(shipped[0]["source"], "auto")
                open_user = [r for r in w.list_requests(status="open")
                             if r["source"] == "user"]
                self.assertEqual(len(open_user), 1)
                # Idempotent: nothing left matching and open.
                self.assertEqual(w.mark_shipped("no NPI column"), 0)
                # source=None widens to human requests too.
                self.assertEqual(
                    w.mark_shipped("no NPI column", source=None), 1)
                # Blank fragment is a no-op, never a full-table update.
                self.assertEqual(w.mark_shipped("   "), 0)

    def test_broken_store_returns_false_not_500(self):
        import rcm_mc.npi_cleaner.wishlist as w
        bad = Path("/proc/definitely-missing/wl.sqlite3")
        with patch.object(w, "_DB_PATH", bad):
            self.assertFalse(w.set_status(1, "shipped"))
            self.assertFalse(w.delete_request(1))
            self.assertEqual(w.mark_shipped("anything"), 0)
            self.assertEqual(w.list_requests(), [])


# --------------------------------------------------------------- exec report --
class TestExecReportSections(unittest.TestCase):
    def _sc_with(self, **extra):
        sc = _base_scorecard()
        sc.update(extra)
        return sc

    def test_compliance_section_renders_and_names_the_provider(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        sc = self._sc_with(compliance=[{
            "id": "oig_leie", "label": "OIG LEIE (excluded providers)",
            "available": True, "checked": 3, "excluded": 1,
            "matches": [{"npi": GOOD_A, "name": "JANE DOE",
                         "excl_type": "1128a1", "excl_date": "20220315",
                         "billed": 1500.56}],
            "excluded_billed_total": 1500.56,
            "note": "1 of 3 distinct NPIs appear on the OIG exclusions "
                    "list."}])
        html = build_exec_report(sc, "f.csv", "now")
        self.assertIn("Compliance (OIG LEIE", html)
        self.assertIn("JANE DOE", html)
        self.assertIn("1128a1", html)
        self.assertIn("$1,500.56", html)
        self.assertIn("sev-critical", html)

    def test_dollar_exposure_trend_deid_nppes_sections(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        sc = self._sc_with(
            advanced={"issues": [
                {"issue": "invalid_hcpcs", "rows": 12, "pct_rows": 1.2,
                 "dollars": 8123.4, "pct_dollars": 3.4},
                {"issue": "missing_npi", "rows": 40, "pct_rows": 4.0,
                 # 22.16, not 22.15: the binary float for 22.15 is
                 # 22.1499…, so a half-value fixture would assert on
                 # rounding luck instead of the 1dp formatting rule.
                 "dollars": 90555.678, "pct_dollars": 22.16}]},
            trend_alerts=["Quality score dropped 92 → 81 vs the previous "
                          "run of this file."],
            deid={"cells": 120, "columns": ["PatientName", "MemberID"]},
            nppes={"verify": {"checked": 9, "active": 8, "not_found": 1},
                   "recover": {"matches": [{"row": 3, "candidates":
                                            [{"npi": GOOD_B}]}]}},
            recovered_written=1,
            outliers=[{"code": "99213", "n": 40, "outliers": 2,
                       "median": 101.0, "max": 9250.0}])
        html = build_exec_report(sc, "f.csv", "now")
        self.assertIn("Dollar exposure by issue", html)
        self.assertIn("$90,555.68", html)      # 2dp dollars
        self.assertIn("22.2%", html)           # 1dp pct (rounded)
        # Biggest dollars first.
        self.assertLess(html.index("missing_npi"),
                        html.index("invalid_hcpcs"))
        self.assertIn("Change vs the previous run", html)
        self.assertIn("Quality score dropped 92", html)
        self.assertIn("De-identified: 120", html)
        self.assertIn("NPPES verification", html)
        self.assertIn("9 NPIs checked", html)
        self.assertIn("Charge outliers (per HCPCS)", html)
        self.assertIn("$9,250.00", html)

    def test_sections_absent_without_payloads(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        html = build_exec_report(_base_scorecard(), "f.csv", "now")
        self.assertNotIn("Compliance (OIG LEIE", html)
        self.assertNotIn("Dollar exposure by issue", html)
        self.assertNotIn("Change vs the previous run", html)
        self.assertNotIn("NPPES verification", html)
        self.assertNotIn("De-identified:", html)

    def test_prevalence_caption_honest_without_patient_column(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        pop = {"conditions": {"patient_grouping": False, "prevalence": [
            {"condition": "Diabetes", "pct": 30.0, "patients": 3}]}}
        html = build_exec_report(self._sc_with(population=pop), "f", "now")
        self.assertIn("no patient column detected", html)
        self.assertNotIn("Chronic conditions (prevalence)", html)
        pop2 = {"conditions": {"patient_grouping": True, "prevalence": [
            {"condition": "Diabetes", "pct": 30.0, "patients": 3}]}}
        html2 = build_exec_report(self._sc_with(population=pop2), "f", "now")
        self.assertIn("Chronic conditions (prevalence)", html2)

    def test_coding_intensity_shows_national_context(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        pop = {"coding_intensity": {
            "established_visits": 60, "file_avg_level": 3.9,
            "provider_basis": "rendering",
            "national_mix": {"99211": 0.02, "99212": 0.08, "99213": 0.34,
                             "99214": 0.45, "99215": 0.11}}}
        html = build_exec_report(self._sc_with(population=pop), "f", "now")
        # Weighted national average = 3.55.
        self.assertIn("vs national avg level 3.55", html)
        self.assertIn("per-rendering-provider basis", html)

    def test_prefixed_carc_gets_meaning_and_playbook(self):
        from rcm_mc.npi_cleaner.exec_report import build_exec_report
        sc = self._sc_with(denials={"column": "DenialCode", "distinct": 1,
                                    "top": [{"code": "CO-45", "count": 12}]})
        html = build_exec_report(sc, "f.csv", "now")
        self.assertIn("fee schedule", html)          # description of 45
        self.assertIn("[contractual]", html)         # recovered playbook


# ------------------------------------------------------------------ workbook --
class TestWorkbookSheets(unittest.TestCase):
    def _res_with_payloads(self):
        rows = ["ClaimID,BillingNPI,HCPCS,BilledAmt,DenialCode"]
        charges = [95, 96, 97, 98, 99, 101, 102, 103, 104, 9999]
        rows += [f"{i},{GOOD_A},99213,{c},45"
                 for i, c in enumerate(charges, start=1)]
        res = engine.clean_bytes(("\n".join(rows) + "\n").encode(),
                                 "wb.csv")
        # Attach the payloads an online run would carry (compliance runs
        # only in online mode; trend alerts need a prior run).
        res.compliance = [{
            "id": "oig_leie", "label": "OIG LEIE (excluded providers)",
            "available": True, "checked": 1, "excluded": 1,
            "matches": [{"npi": GOOD_A, "name": "JANE DOE",
                         "excl_type": "1128a1", "excl_date": "20220315",
                         "billed": 999.99}],
            "excluded_billed_total": 999.99, "note": "1 of 1."}]
        res.trend_alerts = ["'carc-invalid' is new since the previous run "
                            "(30 rows)."]
        return res

    def test_new_sheets_present_with_content(self):
        from rcm_mc.npi_cleaner import report
        res = self._res_with_payloads()
        self.assertTrue(res.outliers)      # 9999 vs ~100 → real outlier
        headers, rows = _cleaned_table(res)
        wb = _load_workbook(report.build_workbook(res, headers, rows))
        for name in ("Denials", "Compliance", "Charge outliers",
                     "Dictionary"):
            self.assertIn(name, wb.sheetnames)
        den = [str(c.value) for row in wb["Denials"].iter_rows()
               for c in row if c.value]
        self.assertTrue(any("fee schedule" in c for c in den))
        comp = [str(c.value) for row in wb["Compliance"].iter_rows()
                for c in row if c.value]
        self.assertTrue(any("JANE DOE" in c for c in comp))
        self.assertTrue(any("1128a1" in c for c in comp))
        outl = [str(c.value) for row in wb["Charge outliers"].iter_rows()
                for c in row if c.value]
        self.assertTrue(any("99213" in c for c in outl))
        dic = [str(c.value) for row in wb["Dictionary"].iter_rows()
               for c in row if c.value]
        self.assertTrue(any("hcpcs/cpt" in c for c in dic))
        # Summary carries the trend header + honest findings label.
        summ = [str(c.value) for row in wb["Summary"].iter_rows()
                for c in row if c.value]
        self.assertTrue(any("Findings (rule hits, all rules)" in c
                            for c in summ))
        self.assertTrue(any("Change vs previous run" in c for c in summ))
        self.assertTrue(any("carc-invalid" in c for c in summ))
        self.assertTrue(any("Rows with ≥1 finding" in c for c in summ))

    def test_guarded_sheets_absent_without_payloads(self):
        from rcm_mc.npi_cleaner import report
        res = engine.clean_bytes(
            f"ClaimID,BillingNPI\n1,{GOOD_A}\n".encode(), "min.csv")
        headers, rows = _cleaned_table(res)
        wb = _load_workbook(report.build_workbook(res, headers, rows))
        self.assertNotIn("Compliance", wb.sheetnames)
        self.assertNotIn("Denials", wb.sheetnames)
        self.assertNotIn("Charge outliers", wb.sheetnames)
        self.assertIn("Dictionary", wb.sheetnames)   # always has columns

    def test_worklist_banner_and_dollar_ranking(self):
        from rcm_mc.npi_cleaner import report
        rows = ["ClaimID,HCPCS,BilledAmt"]
        # Flagged rows (BAD!!) carry ascending charges so file order and
        # dollar order disagree — the tab must rank by dollars.
        rows += [f"{i},BAD!!,{i * 10}" for i in range(1, 8)]
        rows += [f"{i},99213,50" for i in range(8, 11)]
        res = engine.clean_bytes(("\n".join(rows) + "\n").encode(),
                                 "wl.csv")
        headers, out_rows = _cleaned_table(res)
        wb = _load_workbook(report.build_workbook(res, headers, out_rows))
        name = next(s for s in wb.sheetnames
                    if s.startswith("WL hcpcs-malformed"))
        grid = [[c.value for c in row] for row in wb[name].iter_rows()]
        self.assertIn("[critical]", str(grid[0][0]))
        self.assertIn("Malformed HCPCS/CPT", str(grid[0][0]))
        self.assertTrue(str(grid[1][0]).startswith("What to do:"))
        hdr = grid[2]
        self.assertEqual(hdr[0], "_row")
        billed_col = hdr.index("BilledAmt")
        billed = [float(r[billed_col]) for r in grid[3:]
                  if r[billed_col] is not None
                  and str(r[billed_col]).replace(".", "").isdigit()]
        self.assertEqual(billed, sorted(billed, reverse=True))
        self.assertEqual(billed[0], 70.0)
        # The ranking note is present.
        flat = [str(c) for row in grid for c in row if c]
        self.assertTrue(any("Sorted by billed $" in c for c in flat))


# ------------------------------------------------------------ deep preflight --
class TestDeepPreflight(unittest.TestCase):
    def test_no_egress_fails_in_seconds_not_minutes(self):
        from rcm_mc.npi_cleaner import deep_pipeline as D
        if not D.available():
            self.skipTest("deep pipeline unavailable")
        msgs = []
        t0 = time.monotonic()
        out = D.run(b"BillingNPI\n" + GOOD_A.encode(), "x.csv",
                    probe=lambda: False,
                    progress=lambda m, f: msgs.append((m, f)))
        elapsed = time.monotonic() - t0
        self.assertFalse(out["ok"])
        self.assertIn("outbound access", out["error"])
        self.assertIn("preflight", out["error"])
        self.assertLess(elapsed, 5.0)
        self.assertTrue(any("preflight failed" in m for m, _ in msgs))
        # The deterministic-results promise stays in the message.
        self.assertIn("deterministic results", out["error"])

    def test_default_probe_never_raises(self):
        from rcm_mc.npi_cleaner import deep_pipeline as D
        self.assertIn(D._default_probe(timeout=0.5), (True, False))


# ----------------------------------------------------- coding-intensity grain --
class TestCodingIntensityBasis(unittest.TestCase):
    def _rows(self):
        # One billing org; two rendering clinicians — R1 codes all level 5,
        # R2 all level 2. At org grain the mix averages out; only the
        # rendering grain can see the hot coder.
        rows = []
        for _ in range(20):
            rows.append(["99215", GOOD_A, "R1"])
            rows.append(["99212", GOOD_A, "R2"])
        return rows

    def test_rendering_grain_finds_hot_coder_org_grain_cannot(self):
        from rcm_mc.npi_cleaner import analytics
        idx_org = {"hcpcs_i": 0, "billing_idx": 1}
        out_org = analytics.build(["h", "b", "r"], self._rows(), idx_org)
        ci_org = out_org["coding_intensity"]
        self.assertEqual(ci_org["provider_basis"], "billing")
        self.assertEqual(ci_org["outliers"], [])
        idx_rend = {"hcpcs_i": 0, "billing_idx": 1, "rendering_i": 2}
        out_rend = analytics.build(["h", "b", "r"], self._rows(), idx_rend)
        ci_rend = out_rend["coding_intensity"]
        self.assertEqual(ci_rend["provider_basis"], "rendering")
        self.assertEqual(len(ci_rend["outliers"]), 1)
        self.assertEqual(ci_rend["outliers"][0]["npi"], "R1")
        self.assertEqual(ci_rend["outliers"][0]["avg_level"], 5.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
