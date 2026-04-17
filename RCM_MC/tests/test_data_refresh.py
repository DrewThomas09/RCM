"""Tests for the CMS public-data refresh pipeline.

HTTP is mocked throughout — none of these tests should hit CMS.
Downloads are replaced via ``monkeypatch.setattr`` on the
``fetch_url`` entry in ``rcm_mc.data._cms_download``.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from rcm_mc.data import _cms_download
from rcm_mc.data import cms_care_compare, cms_hcris, cms_utilization, irs990_loader
from rcm_mc.data import data_refresh as dr
from rcm_mc.portfolio.store import PortfolioStore


# ── Fixtures ─────────────────────────────────────────────────────────

def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


def _stub_fetch_url(written_content: bytes):
    """Return a fetch_url stub that writes ``written_content`` to the
    requested ``dest`` path and returns it. Used to divert HTTP in tests.
    """
    def _stub(url, dest, *, timeout=60.0, overwrite=False):
        dest = Path(dest)
        if dest.exists() and not overwrite:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(written_content)
        return dest
    return _stub


def _write_hcris_csv(path: Path, rows: list):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "ccn", "name", "city", "state", "fiscal_year", "fy_end_dt",
            "beds", "medicare_day_pct", "medicaid_day_pct",
            "gross_patient_revenue", "net_patient_revenue",
            "operating_expenses", "ime_payments",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_hcris_csv_gz(path: Path, rows: list):
    tmp = path.with_suffix(".csv.tmp")
    _write_hcris_csv(tmp, rows)
    with open(tmp, "rb") as fin, gzip.open(path, "wb") as fout:
        fout.write(fin.read())
    tmp.unlink()


# ── Tables / save_benchmarks ─────────────────────────────────────────

class TestTables(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_ensure_tables_creates_both(self):
        dr._ensure_tables(self.store)
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('hospital_benchmarks','data_source_status')"
            ).fetchall()
        names = {r["name"] for r in rows}
        self.assertEqual(names, {"hospital_benchmarks", "data_source_status"})

    def test_save_benchmarks_numeric_and_text(self):
        n = dr.save_benchmarks(self.store, [
            {"provider_id": "100001", "metric_key": "bed_count", "value": 420.0},
            {"provider_id": "100001", "metric_key": "state", "value": "IL"},
        ], source="HCRIS", period="2024")
        self.assertEqual(n, 2)
        with self.store.connect() as con:
            bc = con.execute(
                "SELECT value, text_value FROM hospital_benchmarks "
                "WHERE metric_key='bed_count'"
            ).fetchone()
            st = con.execute(
                "SELECT value, text_value FROM hospital_benchmarks "
                "WHERE metric_key='state'"
            ).fetchone()
        self.assertEqual(bc["value"], 420.0)
        self.assertIsNone(bc["text_value"])
        self.assertIsNone(st["value"])
        self.assertEqual(st["text_value"], "IL")

    def test_save_benchmarks_upsert(self):
        dr.save_benchmarks(self.store, [
            {"provider_id": "X", "metric_key": "bed_count", "value": 100},
        ], source="HCRIS", period="2024")
        dr.save_benchmarks(self.store, [
            {"provider_id": "X", "metric_key": "bed_count", "value": 200},
        ], source="HCRIS", period="2024")
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT value FROM hospital_benchmarks WHERE provider_id='X'"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], 200.0)

    def test_save_benchmarks_drops_rows_missing_keys(self):
        n = dr.save_benchmarks(self.store, [
            {"provider_id": "X"},  # no metric_key
            {"metric_key": "bed_count", "value": 1},  # no provider_id
            {"provider_id": "Y", "metric_key": "bed_count", "value": 100},
        ], source="HCRIS")
        self.assertEqual(n, 1)


# ── Status / scheduling ──────────────────────────────────────────────

class TestStatus(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_schedule_refresh_seeds_four_sources(self):
        dr.schedule_refresh(self.store, interval_days=14)
        rows = dr.get_status(self.store)
        names = {r["source_name"] for r in rows}
        self.assertEqual(names, set(dr.KNOWN_SOURCES))
        for r in rows:
            self.assertEqual(r["status"], "STALE")

    def test_set_status_ok_updates_row(self):
        dr.schedule_refresh(self.store, interval_days=14)
        dr.set_status(self.store, "hcris", status="OK", record_count=42,
                      interval_days=30)
        rows = dr.get_status(self.store, source_name="hcris")
        self.assertEqual(rows[0]["status"], "OK")
        self.assertEqual(rows[0]["record_count"], 42)

    def test_mark_stale_sources_flips_past_due_rows(self):
        dr.schedule_refresh(self.store, interval_days=14)
        # Force a past-due next_refresh_at on one source
        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        with self.store.connect() as con:
            con.execute(
                "UPDATE data_source_status SET status='OK', next_refresh_at=? "
                "WHERE source_name='hcris'",
                (past,),
            )
            con.commit()
        marked = dr.mark_stale_sources(self.store)
        self.assertIn("hcris", marked)
        rows = dr.get_status(self.store, source_name="hcris")
        self.assertEqual(rows[0]["status"], "STALE")


# ── Orchestrator ─────────────────────────────────────────────────────

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_refresh_all_sources_uses_injected_refreshers(self):
        called = []

        def _r(name, count):
            def _fn(store):
                called.append(name)
                return count
            return _fn

        refreshers = {
            "hcris": _r("hcris", 10),
            "care_compare": _r("care_compare", 20),
            "utilization": _r("utilization", 30),
            "irs990": _r("irs990", 5),
        }
        report = dr.refresh_all_sources(
            self.store, refreshers=refreshers,
        )
        self.assertEqual(set(called), set(dr.KNOWN_SOURCES))
        self.assertEqual(report.total_records, 65)
        self.assertFalse(report.any_errors)
        rows = {r["source_name"]: r for r in dr.get_status(self.store)}
        self.assertEqual(rows["hcris"]["record_count"], 10)
        self.assertEqual(rows["hcris"]["status"], "OK")

    def test_refresh_partial_failure_does_not_block_others(self):
        def _bad(store):
            raise RuntimeError("boom")

        def _ok(store):
            return 7

        report = dr.refresh_all_sources(
            self.store,
            refreshers={"hcris": _bad, "care_compare": _ok,
                        "utilization": _ok, "irs990": _ok},
        )
        self.assertTrue(report.any_errors)
        results = {r.source: r for r in report.per_source}
        self.assertEqual(results["hcris"].status, "ERROR")
        self.assertEqual(results["care_compare"].status, "OK")
        self.assertEqual(results["care_compare"].record_count, 7)
        rows = {r["source_name"]: r for r in dr.get_status(self.store)}
        self.assertEqual(rows["hcris"]["status"], "ERROR")

    def test_refresh_sources_subset(self):
        calls = []

        def _fn(name):
            def _inner(store):
                calls.append(name)
                return 1
            return _inner
        refreshers = {n: _fn(n) for n in dr.KNOWN_SOURCES}
        dr.refresh_all_sources(self.store, sources=["hcris", "irs990"],
                               refreshers=refreshers)
        self.assertEqual(set(calls), {"hcris", "irs990"})


# ── HCRIS parse + load ───────────────────────────────────────────────

class TestCmsHcris(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        try:
            os.unlink(self.path)
        except OSError:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parse_hcris_csv_fills_record(self):
        csv_path = Path(self.tmpdir) / "hcris.csv"
        _write_hcris_csv(csv_path, [{
            "ccn": "360180", "name": "Acme", "city": "Chicago", "state": "IL",
            "fiscal_year": "2024", "fy_end_dt": "2024-12-31",
            "beds": "420", "medicare_day_pct": "0.40",
            "medicaid_day_pct": "0.15",
            "gross_patient_revenue": "500000000",
            "net_patient_revenue": "350000000",
            "operating_expenses": "325000000",
            "ime_payments": "1500000",
        }])
        recs = cms_hcris.parse_hcris(csv_path)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec.provider_id, "360180")
        self.assertEqual(rec.bed_count, 420)
        self.assertEqual(rec.state, "IL")
        self.assertTrue(rec.teaching_status)   # ime_payments > 0
        self.assertAlmostEqual(rec.payer_mix["medicare"], 0.40)
        # Operating margin = (NPR - OPEX) / NPR
        self.assertAlmostEqual(rec.operating_margin,
                               (350e6 - 325e6) / 350e6, places=5)

    def test_parse_hcris_gz(self):
        csv_gz_path = Path(self.tmpdir) / "hcris.csv.gz"
        _write_hcris_csv_gz(csv_gz_path, [{
            "ccn": "999001", "name": "Z", "city": "Z", "state": "CA",
            "fiscal_year": "2023", "fy_end_dt": "2023-06-30",
            "beds": "50",
        }])
        recs = cms_hcris.parse_hcris(csv_gz_path)
        self.assertEqual(recs[0].provider_id, "999001")
        self.assertEqual(recs[0].bed_count, 50)

    def test_load_hcris_to_store_writes_benchmark_rows(self):
        csv_path = Path(self.tmpdir) / "hcris.csv"
        _write_hcris_csv(csv_path, [
            {"ccn": "A", "name": "", "city": "", "state": "IL",
             "fiscal_year": "2024", "fy_end_dt": "2024-12-31", "beds": "100",
             "medicare_day_pct": "", "medicaid_day_pct": "",
             "gross_patient_revenue": "", "net_patient_revenue": "",
             "operating_expenses": "", "ime_payments": ""},
            {"ccn": "B", "name": "", "city": "", "state": "CA",
             "fiscal_year": "2024", "fy_end_dt": "2024-12-31", "beds": "300",
             "medicare_day_pct": "", "medicaid_day_pct": "",
             "gross_patient_revenue": "", "net_patient_revenue": "",
             "operating_expenses": "", "ime_payments": ""},
        ])
        records = cms_hcris.parse_hcris(csv_path)
        cms_hcris.load_hcris_to_store(self.store, records)
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT provider_id, metric_key, value, text_value "
                "FROM hospital_benchmarks ORDER BY provider_id, metric_key"
            ).fetchall()
        by_pid = {}
        for r in rows:
            by_pid.setdefault(r["provider_id"], {})[r["metric_key"]] = (
                r["value"] if r["value"] is not None else r["text_value"]
            )
        self.assertEqual(by_pid["A"]["bed_count"], 100.0)
        self.assertEqual(by_pid["A"]["state"], "IL")
        self.assertEqual(by_pid["B"]["bed_count"], 300.0)
        self.assertEqual(by_pid["B"]["state"], "CA")

    def test_download_hcris_uses_cms_download_fetch(self):
        called = {}

        def _fake(url, dest, *, timeout=60.0, overwrite=False):
            called["url"] = url
            called["dest"] = dest
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            Path(dest).write_text("pretend-zip-bytes")
            return Path(dest)

        with mock.patch("rcm_mc.data._cms_download.fetch_url", _fake):
            p = cms_hcris.download_hcris(year=2022, dest=Path(self.tmpdir) / "hcris.zip")
        self.assertTrue(p.exists())
        self.assertIn("HOSP10FY2022", called["url"])


# ── Care Compare parse + load ────────────────────────────────────────

class TestCareCompare(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        try:
            os.unlink(self.path)
        except OSError:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parse_general_csv(self):
        general = self.tmpdir / "general.csv"
        with open(general, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Facility ID", "Hospital overall rating"])
            w.writerow(["360180", "4"])
            w.writerow(["999001", "Not Available"])
        recs = cms_care_compare.parse_care_compare({"general": general})
        by = {r.provider_id: r for r in recs}
        self.assertEqual(by["360180"].star_rating, 4.0)
        self.assertIsNone(by["999001"].star_rating)

    def test_parse_complications_csv_maps_measure_ids(self):
        comp = self.tmpdir / "complications.csv"
        with open(comp, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Facility ID", "Measure ID", "Score"])
            w.writerow(["100001", "READM_30_HOSPWIDE", "15.2"])
            w.writerow(["100001", "MORT_30_AMI", "13.8"])
            w.writerow(["100001", "HAC_6", "1.05"])
            w.writerow(["100001", "MSPB_1", "0.97"])
        recs = cms_care_compare.parse_care_compare({"complications": comp})
        r = recs[0]
        self.assertAlmostEqual(r.readmission_rate, 15.2)
        self.assertAlmostEqual(r.mortality_rate, 13.8)
        self.assertAlmostEqual(r.hac_score, 1.05)
        self.assertAlmostEqual(r.medicare_spending_per_beneficiary, 0.97)

    def test_load_care_compare_writes_benchmarks(self):
        general = self.tmpdir / "general.csv"
        with open(general, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Facility ID", "Hospital overall rating"])
            w.writerow(["360180", "4"])
        records = cms_care_compare.parse_care_compare({"general": general})
        cms_care_compare.load_care_compare_to_store(self.store, records,
                                                    period="2025Q1")
        with self.store.connect() as con:
            row = con.execute(
                "SELECT value, source, period FROM hospital_benchmarks "
                "WHERE metric_key='star_rating'"
            ).fetchone()
        self.assertEqual(row["value"], 4.0)
        self.assertEqual(row["source"], "CARE_COMPARE")
        self.assertEqual(row["period"], "2025Q1")


# ── Utilization derived metrics ──────────────────────────────────────

class TestUtilization(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        try:
            os.unlink(self.path)
        except OSError:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parse_and_compute_derived_metrics(self):
        csv_path = self.tmpdir / "util.csv"
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Rndrng_Prvdr_CCN", "DRG_Cd", "DRG_Desc",
                        "Tot_Dschrgs", "Avg_Submtd_Cvrd_Chrg",
                        "Avg_Tot_Pymt_Amt", "Avg_Mdcr_Pymt_Amt"])
            w.writerow(["100001", "470", "Joint Replace", "400", "70000", "14000", "12000"])
            w.writerow(["100001", "291", "Heart Failure", "300", "25000", "8000", "7000"])
            w.writerow(["100001", "871", "Sepsis", "100", "40000", "10000", "9000"])
        recs = cms_utilization.parse_utilization(csv_path)
        self.assertEqual(len(recs), 3)
        derived = cms_utilization.compute_provider_metrics(recs)["100001"]
        self.assertAlmostEqual(derived["total_medicare_discharges"], 800.0)
        self.assertEqual(derived["top_drg_volume"], 400.0)
        # HHI: (400/800)^2 + (300/800)^2 + (100/800)^2
        expected_hhi = 0.5**2 + 0.375**2 + 0.125**2
        self.assertAlmostEqual(derived["service_line_concentration"],
                               expected_hhi, places=5)
        # Weighted charge/payment: (70000/14000 × 400 + 25000/8000 × 300 + 40000/10000 × 100) / 800
        expected_ratio = (5.0 * 400 + 3.125 * 300 + 4.0 * 100) / 800
        self.assertAlmostEqual(derived["avg_charge_to_payment_ratio"],
                               expected_ratio, places=5)

    def test_load_utilization_to_store(self):
        csv_path = self.tmpdir / "util.csv"
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Rndrng_Prvdr_CCN", "DRG_Cd", "Tot_Dschrgs",
                        "Avg_Submtd_Cvrd_Chrg", "Avg_Tot_Pymt_Amt",
                        "Avg_Mdcr_Pymt_Amt"])
            w.writerow(["200001", "470", "100", "20000", "5000", "4500"])
        recs = cms_utilization.parse_utilization(csv_path)
        n = cms_utilization.load_utilization_to_store(self.store, recs,
                                                     period="2024")
        self.assertGreater(n, 0)
        with self.store.connect() as con:
            row = con.execute(
                "SELECT value FROM hospital_benchmarks "
                "WHERE provider_id='200001' AND metric_key='total_medicare_discharges'"
            ).fetchone()
        self.assertEqual(row["value"], 100.0)


# ── IRS 990 loader ───────────────────────────────────────────────────

class TestIRS990(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_parse_schedule_h_from_mock_payload(self):
        payload = {
            "organization": {"ein": "123456789", "name": "Acme Hospital"},
            "filings_with_data": [
                {"tax_prd_yr": 2022, "totrevenue": 500_000_000,
                 "totfuncexpns": 480_000_000, "charitycareatcost": 12_000_000,
                 "baddebtexpense": 8_000_000},
                {"tax_prd_yr": 2021, "totrevenue": 450_000_000,
                 "totfuncexpns": 440_000_000},
            ],
            "officers": [
                {"name": "CEO", "title": "CEO", "compensation": 1_200_000},
                {"name": "CFO", "title": "CFO", "compensation": 700_000},
            ],
        }
        rec = irs990_loader.parse_990_schedule_h(
            "12-3456789", fetcher=lambda ein: payload,
        )
        self.assertEqual(rec.ein, "12-3456789")
        self.assertEqual(rec.fiscal_year, 2022)     # picks latest
        self.assertEqual(rec.total_revenue, 500_000_000)
        self.assertEqual(rec.charity_care_at_cost, 12_000_000)
        self.assertEqual(rec.bad_debt_expense, 8_000_000)
        self.assertEqual(len(rec.executive_compensation), 2)
        self.assertEqual(rec.executive_compensation[0]["compensation"], 1_200_000)

    def test_refresh_from_ein_list_writes_benchmarks(self):
        payload = {
            "organization": {"ein": "999999999", "name": "Z"},
            "filings_with_data": [
                {"tax_prd_yr": 2023, "totrevenue": 100.0,
                 "charitycareatcost": 5.0},
            ],
        }
        n = irs990_loader.refresh_from_ein_list(
            self.store, ["999999999"],
            ein_to_ccn={"999999999": "800123"},
            fetcher=lambda ein: payload,
        )
        self.assertGreater(n, 0)
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT provider_id, metric_key, value FROM hospital_benchmarks"
            ).fetchall()
        self.assertTrue(all(r["provider_id"] == "800123" for r in rows))
        keys = {r["metric_key"] for r in rows}
        self.assertIn("charity_care_at_cost", keys)
        self.assertIn("total_revenue", keys)


# ── query_hospitals filter ───────────────────────────────────────────

class TestQueryHospitals(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        # Seed 3 hospitals
        dr.save_benchmarks(self.store, [
            {"provider_id": "A", "metric_key": "bed_count", "value": 100},
            {"provider_id": "A", "metric_key": "state", "value": "IL"},
            {"provider_id": "B", "metric_key": "bed_count", "value": 400},
            {"provider_id": "B", "metric_key": "state", "value": "IL"},
            {"provider_id": "C", "metric_key": "bed_count", "value": 800},
            {"provider_id": "C", "metric_key": "state", "value": "CA"},
        ], source="HCRIS", period="2024")

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_filter_by_state(self):
        results = dr.query_hospitals(self.store, state="IL")
        pids = [r["provider_id"] for r in results]
        self.assertEqual(pids, ["A", "B"])

    def test_filter_by_beds_min(self):
        results = dr.query_hospitals(self.store, beds_min=200)
        pids = {r["provider_id"] for r in results}
        self.assertEqual(pids, {"B", "C"})

    def test_filter_by_beds_range(self):
        results = dr.query_hospitals(self.store, beds_min=200, beds_max=500)
        self.assertEqual([r["provider_id"] for r in results], ["B"])

    def test_filter_combined(self):
        results = dr.query_hospitals(self.store, state="IL", beds_min=200)
        self.assertEqual([r["provider_id"] for r in results], ["B"])


# ── End-to-end ingestion with mocked HTTP ────────────────────────────

class TestEndToEndMockedHttp(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        try:
            os.unlink(self.path)
        except OSError:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_care_compare_refresh_with_mocked_fetch(self):
        """Drive refresh_care_compare_source through a mocked fetch_url."""
        # Build three CSV payloads that will be returned by the stub
        general_csv = (b"Facility ID,Hospital overall rating\n"
                       b"360180,4\n")
        hcahps_csv = (b"Facility ID,Patient Survey Star Rating\n"
                      b"360180,5\n")
        comp_csv = (b"Facility ID,Measure ID,Score\n"
                    b"360180,READM_30_HOSPWIDE,14.1\n")

        # Stub picks payload by URL — cms_care_compare downloads 3 files.
        def _stub(url, dest, *, timeout=60.0, overwrite=False):
            if "xubh-q36u" in url:
                Path(dest).write_bytes(general_csv)
            elif "632h-zaca" in url:
                Path(dest).write_bytes(hcahps_csv)
            elif "ynj2-r877" in url:
                Path(dest).write_bytes(comp_csv)
            else:
                raise AssertionError(f"unexpected URL: {url}")
            return Path(dest)

        with mock.patch("rcm_mc.data._cms_download.fetch_url", _stub), \
             mock.patch("rcm_mc.data.cms_care_compare._cms_download.cache_dir",
                        return_value=self.tmpdir):
            n = cms_care_compare.refresh_care_compare_source(self.store)
        self.assertGreater(n, 0)
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT metric_key, value FROM hospital_benchmarks "
                "WHERE provider_id='360180'"
            ).fetchall()
        keys = {r["metric_key"] for r in rows}
        self.assertIn("star_rating", keys)
        self.assertIn("readmission_rate", keys)


# ── Download cache dir ───────────────────────────────────────────────

class TestCacheDir(unittest.TestCase):
    def test_cache_dir_override_via_env(self):
        tmp = tempfile.mkdtemp()
        old = os.environ.get("RCM_MC_DATA_CACHE")
        os.environ["RCM_MC_DATA_CACHE"] = tmp
        try:
            p = _cms_download.cache_dir("mytest")
            self.assertEqual(str(p), os.path.join(tmp, "mytest"))
            self.assertTrue(p.is_dir())
        finally:
            if old is None:
                del os.environ["RCM_MC_DATA_CACHE"]
            else:
                os.environ["RCM_MC_DATA_CACHE"] = old
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fetch_url_cache_hit_short_circuits(self):
        tmp = Path(tempfile.mkdtemp())
        dest = tmp / "cached.txt"
        dest.write_bytes(b"existing")
        # Call fetch_url — it should NOT re-download (file exists).
        # We deliberately don't install a stub; if it hits the network,
        # the test would either hang or fail.
        result = _cms_download.fetch_url("https://invalid.invalid", dest,
                                         overwrite=False)
        self.assertEqual(result.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
