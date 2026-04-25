"""Tests for US Census ACS demographic ingestion."""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path


class TestACSParser(unittest.TestCase):
    def test_friendly_column_names(self):
        from rcm_mc.data.census_demographics import parse_acs_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "acs.csv"
            with csv_path.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=[
                    "cbsa", "year", "geography_name", "state",
                    "population", "population_growth_5yr",
                    "pct_65_plus", "median_household_income",
                    "pct_uninsured", "poverty_rate",
                ])
                w.writeheader()
                w.writerow({
                    "cbsa": "12060", "year": "2023",
                    "geography_name": "Atlanta-Sandy Springs",
                    "state": "GA",
                    "population": "6300000",
                    "population_growth_5yr": "0.04",
                    "pct_65_plus": "0.14",
                    "median_household_income": "78000",
                    "pct_uninsured": "0.12",
                    "poverty_rate": "0.10",
                })
            recs = list(parse_acs_csv(csv_path))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.cbsa, "12060")
            self.assertEqual(r.year, 2023)
            self.assertEqual(r.state, "GA")
            self.assertEqual(r.population, 6_300_000)
            self.assertAlmostEqual(r.population_growth_5yr, 0.04)
        finally:
            tmp.cleanup()

    def test_acs_b_table_aliases(self):
        """B01003_001E (population), B19013_001E (median income)
        — the canonical ACS column names."""
        from rcm_mc.data.census_demographics import parse_acs_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "acs_btable.csv"
            with csv_path.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=[
                    "GEOID", "NAME", "State",
                    "B01003_001E", "B19013_001E",
                ])
                w.writeheader()
                w.writerow({
                    "GEOID": "33100",
                    "NAME": "Miami-Fort Lauderdale",
                    "State": "FL",
                    "B01003_001E": "6200000",
                    "B19013_001E": "65000",
                })
            recs = list(parse_acs_csv(csv_path, year=2023))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.cbsa, "33100")
            self.assertEqual(r.population, 6_200_000)
            self.assertEqual(r.median_household_income, 65000)
        finally:
            tmp.cleanup()

    def test_blank_rows_skipped(self):
        from rcm_mc.data.census_demographics import parse_acs_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "acs.csv"
            with csv_path.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["cbsa", "year"])
                w.writeheader()
                w.writerow({"cbsa": "", "year": "2023"})
                w.writerow({"cbsa": "12060", "year": "2023"})
            recs = list(parse_acs_csv(csv_path))
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0].cbsa, "12060")
        finally:
            tmp.cleanup()


class TestAttractivenessScore(unittest.TestCase):
    def test_high_attractiveness_market(self):
        """Strong growth + 65+ + income + low uninsured = high score."""
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            compute_market_attractiveness_score,
        )
        d = MarketDemographics(
            cbsa="33100", year=2023,
            population=6_000_000,
            population_growth_5yr=0.05,
            pct_65_plus=0.22,
            median_household_income=110_000,
            pct_uninsured=0.05,
            poverty_rate=0.07,
        )
        score = compute_market_attractiveness_score(d)
        self.assertGreater(score, 0.80)

    def test_low_attractiveness_market(self):
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            compute_market_attractiveness_score,
        )
        d = MarketDemographics(
            cbsa="00001", year=2023,
            population=80_000,
            population_growth_5yr=-0.02,
            pct_65_plus=0.10,
            median_household_income=32_000,
            pct_uninsured=0.18,
            poverty_rate=0.28,
        )
        score = compute_market_attractiveness_score(d)
        self.assertLess(score, 0.20)

    def test_partial_data_renormalizes(self):
        """When only a subset of metrics are present, the score
        should still be a defensible 0-1 (renormalized)."""
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            compute_market_attractiveness_score,
        )
        d = MarketDemographics(
            cbsa="11111", year=2023,
            # Only growth + income — should still produce a score
            population_growth_5yr=0.05,
            median_household_income=120_000,
        )
        score = compute_market_attractiveness_score(d)
        self.assertGreater(score, 0.95)
        self.assertLessEqual(score, 1.0)

    def test_no_data_returns_zero(self):
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            compute_market_attractiveness_score,
        )
        d = MarketDemographics(cbsa="00000", year=2023)
        self.assertEqual(
            compute_market_attractiveness_score(d), 0.0)


