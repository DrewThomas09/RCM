"""Tests for CDC PLACES + NVSS county health ingestion."""
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


class TestPlacesParser(unittest.TestCase):
    def test_wide_form_friendly_columns(self):
        from rcm_mc.data.cdc_places import parse_places_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "places.csv"
            _write_csv(csv_path, [
                "county_fips", "year", "county_name", "state",
                "population", "diabetes_pct", "copd_pct",
                "obesity_pct", "smoking_pct",
                "no_health_insurance_pct",
            ], [{
                "county_fips": "13089",
                "year": "2023",
                "county_name": "DeKalb",
                "state": "GA",
                "population": "760000",
                "diabetes_pct": "12.5",
                "copd_pct": "5.8",
                "obesity_pct": "32.1",
                "smoking_pct": "13.2",
                "no_health_insurance_pct": "11.5",
            }])
            recs = list(parse_places_csv(csv_path))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.county_fips, "13089")
            self.assertEqual(r.state, "GA")
            self.assertAlmostEqual(r.diabetes_pct, 12.5)
            self.assertAlmostEqual(r.smoking_pct, 13.2)
        finally:
            tmp.cleanup()

    def test_long_form_measure_id_aggregates(self):
        """PLACES API export: one row per (county × measure)."""
        from rcm_mc.data.cdc_places import parse_places_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "places_long.csv"
            _write_csv(csv_path, [
                "LocationID", "LocationName", "StateAbbr",
                "MeasureId", "Data_Value", "Year",
            ], [
                {"LocationID": "13089",
                 "LocationName": "DeKalb",
                 "StateAbbr": "GA",
                 "MeasureId": "DIABETES",
                 "Data_Value": "12.5",
                 "Year": "2023"},
                {"LocationID": "13089",
                 "LocationName": "DeKalb",
                 "StateAbbr": "GA",
                 "MeasureId": "COPD",
                 "Data_Value": "5.8",
                 "Year": "2023"},
                {"LocationID": "13089",
                 "LocationName": "DeKalb",
                 "StateAbbr": "GA",
                 "MeasureId": "CSMOKING",
                 "Data_Value": "13.2",
                 "Year": "2023"},
            ])
            recs = list(parse_places_csv(csv_path))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.county_fips, "13089")
            self.assertAlmostEqual(r.diabetes_pct, 12.5)
            self.assertAlmostEqual(r.copd_pct, 5.8)
            self.assertAlmostEqual(r.smoking_pct, 13.2)
        finally:
            tmp.cleanup()

    def test_fips_zero_padded(self):
        """Numeric FIPS without leading zero (1001 → 01001)."""
        from rcm_mc.data.cdc_places import parse_places_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "places.csv"
            _write_csv(csv_path, [
                "county_fips", "diabetes_pct",
            ], [{"county_fips": "1001",
                 "diabetes_pct": "10"}])
            recs = list(parse_places_csv(csv_path))
            self.assertEqual(recs[0].county_fips, "01001")
        finally:
            tmp.cleanup()

    def test_suppressed_values_become_none(self):
        from rcm_mc.data.cdc_places import parse_places_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "places.csv"
            _write_csv(csv_path, [
                "county_fips", "diabetes_pct", "copd_pct",
            ], [{"county_fips": "13089",
                 "diabetes_pct": "Suppressed",
                 "copd_pct": "*"}])
            recs = list(parse_places_csv(csv_path))
            self.assertIsNone(recs[0].diabetes_pct)
            self.assertIsNone(recs[0].copd_pct)
        finally:
            tmp.cleanup()


class TestNVSSParser(unittest.TestCase):
    def test_aggregates_causes_per_county(self):
        from rcm_mc.data.cdc_places import parse_nvss_mortality_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "nvss.csv"
            _write_csv(csv_path, [
                "County Code", "County", "State",
                "Cause", "Age Adjusted Rate",
            ], [
                {"County Code": "13089", "County": "DeKalb",
                 "State": "GA", "Cause": "All Causes",
                 "Age Adjusted Rate": "780.5"},
                {"County Code": "13089", "County": "DeKalb",
                 "State": "GA", "Cause": "Heart Disease",
                 "Age Adjusted Rate": "165.2"},
                {"County Code": "13089", "County": "DeKalb",
                 "State": "GA", "Cause": "Cancer",
                 "Age Adjusted Rate": "145.8"},
                {"County Code": "13089", "County": "DeKalb",
                 "State": "GA", "Cause": "Drug Overdose",
                 "Age Adjusted Rate": "32.4"},
            ])
            recs = list(parse_nvss_mortality_csv(csv_path,
                                                 year=2023))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.county_fips, "13089")
            self.assertAlmostEqual(r.all_cause_mortality, 780.5)
            self.assertAlmostEqual(
                r.heart_disease_mortality, 165.2)
            self.assertAlmostEqual(r.cancer_mortality, 145.8)
            self.assertAlmostEqual(
                r.drug_overdose_mortality, 32.4)
        finally:
            tmp.cleanup()


