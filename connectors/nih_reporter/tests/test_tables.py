import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import NihReporterStore
from .fakes import project_record, publication_record


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = NihReporterStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("projects")
        rows = normalize(spec, [project_record(appl_id=1),
                                project_record(appl_id=2)]).rows["nih_projects"]
        self.store.upsert("nih_projects", rows)
        self.store.upsert("nih_projects", rows)   # re-run
        self.assertEqual(self.store.count("nih_projects"), 2)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("projects")
        self.store.upsert("nih_projects", normalize(
            spec, [project_record(appl_id=1, award_amount=100)]).rows["nih_projects"])
        self.store.upsert("nih_projects", normalize(
            spec, [project_record(appl_id=1, award_amount=999)]).rows["nih_projects"])
        self.assertEqual(self.store.count("nih_projects"), 1)
        row = self.store.fetchall(
            "SELECT award_amount FROM nih_projects WHERE appl_id = ?", ("1",))[0]
        self.assertEqual(row["award_amount"], "999")

    def test_publication_upsert_idempotent_on_composed_key(self):
        spec = get_endpoint("publications")
        rows = normalize(spec, [publication_record()]).rows["nih_publications"]
        self.store.upsert("nih_publications", rows)
        self.store.upsert("nih_publications", rows)
        self.assertEqual(self.store.count("nih_publications"), 1)
        # Same PMID under a different application is a distinct edge.
        other = normalize(spec, [publication_record(applid=999)]).rows["nih_publications"]
        self.store.upsert("nih_publications", other)
        self.assertEqual(self.store.count("nih_publications"), 2)

    def test_coercion_bools_and_none(self):
        spec = get_endpoint("projects")
        rows = normalize(spec, [project_record(appl_id=7)]).rows["nih_projects"]
        self.store.upsert("nih_projects", rows)
        row = self.store.fetchall(
            "SELECT is_active, is_new, subproject_id, ingested_at "
            "FROM nih_projects WHERE appl_id = ?", ("7",))[0]
        self.assertEqual(row["is_active"], "1")     # bool → "1"/"0"
        self.assertEqual(row["is_new"], "0")
        self.assertIsNone(row["subproject_id"])     # None → NULL
        self.assertIn("+00:00", row["ingested_at"])  # tz-aware stamp


if __name__ == "__main__":
    unittest.main()
