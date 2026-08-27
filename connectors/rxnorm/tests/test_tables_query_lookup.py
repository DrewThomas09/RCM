import unittest

from ..lookup import lookup_concept, lookup_drug_name, lookup_ndc
from ..query import QueryError, aggregate, query
from ..tables import RxNormStore


def _seed(store):
    store.upsert("dim_rxnorm_concept", [
        {"rxcui": "1547220", "name": "pembrolizumab 25 MG/ML", "tty": "SCD",
         "ingredients": "pembrolizumab", "n_ingredients": "1",
         "atc_classes": "Antineoplastic agents", "class_source": "ATC",
         "source_endpoint": "ndc"},
        {"rxcui": "1657443", "name": "immune globulin", "tty": "SCD",
         "ingredients": "immune globulin", "n_ingredients": "1",
         "dailymed_classes": "Immunoglobulin", "class_source": "DAILYMED",
         "source_endpoint": "concept"},
    ])
    store.upsert("xwalk_ndc_rxcui", [
        {"ndc": "00006-3026-02", "ndc_digits": "00006302602",
         "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
         "source_endpoint": "ndc"},
        {"ndc": "00006-3029-01", "ndc_digits": "00006302901",
         "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
         "source_endpoint": "ndc"},
    ])
    store.upsert("xwalk_name_rxcui", [
        {"name_key": "keytruda", "query_name": "KEYTRUDA",
         "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
         "matched_on": "KEYTRUDA", "match_type": "exact",
         "source_endpoint": "name"},
        {"name_key": "keytrudah", "query_name": "KEYTRUDAH",
         "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
         "matched_on": "KEYTRUDAH", "match_type": "approximate",
         "source_endpoint": "name"},
    ])


class StoreUpsertTests(unittest.TestCase):
    def test_upsert_is_idempotent_and_updates(self):
        store = RxNormStore(":memory:")
        try:
            store.upsert("dim_rxnorm_concept", [
                {"rxcui": "1", "name": "OLD", "source_endpoint": "concept"}])
            store.upsert("dim_rxnorm_concept", [
                {"rxcui": "1", "name": "NEW", "source_endpoint": "concept"}])
            self.assertEqual(store.count("dim_rxnorm_concept"), 1)
            row = store.fetchall("SELECT name FROM dim_rxnorm_concept")[0]
            self.assertEqual(row["name"], "NEW")
        finally:
            store.close()


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = RxNormStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_each_dataset_slices_its_own_grain(self):
        self.assertEqual(query(self.store, "rxnorm_ndc").total, 2)
        self.assertEqual(query(self.store, "rxnorm_name").total, 2)
        # The concept dataset is pinned to concepts IT resolved — the one
        # the NDC sweep pulled in carries source_endpoint='ndc'.
        self.assertEqual(query(self.store, "rxnorm_concept").total, 1)

    def test_rxcui_filter_spans_the_crosswalk(self):
        res = query(self.store, "rxnorm_ndc", filters={"rxcui": "1547220"})
        self.assertEqual(res.total, 2)

    def test_aggregate_by_match_type(self):
        res = aggregate(self.store, "rxnorm_name", group_by=["match_type"])
        counts = {r["match_type"]: r["count"] for r in res.rows}
        self.assertEqual(counts["exact"], 1)
        self.assertEqual(counts["approximate"], 1)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "rxnorm_ndc", filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "rxnorm_not_a_dataset")


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = RxNormStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_lookup_ndc_exact_spelling(self):
        out = lookup_ndc(self.store, "00006-3026-02")
        self.assertEqual(out["rxcui"], "1547220")
        self.assertEqual(out["concept"]["name"], "pembrolizumab 25 MG/ML")

    def test_lookup_ndc_matches_on_digits_across_spellings(self):
        # CMS files spell the same NDC three different ways; all must hit.
        for spelling in ("00006302602", "0000 6302602", "00006 3026 02"):
            out = lookup_ndc(self.store, spelling)
            self.assertEqual(out.get("rxcui"), "1547220", spelling)

    def test_lookup_ndc_unknown_is_empty(self):
        self.assertEqual(lookup_ndc(self.store, "99999999999"), {})

    def test_lookup_concept_returns_the_reverse_crosswalk(self):
        out = lookup_concept(self.store, "1547220")
        self.assertEqual(out["n_ndcs"], 2)
        self.assertEqual(out["concept"]["atc_classes"], "Antineoplastic agents")
        self.assertEqual({n["query_name"] for n in out["names"]},
                         {"KEYTRUDA", "KEYTRUDAH"})

    def test_lookup_name_is_case_insensitive(self):
        out = lookup_drug_name(self.store, "keytruda")
        self.assertEqual(out["rxcui"], "1547220")
        self.assertEqual(lookup_drug_name(self.store, "KeYtRuDa")["rxcui"],
                         "1547220")

    def test_lookup_name_unknown_is_empty(self):
        self.assertEqual(lookup_drug_name(self.store, "nope"), {})


if __name__ == "__main__":
    unittest.main()