class TestBurdenScore(unittest.TestCase):
    def test_high_burden_county(self):
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics,
            compute_health_burden_score,
        )
        s = CountyHealthStatistics(
            county_fips="51001", year=2023,
            diabetes_pct=22.0, copd_pct=14.0,
            chd_pct=12.0, stroke_pct=6.0,
            obesity_pct=42.0, smoking_pct=28.0,
            physical_inactivity_pct=40.0,
            heart_disease_mortality=300.0,
            cancer_mortality=240.0,
            drug_overdose_mortality=80.0,
            no_health_insurance_pct=22.0,
        )
        score = compute_health_burden_score(s)
        self.assertGreater(score, 0.65)

    def test_low_burden_county(self):
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics,
            compute_health_burden_score,
        )
        s = CountyHealthStatistics(
            county_fips="06075", year=2023,  # SF
            diabetes_pct=6.0, copd_pct=3.0,
            chd_pct=4.0, stroke_pct=1.5,
            obesity_pct=18.0, smoking_pct=8.0,
            physical_inactivity_pct=12.0,
            heart_disease_mortality=110.0,
            cancer_mortality=125.0,
            drug_overdose_mortality=18.0,
            no_health_insurance_pct=4.0,
        )
        score = compute_health_burden_score(s)
        self.assertLess(score, 0.25)

    def test_partial_data_renormalizes(self):
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics,
            compute_health_burden_score,
        )
        s = CountyHealthStatistics(
            county_fips="11111", year=2023,
            # Only diabetes + smoking
            diabetes_pct=20.0, smoking_pct=30.0,
        )
        score = compute_health_burden_score(s)
        self.assertGreater(score, 0.45)
        self.assertLessEqual(score, 1.0)

    def test_no_data_returns_zero(self):
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics,
            compute_health_burden_score,
        )
        s = CountyHealthStatistics(county_fips="00000", year=2023)
        self.assertEqual(compute_health_burden_score(s), 0.0)


class TestRoundTrip(unittest.TestCase):
    def test_load_lookup_and_rank(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics,
            load_cdc_places,
            get_health_stats_for_county,
            list_high_burden_counties,
            list_counties_by_condition,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            recs = [
                CountyHealthStatistics(
                    county_fips="13089", year=2022,
                    state="GA", diabetes_pct=11.0,
                    smoking_pct=14.0,
                    heart_disease_mortality=160.0),
                CountyHealthStatistics(
                    county_fips="13089", year=2023,
                    state="GA", diabetes_pct=12.5,
                    smoking_pct=13.2,
                    heart_disease_mortality=158.0),
                CountyHealthStatistics(
                    county_fips="51001", year=2023,
                    state="VA", diabetes_pct=22.0,
                    smoking_pct=28.0,
                    heart_disease_mortality=290.0),
            ]
            n = load_cdc_places(store, recs)
            self.assertEqual(n, 3)

            # Default → most recent year
            row = get_health_stats_for_county(store, "13089")
            self.assertEqual(row["year"], 2023)
            self.assertAlmostEqual(row["diabetes_pct"], 12.5)
            self.assertIsNotNone(row["health_burden_score"])

            # FIPS zero-padding on lookup
            row_padded = get_health_stats_for_county(
                store, "13089")
            self.assertIsNotNone(row_padded)

            # High burden ranking
            top = list_high_burden_counties(store)
            # 51001 has heavier metrics → top
            self.assertEqual(top[0]["county_fips"], "51001")

            # State filter on burden ranking
            ga = list_high_burden_counties(store, state="GA")
            self.assertTrue(all(
                r["state"] == "GA" for r in ga))

            # Condition-specific ranking
            top_diabetes = list_counties_by_condition(
                store, "diabetes_pct")
            self.assertEqual(
                top_diabetes[0]["county_fips"], "51001")
        finally:
            tmp.cleanup()

    def test_unknown_condition_field_rejected(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cdc_places import (
            list_counties_by_condition,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            with self.assertRaises(ValueError):
                list_counties_by_condition(
                    store, "drop_table_pct")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
