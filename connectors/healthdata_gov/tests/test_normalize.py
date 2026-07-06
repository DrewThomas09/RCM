import json
import unittest

from ..endpoints import get_endpoint
from ..flatten import to_column, to_snake
from ..normalize import normalize, normalize_generic
from .fakes import (catalog_items, community_profile_rows,
                    facility_capacity_rows, pcr_testing_rows,
                    policy_orders_rows, school_modality_rows, state_ts_rows,
                    therapeutics_rows)


class CatalogNormalizeTests(unittest.TestCase):
    def test_catalog_mapper_snake_cases_and_lifts_common_core(self):
        res = normalize(get_endpoint("catalog"), catalog_items(1))
        rows = res.rows["healthdata_gov_catalog"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["dataset_uid"], "aaa0-bbb0")
        self.assertEqual(row["name"], "Test Dataset 0")
        # camelCase → snake_case via the documented normalizer.
        self.assertEqual(row["data_updated_at"], "2026-06-20T15:36:30+0000")
        # Periodicity lifted out of nested customFields."Common Core".
        self.assertEqual(row["update_frequency"], "Weekly")
        self.assertEqual(row["data_uri"], "https://healthdata.gov/resource/aaa0-bbb0")
        self.assertEqual(row["source_endpoint"], "catalog")
        # Unplaced fields (approvals, externalId, …) surface in the audit.
        self.assertIn("approvals", res.unmapped)

    def test_catalog_mapper_carries_hub_vs_copy_domain(self):
        # healthdata.gov is a meta-catalog: domain + attribution are what
        # let mirror entries be deduped against the rest of the estate.
        # Live anatomy: hub natives and federal-portal mirrors both live
        # on datahub.hhs.gov (attribution tells them apart); state-portal
        # copies carry domain=healthdata.gov.
        res = normalize(get_endpoint("catalog"), catalog_items(3))
        rows = res.rows["healthdata_gov_catalog"]
        self.assertEqual(rows[0]["domain"], "datahub.hhs.gov")
        self.assertEqual(rows[0]["attribution"],
                         "U.S. Department of Health & Human Services")
        self.assertEqual(rows[1]["domain"], "datahub.hhs.gov")
        self.assertEqual(rows[1]["attribution"], "data.cdc.gov")
        self.assertEqual(rows[2]["domain"], "healthdata.gov")
        self.assertEqual(rows[2]["attribution"], "chhs.data.ca.gov")
        self.assertNotIn("domain", res.unmapped)

    def test_catalog_row_without_id_is_skipped(self):
        res = normalize(get_endpoint("catalog"), [{"name": "orphan"}])
        self.assertEqual(res.rows.get("healthdata_gov_catalog", []), [])


