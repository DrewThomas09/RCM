import unittest

from ..lookup import lookup_category, lookup_code, search_codes
from ..query import QueryError, aggregate, query
from ..tables import Icd10Store


def _seed(store):
    store.upsert("dim_icd10_code", [
        {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
         "name": "Type 2 diabetes mellitus without complications",
         "chapter": "E", "category": "E11", "source_endpoint": "cm"},
        {"code_key": "cm:E11.65", "code_type": "cm", "code": "E11.65",
         "name": "Type 2 diabetes mellitus with hyperglycemia",
         "chapter": "E", "category": "E11", "source_endpoint": "cm"},
        {"code_key": "cm:A00.0", "code_type": "cm", "code": "A00.0",
         "name": "Cholera due to Vibrio cholerae",
         "chapter": "A", "category": "A00", "source_endpoint": "cm"},
        {"code_key": "pcs:0DTJ4ZZ", "code_type": "pcs", "code": "0DTJ4ZZ",
         "name": "Resection of Appendix", "chapter": "0", "category": "0DT",
         "source_endpoint": "pcs"},
    ])


class StoreUpsertTests(unittest.TestCase):
    def setUp(self):
        self.store = Icd10Store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent_and_updates(self):
        self.store.upsert("dim_icd10_code", [
            {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
             "name": "OLD", "source_endpoint": "cm"}])
        self.store.upsert("dim_icd10_code", [
            {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
             "name": "NEW", "source_endpoint": "cm"}])
        self.assertEqual(self.store.count("dim_icd10_code"), 1)
        row = self.store.fetchall("SELECT name FROM dim_icd10_code")[0]
        self.assertEqual(row["name"], "NEW")


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = Icd10Store(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_dataset_slice_filters_by_code_type(self):
        res = query(self.store, "icd10_cm")
        self.assertEqual(res.total, 3)  # PCS row excluded by the slice
        self.assertTrue(all(r["code_type"] == "cm" for r in res.rows))

    def test_code_like_filter(self):
        res = query(self.store, "icd10_cm", filters={"code__like": "E11%"},
                    sort=["code"])
        self.assertEqual(res.total, 2)
        self.assertEqual(res.rows[0]["code"], "E11.65")

    def test_aggregate_by_chapter(self):
        res = aggregate(self.store, "icd10_cm", group_by=["chapter"])
        counts = {r["chapter"]: r["count"] for r in res.rows}
        self.assertEqual(counts["E"], 2)
        self.assertEqual(counts["A"], 1)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "icd10_cm", filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "icd10_not_a_dataset")

    def test_limit_is_clamped(self):
        res = query(self.store, "icd10_cm", limit=999999)
        self.assertEqual(res.limit, 1000)  # clamped to _MAX_LIMIT
        res2 = query(self.store, "icd10_cm", limit=0)
        self.assertEqual(res2.limit, 1)    # clamped up to the floor


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = Icd10Store(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_lookup_code_default_cm(self):
        row = lookup_code(self.store, "E11.65")
        self.assertEqual(row["code_key"], "cm:E11.65")
        self.assertEqual(row["category"], "E11")

    def test_lookup_code_case_insensitive_and_pcs(self):
        row = lookup_code(self.store, "0dtj4zz", "pcs")
        self.assertEqual(row["code_key"], "pcs:0DTJ4ZZ")

    def test_lookup_code_unknown_returns_empty(self):
        self.assertEqual(lookup_code(self.store, "Z99.9"), {})

    def test_lookup_category_groups_codes(self):
        out = lookup_category(self.store, "E11")
        self.assertEqual(out["count"], 2)
        self.assertEqual([c["code"] for c in out["codes"]], ["E11.65", "E11.9"])

    def test_search_matches_name_or_code(self):
        by_name = search_codes(self.store, "cm", "cholera")
        self.assertEqual([r["code"] for r in by_name], ["A00.0"])
        by_code = search_codes(self.store, "cm", "E11")
        self.assertEqual({r["code"] for r in by_code}, {"E11.9", "E11.65"})


if __name__ == "__main__":
    unittest.main()
