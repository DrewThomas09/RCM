import unittest

from ..normalize import normalize_generic
from ..query import QueryError, aggregate, query
from ..tables import CdcDataStore


def _places(state, fips, measure, dvt, value, name="County"):
    return {"record_key": f"{state}:{fips}:{measure}:{dvt}",
            "year": "2023", "stateabbr": state, "locationname": name,
            "locationid": fips, "measureid": measure, "datavaluetypeid": dvt,
            "data_value": value, "categoryid": "HLTHOUT",
            "source_endpoint": "places_county"}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = CdcDataStore(":memory:")
        self.store.upsert("cdc_places_county", [
            _places("AL", "01073", "CSMOKING", "CrdPrv", "17.4", "Jefferson"),
            _places("AL", "01073", "ARTHRITIS", "CrdPrv", "25.0", "Jefferson"),
            _places("AR", "05043", "ARTHRITIS", "CrdPrv", "29.9", "Drew"),
            _places("AR", "05043", "ARTHRITIS", "AgeAdjPrv", "27.1", "Drew"),
        ])
        # Two different generic pulls sharing cdc_data_rows.
        self.store.upsert("cdc_data_rows",
                          normalize_generic("aaaa-1111", [{"x": 1}, {"x": 2}]))
        self.store.upsert("cdc_data_rows",
                          normalize_generic("bbbb-2222", [{"y": 9}]))

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "cdc_data_places_county",
                    filters={"stateabbr": "AR"})
        self.assertEqual(res.total, 2)
        self.assertTrue(all(r["stateabbr"] == "AR" for r in res.rows))

    def test_like_and_sort_and_select(self):
        res = query(self.store, "cdc_data_places_county",
                    filters={"measureid__like": "%ARTH%"},
                    select=["record_key", "data_value"],
                    sort=["-data_value"])
        self.assertEqual(res.total, 3)
        self.assertEqual(list(res.rows[0].keys()), ["record_key", "data_value"])
        self.assertEqual(res.rows[0]["data_value"], "29.9")

    def test_in_filter(self):
        res = query(self.store, "cdc_data_places_county",
                    filters={"measureid__in": ["CSMOKING"]})
        self.assertEqual(res.total, 1)

    def test_between_filter(self):
        res = query(self.store, "cdc_data_places_county",
                    filters={"data_value__between": "20,28"})
        self.assertEqual(res.total, 2)   # 25.0 and 27.1

    def test_generic_rows_sliced_by_dataset_key_not_pinned(self):
        # source_filter is "" for fetched_rows: both pulls visible, then
        # the caller slices by dataset_key.
        res = query(self.store, "cdc_data_fetched_rows")
        self.assertEqual(res.total, 3)
        res2 = query(self.store, "cdc_data_fetched_rows",
                     filters={"dataset_key": "aaaa-1111"})
        self.assertEqual(res2.total, 2)
        res3 = query(self.store, "cdc_data_fetched_rows",
                     filters={"row_json__like": '%"y": 9%'})
        self.assertEqual(res3.total, 1)

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "cdc_data_places_county",
                        group_by=["measureid"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"measureid": "ARTHRITIS", "count": 3})

    def test_aggregate_with_filter(self):
        res = aggregate(self.store, "cdc_data_places_county",
                        group_by=["stateabbr"],
                        filters={"datavaluetypeid": "CrdPrv"})
        rows = {r["stateabbr"]: r["count"] for r in res.rows}
        self.assertEqual(rows, {"AL": 2, "AR": 1})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cdc_data_places_county", filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cdc_data_does_not_exist")

    def test_unknown_sort_and_group_by_raise(self):
        with self.assertRaises(QueryError):
            query(self.store, "cdc_data_places_county", sort=["-nope"])
        with self.assertRaises(QueryError):
            aggregate(self.store, "cdc_data_places_county", group_by=["nope"])

    def test_limit_is_clamped(self):
        res = query(self.store, "cdc_data_places_county", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "cdc_data_places_county", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
