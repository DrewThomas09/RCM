import json
import unittest

from ..endpoints import get_endpoint
from ..flatten import to_column, to_snake
from ..normalize import normalize, normalize_generic
from .fakes import (catalog_items, heart_disease_rows, places_rows,
                    provisional_deaths_rows, vsrr_rows)


class CatalogNormalizeTests(unittest.TestCase):
    def test_catalog_mapper_snake_cases_and_lifts_common_core(self):
        res = normalize(get_endpoint("catalog"), catalog_items(1))
        rows = res.rows["cdc_data_catalog"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["dataset_uid"], "aaa0-bbb0")
        self.assertEqual(row["name"], "Test Dataset 0")
        # camelCase → snake_case via the documented normalizer.
        self.assertEqual(row["data_updated_at"], "2026-06-20T15:36:30+0000")
        # Periodicity lifted out of nested customFields."Common Core".
        self.assertEqual(row["update_frequency"], "Annually")
        self.assertEqual(row["data_uri"], "https://data.cdc.gov/resource/aaa0-bbb0")
        self.assertEqual(row["source_endpoint"], "catalog")
        # Unplaced fields (approvals, domain, …) surface in the drift audit.
        self.assertIn("approvals", res.unmapped)

    def test_catalog_row_without_id_is_skipped(self):
        res = normalize(get_endpoint("catalog"), [{"name": "orphan"}])
        self.assertEqual(res.rows.get("cdc_data_catalog", []), [])


class CuratedNormalizeTests(unittest.TestCase):
    def test_places_mapper_composes_key_and_maps_columns(self):
        res = normalize(get_endpoint("places_county"), places_rows())
        rows = res.rows["cdc_places_county"]
        self.assertEqual(len(rows), 3)
        row = rows[0]
        self.assertEqual(row["record_key"], "AR:05043:ARTHRITIS:CrdPrv")
        self.assertEqual(row["locationid"], "05043")
        self.assertEqual(row["data_value"], "29.9")
        self.assertEqual(row["source_endpoint"], "places_county")
        # The two data_value_type slices of one measure key separately.
        self.assertEqual(rows[1]["record_key"], "AR:05043:ARTHRITIS:AgeAdjPrv")

    def test_vsrr_mapper_key_matches_assignment_grain(self):
        res = normalize(get_endpoint("vsrr_drug_overdose"), vsrr_rows())
        keys = [r["record_key"] for r in res.rows["cdc_vsrr_drug_overdose"]]
        self.assertEqual(keys, ["CA:2023:January:Cocaine (T40.5)",
                                "CA:2023:February:Cocaine (T40.5)"])

    def test_missing_fields_become_null_not_keyerror(self):
        # Socrata omits null fields; a sparse row still normalizes.
        res = normalize(get_endpoint("heart_disease_mortality_county"),
                        [{"locationid": "01073", "year": "2022"}])
        row = res.rows["cdc_heart_disease_mortality"][0]
        self.assertEqual(row["record_key"], "01073:2022::")
        self.assertIsNone(row["data_value"])

    def test_row_missing_every_pk_field_is_skipped(self):
        res = normalize(get_endpoint("places_county"), [{"measure": "orphan"}])
        self.assertEqual(res.rows.get("cdc_places_county", []), [])

    def test_computed_region_noise_not_flagged_as_drift(self):
        res = normalize(get_endpoint("places_county"), places_rows())
        self.assertNotIn(":@computed_region_hjsp_umg2", res.unmapped)

    def test_reserved_word_field_renamed_sql_safe(self):
        # Live "group" (an SQL keyword) must land in group_field, both in
        # the column and in the composed key.
        res = normalize(get_endpoint("provisional_deaths_state"),
                        provisional_deaths_rows())
        rows = res.rows["cdc_provisional_deaths_state"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["group_field"], "By Total")
        self.assertNotIn("group", rows[0])
        self.assertEqual(
            rows[0]["record_key"],
            "By Total:::United States:All Sexes:All Ages")
        self.assertEqual(
            rows[1]["record_key"],
            "By Month:2021:1:United States:Male:65-74 years")

    def test_heart_disease_mapper(self):
        res = normalize(get_endpoint("heart_disease_mortality_county"),
                        heart_disease_rows())
        row = res.rows["cdc_heart_disease_mortality"][0]
        self.assertEqual(row["record_key"], "01073:2022:Overall:Overall")
        self.assertEqual(row["geographiclevel"], "County")


class GenericNormalizeTests(unittest.TestCase):
    def test_generic_rows_key_and_round_trip(self):
        raw = [{"b": 2, "a": 1}, {"a": 3}]
        rows = normalize_generic("zzzz-9999", raw)
        self.assertEqual(rows[0]["row_key"], "zzzz-9999:0")
        self.assertEqual(rows[1]["row_key"], "zzzz-9999:1")
        self.assertEqual(rows[0]["dataset_key"], "zzzz-9999")
        # dataset_key mirrored into source_endpoint for slice grammar.
        self.assertEqual(rows[0]["source_endpoint"], "zzzz-9999")
        self.assertEqual(json.loads(rows[0]["row_json"]), {"a": 1, "b": 2})

    def test_generic_rows_continue_from_start_idx(self):
        rows = normalize_generic("zzzz-9999", [{"a": 1}], start_idx=10)
        self.assertEqual(rows[0]["row_key"], "zzzz-9999:10")
        self.assertEqual(rows[0]["row_idx"], 10)


class ToSnakeTests(unittest.TestCase):
    def test_documented_casing_normalizer(self):
        self.assertEqual(to_snake("dataUpdatedAt"), "data_updated_at")
        self.assertEqual(to_snake("hideFromCatalog"), "hide_from_catalog")
        self.assertEqual(to_snake("already_snake"), "already_snake")
        self.assertEqual(to_snake("Update Frequency"), "update_frequency")

    def test_to_column_makes_reserved_words_sql_safe(self):
        self.assertEqual(to_column("group"), "group_field")
        self.assertEqual(to_column("order"), "order_field")
        self.assertEqual(to_column("data_value"), "data_value")


if __name__ == "__main__":
    unittest.main()
