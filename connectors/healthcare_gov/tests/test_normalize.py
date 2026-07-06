import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import _snake, generic_rows, normalize
from .fakes import (
    CATALOG_ITEMS,
    PLAN_ATTRIBUTES_ROWS,
    QUALITY_ROWS,
    SERVICE_AREA_ROWS,
)


class SnakeTests(unittest.TestCase):
    def test_camel_case_and_punctuation(self):
        self.assertEqual(_snake("accrualPeriodicity"), "accrual_periodicity")
        self.assertEqual(_snake("HPSA Source ID"), "hpsa_source_id")
        self.assertEqual(_snake("MUA/P ID"), "mua_p_id")

    def test_lowercase_passthrough(self):
        # DKAN datastore headers arrive already lower-cased.
        self.assertEqual(_snake("businessyear"), "businessyear")


class CatalogNormalizeTests(unittest.TestCase):
    def test_catalog_item_maps_dcat_fields(self):
        res = normalize(get_endpoint("catalog"), CATALOG_ITEMS)
        rows = res.rows["healthcare_gov_catalog"]
        self.assertEqual(len(rows), 2)   # orphan (no identifier) skipped
        row = rows[0]
        self.assertEqual(row["identifier"],
                         "ca253298-c4ef-4a77-9c44-0de0bbe91941")
        self.assertEqual(row["title"], "Plan Attributes PUF - PY2026")
        self.assertEqual(row["accrual_periodicity"], "R/PT1S")
        self.assertEqual(row["publisher_name"], "data.healthcare.gov")
        self.assertEqual(row["contact_email"], "mailto:CCIIO@cms.hhs.gov")
        self.assertEqual(row["keyword"], "puf|healthcare")
        self.assertEqual(row["distribution_count"], 1)
        self.assertEqual(row["format"], "csv")
        self.assertTrue(row["download_url"].endswith("PlanAttributes.csv"))
        self.assertEqual(
            row["landing_page"],
            "https://data.healthcare.gov/dataset/"
            "ca253298-c4ef-4a77-9c44-0de0bbe91941")
        self.assertEqual(row["source_endpoint"], "catalog")

    def test_zip_only_dataset_still_lands_in_catalog(self):
        res = normalize(get_endpoint("catalog"), CATALOG_ITEMS)
        rows = res.rows["healthcare_gov_catalog"]
        zips = [r for r in rows if r["format"] == "zip"]
        self.assertEqual(len(zips), 1)
        self.assertIsNone(zips[0]["accrual_periodicity"])


class DatastoreNormalizeTests(unittest.TestCase):
    def test_plan_attributes_composes_key_and_slice(self):
        spec = get_endpoint("plan_attributes_py2026")
        res = normalize(spec, PLAN_ATTRIBUTES_ROWS)
        rows = res.rows["healthcare_gov_plan_attributes"]
        self.assertEqual(len(rows), 3)
        row = rows[0]
        self.assertEqual(row["plan_key"],
                         "plan_attributes_py2026:2026:21989AK0030001-00")
        self.assertEqual(row["source_endpoint"], "plan_attributes_py2026")
        self.assertEqual(row["metallevel"], "Low")
        # Columns absent from the record default to None (NULL).
        self.assertIsNone(row["networkid"])

    def test_quality_key_uses_planid(self):
        res = normalize(get_endpoint("quality_puf_py2026"), QUALITY_ROWS)
        rows = res.rows["healthcare_gov_plan_quality"]
        self.assertEqual(rows[0]["quality_key"],
                         "quality_puf_py2026:38344AK1060001")
        self.assertEqual(rows[0]["overallratingvalue"], "3")

    def test_service_area_empty_county_keeps_key_alignment(self):
        res = normalize(get_endpoint("service_area_puf_py2026"),
                        SERVICE_AREA_ROWS)
        rows = res.rows["healthcare_gov_service_areas"]
        # Statewide row: county segment is empty but present.
        self.assertEqual(
            rows[0]["service_area_key"],
            "service_area_puf_py2026:2026:AK:21989:AKS001::Individual:Yes")
        # County rows differ only by county → distinct keys.
        self.assertNotEqual(rows[1]["service_area_key"],
                            rows[2]["service_area_key"])

    def test_row_missing_first_id_field_is_skipped(self):
        spec = get_endpoint("plan_attributes_py2026")
        res = normalize(spec, [{"planid": "x", "statecode": "AK"}])
        self.assertEqual(res.rows.get("healthcare_gov_plan_attributes", []),
                         [])

    def test_record_number_is_known_but_novel_fields_are_audited(self):
        spec = get_endpoint("quality_puf_py2026")
        rec = dict(QUALITY_ROWS[0], record_number=7, brand_new_field="x")
        res = normalize(spec, [rec])
        self.assertNotIn("record_number", res.unmapped)
        self.assertEqual(res.unmapped.get("brand_new_field"), 1)


