import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import _snake, normalize
from .fakes import (asc_facility_rows, catalog_items, clinician_rows,
                    generic_hai_rows, hcahps_rows, ich_cahps_facility_rows,
                    qip_tps_rows)


class SnakeTests(unittest.TestCase):
    def test_live_hazards_are_canonicalised(self):
        # The exact hazard shapes observed in the live files (2026-07-06).
        self.assertEqual(_snake("_condition"), "condition")
        self.assertEqual(_snake("95_ci_upper_limit_for_fyswr"),
                         "n_95_ci_upper_limit_for_fyswr")
        self.assertEqual(_snake("hgb__12_data_availability_code"),
                         "hgb_12_data_availability_code")
        self.assertEqual(_snake("Facility ID"), "facility_id")
        self.assertEqual(_snake("facility_id"), "facility_id")  # no-op on clean


class CatalogNormalizeTests(unittest.TestCase):
    def test_catalog_mapper(self):
        res = normalize(get_endpoint("catalog"), catalog_items())
        rows = res.rows["provider_data_catalog"]
        self.assertEqual(len(rows), 3)
        row = {r["identifier"]: r for r in rows}["4pq5-n9py"]
        self.assertEqual(
            row["title"],
            "Nursing homes including rehab services - Provider Information")
        self.assertEqual(row["keywords"], "Five Star|Quality")
        self.assertEqual(row["modified"], "2026-06-01")
        self.assertIn("nh_provider.csv", row["csv_url"])
        self.assertEqual(row["source_endpoint"], "catalog")

    def test_item_missing_identifier_is_skipped(self):
        res = normalize(get_endpoint("catalog"), [{"title": "orphan"}])
        self.assertEqual(res.rows.get("provider_data_catalog", []), [])


class CuratedNormalizeTests(unittest.TestCase):
    def test_single_field_key_degrades_to_bare_value(self):
        rec = {"facility_id": "010001", "facility_name": "TEST",
               "state": "AL", "hospital_overall_rating": "3"}
        res = normalize(get_endpoint("hospital_general"), [rec])
        row = res.rows["hospital_general"][0]
        self.assertEqual(row["record_key"], "010001")
        self.assertEqual(row["hospital_overall_rating"], "3")
        self.assertEqual(row["source_endpoint"], "hospital_general")

    def test_composed_key_and_full_live_shape(self):
        res = normalize(get_endpoint("hcahps_hospital"), hcahps_rows())
        rows = res.rows["hcahps_hospital"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["record_key"], "010001:H_COMP_1_A_P")
        self.assertEqual(rows[1]["record_key"], "010001:H_STAR_RATING")
        self.assertEqual(rows[1]["patient_survey_star_rating"], "4")
        self.assertEqual(res.unmapped, {})     # fixtures mirror the live schema

    def test_four_field_clinician_key(self):
        res = normalize(get_endpoint("dac_national"), clinician_rows())
        keys = [r["record_key"] for r in res.rows["dac_national"]]
        self.assertEqual(keys, [
            "1659447118:I20200729003366:2860304482:VI00840XXXXFRXXXXXXXXXX00",
            "1659447118:I20200729003366:4385740141:VI00840XXXXSTXXXXXXXXXX00",
        ])

    def test_unknown_raw_field_is_audited_not_dropped_silently(self):
        rec = {"facility_id": "010001", "brand_new_column": "x"}
        res = normalize(get_endpoint("hospital_general"), [rec])
        self.assertEqual(res.unmapped, {"brand_new_column": 1})

    def test_row_missing_natural_key_is_skipped(self):
        res = normalize(get_endpoint("hospital_general"),
                        [{"facility_name": "orphan"}])
        self.assertEqual(res.rows.get("hospital_general", []), [])

    def test_ich_cahps_doubled_underscore_headers_map_cleanly(self):
        # The live 59mq-zhts file serves doubled-underscore headers
        # (…communication_and__205e); _snake collapses them onto the
        # frozen schema columns, so nothing lands in the unmapped audit.
        res = normalize(get_endpoint("ich_cahps_facility"),
                        ich_cahps_facility_rows())
        rows = res.rows["ich_cahps_facility"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["record_key"], "012300")
        self.assertEqual(
            rows[0]["top_box_percent_of_patientsnephrologists_communication_and_205e"],
            "75")
        self.assertEqual(res.unmapped, {})

    def test_slug_identified_qip_rows_key_by_ccn(self):
        res = normalize(get_endpoint("esrd_qip_tps"), qip_tps_rows())
        rows = res.rows["esrd_qip_tps"]
        self.assertEqual([r["record_key"] for r in rows],
                         ["032300", "032301", "032302"])
        self.assertEqual(rows[0]["source_endpoint"], "esrd_qip_tps")
        self.assertEqual(res.unmapped, {})

    def test_asc_facility_npi_led_key_survives_live_hazards(self):
        # (npi, facility_id, year): shared-CCN pairs stay distinct and a
        # row with an empty facility_id (npi populated) is kept, not
        # skipped — both hazards exist in the live 4jcv-atw7 file.
        res = normalize(get_endpoint("asc_quality_facility"),
                        asc_facility_rows())
        keys = [r["record_key"] for r in res.rows["asc_quality_facility"]]
        self.assertEqual(keys, [
            "1023420577:45C0001277:2024",
            "1184976797:34C0001142:2024",
            "1306005343:34C0001142:2024",
            "1134590912::2024",
        ])
        self.assertEqual(res.unmapped, {})


class GenericNormalizeTests(unittest.TestCase):
    def test_generic_rows_compose_key_and_slice(self):
        spec = get_endpoint("fetched_rows")
        raw = generic_hai_rows(2)
        res = normalize(spec, raw, dataset_key="77hc-ibv8", start_idx=10,
                        fetched_at="2026-07-06T00:00:00+00:00")
        rows = res.rows["provider_data_rows"]
        self.assertEqual(rows[0]["row_key"], "77hc-ibv8:10")
        self.assertEqual(rows[1]["row_key"], "77hc-ibv8:11")
        self.assertEqual(rows[0]["dataset_key"], "77hc-ibv8")
        self.assertEqual(rows[0]["source_endpoint"], "77hc-ibv8")
        # The raw record round-trips through row_json intact.
        self.assertEqual(json.loads(rows[0]["row_json"]), raw[0])

    def test_generic_requires_dataset_key(self):
        with self.assertRaises(ValueError):
            normalize(get_endpoint("fetched_rows"), [{"a": 1}])


if __name__ == "__main__":
    unittest.main()
