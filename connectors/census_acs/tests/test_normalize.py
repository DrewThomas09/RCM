import unittest

from ..connector import FetchResult
from ..endpoints import get_endpoint
from ..normalize import clean_value, normalize, rows_from_table
from .fakes import (CBSA_DETAIL, CBSA_SUBJECT, COUNTY_DETAIL, COUNTY_SUBJECT,
                    STATE_DETAIL, STATE_SUBJECT)


def _fetched(spec_key, detail, subject, year=2023):
    return FetchResult(detail=detail, subject=subject,
                       endpoint=spec_key, year=year, requests=2)


class RowsFromTableTests(unittest.TestCase):
    def test_header_row_maps_to_declared_canonical_columns(self):
        rows, unmapped = rows_from_table(COUNTY_DETAIL)
        self.assertEqual(unmapped, [])                  # every header declared
        harris = rows[0]
        self.assertEqual(harris["name"], "Harris County, Texas")
        self.assertEqual(harris["total_pop"], "4835125")
        self.assertEqual(harris["median_age"], "34.4")
        self.assertEqual(harris["median_hh_income"], "70789")
        self.assertEqual(harris["poverty_count"], "770564")
        self.assertEqual(harris["state_fips"], "48")
        self.assertEqual(harris["county_fips"], "201")

    def test_unknown_headers_kept_verbatim_and_reported(self):
        table = [["NAME", "B99999_001E", "state"], ["Texas", "1", "48"]]
        rows, unmapped = rows_from_table(table)
        self.assertEqual(unmapped, ["B99999_001E"])
        self.assertEqual(rows[0]["B99999_001E"], "1")   # kept, not dropped

    def test_short_and_empty_tables_are_defensive(self):
        self.assertEqual(rows_from_table([]), ([], []))
        rows, _ = rows_from_table([["NAME", "state"], ["Texas"]])
        self.assertIsNone(rows[0]["state_fips"])        # missing cell → None

    def test_jam_values_become_none(self):
        for jam in ("-666666666", "-999999999", "-888888888", "-222222222"):
            self.assertIsNone(clean_value(jam))
        self.assertEqual(clean_value("-42"), "-42")     # real negatives survive
        self.assertEqual(clean_value("34.4"), "34.4")
        self.assertIsNone(clean_value(""))
        self.assertIsNone(clean_value(None))


class NormalizeTests(unittest.TestCase):
    def test_county_join_composes_key_and_fips5(self):
        res = normalize(get_endpoint("county_profile"),
                        _fetched("county_profile", COUNTY_DETAIL, COUNTY_SUBJECT))
        rows = res.rows["census_acs_county"]
        self.assertEqual(len(rows), 3)
        harris = next(r for r in rows if r["county_fips"] == "201")
        self.assertEqual(harris["county_key"], "48201:2023")
        self.assertEqual(harris["fips5"], "48201")
        self.assertEqual(harris["year"], "2023")
        # Subject columns joined on (state, county):
        self.assertEqual(harris["pop_65_plus"], "555417")
        self.assertEqual(harris["uninsured_rate"], "21.5")
        self.assertEqual(harris["source_endpoint"], "county_profile")

    def test_missing_subject_row_leaves_none(self):
        res = normalize(get_endpoint("county_profile"),
                        _fetched("county_profile", COUNTY_DETAIL, COUNTY_SUBJECT))
        loving = next(r for r in res.rows["census_acs_county"]
                      if r["county_fips"] == "301")
        self.assertIsNone(loving["pop_65_plus"])        # absent from subject
        self.assertIsNone(loving["uninsured_rate"])
        self.assertIsNone(loving["median_hh_income"])   # jam value collapsed
        self.assertEqual(loving["total_pop"], "43")

    def test_state_profile_key(self):
        res = normalize(get_endpoint("state_profile"),
                        _fetched("state_profile", STATE_DETAIL, STATE_SUBJECT))
        rows = res.rows["census_acs_state"]
        texas = next(r for r in rows if r["state_fips"] == "48")
        self.assertEqual(texas["state_key"], "48:2023")
        self.assertEqual(texas["total_pop"], "29243342")
        self.assertEqual(texas["uninsured_rate"], "16.6")

    def test_cbsa_profile_key(self):
        res = normalize(get_endpoint("cbsa_profile"),
                        _fetched("cbsa_profile", CBSA_DETAIL, CBSA_SUBJECT))
        rows = res.rows["census_acs_cbsa"]
        houston = next(r for r in rows if r["cbsa_code"] == "26420")
        self.assertEqual(houston["cbsa_key"], "26420:2023")
        self.assertEqual(houston["pop_65_plus"], "801245")

    def test_empty_payloads_produce_no_rows(self):
        res = normalize(get_endpoint("county_profile"),
                        _fetched("county_profile", [], []))
        self.assertEqual(res.rows, {})


if __name__ == "__main__":
    unittest.main()
