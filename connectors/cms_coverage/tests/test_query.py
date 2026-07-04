import unittest

from ..query import QueryError, aggregate, query
from ..tables import CmsCoverageStore


def _row(doc_id, doc_type, title, chapter, source="national_ncd", level="national"):
    return {"document_key": f"{doc_type}:{doc_id}:1", "document_id": doc_id,
            "document_version": "1", "document_type": doc_type, "title": title,
            "chapter": chapter, "coverage_level": level, "source_endpoint": source}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsCoverageStore(":memory:")
        self.store.upsert("dim_coverage_document", [
            _row(169, "NCD", "Home Use of Oxygen", "240"),
            _row(170, "NCD", "Oxygen Therapy", "240"),
            _row(171, "NCD", "Cardiac Pacemaker", "20"),
            # A different endpoint sharing the same table (must be sliced out).
            _row(500, "LCD", "MolDX", "240", source="local_lcd", level="local"),
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "cms_coverage_national_ncd",
                    filters={"chapter": "20"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["document_id"], "171")

    def test_slice_excludes_other_endpoint(self):
        # The LCD row shares the table but must not appear for the NCD dataset.
        res = query(self.store, "cms_coverage_national_ncd")
        self.assertEqual(res.total, 3)
        self.assertTrue(all(r["document_type"] == "NCD" for r in res.rows))

    def test_like_filter(self):
        res = query(self.store, "cms_coverage_national_ncd",
                    filters={"title__like": "%Oxygen%"})
        self.assertEqual(res.total, 2)

    def test_in_filter(self):
        res = query(self.store, "cms_coverage_national_ncd",
                    filters={"document_id__in": ["169", "171"]})
        self.assertEqual(res.total, 2)

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "cms_coverage_national_ncd",
                        group_by=["chapter"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"chapter": "240", "count": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cms_coverage_national_ncd", filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "cms_coverage_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "cms_coverage_national_ncd", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "cms_coverage_national_ncd", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
