"""Tests for multi-year HCRIS: get_trend + year-aware lookup + latest-per-CCN."""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.hcris import (
    _clear_cache,
    _get_latest_per_ccn,
    available_fiscal_years,
    browse_by_state,
    find_peers,
    get_trend,
    load_hcris,
    lookup_by_ccn,
    lookup_by_name,
)


class TestShippedDatasetIsMultiYear(unittest.TestCase):
    def setUp(self):
        _clear_cache()

    def test_shipped_has_at_least_two_fiscal_years(self):
        years = available_fiscal_years()
        self.assertGreaterEqual(len(years), 2,
                                msg=f"Shipped dataset must carry multi-year data; got {years}")
        # Years should be recent + in ascending order
        self.assertEqual(years, sorted(years))

    def test_one_row_per_ccn_per_year(self):
        df = load_hcris()
        dup_count = df.duplicated(subset=["ccn", "fiscal_year"]).sum()
        self.assertEqual(dup_count, 0, msg=f"{dup_count} duplicate (ccn, fy) rows")


class TestLookupByCCNYearAware(unittest.TestCase):
    def setUp(self):
        _clear_cache()

    def test_default_returns_latest_year(self):
        row = lookup_by_ccn("360180")
        self.assertIsNotNone(row)
        years = available_fiscal_years()
        self.assertEqual(int(row["fiscal_year"]), years[-1])

    def test_explicit_year_selects_that_filing(self):
        years = available_fiscal_years()
        if len(years) < 2:
            self.skipTest("Need ≥2 years to test per-year lookup")
        earlier = years[0]
        row = lookup_by_ccn("360180", year=earlier)
        self.assertIsNotNone(row)
        self.assertEqual(int(row["fiscal_year"]), earlier)

    def test_missing_year_returns_none(self):
        self.assertIsNone(lookup_by_ccn("360180", year=1999))

    def test_unknown_ccn_with_year_returns_none(self):
        self.assertIsNone(lookup_by_ccn("999999", year=2022))


class TestGetTrend(unittest.TestCase):
    def setUp(self):
        _clear_cache()

    def test_returns_dataframe_with_expected_columns(self):
        df = get_trend("360180")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("ccn", df.columns)
        self.assertIn("fiscal_year", df.columns)
        self.assertIn("net_patient_revenue", df.columns)

    def test_returns_one_row_per_fiscal_year(self):
        df = get_trend("360180")
        years = available_fiscal_years()
        self.assertEqual(len(df), len(years))
        # Already sorted by fiscal year
        self.assertEqual(list(df["fiscal_year"]), sorted(df["fiscal_year"]))

    def test_custom_metrics_subset_honored(self):
        df = get_trend("360180", metrics=["beds"])
        self.assertIn("beds", df.columns)
        self.assertNotIn("net_patient_revenue", df.columns)

    def test_unknown_ccn_returns_empty_frame(self):
        df = get_trend("999999")
        self.assertTrue(df.empty)

    def test_handles_non_string_input_gracefully(self):
        self.assertTrue(get_trend(None).empty)  # type: ignore[arg-type]
        self.assertTrue(get_trend("").empty)

    def test_ccn_leading_zero_normalization(self):
        """get_trend should accept short CCNs ('50108') same way lookup does."""
        normalized = get_trend("50108")
        not_normalized = get_trend("050108")
        # Either both empty (CCN absent) or equal length
        self.assertEqual(len(normalized), len(not_normalized))


class TestLatestPerCCNDeduplication(unittest.TestCase):
    """Name search / state browse / peer matching must not show dupes from multi-year data."""

    def setUp(self):
        _clear_cache()

    def test_latest_per_ccn_is_unique(self):
        df = _get_latest_per_ccn()
        self.assertEqual(df["ccn"].duplicated().sum(), 0)

    def test_lookup_by_name_no_dupes_across_years(self):
        results = lookup_by_name("CLEVELAND CLINIC HOSPITAL", limit=20)
        # "CLEVELAND CLINIC HOSPITAL" (CCN 360180) should appear exactly once
        ccn_matches = [r for r in results if r["ccn"] == "360180"]
        self.assertEqual(len(ccn_matches), 1)

    def test_browse_by_state_no_dupes_across_years(self):
        rows = browse_by_state("OH", limit=100)
        ccns = [r["ccn"] for r in rows]
        self.assertEqual(len(ccns), len(set(ccns)))

    def test_find_peers_uses_latest_year(self):
        peers = find_peers("360180", n=10)
        # All peers should be in the latest fiscal year
        latest_year = available_fiscal_years()[-1]
        self.assertTrue(all(int(y) == latest_year for y in peers["fiscal_year"]))


class TestAvailableFiscalYears(unittest.TestCase):
    def test_returns_sorted_list(self):
        years = available_fiscal_years()
        self.assertEqual(years, sorted(years))

    def test_all_years_are_ints(self):
        for y in available_fiscal_years():
            self.assertIsInstance(y, int)
