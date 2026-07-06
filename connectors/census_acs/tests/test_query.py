import unittest

from ..query import QueryError, aggregate, query
from ..tables import CensusAcsStore


def _county(fips5, name, year="2023", pop="1000", income="50000",
            uninsured="10.0"):
    return {"county_key": f"{fips5}:{year}", "fips5": fips5,
            "state_fips": fips5[:2], "county_fips": fips5[2:], "name": name,
            "year": year, "total_pop": pop, "median_age": "35.0",
            "median_hh_income": income, "poverty_count": "100",
            "pop_65_plus": "200", "uninsured_rate": uninsured,
            "source_endpoint": "county_profile"}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = CensusAcsStore(":memory:")
        self.store.upsert("census_acs_county", [
            _county("48201", "Harris County, Texas", pop="4835125",
                    income="70789", uninsured="21.5"),
            _county("48453", "Travis County, Texas", pop="1334196",
                    income="97600", uninsured="12.4"),
            _county("06037", "Los Angeles County, California", pop="9848406",
                    income="83411", uninsured="9.1"),
            _county("48201", "Harris County, Texas", year="2022",
                    pop="4800000"),
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "census_acs_county_profile",
                    filters={"state_fips": "06"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["fips5"], "06037")

    def test_source_endpoint_slice_is_pinned(self):
        # A stray row with a foreign source_endpoint must not surface.
        self.store.upsert("census_acs_county", [
            dict(_county("99999", "Bogus"), source_endpoint="other_thing")])
        res = query(self.store, "census_acs_county_profile")
        self.assertEqual(res.total, 4)
        self.assertTrue(all(r["source_endpoint"] == "county_profile"
                            for r in res.rows))

    def test_like_and_in_filters(self):
        res = query(self.store, "census_acs_county_profile",
                    filters={"name__like": "%Texas%", "year": "2023"})
        self.assertEqual(res.total, 2)
        res2 = query(self.store, "census_acs_county_profile",
                     filters={"fips5__in": ["48201", "06037"],
                              "year": "2023"})
        self.assertEqual(res2.total, 2)

    def test_sort_select_and_offset(self):
        res = query(self.store, "census_acs_county_profile",
                    filters={"year": "2023"},
                    select=["fips5", "name"], sort=["-fips5"],
                    limit=2, offset=1)
        self.assertEqual([r["fips5"] for r in res.rows], ["48201", "06037"])
        self.assertEqual(set(res.rows[0]), {"fips5", "name"})

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "census_acs_county_profile",
                        group_by=["state_fips"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"state_fips": "48", "count": 3})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "census_acs_county_profile",
                  filters={"nope": "x"})
        with self.assertRaises(QueryError):
            query(self.store, "census_acs_county_profile", sort=["-nope"])
        with self.assertRaises(QueryError):
            aggregate(self.store, "census_acs_county_profile",
                      group_by=["nope"])

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "census_acs_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "census_acs_county_profile", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "census_acs_county_profile", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
