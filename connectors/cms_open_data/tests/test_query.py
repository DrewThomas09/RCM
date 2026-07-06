import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize_curated, normalize_generic
from ..query import QueryError, aggregate, query
from ..tables import CmsOpenDataStore
from .fakes import phys_rows


def _phys(npi, state, benes):
    return {"Rndrng_NPI": npi, "Rndrng_Prvdr_State_Abrvtn": state,
            "Rndrng_Prvdr_Type": "Internal Medicine", "Tot_Benes": benes}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsOpenDataStore(":memory:")
        spec = get_endpoint("mup_physician_by_provider")
        self.store.upsert(spec.target_table, normalize_curated(spec, [
            _phys("1000000001", "MD", "100"),
            _phys("1000000002", "MD", "250"),
            _phys("1000000003", "CA", "999"),
        ]))
        # A generic slice sharing nothing but the engine.
        self.store.upsert("cms_open_data_rows", normalize_generic(
            "opioid_treatment_program_providers",
            [{"NPI": "1003008301", "STATE": "NY"},
             {"NPI": "1003008302", "STATE": "CA"}]))
        self.store.upsert("cms_open_data_rows", normalize_generic(
            "some_other_dataset", [{"foo": "bar"}]))

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "cms_open_data_mup_physician_by_provider",
                    filters={"rndrng_prvdr_state_abrvtn": "CA"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["rndrng_npi"], "1000000003")

    def test_like_and_in_filters(self):
        res = query(self.store, "cms_open_data_mup_physician_by_provider",
                    filters={"rndrng_prvdr_type__like": "%Internal%"})
        self.assertEqual(res.total, 3)
        res = query(self.store, "cms_open_data_mup_physician_by_provider",
                    filters={"rndrng_npi__in": ["1000000001", "1000000003"]})
        self.assertEqual(res.total, 2)

    def test_select_sort_and_offset(self):
        res = query(self.store, "cms_open_data_mup_physician_by_provider",
                    select=["rndrng_npi"], sort=["-rndrng_npi"], limit=2,
                    offset=1)
        self.assertEqual([r["rndrng_npi"] for r in res.rows],
                         ["1000000002", "1000000001"])
        self.assertEqual(set(res.rows[0].keys()), {"rndrng_npi"})

    def test_generic_rows_slice_by_dataset_key(self):
        res = query(self.store, "cms_open_data_fetched_rows",
                    filters={"dataset_key": "opioid_treatment_program_providers"})
        self.assertEqual(res.total, 2)
        res2 = query(self.store, "cms_open_data_fetched_rows",
                     filters={"dataset_key": "opioid_treatment_program_providers",
                              "row_json__like": '%"STATE": "NY"%'})
        self.assertEqual(res2.total, 1)

    def test_generic_rows_unpinned_sees_all_slices(self):
        # fetched_rows carries no source_filter by design: the shared
        # table holds one slice per fetched dataset.
        res = query(self.store, "cms_open_data_fetched_rows")
        self.assertEqual(res.total, 3)

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "cms_open_data_mup_physician_by_provider",
                        group_by=["rndrng_prvdr_state_abrvtn"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"rndrng_prvdr_state_abrvtn": "MD", "count": 2})

    def test_aggregate_generic_by_dataset_key(self):
        res = aggregate(self.store, "cms_open_data_fetched_rows",
                        group_by=["dataset_key"])
        self.assertEqual(res.rows[0]["dataset_key"],
                         "opioid_treatment_program_providers")

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cms_open_data_mup_physician_by_provider",
                  filters={"nope": "x"})
        with self.assertRaises(QueryError):
            query(self.store, "cms_open_data_mup_physician_by_provider",
                  sort=["nope"])
        with self.assertRaises(QueryError):
            aggregate(self.store, "cms_open_data_mup_physician_by_provider",
                      group_by=["nope"])

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cms_open_data_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "cms_open_data_mup_physician_by_provider",
                    limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "cms_open_data_mup_physician_by_provider",
                     limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound

    def test_catalog_dataset_is_queryable_too(self):
        from ..normalize import normalize_catalog
        from .fakes import catalog_doc
        self.store.upsert("cms_open_data_catalog", normalize_catalog(catalog_doc()))
        res = query(self.store, "cms_open_data_catalog",
                    filters={"title__like": "%Cost Report%"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["dataset_key"],
                         "hospital_provider_cost_report")


if __name__ == "__main__":
    unittest.main()
