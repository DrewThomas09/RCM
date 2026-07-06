import unittest

from ..endpoints import curated_endpoints, get_endpoint
from ..normalize import normalize, normalize_generic
from ..registry import registry_rows
from ..tables import TABLES, CdcDataStore
from .fakes import catalog_items, places_rows


class SchemaTests(unittest.TestCase):
    def test_every_table_ends_with_meta_columns(self):
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:], ("source_endpoint", "ingested_at"),
                             tdef.name)

    def test_curated_tables_mirror_live_column_snapshots(self):
        for spec in curated_endpoints():
            tdef = TABLES[spec.target_table]
            self.assertEqual(
                tdef.columns,
                ("record_key", *spec.columns, "source_endpoint", "ingested_at"))

    def test_registry_targets_all_exist(self):
        for row in registry_rows():
            self.assertIn(row.target_table, TABLES, row.dataset_id)

    def test_row_idx_declared_integer(self):
        self.assertIn("row_idx INTEGER", TABLES["cdc_data_rows"].create_sql())


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = CdcDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_curated_upsert_is_idempotent(self):
        spec = get_endpoint("places_county")
        rows = normalize(spec, places_rows()).rows["cdc_places_county"]
        self.store.upsert("cdc_places_county", rows)
        self.store.upsert("cdc_places_county", rows)   # re-run
        self.assertEqual(self.store.count("cdc_places_county"), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("places_county")
        first = places_rows()[:1]
        self.store.upsert("cdc_places_county",
                          normalize(spec, first).rows["cdc_places_county"])
        first[0]["data_value"] = "31.0"                 # revised release
        self.store.upsert("cdc_places_county",
                          normalize(spec, first).rows["cdc_places_county"])
        self.assertEqual(self.store.count("cdc_places_county"), 1)
        row = self.store.fetchall(
            "SELECT data_value FROM cdc_places_county WHERE record_key = ?",
            ("AR:05043:ARTHRITIS:CrdPrv",))[0]
        self.assertEqual(row["data_value"], "31.0")

    def test_catalog_upsert_idempotent_on_4x4(self):
        spec = get_endpoint("catalog")
        rows = normalize(spec, catalog_items(2)).rows["cdc_data_catalog"]
        self.store.upsert("cdc_data_catalog", rows)
        self.store.upsert("cdc_data_catalog", rows)
        self.assertEqual(self.store.count("cdc_data_catalog"), 2)

    def test_generic_rows_idempotent_and_typed(self):
        rows = normalize_generic("zzzz-9999", [{"a": 1}, {"a": 2}])
        self.store.upsert("cdc_data_rows", rows)
        self.store.upsert("cdc_data_rows", rows)
        self.assertEqual(self.store.count("cdc_data_rows"), 2)
        got = self.store.fetchall(
            "SELECT row_idx FROM cdc_data_rows ORDER BY row_idx DESC LIMIT 1")
        self.assertEqual(got[0]["row_idx"], 1)   # INTEGER affinity, not "1"<"10"

    def test_coerce_nested_types_to_text(self):
        spec = get_endpoint("places_county")
        rows = normalize(spec, places_rows()[:1]).rows["cdc_places_county"]
        self.store.upsert("cdc_places_county", rows)
        row = self.store.fetchall(
            "SELECT geolocation FROM cdc_places_county LIMIT 1")[0]
        self.assertIn('"type": "Point"', row["geolocation"])  # dict → JSON text

    def test_ingested_at_is_stamped(self):
        rows = normalize_generic("zzzz-9999", [{"a": 1}])
        self.store.upsert("cdc_data_rows", rows)
        row = self.store.fetchall("SELECT ingested_at FROM cdc_data_rows")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