class GenericRowsTests(unittest.TestCase):
    def test_prefers_record_number_and_strips_it_from_json(self):
        raw = [{"record_number": 41, "a": "1"},
               {"record_number": 42, "a": "2"}]
        rows = generic_rows("e4rr-zk4i", raw)
        self.assertEqual(rows[0]["row_key"], "e4rr-zk4i:00000041")
        self.assertEqual(rows[1]["row_idx"], "00000042")
        self.assertEqual(json.loads(rows[0]["row_json"]), {"a": "1"})
        self.assertEqual(rows[0]["source_endpoint"], "e4rr-zk4i")
        self.assertTrue(rows[0]["fetched_at"])

    def test_falls_back_to_absolute_offset(self):
        rows = generic_rows("some-id", [{"a": "1"}, {"a": "2"}], start_idx=500)
        self.assertEqual(rows[0]["row_key"], "some-id:00000500")
        self.assertEqual(rows[1]["row_key"], "some-id:00000501")

    def test_row_idx_zero_padded_so_text_order_is_numeric(self):
        # Regression: unpadded TEXT indexes sorted "10" < "9".
        rows = generic_rows("some-id", [{"a": str(i)} for i in range(11)])
        idxs = [r["row_idx"] for r in rows]
        self.assertEqual(idxs, sorted(idxs))          # lexicographic == numeric
        self.assertEqual(idxs[9], "00000009")
        self.assertEqual(idxs[10], "00000010")
        self.assertGreater(idxs[10], idxs[9])

    def test_non_dict_rows_are_skipped(self):
        rows = generic_rows("some-id", [{"a": "1"}, "junk", None])
        self.assertEqual(len(rows), 1)

    def test_slice_params_sign_the_key_and_land_in_json(self):
        # Regression: two differently-filtered fetches whose rows fall
        # back to positional indexes must not overwrite each other.
        ak = generic_rows("some-id", [{"a": "1"}],
                          slice_params={"statecode": "AK"})
        tx = generic_rows("some-id", [{"a": "2"}],
                          slice_params={"statecode": "TX"})
        self.assertNotEqual(ak[0]["row_key"], tx[0]["row_key"])
        self.assertTrue(ak[0]["row_key"].startswith("some-id:"))
        self.assertTrue(ak[0]["row_key"].endswith(":00000000"))
        self.assertEqual(json.loads(ak[0]["row_json"])["_slice_params"],
                         {"statecode": "AK"})
        # The signature is deterministic: same filters → same key.
        again = generic_rows("some-id", [{"a": "9"}],
                             slice_params={"statecode": "AK"})
        self.assertEqual(ak[0]["row_key"], again[0]["row_key"])

    def test_empty_slice_params_keep_unfiltered_key_shape(self):
        plain = generic_rows("some-id", [{"a": "1"}],
                             fetched_at="2026-07-06T00:00:00+00:00")
        empt = generic_rows("some-id", [{"a": "1"}], slice_params={},
                            fetched_at="2026-07-06T00:00:00+00:00")
        blank = generic_rows("some-id", [{"a": "1"}],
                             slice_params={"keyword": ""},
                             fetched_at="2026-07-06T00:00:00+00:00")
        self.assertEqual(plain, empt)
        self.assertEqual(plain, blank)
        self.assertEqual(plain[0]["row_key"], "some-id:00000000")


if __name__ == "__main__":
    unittest.main()
