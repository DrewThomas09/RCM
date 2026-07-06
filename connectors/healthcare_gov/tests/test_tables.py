import unittest

from ..endpoints import get_endpoint
from ..normalize import generic_rows, normalize
from ..tables import HealthcareGovStore
from .fakes import CATALOG_ITEMS, PLAN_ATTRIBUTES_ROWS


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthcareGovStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("plan_attributes_py2026")
        rows = normalize(spec, PLAN_ATTRIBUTES_ROWS).rows[
            "healthcare_gov_plan_attributes"]
        self.store.upsert("healthcare_gov_plan_attributes", rows)
        self.store.upsert("healthcare_gov_plan_attributes", rows)   # re-run
        self.assertEqual(
            self.store.count("healthcare_gov_plan_attributes"), 3)

    def test_upsert_updates_in_place_on_same_key(self):
        spec = get_endpoint("plan_attributes_py2026")
        old = normalize(spec, PLAN_ATTRIBUTES_ROWS[:1]).rows[
            "healthcare_gov_plan_attributes"]
        self.store.upsert("healthcare_gov_plan_attributes", old)
        changed = dict(PLAN_ATTRIBUTES_ROWS[0],
                       planmarketingname="Dental Value RENAMED")
        new = normalize(spec, [changed]).rows[
            "healthcare_gov_plan_attributes"]
        self.store.upsert("healthcare_gov_plan_attributes", new)
        self.assertEqual(
            self.store.count("healthcare_gov_plan_attributes"), 1)
        row = self.store.fetchall(
            "SELECT planmarketingname FROM healthcare_gov_plan_attributes "
            "WHERE plan_key = ?",
            ("plan_attributes_py2026:2026:21989AK0030001-00",))[0]
        self.assertEqual(row["planmarketingname"], "Dental Value RENAMED")

    def test_catalog_upsert_idempotent(self):
        rows = normalize(get_endpoint("catalog"), CATALOG_ITEMS).rows[
            "healthcare_gov_catalog"]
        self.store.upsert("healthcare_gov_catalog", rows)
        self.store.upsert("healthcare_gov_catalog", rows)
        self.assertEqual(self.store.count("healthcare_gov_catalog"), 2)

    def test_generic_rows_idempotent_and_json_preserved(self):
        rows = generic_rows("e4rr-zk4i",
                            [{"record_number": 1, "npn": "123"}])
        self.store.upsert("healthcare_gov_rows", rows)
        self.store.upsert("healthcare_gov_rows", rows)
        self.assertEqual(self.store.count("healthcare_gov_rows"), 1)
        row = self.store.fetchall(
            "SELECT row_json FROM healthcare_gov_rows WHERE row_key = ?",
            ("e4rr-zk4i:1",))[0]
        self.assertIn('"npn": "123"', row["row_json"])

    def test_coercion_lists_bools_to_text(self):
        # distribution_count is an int, keyword joins may stay lists in
        # future — the store must coerce anything scalar-ish to TEXT.
        self.store.upsert("healthcare_gov_catalog", [{
            "identifier": "x", "title": "T", "distribution_count": 2,
            "keyword": ["a", "b"], "source_endpoint": "catalog"}])
        row = self.store.fetchall(
            "SELECT distribution_count, keyword FROM healthcare_gov_catalog")[0]
        self.assertEqual(row["distribution_count"], "2")
        self.assertEqual(row["keyword"], '["a", "b"]')


if __name__ == "__main__":
    unittest.main()
