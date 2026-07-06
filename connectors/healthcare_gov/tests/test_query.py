import unittest

from ..query import QueryError, aggregate, query
from ..tables import HealthcareGovStore


def _plan(planid, state, metal, market="Individual",
          source="plan_attributes_py2026"):
    return {"plan_key": f"{source}:2026:{planid}", "businessyear": "2026",
            "statecode": state, "planid": planid,
            "standardcomponentid": planid.split("-")[0],
            "metallevel": metal, "marketcoverage": market,
            "source_endpoint": source}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthcareGovStore(":memory:")
        self.store.upsert("healthcare_gov_plan_attributes", [
            _plan("21989AK0030001-00", "AK", "Low"),
            _plan("21989AK0030001-01", "AK", "Low"),
            _plan("33602TX0450002-04", "TX", "Silver"),
            # A hypothetical future PY sharing the table — must be sliced out.
            _plan("99999TX0450002-01", "TX", "Gold",
                  source="plan_attributes_py2027"),
        ])
        self.store.upsert("healthcare_gov_rows", [
            {"row_key": "e4rr-zk4i:1", "dataset_key": "e4rr-zk4i",
             "row_idx": "1", "row_json": '{"npn": "123"}',
             "source_endpoint": "e4rr-zk4i"},
            {"row_key": "other-id:1", "dataset_key": "other-id",
             "row_idx": "1", "row_json": '{"x": "y"}',
             "source_endpoint": "other-id"},
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "healthcare_gov_plan_attributes_py2026",
                    filters={"statecode": "TX"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["planid"], "33602TX0450002-04")

    def test_slice_excludes_other_endpoint(self):
        res = query(self.store, "healthcare_gov_plan_attributes_py2026")
        self.assertEqual(res.total, 3)   # the py2027 row is pinned out
        self.assertTrue(all(r["source_endpoint"] == "plan_attributes_py2026"
                            for r in res.rows))

    def test_like_and_in_filters(self):
        res = query(self.store, "healthcare_gov_plan_attributes_py2026",
                    filters={"planid__like": "21989%"})
        self.assertEqual(res.total, 2)
        res = query(self.store, "healthcare_gov_plan_attributes_py2026",
                    filters={"metallevel__in": ["Silver", "Gold"]})
        self.assertEqual(res.total, 1)   # Gold row belongs to the other slice

    def test_sort_and_select(self):
        res = query(self.store, "healthcare_gov_plan_attributes_py2026",
                    select=["planid", "metallevel"], sort=["-planid"])
        self.assertEqual(list(res.rows[0].keys()), ["planid", "metallevel"])
        self.assertEqual(res.rows[0]["planid"], "33602TX0450002-04")

    def test_generic_rows_have_no_pin_and_filter_by_dataset_key(self):
        res = query(self.store, "healthcare_gov_fetched_rows")
        self.assertEqual(res.total, 2)   # empty source_filter → whole table
        res = query(self.store, "healthcare_gov_fetched_rows",
                    filters={"dataset_key": "e4rr-zk4i",
                             "row_json__like": "%npn%"})
        self.assertEqual(res.total, 1)

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "healthcare_gov_plan_attributes_py2026",
                        group_by=["metallevel"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"metallevel": "Low", "count": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "healthcare_gov_plan_attributes_py2026",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "healthcare_gov_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "healthcare_gov_plan_attributes_py2026",
                    limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "healthcare_gov_plan_attributes_py2026",
                     limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
