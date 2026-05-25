"""Deal Library ingestion + loader.

Drives the pipeline on a SYNTHETIC CapIQ-shaped fixture (no licensed data, no
xlrd / network) and the loader on a temp SQLite store. Locks in the honesty
rules: missing means NULL (never 0), no invented values, provenance preserved,
deterministic ids, conservative duplicate flagging.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
import ingest_deal_library_exports as ing  # noqa: E402
from rcm_mc.data import deal_library  # noqa: E402

_FIXTURE = _ROOT / "tests" / "fixtures" / "deal_library_capiq_sample.csv"


class TestValueNormalization(unittest.TestCase):
    def test_missing_tokens_become_none_not_zero(self):
        for tok in ("-", "", "NM", "N/A", "nan"):
            self.assertIsNone(ing.norm_str(tok))
            self.assertIsNone(ing.parse_money(tok))   # crucial: not 0.0

    def test_money_parsing(self):
        self.assertEqual(ing.parse_money("1,250.0"), 1250.0)
        self.assertEqual(ing.parse_money("(15.5)"), -15.5)   # parens negative
        self.assertEqual(ing.parse_money("$12.5x"), 12.5)

    def test_clean_name_keeps_leading_digits(self):
        # '100% Wellness' must NOT be treated as a rank prefix.
        self.assertIn("100", ing.clean_company_name("100% Wellness Clinics"))
        self.assertEqual(ing.clean_company_name("Acme Health Partners LLC"),
                         ing.clean_company_name("Acme Health Partners"))

    def test_sponsor_prefers_current(self):
        s = ing.parse_sponsor("Synthetic Capital (Current Sponsor); Other Fund (Prior Sponsor)")
        self.assertEqual(s, "Synthetic Capital")

    def test_state_from_address(self):
        self.assertEqual(ing.parse_state("12 Main St, Austin, TX"), "TX")
        self.assertIsNone(ing.parse_state("-"))


class TestIngestFixture(unittest.TestCase):
    def setUp(self):
        self.recs, self.info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(self.recs)

    def test_header_detected_and_all_columns_mapped(self):
        # Title rows skipped; header row auto-detected; nothing unmapped.
        self.assertEqual(self.info["unmapped_columns"], [])

    def test_nameless_row_skipped(self):
        # 5 data rows in fixture, one has no company name → 4 records.
        self.assertEqual(len(self.recs), 4)

    def test_missing_financials_are_none(self):
        acme = next(r for r in self.recs if r["company_name"].startswith("Acme"))
        self.assertIsNone(acme["enterprise_value"])   # '-' → None, not 0
        self.assertIsNone(acme["ebitda"])
        self.assertEqual(acme["revenue"], 125.5)
        self.assertEqual(acme["sponsor_owner"], "Synthetic Capital")
        self.assertEqual(acme["state"], "TX")

    def test_completeness_and_missing_fields(self):
        for r in self.recs:
            self.assertGreaterEqual(r["completeness_score"], 0.0)
            self.assertLessEqual(r["completeness_score"], 1.0)
            # missing_fields lists exactly the empty core fields
            for f in r["missing_fields"].split(";"):
                if f:
                    self.assertIn(r.get(f), (None, ""))

    def test_duplicate_candidate_flagged_conservatively(self):
        # Two "Acme Health Partners" in TX → second flagged, first not.
        acmes = [r for r in self.recs if r["clean_name"].startswith("acme health")]
        self.assertEqual(len(acmes), 2)
        self.assertEqual(sorted(r["duplicate_candidate"] for r in acmes), [0, 1])

    def test_deterministic_ids_stable(self):
        recs2, _ = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        self.assertEqual([r["company_id"] for r in self.recs],
                         [r["company_id"] for r in recs2])

    def test_no_synthetic_fill_in_report(self):
        rep = ing.build_report(self.recs, [self.info], "Capital IQ")
        # EV is absent for most fixture rows → high missingness, not 0%.
        self.assertGreater(rep["missingness_pct_by_field"]["enterprise_value"], 50.0)


class TestLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        recs, info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(recs)
        rep = ing.build_report(recs, [info], "Capital IQ")
        self.out = Path(self.tmp.name)
        ing.write_outputs(recs, rep, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_vertical_estimate_is_labeled_heuristic(self):
        # Inferred from name; unmatched stays None (never guessed).
        self.assertEqual(ing.infer_vertical("Beacon Dialysis Inc."), "Dialysis/Renal")
        self.assertEqual(ing.infer_vertical("42 North Dental LLC"), "Dental")
        self.assertIsNone(ing.infer_vertical("Acme Health Partners LLC"))
        self.assertIsNone(ing.infer_vertical(""))
        # populated on the record + canonical field present
        recs, _ = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        beacon = next(r for r in recs if r["company_name"].startswith("Beacon"))
        self.assertEqual(beacon["healthcare_vertical_est"], "Dialysis/Renal")
        acme = next(r for r in recs if r["company_name"].startswith("Acme"))
        self.assertIsNone(acme["healthcare_vertical_est"])

    def test_migration_adds_vertical_column_to_old_table(self):
        # A table created by an earlier schema must gain the column on load.
        with self.store.connect() as con:
            con.execute("CREATE TABLE deal_library_companies "
                        "(company_id TEXT PRIMARY KEY, company_name TEXT)")
            con.commit()
        recs, info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(recs)
        ing.write_outputs(recs, ing.build_report(recs, [info], "Capital IQ"), self.out)
        n = deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv")
        self.assertEqual(n, 4)
        res = deal_library.query(
            self.store, filters={"healthcare_vertical_est": "Dialysis/Renal"})
        self.assertEqual(res["total"], 1)

    def test_sources_provenance_table(self):
        recs, info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(recs)
        srcs = ing.build_sources([info], "Capital IQ")
        self.assertEqual(len(srcs), 1)
        self.assertEqual(srcs[0]["source_file"], _FIXTURE.name)
        self.assertEqual(srcs[0]["row_count"], len(recs))
        ing.write_outputs(recs, ing.build_report(recs, [info], "Capital IQ"),
                          self.out, sources=srcs)
        n = deal_library.load_sources_csv(
            self.store, self.out / "deal_library_sources.csv")
        self.assertEqual(n, 1)
        # idempotent
        self.assertEqual(deal_library.load_sources_csv(
            self.store, self.out / "deal_library_sources.csv"), 1)
        rows = deal_library.sources(self.store)
        self.assertEqual(rows[0]["source_system"], "Capital IQ")
        self.assertIn("not redistributed", rows[0]["license_scope_note"])

    def test_load_and_query_roundtrip(self):
        n = deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv")
        self.assertEqual(n, 4)
        self.assertEqual(deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv"), 4)  # idempotent
        self.assertEqual(deal_library.count(self.store), 4)

    def test_filters_search_sort_pagination(self):
        deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv")
        # filter by sponsor
        res = deal_library.query(self.store, filters={"sponsor_owner": "Synthetic Capital"})
        self.assertTrue(all(r["sponsor_owner"] == "Synthetic Capital" for r in res["rows"]))
        self.assertEqual(res["total"], 3)
        # search
        res = deal_library.query(self.store, search="Dialysis")
        self.assertEqual(res["total"], 1)
        # numeric sort puts NULL revenue last, not first
        res = deal_library.query(self.store, sort_by="revenue", sort_dir="asc", limit=10)
        revs = [r["revenue"] for r in res["rows"]]
        self.assertEqual(revs[-1], None)
        self.assertIn(125.5, revs)

    def test_missingness_and_breakdown(self):
        deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv")
        miss = deal_library.field_missingness(self.store)
        self.assertGreater(miss["enterprise_value"], 50.0)
        self.assertEqual(deal_library.field_missingness(self.store)["sponsor_owner"], 0.0)
        sb = deal_library.source_breakdown(self.store)
        self.assertEqual(sb[0]["source_system"], "Capital IQ")
        self.assertEqual(sb[0]["n"], 4)

    def test_sort_param_is_allowlisted(self):
        deal_library.load_companies_csv(
            self.store, self.out / "deal_library_companies.csv")
        # injection attempt falls back to default sort, does not error
        res = deal_library.query(self.store, sort_by="revenue; DROP TABLE x")
        self.assertEqual(res["total"], 4)


if __name__ == "__main__":
    unittest.main()
