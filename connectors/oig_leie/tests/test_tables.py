import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import TABLES, OigLeieStore
from .fakes import supplement_rein_rows, updated_rows


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = OigLeieStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_schema_declares_all_live_columns_plus_meta(self):
        # 1 pk + 18 live LEIE columns + 2 meta = 21. Guard against
        # accidental edits to the snapshotted column list.
        self.assertEqual(len(TABLES["oig_exclusions"].columns), 21)
        self.assertEqual(len(TABLES["oig_reinstatements"].columns), 21)
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:], ("source_endpoint",
                                                 "ingested_at"))
            self.assertEqual(tdef.columns[0], tdef.pk)

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("exclusions")
        rows = normalize(spec, updated_rows()).rows["oig_exclusions"]
        self.store.upsert("oig_exclusions", rows)
        self.store.upsert("oig_exclusions", rows)   # re-run
        self.assertEqual(self.store.count("oig_exclusions"), 4)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("exclusions")
        first = updated_rows()[2]
        self.store.upsert("oig_exclusions",
                          normalize(spec, [first]).rows["oig_exclusions"])
        # Same natural key, changed payload (e.g. OIG corrects specialty).
        changed = dict(first, **{"SPECIALTY": "PHYSICIAN"})
        self.store.upsert("oig_exclusions",
                          normalize(spec, [changed]).rows["oig_exclusions"])
        self.assertEqual(self.store.count("oig_exclusions"), 1)
        row = self.store.fetchall(
            "SELECT specialty FROM oig_exclusions WHERE npi = ?",
            ("1234567893",))[0]
        self.assertEqual(row["specialty"], "PHYSICIAN")

    def test_full_and_supplement_share_table_via_same_key(self):
        rec = updated_rows()[2]
        self.store.upsert("oig_exclusions", normalize(
            get_endpoint("exclusions"), [rec]).rows["oig_exclusions"])
        self.store.upsert("oig_exclusions", normalize(
            get_endpoint("supplement"), [rec],
            month_tag="2026-05").rows["oig_exclusions"])
        # One logical record — the later write wins provenance.
        self.assertEqual(self.store.count("oig_exclusions"), 1)
        row = self.store.fetchall(
            "SELECT source_endpoint FROM oig_exclusions")[0]
        self.assertEqual(row["source_endpoint"], "supplement:2026-05")

    def test_reinstatements_upsert_idempotent(self):
        rows = normalize(get_endpoint("reinstatements"),
                         supplement_rein_rows(),
                         month_tag="2026-05").rows["oig_reinstatements"]
        self.store.upsert("oig_reinstatements", rows)
        self.store.upsert("oig_reinstatements", rows)
        self.assertEqual(self.store.count("oig_reinstatements"), 2)

    def test_missing_columns_are_null_not_empty(self):
        # A row that never mentions a column stores NULL there, keeping
        # "absent" distinguishable from "published empty".
        self.store.upsert("oig_exclusions",
                          [{"exclusion_key": "k1", "lastname": "DOE"}])
        row = self.store.fetchall(
            "SELECT upin FROM oig_exclusions WHERE exclusion_key = ?",
            ("k1",))[0]
        self.assertIsNone(row["upin"])

    def test_ingested_at_is_set(self):
        rows = normalize(get_endpoint("exclusions"),
                         updated_rows()).rows["oig_exclusions"]
        self.store.upsert("oig_exclusions", rows)
        row = self.store.fetchall(
            "SELECT ingested_at FROM oig_exclusions LIMIT 1")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
