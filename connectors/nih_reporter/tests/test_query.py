import unittest

from ..query import QueryError, aggregate, query
from ..tables import NihReporterStore


def _project(appl_id, org_state, fiscal_year, award, title="T",
             org_name="UNIV"):
    return {"appl_id": appl_id, "project_num": f"5R01AA{appl_id:06d}-01",
            "core_project_num": f"R01AA{appl_id:06d}",
            "fiscal_year": str(fiscal_year), "project_title": title,
            "org_state": org_state, "org_name": org_name,
            "award_amount": str(award), "source_endpoint": "projects"}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = NihReporterStore(":memory:")
        self.store.upsert("nih_projects", [
            _project(1, "TX", 2025, 100000, title="Cancer immunotherapy"),
            _project(2, "TX", 2024, 250000, title="Cardiology outcomes"),
            _project(3, "CA", 2025, 500000, title="Cancer genomics"),
        ])
        self.store.upsert("nih_publications", [
            {"pub_key": "111:1", "pmid": "111", "appl_id": "1",
             "core_project_num": "R01AA000001",
             "source_endpoint": "publications"},
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "nih_reporter_projects",
                    filters={"org_state": "CA"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["appl_id"], "3")

    def test_like_filter(self):
        res = query(self.store, "nih_reporter_projects",
                    filters={"project_title__like": "%Cancer%"})
        self.assertEqual(res.total, 2)

    def test_in_filter(self):
        res = query(self.store, "nih_reporter_projects",
                    filters={"appl_id__in": ["1", "3"]})
        self.assertEqual(res.total, 2)

    def test_gte_filter_and_sort_desc(self):
        res = query(self.store, "nih_reporter_projects",
                    filters={"fiscal_year__gte": "2025"},
                    sort=["-award_amount"])
        self.assertEqual(res.total, 2)
        self.assertEqual(res.rows[0]["appl_id"], "3")

    def test_select_projection(self):
        res = query(self.store, "nih_reporter_projects",
                    select=["appl_id", "org_state"])
        self.assertEqual(set(res.rows[0].keys()), {"appl_id", "org_state"})

    def test_publications_dataset_queryable(self):
        res = query(self.store, "nih_reporter_publications",
                    filters={"pmid": "111"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["pub_key"], "111:1")

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "nih_reporter_projects",
                        group_by=["org_state"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"org_state": "TX", "count": 2})

    def test_aggregate_with_filter(self):
        res = aggregate(self.store, "nih_reporter_projects",
                        group_by=["org_state"],
                        filters={"fiscal_year": "2025"})
        rows = {r["org_state"]: r["count"] for r in res.rows}
        self.assertEqual(rows, {"TX": 1, "CA": 1})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "nih_reporter_projects", filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "nih_reporter_does_not_exist")

    def test_unknown_sort_and_group_by_raise(self):
        with self.assertRaises(QueryError):
            query(self.store, "nih_reporter_projects", sort=["-nope"])
        with self.assertRaises(QueryError):
            aggregate(self.store, "nih_reporter_projects", group_by=["nope"])

    def test_limit_is_clamped(self):
        res = query(self.store, "nih_reporter_projects", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "nih_reporter_projects", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