class CuratedNormalizeTests(unittest.TestCase):
    def test_facility_mapper_composes_key_and_maps_columns(self):
        res = normalize(get_endpoint("hospital_capacity_facility"),
                        facility_capacity_rows())
        rows = res.rows["hhs_hospital_capacity_facility"]
        self.assertEqual(len(rows), 3)
        row = rows[0]
        self.assertEqual(row["record_key"], "010039:2024-04-21T00:00:00.000")
        self.assertEqual(row["ccn"], "010039")
        self.assertEqual(row["total_beds_7_day_avg"], "941.9")
        self.assertEqual(row["source_endpoint"], "hospital_capacity_facility")
        # Consecutive weeks of one hospital key separately.
        self.assertEqual(rows[1]["record_key"],
                         "010039:2024-04-14T00:00:00.000")

    def test_state_ts_mapper_key_is_state_date(self):
        res = normalize(get_endpoint("hospital_capacity_state_ts"),
                        state_ts_rows())
        keys = [r["record_key"]
                for r in res.rows["hhs_hospital_capacity_state_ts"]]
        self.assertEqual(keys, ["AL:2024-04-26T00:00:00.000",
                                "AL:2024-04-25T00:00:00.000",
                                "TX:2024-04-26T00:00:00.000"])

    def test_pcr_mapper_key_includes_outcome_dimension(self):
        # (state, date) alone under-keys: Positive and Negative rows share
        # the day — the live-verified grain adds overall_outcome.
        res = normalize(get_endpoint("covid_pcr_testing"), pcr_testing_rows())
        keys = [r["record_key"] for r in res.rows["hhs_covid_pcr_testing"]]
        self.assertEqual(keys, [
            "AL:2020-03-01T00:00:00.000:Negative",
            "AL:2020-03-01T00:00:00.000:Positive",
            "TX:2020-03-01T00:00:00.000:Positive"])

    def test_therapeutics_mapper_keys_same_site_pharmacies_apart(self):
        # The live duplicate that shaped the key: two Kaiser pharmacies in
        # one building differ only in address2.
        res = normalize(get_endpoint("covid_therapeutics_locator"),
                        therapeutics_rows())
        rows = res.rows["hhs_covid_therapeutics_locator"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r["record_key"] for r in rows}), 3)
        self.assertIn("Hosp Bldg FL 1 Discharge Pharmacy",
                      rows[0]["record_key"])
        self.assertIn("Outpatient Pharmacy", rows[1]["record_key"])

    def test_policy_orders_mapper_keys_comment_variants_apart(self):
        # Same county/date/type/start differing only in comments/source —
        # the live duplicate that pushed both fields into the key.
        res = normalize(get_endpoint("covid_policy_orders"),
                        policy_orders_rows())
        rows = res.rows["hhs_covid_policy_orders"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r["record_key"] for r in rows}), 3)

    def test_missing_fields_become_null_not_keyerror(self):
        # Socrata omits null fields; a sparse row still normalizes.
        res = normalize(get_endpoint("hospital_capacity_facility"),
                        [{"hospital_pk": "450054",
                          "collection_week": "2024-04-21T00:00:00.000"}])
        row = res.rows["hhs_hospital_capacity_facility"][0]
        self.assertEqual(row["record_key"], "450054:2024-04-21T00:00:00.000")
        self.assertIsNone(row["total_beds_7_day_avg"])

    def test_row_missing_every_pk_field_is_skipped(self):
        res = normalize(get_endpoint("hospital_capacity_facility"),
                        [{"hospital_name": "orphan"}])
        self.assertEqual(res.rows.get("hhs_hospital_capacity_facility", []), [])

    def test_sparse_policy_row_keys_with_empty_segments(self):
        # State-level orders carry no county/fips — they compose as "".
        res = normalize(get_endpoint("covid_policy_orders"),
                        policy_orders_rows()[2:])
        row = res.rows["hhs_covid_policy_orders"][0]
        self.assertTrue(row["record_key"].startswith("DE:::state:"))

    def test_computed_region_noise_not_flagged_as_drift(self):
        res = normalize(get_endpoint("hospital_capacity_facility"),
                        facility_capacity_rows())
        self.assertNotIn(":@computed_region_abcd_1234", res.unmapped)

    def test_school_and_county_profile_mappers(self):
        res = normalize(get_endpoint("school_learning_modalities"),
                        school_modality_rows())
        rows = res.rows["hhs_school_learning_modalities"]
        self.assertEqual(rows[0]["record_key"],
                         "0100005:2022-12-25T00:00:00.000")
        res2 = normalize(get_endpoint("community_profile_county"),
                         community_profile_rows())
        rows2 = res2.rows["hhs_community_profile_county"]
        # CPR stores county FIPS unpadded ("1089") — keyed verbatim.
        self.assertEqual(rows2[0]["record_key"],
                         "1089:2023-05-10T00:00:00.000")


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

    def test_generic_rows_slice_params_sign_the_key(self):
        plain = normalize_generic("zzzz-9999", [{"a": 1}])
        sliced = normalize_generic("zzzz-9999", [{"a": 1}],
                                   slice_params={"state": "AL"})
        self.assertNotEqual(plain[0]["row_key"], sliced[0]["row_key"])
        self.assertIn("_slice_params", json.loads(sliced[0]["row_json"]))
        # Empty filters degrade to the plain key shape.
        empty = normalize_generic("zzzz-9999", [{"a": 1}], slice_params={})
        self.assertEqual(empty[0]["row_key"], plain[0]["row_key"])


class ToSnakeTests(unittest.TestCase):
    def test_documented_casing_normalizer(self):
        self.assertEqual(to_snake("dataUpdatedAt"), "data_updated_at")
        self.assertEqual(to_snake("hideFromCatalog"), "hide_from_catalog")
        self.assertEqual(to_snake("already_snake"), "already_snake")
        self.assertEqual(to_snake("Update Frequency"), "update_frequency")

    def test_to_column_makes_reserved_words_sql_safe(self):
        self.assertEqual(to_column("group"), "group_field")
        self.assertEqual(to_column("order"), "order_field")
        self.assertEqual(to_column("courses_available"), "courses_available")
        # A live healthdata.gov quirk: trailing underscores pass through
        # verbatim (sgxm-t72h's ..._suspected_80_ field).
        self.assertEqual(
            to_column("previous_day_admission_adult_covid_suspected_80_"),
            "previous_day_admission_adult_covid_suspected_80_")


if __name__ == "__main__":
    unittest.main()
