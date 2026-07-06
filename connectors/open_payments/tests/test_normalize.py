import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, normalize_generic
from .fakes import CATALOG_ITEMS, GENERAL_UUID, general_payment_row, state_totals_row


class NormalizeCatalogTests(unittest.TestCase):
    def test_catalog_entry_flattened(self):
        res = normalize(get_endpoint("catalog"), CATALOG_ITEMS)
        rows = res.rows["open_payments_catalog"]
        self.assertEqual(len(rows), 3)
        row = {r["identifier"]: r for r in rows}[GENERAL_UUID]
        self.assertEqual(row["title"], "2024 General Payment Data")
        self.assertEqual(row["theme"], "General Payments")
        self.assertEqual(row["keyword"], "2024")
        self.assertEqual(row["media_type"], "text/csv")
        self.assertTrue(row["download_url"].endswith(".csv"))
        self.assertEqual(row["n_distributions"], 1)
        self.assertEqual(
            row["api_url"],
            f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{GENERAL_UUID}/0")
        self.assertEqual(
            row["landing_page"],
            f"https://openpaymentsdata.cms.gov/dataset/{GENERAL_UUID}")
        self.assertEqual(row["contact_email"], "openpayments@cms.hhs.gov")
        self.assertEqual(row["publisher"], "openpaymentsdata.cms.gov")
        self.assertEqual(row["bureau_code"], "009:38")
        self.assertEqual(row["source_endpoint"], "catalog")

    def test_catalog_entry_missing_temporal_is_fine(self):
        res = normalize(get_endpoint("catalog"), [CATALOG_ITEMS[2]])
        row = res.rows["open_payments_catalog"][0]
        self.assertIsNone(row["temporal"])
        self.assertEqual(row["title"], "Summary Dashboard")

    def test_catalog_entry_missing_identifier_is_skipped(self):
        res = normalize(get_endpoint("catalog"), [{"title": "orphan"}])
        self.assertEqual(res.rows.get("open_payments_catalog", []), [])


class NormalizeDatastoreTests(unittest.TestCase):
    def test_general_payment_row_keeps_native_columns(self):
        rec = general_payment_row("1092248200")
        res = normalize(get_endpoint("general_payments_2024"), [rec])
        rows = res.rows["op_general_payment"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["record_id"], "1092248200")
        self.assertEqual(row["recipient_state"], "VT")
        self.assertEqual(row["total_amount_of_payment_usdollars"], "175.14")
        self.assertEqual(row["nature_of_payment_or_transfer_of_value"],
                         "Food and Beverage")
        # Absent native columns are NULL-filled, not dropped.
        self.assertIsNone(row["city_of_travel"])
        self.assertEqual(row["source_endpoint"], "general_payments_2024")
        # Every native column made it through (91 + pk-shared).
        self.assertEqual(len(row), 91 + 1)      # + source_endpoint

    def test_row_missing_record_id_is_skipped(self):
        rec = general_payment_row("x")
        del rec["record_id"]
        res = normalize(get_endpoint("general_payments_2024"), [rec])
        self.assertEqual(res.rows.get("op_general_payment", []), [])

    def test_state_totals_composed_key(self):
        rec = state_totals_row("VT", "Food and Beverage")
        res = normalize(get_endpoint("state_payment_totals"), [rec])
        row = res.rows["op_state_payment_totals"][0]
        self.assertEqual(
            row["state_totals_key"],
            "US:VT:2024:Food and Beverage:Covered Recipient Physician")
        self.assertEqual(row["source_endpoint"], "state_payment_totals")

    def test_by_entity_nature_composed_key(self):
        rec = {"amgpo_id": "100000000053", "nature_of_payment_type_code": "1",
               "number_of_transaction": "2611", "total_amount": "8248491.89",
               "amgpo_name": "MERCK SHARP & DOHME LLC"}
        res = normalize(get_endpoint("payments_by_entity_nature_2024"), [rec])
        row = res.rows["op_payments_by_entity_nature"][0]
        self.assertEqual(row["entity_nature_key"], "100000000053:1")
        self.assertEqual(row["amgpo_name"], "MERCK SHARP & DOHME LLC")

    def test_unknown_field_recorded_as_unmapped_drift(self):
        rec = general_payment_row("1")
        rec["brand_new_cms_field"] = "surprise"
        res = normalize(get_endpoint("general_payments_2024"), [rec])
        self.assertIn("brand_new_cms_field", res.unmapped)


class NormalizeGenericTests(unittest.TestCase):
    def test_rows_wrapped_as_json_with_stable_keys(self):
        recs = [general_payment_row("1"), general_payment_row("2")]
        res = normalize_generic("some-uuid", recs, row_offset=500)
        rows = res.rows["open_payments_rows"]
        self.assertEqual(rows[0]["row_key"], "some-uuid:00000500")
        self.assertEqual(rows[1]["row_key"], "some-uuid:00000501")
        self.assertEqual(rows[0]["dataset_key"], "some-uuid")
        # dataset_key doubles as source_endpoint for slice pinning.
        self.assertEqual(rows[0]["source_endpoint"], "some-uuid")
        round_tripped = json.loads(rows[0]["row_json"])
        self.assertEqual(round_tripped["record_id"], "1")
        self.assertTrue(rows[0]["fetched_at"].endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
