import unittest

from ..connector import FetchResult
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import CensusAcsStore
from .fakes import COUNTY_DETAIL, COUNTY_SUBJECT, STATE_DETAIL, STATE_SUBJECT


def _county_rows(year=2023):
    fetched = FetchResult(detail=COUNTY_DETAIL, subject=COUNTY_SUBJECT,
                          endpoint="county_profile", year=year)
    return normalize(get_endpoint("county_profile"), fetched
                     ).rows["census_acs_county"]


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = CensusAcsStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent(self):
        rows = _county_rows()
        self.store.upsert("census_acs_county", rows)
        self.store.upsert("census_acs_county", rows)   # re-run
        self.assertEqual(self.store.count("census_acs_county"), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        rows = _county_rows()
        self.store.upsert("census_acs_county", rows)
        revised = [dict(r, total_pop="9999999") if r["fips5"] == "48201" else r
                   for r in rows]
        self.store.upsert("census_acs_county", revised)
        self.assertEqual(self.store.count("census_acs_county"), 3)
        got = self.store.fetchall(
            "SELECT total_pop FROM census_acs_county WHERE county_key = ?",
            ("48201:2023",))[0]
        self.assertEqual(got["total_pop"], "9999999")

    def test_vintages_coexist_under_distinct_keys(self):
        self.store.upsert("census_acs_county", _county_rows(2023))
        self.store.upsert("census_acs_county", _county_rows(2022))
        self.assertEqual(self.store.count("census_acs_county"), 6)
        self.assertEqual(
            self.store.count("census_acs_county", "year = ?", ("2022",)), 3)

    def test_jam_value_lands_as_null(self):
        self.store.upsert("census_acs_county", _county_rows())
        got = self.store.fetchall(
            "SELECT median_hh_income FROM census_acs_county "
            "WHERE county_key = ?", ("48301:2023",))[0]
        self.assertIsNone(got["median_hh_income"])

    def test_state_upsert_and_meta_columns(self):
        fetched = FetchResult(detail=STATE_DETAIL, subject=STATE_SUBJECT,
                              endpoint="state_profile", year=2023)
        rows = normalize(get_endpoint("state_profile"), fetched
                         ).rows["census_acs_state"]
        self.store.upsert("census_acs_state", rows)
        got = self.store.fetchall(
            "SELECT * FROM census_acs_state WHERE state_key = ?", ("48:2023",))[0]
        self.assertEqual(got["source_endpoint"], "state_profile")
        self.assertIsNotNone(got["ingested_at"])       # meta stamped on write


if __name__ == "__main__":
    unittest.main()
