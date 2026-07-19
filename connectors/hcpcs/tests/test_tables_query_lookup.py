import unittest

from ..lookup import lookup_code, lookup_section, search_codes
from ..query import QueryError, aggregate, query
from ..tables import HcpcsStore


def _seed(store):
    store.upsert("dim_hcpcs_code", [
        {"code_key": "lvl2:J9271", "code_type": "lvl2", "code": "J9271",
         "display": "Injection, pembrolizumab, 1 mg",
         "short_desc": "Pembrolizumab",
         "section": "J", "category": "J92", "source_endpoint": "lvl2"},
        {"code_key": "lvl2:J9299", "code_type": "lvl2", "code": "J9299",
         "display": "Injection, nivolumab, 1 mg",
         "short_desc": "Nivolumab",
         "section": "J", "category": "J92", "source_endpoint": "lvl2"},
        {"code_key": "lvl2:E0601", "code_type": "lvl2", "code": "E0601",
         "display": "Continuous positive airway pressure (CPAP) device",
         "short_desc": "CPAP device",
         "section": "E", "category": "E06", "source_endpoint": "lvl2"},
        {"code_key": "lvl2:A0428", "code_type": "lvl2", "code": "A0428",
         "display": "Ambulance service, BLS, non-emergency",
         "short_desc": "BLS ambulance",
         "section": "A", "category": "A04", "source_endpoint": "lvl2"},
    ])


class StoreUpsertTests(unittest.TestCase):
    def setUp(self):
        self.store = HcpcsStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent_and_updates(self):
        self.store.upsert("dim_hcpcs_code", [
            {"code_key": "lvl2:J9271", "code_type": "lvl2", "code": "J9271",
             "display": "OLD", "source_endpoint": "lvl2"}])
        self.store.upsert("dim_hcpcs_code", [
            {"code_key": "lvl2:J9271", "code_type": "lvl2", "code": "J9271",
             "display": "NEW", "source_endpoint": "lvl2"}])
        self.assertEqual(self.store.count("dim_hcpcs_code"), 1)
        row = self.store.fetchall("SELECT display FROM dim_hcpcs_code")[0]
        self.assertEqual(row["display"], "NEW")


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = HcpcsStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_dataset_slice_returns_all_lvl2_rows(self):
        res = query(self.store, "hcpcs_lvl2")
        self.assertEqual(res.total, 4)
        self.assertTrue(all(r["code_type"] == "lvl2" for r in res.rows))

    def test_code_like_filter(self):
        res = query(self.store, "hcpcs_lvl2", filters={"code__like": "J92%"},
                    sort=["code"])
        self.assertEqual(res.total, 2)
        self.assertEqual(res.rows[0]["code"], "J9271")

    def test_aggregate_by_section(self):
        res = aggregate(self.store, "hcpcs_lvl2", group_by=["section"])
        counts = {r["section"]: r["count"] for r in res.rows}
        self.assertEqual(counts["J"], 2)
        self.assertEqual(counts["E"], 1)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "hcpcs_lvl2", filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "hcpcs_not_a_dataset")

    def test_limit_is_clamped(self):
        res = query(self.store, "hcpcs_lvl2", limit=999999)
        self.assertEqual(res.limit, 1000)  # clamped to _MAX_LIMIT
        res2 = query(self.store, "hcpcs_lvl2", limit=0)
        self.assertEqual(res2.limit, 1)    # clamped up to the floor


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = HcpcsStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_lookup_code(self):
        row = lookup_code(self.store, "J9271")
        self.assertEqual(row["code_key"], "lvl2:J9271")
        self.assertEqual(row["category"], "J92")

    def test_lookup_code_case_insensitive(self):
        row = lookup_code(self.store, "e0601")
        self.assertEqual(row["code_key"], "lvl2:E0601")

    def test_lookup_code_unknown_returns_empty(self):
        self.assertEqual(lookup_code(self.store, "Z9999"), {})

    def test_lookup_section_groups_codes(self):
        out = lookup_section(self.store, "J")
        self.assertEqual(out["count"], 2)
        self.assertEqual([c["code"] for c in out["codes"]], ["J9271", "J9299"])

    def test_search_matches_description_or_code(self):
        by_desc = search_codes(self.store, "ambulance")
        self.assertEqual([r["code"] for r in by_desc], ["A0428"])
        by_code = search_codes(self.store, "J92")
        self.assertEqual({r["code"] for r in by_code}, {"J9271", "J9299"})


if __name__ == "__main__":
    unittest.main()
