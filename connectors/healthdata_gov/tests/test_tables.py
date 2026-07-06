import unittest

from ..endpoints import curated_endpoints, get_endpoint
from ..normalize import normalize, normalize_generic
from ..registry import registry_rows
from ..tables import TABLES, HealthdataGovStore
from .fakes import catalog_items, facility_capacity_rows


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

    def test_catalog_table_carries_domain_discriminator(self):
        # The meta-catalog's native-vs-federated column is load-bearing
        # for estate dedup; it must exist in the schema.
        self.assertIn("domain", TABLES["healthdata_gov_catalog"].columns)

    def test_row_idx_declared_integer(self):
        self.assertIn("row_idx INTEGER",
                      TABLES["healthdata_gov_rows"].create_sql())


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthdataGovStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_curated_upsert_is_idempotent(self):
        spec = get_endpoint("hospital_capacity_facility")
        rows = normalize(spec, facility_capacity_rows()
                         ).rows["hhs_hospital_capacity_facility"]
        self.store.upsert("hhs_hospital_capacity_facility", rows)
        self.store.upsert("hhs_hospital_capacity_facility", rows)   # re-run
        self.assertEqual(self.store.count("hhs_hospital_capacity_facility"), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("hospital_capacity_facility")
        first = facility_capacity_rows()[:1]
        self.store.upsert(
            "hhs_hospital_capacity_facility",
            normalize(spec, first).rows["hhs_hospital_capacity_facility"])
        first[0]["total_beds_7_day_avg"] = "950.0"     # revised release
        self.store.upsert(
            "hhs_hospital_capacity_facility",
            normalize(spec, first).rows["hhs_hospital_capacity_facility"])
        self.assertEqual(self.store.count("hhs_hospital_capacity_facility"), 1)
        row = self.store.fetchall(
            "SELECT total_beds_7_day_avg FROM hhs_hospital_capacity_facility "
            "WHERE record_key = ?",
            ("010039:2024-04-21T00:00:00.000",))[0]
        self.assertEqual(row["total_beds_7_day_avg"], "950.0")

    def test_catalog_upsert_idempotent_on_4x4(self):
        spec = get_endpoint("catalog")
        rows = normalize(spec, catalog_items(2)).rows["healthdata_gov_catalog"]
        self.store.upsert("healthdata_gov_catalog", rows)
        self.store.upsert("healthdata_gov_catalog", rows)
        self.assertEqual(self.store.count("healthdata_gov_catalog"), 2)

    def test_generic_rows_idempotent_and_typed(self):
        rows = normalize_generic("zzzz-9999", [{"a": 1}, {"a": 2}])
        self.store.upsert("healthdata_gov_rows", rows)
        self.store.upsert("healthdata_gov_rows", rows)
        self.assertEqual(self.store.count("healthdata_gov_rows"), 2)
        got = self.store.fetchall(
            "SELECT row_idx FROM healthdata_gov_rows "
            "ORDER BY row_idx DESC LIMIT 1")
        self.assertEqual(got[0]["row_idx"], 1)   # INTEGER affinity, not "1"<"10"

    def test_coerce_nested_types_to_text(self):
        spec = get_endpoint("hospital_capacity_facility")
        rows = normalize(spec, facility_capacity_rows()[:1]
                         ).rows["hhs_hospital_capacity_facility"]
        self.store.upsert("hhs_hospital_capacity_facility", rows)
        row = self.store.fetchall(
            "SELECT geocoded_hospital_address, is_metro_micro "
            "FROM hhs_hospital_capacity_facility LIMIT 1")[0]
        self.assertIn('"type": "Point"',
                      row["geocoded_hospital_address"])  # dict → JSON text
        self.assertEqual(row["is_metro_micro"], "1")     # bool → "1"

    def test_ingested_at_is_stamped(self):
        rows = normalize_generic("zzzz-9999", [{"a": 1}])
        self.store.upsert("healthdata_gov_rows", rows)
        row = self.store.fetchall(
            "SELECT ingested_at FROM healthdata_gov_rows")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
