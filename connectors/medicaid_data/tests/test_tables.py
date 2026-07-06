import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, normalize_generic
from ..tables import TABLES, MedicaidDataStore
from .fakes import nadac_row, sdud_row


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = MedicaidDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_every_table_ends_with_meta_columns(self):
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:],
                             ("source_endpoint", "ingested_at"),
                             f"{tdef.name} must end with the meta columns")

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("nadac_2026")
        rows = normalize(spec, [nadac_row(), nadac_row(ndc="11111111111")]
                         ).rows["medicaid_nadac"]
        self.store.upsert("medicaid_nadac", rows)
        self.store.upsert("medicaid_nadac", rows)   # re-run
        self.assertEqual(self.store.count("medicaid_nadac"), 2)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("nadac_2026")
        self.store.upsert("medicaid_nadac", normalize(
            spec, [nadac_row(per_unit="0.10000")]).rows["medicaid_nadac"])
        self.store.upsert("medicaid_nadac", normalize(
            spec, [nadac_row(per_unit="0.26341")]).rows["medicaid_nadac"])
        self.assertEqual(self.store.count("medicaid_nadac"), 1)
        row = self.store.fetchall(
            "SELECT nadac_per_unit FROM medicaid_nadac WHERE nadac_key = ?",
            ("nadac_2026:24385005452:2025-12-17:2026-01-07",))[0]
        self.assertEqual(row["nadac_per_unit"], "0.26341")

    def test_shared_table_year_slices_coexist(self):
        # The SAME raw row ingested via nadac_2025 and nadac_2026 must land
        # as two rows (different composed keys + source_endpoint slices).
        raw = [nadac_row()]
        for key in ("nadac_2025", "nadac_2026"):
            spec = get_endpoint(key)
            self.store.upsert("medicaid_nadac",
                              normalize(spec, raw).rows["medicaid_nadac"])
        self.assertEqual(self.store.count("medicaid_nadac"), 2)
        self.assertEqual(self.store.count(
            "medicaid_nadac", "source_endpoint = ?", ("nadac_2025",)), 1)

    def test_sdud_upsert_idempotent(self):
        spec = get_endpoint("sdud_2025")
        rows = normalize(spec, [sdud_row()]).rows["medicaid_sdud"]
        self.store.upsert("medicaid_sdud", rows)
        self.store.upsert("medicaid_sdud", rows)
        self.assertEqual(self.store.count("medicaid_sdud"), 1)

    def test_generic_rows_upsert_idempotent_and_typed_idx(self):
        res = normalize_generic("uuid-1", [{"a": 1}, {"a": 2}])
        self.store.upsert("medicaid_data_rows", res.rows["medicaid_data_rows"])
        self.store.upsert("medicaid_data_rows", res.rows["medicaid_data_rows"])
        self.assertEqual(self.store.count("medicaid_data_rows"), 2)
        row = self.store.fetchall(
            "SELECT row_idx FROM medicaid_data_rows ORDER BY row_idx")[1]
        self.assertEqual(row["row_idx"], 1)   # INTEGER, not text

    def test_ingested_at_is_stamped(self):
        spec = get_endpoint("nadac_2026")
        self.store.upsert("medicaid_nadac",
                          normalize(spec, [nadac_row()]).rows["medicaid_nadac"])
        row = self.store.fetchall(
            "SELECT ingested_at FROM medicaid_nadac")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
