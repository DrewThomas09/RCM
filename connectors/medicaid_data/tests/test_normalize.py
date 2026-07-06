import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, normalize_generic
from .fakes import NADAC_2026_ID, catalog_item, nadac_row, sdud_row


class NormalizeTests(unittest.TestCase):
    def test_catalog_mapper_flattens_dcat_item(self):
        res = normalize(get_endpoint("catalog"), [catalog_item()])
        rows = res.rows["medicaid_data_catalog"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["identifier"], NADAC_2026_ID)
        self.assertEqual(row["themes"],
                         "National Average Drug Acquisition Cost")
        self.assertEqual(row["keywords"], "drug prices|pharmacy")
        self.assertEqual(row["publisher"], "data.medicaid.gov")
        self.assertEqual(row["contact_email"], "Medicaid.gov@cms.hhs.gov")
        self.assertEqual(row["periodicity"], "R/P7D")
        self.assertEqual(row["distribution_format"], "csv")
        self.assertEqual(row["n_distributions"], 1)
        self.assertEqual(
            row["api_url"],
            f"https://data.medicaid.gov/api/1/datastore/query/{NADAC_2026_ID}/0")
        self.assertEqual(row["source_endpoint"], "catalog")

    def test_nadac_mapper_composes_key_with_year_slice_prefix(self):
        res = normalize(get_endpoint("nadac_2026"), [nadac_row()])
        row = res.rows["medicaid_nadac"][0]
        # Prefixing with the endpoint key keeps year slices collision-free
        # in the SHARED medicaid_nadac table.
        self.assertEqual(row["nadac_key"],
                         "nadac_2026:24385005452:2025-12-17:2026-01-07")
        self.assertEqual(row["nadac_per_unit"], "0.26341")
        self.assertEqual(row["source_endpoint"], "nadac_2026")
        # The same raw row via nadac_2025 gets a DIFFERENT key + slice tag.
        res25 = normalize(get_endpoint("nadac_2025"), [nadac_row()])
        row25 = res25.rows["medicaid_nadac"][0]
        self.assertNotEqual(row25["nadac_key"], row["nadac_key"])
        self.assertEqual(row25["source_endpoint"], "nadac_2025")

    def test_sdud_mapper_composed_key_and_columns(self):
        res = normalize(get_endpoint("sdud_2025"), [sdud_row()])
        row = res.rows["medicaid_sdud"][0]
        self.assertEqual(row["sdud_key"],
                         "sdud_2025:FFSU:AK:00002143380:2025:4")
        self.assertEqual(row["total_amount_reimbursed"], "106607.76")
        self.assertEqual(row["product_name"], "TRULICITY ")
        self.assertEqual(row["source_endpoint"], "sdud_2025")

    def test_row_missing_first_id_field_is_skipped(self):
        rec = nadac_row()
        rec["ndc"] = ""
        res = normalize(get_endpoint("nadac_2026"), [rec])
        self.assertEqual(res.rows.get("medicaid_nadac", []), [])

    def test_unmapped_fields_are_audited(self):
        rec = nadac_row()
        rec["brand_new_dkan_column"] = "x"    # simulated schema drift
        res = normalize(get_endpoint("nadac_2026"), [rec])
        self.assertIn("brand_new_dkan_column", res.unmapped)

    def test_generic_mapper_row_json_and_absolute_idx(self):
        rows = [{"b": 2, "a": 1}, {"a": 3}]
        res = normalize_generic("uuid-1", rows, start_idx=500,
                                fetched_at="2026-07-06T00:00:00+00:00")
        out = res.rows["medicaid_data_rows"]
        self.assertEqual(out[0]["row_key"], "uuid-1:500")
        self.assertEqual(out[1]["row_key"], "uuid-1:501")
        self.assertEqual(out[0]["dataset_key"], "uuid-1")
        self.assertEqual(out[0]["row_idx"], 500)
        # Stable key order in the JSON so re-ingests compare equal.
        self.assertEqual(json.loads(out[0]["row_json"]), {"a": 1, "b": 2})
        self.assertEqual(out[0]["source_endpoint"], "uuid-1")

    def test_normalize_rejects_generic_kind(self):
        with self.assertRaises(KeyError):
            normalize(get_endpoint("fetched_rows"), [{"a": 1}])


if __name__ == "__main__":
    unittest.main()
