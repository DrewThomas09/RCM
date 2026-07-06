import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import TABLES, HrsaDataStore
from .fakes import hpsa_pc_rows, mua_rows, sites_rows


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = HrsaDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_schema_declares_all_live_columns_plus_meta(self):
        # 1 pk + 65 live HPSA columns + 2 meta = 68, etc. Guard against
        # accidental edits to the snapshotted column lists.
        self.assertEqual(len(TABLES["hrsa_hpsa"].columns), 68)
        self.assertEqual(len(TABLES["hrsa_mua"].columns), 67)
        self.assertEqual(len(TABLES["hrsa_health_center_sites"].columns), 58)
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:], ("source_endpoint",
                                                 "ingested_at"))
            self.assertEqual(tdef.columns[0], tdef.pk)

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("hpsa_primary_care")
        rows = normalize(spec, hpsa_pc_rows()).rows["hrsa_hpsa"]
        self.store.upsert("hrsa_hpsa", rows)
        self.store.upsert("hrsa_hpsa", rows)   # re-run
        self.assertEqual(self.store.count("hrsa_hpsa"), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("hpsa_primary_care")
        first = hpsa_pc_rows()[0]
        self.store.upsert("hrsa_hpsa",
                          normalize(spec, [first]).rows["hrsa_hpsa"])
        changed = dict(first, **{"HPSA Status": "Withdrawn"})
        self.store.upsert("hrsa_hpsa",
                          normalize(spec, [changed]).rows["hrsa_hpsa"])
        self.assertEqual(self.store.count("hrsa_hpsa"), 1)
        row = self.store.fetchall(
            "SELECT hpsa_status FROM hrsa_hpsa WHERE hpsa_key = ?",
            ("1481234567:primary_care:48303",))[0]
        self.assertEqual(row["hpsa_status"], "Withdrawn")

    def test_disciplines_share_table_without_colliding(self):
        rec = hpsa_pc_rows()[0]
        for key in ("hpsa_primary_care", "hpsa_dental", "hpsa_mental_health"):
            spec = get_endpoint(key)
            self.store.upsert("hrsa_hpsa",
                              normalize(spec, [rec]).rows["hrsa_hpsa"])
        self.assertEqual(self.store.count("hrsa_hpsa"), 3)

    def test_mua_upsert_idempotent(self):
        rows = normalize(get_endpoint("mua"), mua_rows()).rows["hrsa_mua"]
        self.store.upsert("hrsa_mua", rows)
        self.store.upsert("hrsa_mua", rows)
        self.assertEqual(self.store.count("hrsa_mua"), 3)

    def test_sites_upsert_idempotent_and_missing_cols_null(self):
        rows = normalize(get_endpoint("health_center_sites"),
                         sites_rows()).rows["hrsa_health_center_sites"]
        self.store.upsert("hrsa_health_center_sites", rows)
        self.store.upsert("hrsa_health_center_sites", rows)
        self.assertEqual(self.store.count("hrsa_health_center_sites"), 2)
        # A column the fixture never set is NULL, not "".
        row = self.store.fetchall(
            "SELECT site_web_address FROM hrsa_health_center_sites "
            "WHERE site_key = ?", ("BPS-H80-556677",))[0]
        self.assertIsNone(row["site_web_address"])

    def test_ingested_at_is_set(self):
        rows = normalize(get_endpoint("mua"), mua_rows()).rows["hrsa_mua"]
        self.store.upsert("hrsa_mua", rows)
        row = self.store.fetchall(
            "SELECT ingested_at FROM hrsa_mua LIMIT 1")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