class TestRoundTrip(unittest.TestCase):
    def test_load_and_lookup(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            load_acs_demographics,
            get_demographics_for_cbsa,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            recs = [
                MarketDemographics(
                    cbsa="33100", year=2022,
                    geography_name="Miami",
                    state="FL", population=6_100_000,
                    population_growth_5yr=0.03,
                    pct_65_plus=0.20,
                    median_household_income=62_000,
                    pct_uninsured=0.10,
                    poverty_rate=0.13),
                MarketDemographics(
                    cbsa="33100", year=2023,
                    geography_name="Miami",
                    state="FL", population=6_200_000,
                    population_growth_5yr=0.04,
                    pct_65_plus=0.21,
                    median_household_income=65_000,
                    pct_uninsured=0.10,
                    poverty_rate=0.12),
            ]
            n = load_acs_demographics(store, recs)
            self.assertEqual(n, 2)

            # Default → most recent year (2023)
            row = get_demographics_for_cbsa(store, "33100")
            self.assertIsNotNone(row)
            self.assertEqual(row["year"], 2023)
            self.assertEqual(row["population"], 6_200_000)
            # attractiveness_score auto-computed on insert
            self.assertIsNotNone(row["attractiveness_score"])
            self.assertGreater(row["attractiveness_score"], 0.0)

            # Specified year override
            row22 = get_demographics_for_cbsa(
                store, "33100", year=2022)
            self.assertEqual(row22["year"], 2022)
        finally:
            tmp.cleanup()

    def test_top_growth_markets_filter_and_sort(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            load_acs_demographics,
            list_top_growth_markets,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa="A", year=2023, state="TX",
                    population=500_000,
                    population_growth_5yr=0.06),
                MarketDemographics(
                    cbsa="B", year=2023, state="TX",
                    population=300_000,
                    population_growth_5yr=0.03),
                MarketDemographics(
                    cbsa="C", year=2023, state="FL",
                    population=400_000,
                    population_growth_5yr=0.08),
                # Below min_population — should be excluded
                MarketDemographics(
                    cbsa="D", year=2023, state="TX",
                    population=50_000,
                    population_growth_5yr=0.10),
            ])

            # All states, default min_population=100K
            top = list_top_growth_markets(store, limit=10)
            cbsas = [r["cbsa"] for r in top]
            self.assertEqual(cbsas, ["C", "A", "B"])

            # Filter by state
            tx = list_top_growth_markets(store, state="TX")
            self.assertEqual(
                [r["cbsa"] for r in tx], ["A", "B"])
        finally:
            tmp.cleanup()

    def test_top_attractive_markets(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.census_demographics import (
            MarketDemographics,
            load_acs_demographics,
            list_top_attractive_markets,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa="A", year=2023, state="TX",
                    population=2_000_000,
                    population_growth_5yr=0.05,
                    pct_65_plus=0.20,
                    median_household_income=100_000,
                    pct_uninsured=0.05,
                    poverty_rate=0.08),
                MarketDemographics(
                    cbsa="B", year=2023, state="TX",
                    population=200_000,
                    population_growth_5yr=-0.01,
                    pct_65_plus=0.10,
                    median_household_income=40_000,
                    pct_uninsured=0.20,
                    poverty_rate=0.25),
            ])
            top = list_top_attractive_markets(store)
            self.assertEqual(top[0]["cbsa"], "A")
            self.assertGreater(
                top[0]["attractiveness_score"],
                top[1]["attractiveness_score"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
