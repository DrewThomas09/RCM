import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import TABLES, ProviderDataStore
from .fakes import catalog_items, hospital_rows


def _hospital(facility_id, rating="3"):
    return {"facility_id": facility_id, "facility_name": "T",
            "state": "AL", "hospital_overall_rating": rating}


class SchemaTests(unittest.TestCase):
    def test_every_table_ends_with_meta_columns(self):
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:], ("source_endpoint", "ingested_at"),
                             tdef.name)

    def test_twenty_tables_registered(self):
        # catalog + 18 curated + generic rows
        self.assertEqual(len(TABLES), 20)

    def test_pk_is_first_column_everywhere(self):
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[0], tdef.pk, tdef.name)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = ProviderDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("hospital_general")
        rows = normalize(spec, [_hospital("010001"), _hospital("010002")]
                         ).rows["hospital_general"]
        self.store.upsert("hospital_general", rows)
        self.store.upsert("hospital_general", rows)   # re-run
        self.assertEqual(self.store.count("hospital_general"), 2)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("hospital_general")
        self.store.upsert("hospital_general",
                          normalize(spec, [_hospital("010001", "2")]
                                    ).rows["hospital_general"])
        self.store.upsert("hospital_general",
                          normalize(spec, [_hospital("010001", "5")]
                                    ).rows["hospital_general"])
        self.assertEqual(self.store.count("hospital_general"), 1)
        row = self.store.fetchall(
            "SELECT hospital_overall_rating FROM hospital_general "
            "WHERE record_key = ?", ("010001",))[0]
        self.assertEqual(row["hospital_overall_rating"], "5")

    def test_catalog_upsert_idempotent(self):
        rows = normalize(get_endpoint("catalog"), catalog_items()
                         ).rows["provider_data_catalog"]
        self.store.upsert("provider_data_catalog", rows)
        self.store.upsert("provider_data_catalog", rows)
        self.assertEqual(self.store.count("provider_data_catalog"), 3)

    def test_generic_row_idx_sorts_numerically(self):
        # row_idx is declared INTEGER, so 2 < 10 (not "10" < "2" as TEXT).
        spec = get_endpoint("fetched_rows")
        raw = [{"v": i} for i in range(12)]
        rows = normalize(spec, raw, dataset_key="ab12-cd34").rows["provider_data_rows"]
        self.store.upsert("provider_data_rows", rows)
        got = [r["row_idx"] for r in self.store.fetchall(
            "SELECT row_idx FROM provider_data_rows ORDER BY row_idx")]
        self.assertEqual(got, list(range(12)))

    def test_curated_full_live_row_round_trips(self):
        # A full-width live-shaped row lands with every column present.
        spec = get_endpoint("hospital_general")
        rows = normalize(spec, hospital_rows(1)).rows["hospital_general"]
        self.store.upsert("hospital_general", rows)
        row = dict(self.store.fetchall("SELECT * FROM hospital_general")[0])
        self.assertEqual(row["facility_name"], "TEST MEDICAL CENTER 0")
        self.assertEqual(row["mort_group_measure_count"], "7")
        self.assertIsNotNone(row["ingested_at"])


if __name__ == "__main__":
    unittest.main()
