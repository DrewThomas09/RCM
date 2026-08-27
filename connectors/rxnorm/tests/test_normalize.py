import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize

_CONCEPT = {
    "rxcui": "1547220",
    "name": "pembrolizumab 25 MG/ML",
    "tty": "SCD",
    "synonym": "",
    "ingredients": ["pembrolizumab"],
    "classes": ["Antineoplastic agents"],
    "class_source": "ATC",
    "properties": {"rxcui": "1547220", "name": "pembrolizumab 25 MG/ML",
                   "tty": "SCD", "futureField": "x"},
}


class NdcNormalizeTests(unittest.TestCase):
    def _res(self):
        rec = {"kind": "ndc", "ndc": "00006-3026-02",
               "ndc_digits": "00006302602", "rxcui": "1547220",
               "concept": _CONCEPT}
        return normalize(get_endpoint("ndc"), [rec])

    def test_writes_both_the_crosswalk_and_the_concept(self):
        res = self._res()
        self.assertEqual(len(res.rows["xwalk_ndc_rxcui"]), 1)
        self.assertEqual(len(res.rows["dim_rxnorm_concept"]), 1)
        x = res.rows["xwalk_ndc_rxcui"][0]
        self.assertEqual(x["ndc"], "00006-3026-02")
        self.assertEqual(x["ndc_digits"], "00006302602")
        self.assertEqual(x["rxcui"], "1547220")
        self.assertEqual(x["resolved_name"], "pembrolizumab 25 MG/ML")
        self.assertEqual(x["source_endpoint"], "ndc")

    def test_concept_row_joins_lists_and_counts_ingredients(self):
        row = self._res().rows["dim_rxnorm_concept"][0]
        self.assertEqual(row["rxcui"], "1547220")
        self.assertEqual(row["ingredients"], "pembrolizumab")
        self.assertEqual(row["n_ingredients"], "1")
        self.assertEqual(row["atc_classes"], "Antineoplastic agents")
        self.assertEqual(row["dailymed_classes"], "")   # not this taxonomy
        self.assertEqual(row["class_source"], "ATC")
        self.assertEqual(json.loads(row["raw"])["futureField"], "x")

    def test_unknown_property_keys_are_audited(self):
        self.assertIn("futureField", self._res().unmapped)

    def test_multi_ingredient_products_keep_the_count(self):
        concept = dict(_CONCEPT, rxcui="2000",
                       ingredients=["amlodipine", "benazepril"])
        res = normalize(get_endpoint("ndc"),
                        [{"kind": "ndc", "ndc": "1", "ndc_digits": "123456789",
                          "rxcui": "2000", "concept": concept}])
        row = res.rows["dim_rxnorm_concept"][0]
        self.assertEqual(row["ingredients"], "amlodipine; benazepril")
        self.assertEqual(row["n_ingredients"], "2")


class NameNormalizeTests(unittest.TestCase):
    def test_name_key_is_lower_cased_for_idempotent_upserts(self):
        rec = {"kind": "name", "query_name": "KEYTRUDA", "rxcui": "1547220",
               "matched_on": "KEYTRUDA", "match_type": "exact",
               "concept": _CONCEPT}
        row = normalize(get_endpoint("name"), [rec]).rows["xwalk_name_rxcui"][0]
        self.assertEqual(row["name_key"], "keytruda")
        self.assertEqual(row["query_name"], "KEYTRUDA")
        self.assertEqual(row["match_type"], "exact")

    def test_approximate_match_type_survives(self):
        rec = {"kind": "name", "query_name": "KEYTRUDAH", "rxcui": "1547220",
               "matched_on": "KEYTRUDAH", "match_type": "approximate",
               "concept": _CONCEPT}
        row = normalize(get_endpoint("name"), [rec]).rows["xwalk_name_rxcui"][0]
        self.assertEqual(row["match_type"], "approximate")


class ConceptNormalizeTests(unittest.TestCase):
    def test_concept_only_record_writes_no_crosswalk(self):
        rec = {"kind": "concept", "rxcui": "1547220", "concept": _CONCEPT}
        res = normalize(get_endpoint("concept"), [rec])
        self.assertEqual(set(res.rows), {"dim_rxnorm_concept"})
        self.assertIn("1547220", res.rxcuis)

    def test_dailymed_classes_land_in_their_own_column(self):
        concept = dict(_CONCEPT, rxcui="1657443", name="immune globulin",
                       classes=["Immunoglobulin"], class_source="DAILYMED")
        rec = {"kind": "concept", "rxcui": "1657443", "concept": concept}
        row = normalize(get_endpoint("concept"),
                        [rec]).rows["dim_rxnorm_concept"][0]
        self.assertEqual(row["dailymed_classes"], "Immunoglobulin")
        self.assertEqual(row["atc_classes"], "")
        self.assertEqual(row["class_source"], "DAILYMED")

    def test_record_without_a_concept_is_skipped(self):
        res = normalize(get_endpoint("concept"),
                        [{"kind": "concept", "rxcui": "1", "concept": {}}])
        self.assertEqual(res.rows, {})


if __name__ == "__main__":
    unittest.main()
