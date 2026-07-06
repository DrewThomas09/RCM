import unittest

from ..normalize import normalize_generic
from ..query import QueryError, aggregate, query
from ..tables import HealthdataGovStore


def _ids_row(hhs_id, ccn, name, state, zip_code="35801"):
    return {"record_key": hhs_id, "hhs_id": hhs_id, "ccn": ccn,
            "facility_name": name, "state": state, "zip": zip_code,
            "source_endpoint": "hospital_ids"}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthdataGovStore(":memory:")
        self.store.upsert("hhs_hospital_ids", [
            _ids_row("C010039-A", "010039", "Huntsville Hospital", "AL"),
            _ids_row("C010039-C", "010039",
                     "Huntsville Hospital for Women & Children", "AL"),
            _ids_row("H450054", "450054",
                     "Ascension Seton Medical Center Austin", "TX", "78705"),
            _ids_row("H450213", "450213", "Midland Memorial Hospital", "TX",
                     "79701"),
        ])
        # Two different generic pulls sharing healthdata_gov_rows.
        self.store.upsert("healthdata_gov_rows",
                          normalize_generic("aaaa-1111", [{"x": 1}, {"x": 2}]))
        self.store.upsert("healthdata_gov_rows",
                          normalize_generic("bbbb-2222", [{"y": 9}]))

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "healthdata_gov_hospital_ids",
                    filters={"state": "TX"})
        self.assertEqual(res.total, 2)
        self.assertTrue(all(r["state"] == "TX" for r in res.rows))

    def test_like_and_sort_and_select(self):
        res = query(self.store, "healthdata_gov_hospital_ids",
                    filters={"facility_name__like": "%Huntsville%"},
                    select=["record_key", "facility_name"],
                    sort=["-facility_name"])
        self.assertEqual(res.total, 2)
        self.assertEqual(list(res.rows[0].keys()),
                         ["record_key", "facility_name"])
        self.assertEqual(res.rows[0]["facility_name"],
                         "Huntsville Hospital for Women & Children")

    def test_in_filter(self):
        res = query(self.store, "healthdata_gov_hospital_ids",
                    filters={"ccn__in": ["450054"]})
        self.assertEqual(res.total, 1)

    def test_between_filter(self):
        res = query(self.store, "healthdata_gov_hospital_ids",
                    filters={"zip__between": "70000,80000"})
        self.assertEqual(res.total, 2)   # 78705 and 79701

    def test_generic_rows_sliced_by_dataset_key_not_pinned(self):
        # source_filter is "" for fetched_rows: both pulls visible, then
        # the caller slices by dataset_key.
        res = query(self.store, "healthdata_gov_fetched_rows")
        self.assertEqual(res.total, 3)
        res2 = query(self.store, "healthdata_gov_fetched_rows",
                     filters={"dataset_key": "aaaa-1111"})
        self.assertEqual(res2.total, 2)
        res3 = query(self.store, "healthdata_gov_fetched_rows",
                     filters={"row_json__like": '%"y": 9%'})
        self.assertEqual(res3.total, 1)

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "healthdata_gov_hospital_ids",
                        group_by=["ccn"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"ccn": "010039", "count": 2})

    def test_aggregate_with_filter(self):
        res = aggregate(self.store, "healthdata_gov_hospital_ids",
                        group_by=["state"], filters={"zip__gte": "35801"})
        rows = {r["state"]: r["count"] for r in res.rows}
        self.assertEqual(rows, {"AL": 2, "TX": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "healthdata_gov_hospital_ids",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "healthdata_gov_does_not_exist")

    def test_unknown_sort_and_group_by_raise(self):
        with self.assertRaises(QueryError):
            query(self.store, "healthdata_gov_hospital_ids", sort=["-nope"])
        with self.assertRaises(QueryError):
            aggregate(self.store, "healthdata_gov_hospital_ids",
                      group_by=["nope"])

    def test_limit_is_clamped(self):
        res = query(self.store, "healthdata_gov_hospital_ids", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "healthdata_gov_hospital_ids", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
