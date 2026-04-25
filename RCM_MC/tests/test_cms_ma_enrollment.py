"""Tests for CMS Medicare Advantage enrollment + Stars + benchmarks."""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


class TestYearMonthParsing(unittest.TestCase):
    def test_iso(self):
        from rcm_mc.data.cms_ma_enrollment import _parse_year_month
        self.assertEqual(_parse_year_month("2024-03"), "2024-03")
        self.assertEqual(_parse_year_month("2024-03-15"),
                         "2024-03")

    def test_compact(self):
        from rcm_mc.data.cms_ma_enrollment import _parse_year_month
        self.assertEqual(_parse_year_month("202403"), "2024-03")

    def test_named_month(self):
        from rcm_mc.data.cms_ma_enrollment import _parse_year_month
        self.assertEqual(_parse_year_month("Jan 2024"), "2024-01")
        self.assertEqual(
            _parse_year_month("January 2024"), "2024-01")

    def test_unknown_returns_blank(self):
        from rcm_mc.data.cms_ma_enrollment import _parse_year_month
        self.assertEqual(_parse_year_month(""), "")
        self.assertEqual(_parse_year_month("garbage"), "")


class TestEnrollmentParser(unittest.TestCase):
    def test_cms_friendly_columns(self):
        from rcm_mc.data.cms_ma_enrollment import (
            parse_ma_enrollment_csv,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "enroll.csv"
            _write_csv(csv_path, [
                "Contract Number", "Plan ID",
                "Organization Marketing Name",
                "Plan Type", "State", "County",
                "FIPS State and County Code",
                "Year Month", "Enrollment",
            ], [{
                "Contract Number": "H0028",
                "Plan ID": "001",
                "Organization Marketing Name": "Humana",
                "Plan Type": "HMO",
                "State": "FL", "County": "Miami-Dade",
                "FIPS State and County Code": "12086",
                "Year Month": "2024-03",
                "Enrollment": "45200",
            }])
            recs = list(parse_ma_enrollment_csv(csv_path))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.contract_id, "H0028")
            self.assertEqual(r.plan_id, "001")
            self.assertEqual(r.county_fips, "12086")
            self.assertEqual(r.year_month, "2024-03")
            self.assertEqual(r.enrollment, 45200)
            self.assertEqual(r.organization_name, "Humana")
        finally:
            tmp.cleanup()

    def test_fips_zero_padded(self):
        from rcm_mc.data.cms_ma_enrollment import (
            parse_ma_enrollment_csv,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "enroll.csv"
            _write_csv(csv_path, [
                "Contract Number", "Plan ID",
                "FIPS State and County Code", "Year Month",
                "Enrollment",
            ], [{
                "Contract Number": "H0028",
                "Plan ID": "001",
                "FIPS State and County Code": "1001",
                "Year Month": "2024-03",
                "Enrollment": "100",
            }])
            recs = list(parse_ma_enrollment_csv(csv_path))
            self.assertEqual(recs[0].county_fips, "01001")
        finally:
            tmp.cleanup()

    def test_blank_contract_or_fips_skipped(self):
        from rcm_mc.data.cms_ma_enrollment import (
            parse_ma_enrollment_csv,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "enroll.csv"
            _write_csv(csv_path, [
                "Contract Number",
                "FIPS State and County Code",
                "Plan ID", "Year Month", "Enrollment",
            ], [
                {"Contract Number": "",
                 "FIPS State and County Code": "12086",
                 "Plan ID": "001",
                 "Year Month": "2024-03",
                 "Enrollment": "100"},
                {"Contract Number": "H0028",
                 "FIPS State and County Code": "",
                 "Plan ID": "001",
                 "Year Month": "2024-03",
                 "Enrollment": "100"},
                {"Contract Number": "H0028",
                 "FIPS State and County Code": "12086",
                 "Plan ID": "001",
                 "Year Month": "2024-03",
                 "Enrollment": "100"},
            ])
            recs = list(parse_ma_enrollment_csv(csv_path))
            self.assertEqual(len(recs), 1)
        finally:
            tmp.cleanup()


class TestStarsParser(unittest.TestCase):
    def test_summary_table(self):
        from rcm_mc.data.cms_ma_enrollment import (
            parse_star_ratings_csv,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "stars.csv"
            _write_csv(csv_path, [
                "Contract ID",
                "Organization Marketing Name",
                "Contract Type",
                "Overall MA-PD Rating",
                "Part C Summary Rating",
                "Part D Summary Rating",
                "Number of Measures",
                "Prior Year Rating",
            ], [{
                "Contract ID": "H0028",
                "Organization Marketing Name": "Humana",
                "Contract Type": "MAPD",
                "Overall MA-PD Rating": "4.5",
                "Part C Summary Rating": "4.5",
                "Part D Summary Rating": "4.0",
                "Number of Measures": "39",
                "Prior Year Rating": "4.0",
            }])
            recs = list(parse_star_ratings_csv(
                csv_path, year=2025))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.contract_id, "H0028")
            self.assertAlmostEqual(r.overall_star_rating, 4.5)
            self.assertAlmostEqual(r.prior_year_overall, 4.0)
            self.assertEqual(r.measure_count, 39)
        finally:
            tmp.cleanup()


class TestBenchmarksParser(unittest.TestCase):
    def test_ratebook_columns(self):
        from rcm_mc.data.cms_ma_enrollment import (
            parse_ma_benchmarks_csv,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "bench.csv"
            _write_csv(csv_path, [
                "FIPS", "State", "County",
                "FFS Baseline", "Aged Benchmark",
                "Disabled Benchmark",
                "Aged Benchmark with QBP",
                "Quartile", "YoY Change",
            ], [{
                "FIPS": "12086", "State": "FL",
                "County": "Miami-Dade",
                "FFS Baseline": "$1,142.50",
                "Aged Benchmark": "$1,256.75",
                "Disabled Benchmark": "$1,180.00",
                "Aged Benchmark with QBP": "$1,319.59",
                "Quartile": "4",
                "YoY Change": "-1.12%",
            }])
            recs = list(parse_ma_benchmarks_csv(
                csv_path, year=2025))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.county_fips, "12086")
            self.assertAlmostEqual(r.ffs_baseline, 1142.5)
            self.assertAlmostEqual(r.benchmark_aged, 1256.75)
            self.assertAlmostEqual(
                r.benchmark_aged_qbp, 1319.59)
            self.assertEqual(r.quartile, 4)
            self.assertAlmostEqual(r.yoy_change_pct, -1.12)
        finally:
            tmp.cleanup()


class TestEnrollmentRoundTrip(unittest.TestCase):
    def test_load_and_county_penetration(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_ma_enrollment import (
            MAEnrollmentRecord,
            load_ma_enrollment,
            compute_county_ma_penetration,
            list_top_ma_penetration_counties,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            recs = [
                MAEnrollmentRecord(
                    contract_id="H0028", plan_id="001",
                    county_fips="12086",
                    year_month="2024-03",
                    state="FL", county_name="Miami-Dade",
                    enrollment=45200),
                MAEnrollmentRecord(
                    contract_id="H1036", plan_id="001",
                    county_fips="12086",
                    year_month="2024-03",
                    state="FL", county_name="Miami-Dade",
                    enrollment=22800),
                MAEnrollmentRecord(
                    contract_id="H0028", plan_id="001",
                    county_fips="13089",
                    year_month="2024-03",
                    state="GA", county_name="DeKalb",
                    enrollment=12500),
            ]
            n = load_ma_enrollment(store, recs)
            self.assertEqual(n, 3)

            # County aggregates across contracts
            row = compute_county_ma_penetration(
                store, "12086")
            self.assertEqual(row["total_enrollment"], 68000)
            self.assertEqual(row["n_contracts"], 2)

            # With Medicare-eligible pop → penetration %
            row = compute_county_ma_penetration(
                store, "12086",
                medicare_eligible_pop=100_000)
            self.assertAlmostEqual(
                row["ma_penetration_pct"], 0.68)

            # State filter on top counties
            fl = list_top_ma_penetration_counties(
                store, state="FL")
            self.assertEqual(
                [r["county_fips"] for r in fl], ["12086"])
            self.assertEqual(
                fl[0]["total_enrollment"], 68000)
        finally:
            tmp.cleanup()


class TestStarsRoundTrip(unittest.TestCase):
    def test_qbp_flag_and_change(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_ma_enrollment import (
            StarRatingRecord,
            load_star_ratings,
            get_contract_quality,
            list_qbp_eligible_contracts,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_star_ratings(store, [
                StarRatingRecord(
                    contract_id="H0028", year=2025,
                    organization_name="Humana",
                    overall_star_rating=4.5,
                    prior_year_overall=4.0),
                StarRatingRecord(
                    contract_id="H1036", year=2025,
                    organization_name="Aetna",
                    overall_star_rating=3.5,
                    prior_year_overall=4.0),
                StarRatingRecord(
                    contract_id="H2222", year=2025,
                    organization_name="UnitedHealthcare",
                    overall_star_rating=4.0,
                    prior_year_overall=4.0),
            ])

            # Contract lookup with QBP flag + YoY change
            row = get_contract_quality(store, "H0028")
            self.assertTrue(row["qbp_eligible"])
            self.assertAlmostEqual(row["star_change"], 0.5)

            row = get_contract_quality(store, "H1036")
            self.assertFalse(row["qbp_eligible"])
            self.assertAlmostEqual(row["star_change"], -0.5)

            # 4.0 is the threshold (>=)
            row = get_contract_quality(store, "H2222")
            self.assertTrue(row["qbp_eligible"])

            # QBP-eligible list (>=4.0 by default)
            qbp = list_qbp_eligible_contracts(store)
            ids = [r["contract_id"] for r in qbp]
            self.assertIn("H0028", ids)
            self.assertIn("H2222", ids)
            self.assertNotIn("H1036", ids)

            # Sensitivity to higher threshold
            high = list_qbp_eligible_contracts(
                store, min_rating=4.5)
            self.assertEqual(
                [r["contract_id"] for r in high], ["H0028"])
        finally:
            tmp.cleanup()


class TestBenchmarksRoundTrip(unittest.TestCase):
    def test_county_lookup_most_recent_year(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_ma_enrollment import (
            BenchmarkRecord,
            load_ma_benchmarks,
            get_county_benchmark,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_ma_benchmarks(store, [
                BenchmarkRecord(
                    county_fips="12086", year=2024,
                    state="FL", benchmark_aged=1245.0),
                BenchmarkRecord(
                    county_fips="12086", year=2025,
                    state="FL", benchmark_aged=1256.75,
                    quartile=4,
                    yoy_change_pct=0.94),
            ])
            row = get_county_benchmark(store, "12086")
            self.assertEqual(row["year"], 2025)
            self.assertAlmostEqual(
                row["benchmark_aged"], 1256.75)
            self.assertEqual(row["quartile"], 4)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
