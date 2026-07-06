import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import (
    _snake,
    compose_row_key,
    normalize_catalog,
    normalize_curated,
    normalize_generic,
    slugify,
    snake_row,
)
from .fakes import CAT_PHYS_UUID, catalog_doc, cost_rows, phys_rows


class SnakeTests(unittest.TestCase):
    """_snake is the schema contract — endpoints.py columns were generated
    with it, so its behaviour is pinned here case by case."""

    def test_real_api_names(self):
        cases = {
            "Rndrng_NPI": "rndrng_npi",
            "Provider CCN": "provider_ccn",
            "ENROLLMENT ID": "enrollment_id",
            "ROLE CODE - OWNER": "role_code_owner",
            "ASSOCIATION DATE - OWNER": "association_date_owner",
            "Tot_30day_Fills": "tot_30day_fills",
            "HHA-based Hospice Provider CCN": "hha_based_hospice_provider_ccn",
            "Skilled Nursing Care-RN, Medicare Title XVIII Visits":
                "skilled_nursing_care_rn_medicare_title_xviii_visits",
            "re-entering_aco": "re_entering_aco",
            "WorkDate": "workdate",     # no camelCase splitting, by design
            "CY_Qtr": "cy_qtr",
            "hcpcs_cd": "hcpcs_cd",
        }
        for raw, want in cases.items():
            self.assertEqual(_snake(raw), want, raw)

    def test_leading_digit_and_empty(self):
        self.assertEqual(_snake("2023 Total"), "c_2023_total")
        self.assertEqual(_snake("---"), "col")

    def test_slugify_matches_catalog_titles(self):
        self.assertEqual(
            slugify("Medicare Physician & Other Practitioners - by Provider"),
            "medicare_physician_other_practitioners_by_provider")

    def test_snake_row_dedupes_and_protects_reserved(self):
        row = {"A B": "1", "A-B": "2", "row_key": "boom"}
        out = snake_row(row)
        self.assertEqual(out, {"a_b": "1", "a_b_2": "2", "src_row_key": "boom"})


class CatalogNormalizeTests(unittest.TestCase):
    def test_catalog_rows(self):
        rows = normalize_catalog(catalog_doc())
        self.assertEqual(len(rows), 3)
        phys = rows[0]
        self.assertEqual(phys["dataset_key"],
                         "medicare_physician_other_practitioners_by_provider")
        self.assertEqual(phys["uuid"], CAT_PHYS_UUID)  # "latest", not the older dist
        self.assertEqual(phys["themes"], "Medicare")
        self.assertEqual(phys["contact"],
                         "PUF - OEDA <Medicare_Provider_Data@cms.hhs.gov>")
        self.assertEqual(phys["source_endpoint"], "catalog")
        hrr = rows[2]
        self.assertEqual(hrr["api_url"], "")           # ZIP-only dataset
        self.assertNotEqual(hrr["uuid"], "")           # ...but identifier UUID kept

    def test_malformed_document_yields_nothing(self):
        self.assertEqual(normalize_catalog({}), [])
        self.assertEqual(normalize_catalog([]), [])
        self.assertEqual(normalize_catalog({"dataset": [{"no": "title"}]}), [])


