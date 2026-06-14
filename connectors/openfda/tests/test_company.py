import unittest

from ..lookup import lookup_company, search_companies, v1_handlers
from ..tables import OpenFdaStore


class CompanyRollupTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")
        # Same company key across a drug and a device record.
        self.store.upsert("dim_company", [
            {"company_key": "co_acme", "normalized_name": "Acme Pharma",
             "kind": "drug_labeler"}])
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "proprietary_name": "FOO", "rxcui": "1",
             "company_key": "co_acme", "source_endpoint": "drug_ndc"}])
        self.store.upsert("dim_drug_approval", [
            {"application_number": "NDA001", "brand_name": "FOO",
             "company_key": "co_acme", "source_endpoint": "drugsfda"}])
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "device_name": "Widget",
             "decision_date": "2020-01-01", "company_key": "co_acme",
             "source_endpoint": "device_510k"}])
        self.store.upsert("fact_device_recall", [
            {"recall_id": "ENF:Z1", "product_code": "ABC",
             "company_key": "co_acme", "source_endpoint": "device_enforcement"}])
        self.store.upsert("fact_drug_adverse_event", [
            {"safetyreportid": "9", "ndc": "0002-1200", "company_key": "co_acme"}])

    def tearDown(self):
        self.store.close()

    def test_rollup_spans_drug_and_device(self):
        out = lookup_company(self.store, "co_acme")
        self.assertEqual(out["company_key"], "co_acme")
        self.assertEqual(out["drug_products"]["count"], 1)
        self.assertEqual(out["drug_approvals"]["count"], 1)
        self.assertEqual(out["devices"]["count"], 1)
        self.assertEqual(out["devices"]["product_codes"], ["ABC"])
        self.assertEqual(out["device_recalls"], 1)
        self.assertEqual(out["drug_adverse_events"], 1)
        self.assertEqual(out["ndcs"], ["0002-1200"])

    def test_raw_name_is_normalized_to_key(self):
        # "Acme Pharmaceuticals, Inc." normalizes to co_acme.
        out = lookup_company(self.store, "Acme Pharmaceuticals, Inc.")
        self.assertEqual(out["company_key"], "co_acme")
        self.assertEqual(out["drug_products"]["count"], 1)

    def test_unresolvable_company_is_handled(self):
        out = lookup_company(self.store, "")
        self.assertIsNone(out["company_key"])

    def test_search_companies_fuzzy(self):
        rows = search_companies(self.store, "acme")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company_key"], "co_acme")

    def test_company_route_in_handler_map(self):
        handlers = v1_handlers(self.store)
        self.assertIn("/v1/lookup/company/{company_key}", handlers)
        out = handlers["/v1/lookup/company/{company_key}"]("co_acme")
        self.assertEqual(out["company_key"], "co_acme")


if __name__ == "__main__":
    unittest.main()
