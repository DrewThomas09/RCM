import unittest

from ..endpoints import ENDPOINTS, get_endpoint
from ..normalize import normalize_catalog, normalize_curated, normalize_generic
from ..tables import TABLES, CmsOpenDataStore
from .fakes import catalog_doc, cost_rows, phys_rows


class SchemaTests(unittest.TestCase):
    def test_every_endpoint_has_a_table_with_meta_columns(self):
        self.assertEqual(len(TABLES), 45)   # catalog + 43 curated + rows
        for spec in ENDPOINTS.values():
            tdef = TABLES[spec.target_table]
            self.assertEqual(tdef.columns[0], tdef.pk)
            self.assertEqual(tdef.columns[-2:], ("source_endpoint", "ingested_at"))

    def test_generic_row_idx_has_integer_affinity(self):
        store = CmsOpenDataStore(":memory:")
        store.upsert("cms_open_data_rows",
                     normalize_generic("x", [{"a": "1"}], start_idx=7))
        row = store.fetchall(
            "SELECT row_idx, typeof(row_idx) AS t FROM cms_open_data_rows")[0]
        self.assertEqual(row["t"], "integer")
        self.assertEqual(row["row_idx"], 7)
        store.close()


class UpsertTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsOpenDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_curated_upsert_is_idempotent(self):
        spec = get_endpoint("mup_physician_by_provider")
        rows = normalize_curated(spec, phys_rows(3))
        table = spec.target_table
        self.store.upsert(table, rows)
        self.store.upsert(table, rows)   # re-run
        self.assertEqual(self.store.count(table), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("hospital_cost_report")
        table = spec.target_table
        old, new = cost_rows()[0], dict(cost_rows()[0])
        new["Hospital Name"] = "RENAMED HOSPITAL"
        self.store.upsert(table, normalize_curated(spec, [old]))
        self.store.upsert(table, normalize_curated(spec, [new]))
        self.assertEqual(self.store.count(table), 1)
        row = self.store.fetchall(
            f"SELECT hospital_name FROM {table} WHERE row_key = ?",
            ("hospital_cost_report:747534",))[0]
        self.assertEqual(row["hospital_name"], "RENAMED HOSPITAL")

    def test_catalog_upsert_idempotent(self):
        rows = normalize_catalog(catalog_doc())
        self.store.upsert("cms_open_data_catalog", rows)
        self.store.upsert("cms_open_data_catalog", rows)
        self.assertEqual(self.store.count("cms_open_data_catalog"), 3)

    def test_generic_refetch_same_window_is_idempotent(self):
        raws = cost_rows()
        self.store.upsert("cms_open_data_rows", normalize_generic("k", raws))
        self.store.upsert("cms_open_data_rows", normalize_generic("k", raws))
        self.assertEqual(self.store.count("cms_open_data_rows"), 2)

    def test_extra_keys_ignored_and_missing_default_null(self):
        spec = get_endpoint("acos")
        rows = normalize_curated(
            spec, [{"aco_id": "A2811", "brand_new_field": "surprise"}])
        self.store.upsert(spec.target_table, rows)
        row = self.store.fetchall(
            f"SELECT aco_name, ingested_at FROM {spec.target_table}")[0]
        self.assertIsNone(row["aco_name"])
        self.assertTrue(str(row["ingested_at"]).endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