class CuratedNormalizeTests(unittest.TestCase):
    def test_single_column_natural_key(self):
        spec = get_endpoint("mup_physician_by_provider")
        rows = normalize_curated(spec, phys_rows(2))
        self.assertEqual(rows[0]["row_key"],
                         "mup_physician_by_provider:1003000126")
        self.assertEqual(rows[0]["rndrng_npi"], "1003000126")
        self.assertEqual(rows[0]["tot_benes"], "328")
        self.assertEqual(rows[0]["source_endpoint"], "mup_physician_by_provider")

    def test_multi_column_natural_key(self):
        spec = get_endpoint("mup_physician_by_provider_service")
        raw = {"Rndrng_NPI": "1003000126", "HCPCS_Cd": "99223",
               "Place_Of_Srvc": "F", "Tot_Srvcs": "146"}
        rows = normalize_curated(spec, [raw])
        self.assertEqual(rows[0]["row_key"],
                         "mup_physician_by_provider_service:1003000126:99223:F")

    def test_spaced_column_names_key(self):
        spec = get_endpoint("hospital_all_owners")
        raw = {"ENROLLMENT ID": "O20020812000015",
               "ASSOCIATE ID - OWNER": "0244144871",
               "ROLE CODE - OWNER": "35",
               "ASSOCIATION DATE - OWNER": "2025-03-01",
               "ORGANIZATION NAME": "SOUTHERN TENNESSEE MEDICAL CENTER LLC"}
        rows = normalize_curated(spec, [raw])
        self.assertEqual(
            rows[0]["row_key"],
            "hospital_all_owners:O20020812000015:0244144871:35:2025-03-01")
        self.assertEqual(rows[0]["enrollment_id"], "O20020812000015")
        self.assertEqual(rows[0]["role_code_owner"], "35")

    def test_cost_report_key_and_columns(self):
        spec = get_endpoint("hospital_cost_report")
        rows = normalize_curated(spec, cost_rows())
        self.assertEqual(rows[0]["row_key"], "hospital_cost_report:747534")
        self.assertEqual(rows[0]["provider_ccn"], "110130")
        self.assertEqual(rows[0]["fiscal_year_end_date"], "2025-12-31")

    def test_geo_multi_key_tolerates_empty_component(self):
        spec = get_endpoint("geo_variation_state_county")
        raw = {"YEAR": "2014", "BENE_GEO_LVL": "National", "BENE_GEO_CD": "",
               "BENE_AGE_LVL": "All", "BENES_TOTAL_CNT": "56767775"}
        rows = normalize_curated(spec, [raw])
        self.assertEqual(rows[0]["row_key"],
                         "geo_variation_state_county:2014:National::All")

    def test_all_empty_natural_key_is_skipped(self):
        spec = get_endpoint("mup_physician_by_provider")
        self.assertEqual(normalize_curated(spec, [{"Tot_Benes": "1"}]), [])
        self.assertIsNone(compose_row_key(spec, {"Rndrng_NPI": "  "}))

    def test_wrong_kind_raises(self):
        with self.assertRaises(ValueError):
            normalize_curated(get_endpoint("catalog"), [])


class GenericNormalizeTests(unittest.TestCase):
    def test_row_json_records(self):
        raws = cost_rows()
        rows = normalize_generic("hospital_provider_cost_report", raws,
                                 fetched_at="2026-07-06T00:00:00+00:00")
        self.assertEqual(rows[0]["row_key"], "hospital_provider_cost_report:0")
        self.assertEqual(rows[1]["row_idx"], 1)
        self.assertEqual(rows[0]["source_endpoint"],
                         "hospital_provider_cost_report")
        self.assertEqual(rows[0]["fetched_at"], "2026-07-06T00:00:00+00:00")
        self.assertEqual(json.loads(rows[0]["row_json"]), raws[0])

    def test_start_idx_keeps_pages_contiguous(self):
        rows = normalize_generic("x", [{"a": 1}], start_idx=1000)
        self.assertEqual(rows[0]["row_key"], "x:1000")
        self.assertEqual(rows[0]["row_idx"], 1000)

    def test_slice_params_sign_the_key_and_land_in_json(self):
        # Regression: differently-filtered fetches of one dataset must
        # never share row keys (row_idx is per-slice positional).
        stamp = "2026-07-06T00:00:00+00:00"
        plain = normalize_generic("x", [{"a": 1}], fetched_at=stamp)
        ga = normalize_generic("x", [{"a": 1}], fetched_at=stamp,
                               slice_params={"State Code": "GA"})
        md = normalize_generic("x", [{"a": 1}], fetched_at=stamp,
                               slice_params={"State Code": "MD"})
        keys = {plain[0]["row_key"], ga[0]["row_key"], md[0]["row_key"]}
        self.assertEqual(len(keys), 3)
        self.assertEqual(plain[0]["row_key"], "x:0")   # unchanged contract
        self.assertEqual(json.loads(ga[0]["row_json"])["_slice_params"],
                         {"State Code": "GA"})
        # Same filters → same deterministic key (idempotent re-fetch).
        again = normalize_generic("x", [{"a": 1}], fetched_at=stamp,
                                  slice_params={"State Code": "GA"})
        self.assertEqual(ga, again)

    def test_empty_slice_params_keep_unfiltered_output_identical(self):
        stamp = "2026-07-06T00:00:00+00:00"
        plain = normalize_generic("x", [{"a": 1}], fetched_at=stamp)
        self.assertEqual(normalize_generic("x", [{"a": 1}], fetched_at=stamp,
                                           slice_params={}), plain)
        self.assertEqual(normalize_generic("x", [{"a": 1}], fetched_at=stamp,
                                           slice_params={"keyword": ""}),
                         plain)


if __name__ == "__main__":
    unittest.main()
