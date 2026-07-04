import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import CmsCoverageStore


def _doc(document_id, version, title="T"):
    return {"document_id": document_id, "document_version": version,
            "document_type": "NCD", "title": title, "chapter": "240",
            "last_updated_sort": "20240101"}


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsCoverageStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("national_ncd")
        rows = normalize(spec, [_doc(169, 2), _doc(170, 1)]).rows["dim_coverage_document"]
        self.store.upsert("dim_coverage_document", rows)
        self.store.upsert("dim_coverage_document", rows)   # re-run
        self.assertEqual(self.store.count("dim_coverage_document"), 2)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("national_ncd")
        self.store.upsert("dim_coverage_document",
                          normalize(spec, [_doc(169, 2, "old")]).rows["dim_coverage_document"])
        self.store.upsert("dim_coverage_document",
                          normalize(spec, [_doc(169, 2, "new")]).rows["dim_coverage_document"])
        self.assertEqual(self.store.count("dim_coverage_document"), 1)
        row = self.store.fetchall(
            "SELECT title FROM dim_coverage_document WHERE document_key = ?",
            ("NCD:169:2",))[0]
        self.assertEqual(row["title"], "new")

    def test_contractor_upsert_idempotent(self):
        spec = get_endpoint("contractors")
        rows = normalize(spec, [
            {"contractor_id": 236, "contractor_version": 2,
             "contractor_name": "CGS"}]).rows["dim_medicare_contractor"]
        self.store.upsert("dim_medicare_contractor", rows)
        self.store.upsert("dim_medicare_contractor", rows)
        self.assertEqual(self.store.count("dim_medicare_contractor"), 1)


if __name__ == "__main__":
    unittest.main()
