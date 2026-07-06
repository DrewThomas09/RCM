import unittest

from ..query import QueryError, aggregate, query
from ..registry import dataset_ids
from ..tables import ProviderDataStore


def _hospital(fid, state, rating):
    return {"record_key": fid, "facility_id": fid,
            "facility_name": f"HOSP {fid}", "state": state,
            "hospital_overall_rating": rating,
            "source_endpoint": "hospital_general"}


def _generic(dataset_key, idx, payload):
    return {"row_key": f"{dataset_key}:{idx}", "dataset_key": dataset_key,
            "row_idx": idx, "row_json": payload,
            "fetched_at": "2026-07-06T00:00:00+00:00",
            "source_endpoint": dataset_key}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = ProviderDataStore(":memory:")
        self.store.upsert("hospital_general", [
            _hospital("010001", "AL", "3"),
            _hospital("010005", "AL", "5"),
            _hospital("450001", "TX", "4"),
        ])
        # Two datasets sharing the generic table (must stay filterable).
        self.store.upsert("provider_data_rows", [
            _generic("77hc-ibv8", 0, '{"owner_name": "OWNER, A"}'),
            _generic("77hc-ibv8", 1, '{"owner_name": "OWNER, B"}'),
            _generic("mm2v-rk6y", 0, '{"measure": "x"}'),
        ])

    def tearDown(self):
        self.store.close()

    def test_registry_exposes_thirty_six_datasets(self):
        ids = dataset_ids()
        self.assertEqual(len(ids), 36)
        self.assertIn("provider_data_catalog", ids)
        self.assertIn("provider_data_hospital_general", ids)
        self.assertIn("provider_data_esrd_qip_tps", ids)
        self.assertIn("provider_data_medical_equipment_suppliers", ids)
        self.assertIn("provider_data_fetched_rows", ids)

    def test_equality_filter(self):
        res = query(self.store, "provider_data_hospital_general",
                    filters={"state": "TX"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["facility_id"], "450001")

    def test_gte_filter_and_sort(self):
        res = query(self.store, "provider_data_hospital_general",
                    filters={"hospital_overall_rating__gte": "4"},
                    sort=["-hospital_overall_rating"])
        self.assertEqual([r["facility_id"] for r in res.rows],
                         ["010005", "450001"])

    def test_like_and_in_filters(self):
        res = query(self.store, "provider_data_hospital_general",
                    filters={"facility_name__like": "%HOSP%"})
        self.assertEqual(res.total, 3)
        res = query(self.store, "provider_data_hospital_general",
                    filters={"facility_id__in": ["010001", "450001"]})
        self.assertEqual(res.total, 2)

    def test_select_projects_columns(self):
        res = query(self.store, "provider_data_hospital_general",
                    select=["facility_id", "state"])
        self.assertEqual(sorted(res.rows[0].keys()), ["facility_id", "state"])

    def test_generic_dataset_slices_by_dataset_key(self):
        # fetched_rows is deliberately unpinned: filter selects the slice.
        res = query(self.store, "provider_data_fetched_rows",
                    filters={"dataset_key": "77hc-ibv8"})
        self.assertEqual(res.total, 2)
        res_all = query(self.store, "provider_data_fetched_rows")
        self.assertEqual(res_all.total, 3)

    def test_generic_row_json_is_like_searchable(self):
        res = query(self.store, "provider_data_fetched_rows",
                    filters={"row_json__like": "%OWNER, B%"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["row_key"], "77hc-ibv8:1")

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "provider_data_hospital_general",
                        group_by=["state"])
        self.assertEqual(res.as_dict()["rows"][0], {"state": "AL", "count": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "provider_data_hospital_general",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "provider_data_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "provider_data_hospital_general", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "provider_data_hospital_general", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound

    def test_aggregate_requires_group_by(self):
        with self.assertRaises(QueryError):
            aggregate(self.store, "provider_data_hospital_general", group_by=[])


if __name__ == "__main__":
    unittest.main()
