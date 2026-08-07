import unittest

from ..lookup import lookup_benchmarks, lookup_clinician, lookup_organizations
from ..query import QueryError, aggregate, query
from ..tables import QppStore


def _seed(store):
    store.upsert("qpp_clinician", [
        {"npi_year": "1234567893:2025", "npi": "1234567893", "year": "2025",
         "first_name": "JANE", "last_name": "DOE",
         "specialty_description": "Internal Medicine",
         "n_organizations": "2", "source_endpoint": "eligibility"},
        {"npi_year": "1234567893:2024", "npi": "1234567893", "year": "2024",
         "first_name": "JANE", "last_name": "DOE",
         "specialty_description": "Internal Medicine",
         "n_organizations": "1", "source_endpoint": "eligibility"},
        {"npi_year": "1932296556:2025", "npi": "1932296556", "year": "2025",
         "first_name": "JOHN", "last_name": "SMITH",
         "specialty_description": "Cardiology",
         "n_organizations": "1", "source_endpoint": "eligibility"},
    ])
    store.upsert("qpp_organization", [
        {"org_key": "1234567893:2025:0", "npi": "1234567893", "year": "2025",
         "org_idx": "0", "org_name": "ACME MEDICAL GROUP",
         "source_endpoint": "organizations"},
        {"org_key": "1234567893:2025:1", "npi": "1234567893", "year": "2025",
         "org_idx": "1", "org_name": "BETA CLINIC",
         "source_endpoint": "organizations"},
    ])
    store.upsert("qpp_benchmark", [
        {"benchmark_key": "2025:001:registry:2023", "measure_id": "001",
         "performance_year": "2025", "benchmark_year": "2023",
         "submission_method": "registry", "source_endpoint": "benchmarks"},
        {"benchmark_key": "2025:001:claims:2023", "measure_id": "001",
         "performance_year": "2025", "benchmark_year": "2023",
         "submission_method": "claims", "source_endpoint": "benchmarks"},
        {"benchmark_key": "2024:001:claims:2022", "measure_id": "001",
         "performance_year": "2024", "benchmark_year": "2022",
         "submission_method": "claims", "source_endpoint": "benchmarks"},
    ])


class StoreUpsertTests(unittest.TestCase):
    def test_upsert_is_idempotent_and_updates(self):
        store = QppStore(":memory:")
        try:
            store.upsert("qpp_clinician", [
                {"npi_year": "1:2025", "npi": "1", "year": "2025",
                 "first_name": "OLD", "source_endpoint": "eligibility"}])
            store.upsert("qpp_clinician", [
                {"npi_year": "1:2025", "npi": "1", "year": "2025",
                 "first_name": "NEW", "source_endpoint": "eligibility"}])
            self.assertEqual(store.count("qpp_clinician"), 1)
            row = store.fetchall("SELECT first_name FROM qpp_clinician")[0]
            self.assertEqual(row["first_name"], "NEW")
        finally:
            store.close()


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = QppStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_each_dataset_slices_its_own_table(self):
        self.assertEqual(query(self.store, "qpp_eligibility").total, 3)
        self.assertEqual(query(self.store, "qpp_organizations").total, 2)
        self.assertEqual(query(self.store, "qpp_benchmarks").total, 3)

    def test_year_filter(self):
        res = query(self.store, "qpp_eligibility", filters={"year": "2025"})
        self.assertEqual(res.total, 2)

    def test_aggregate_by_submission_method(self):
        res = aggregate(self.store, "qpp_benchmarks",
                        group_by=["submission_method"])
        counts = {r["submission_method"]: r["count"] for r in res.rows}
        self.assertEqual(counts["claims"], 2)
        self.assertEqual(counts["registry"], 1)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "qpp_eligibility",
                  filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "qpp_not_a_dataset")


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = QppStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_lookup_clinician_spans_years_and_orgs(self):
        out = lookup_clinician(self.store, "1234567893")
        self.assertEqual(out["years"], ["2024", "2025"])
        self.assertEqual(len(out["clinician"]), 2)
        self.assertEqual(len(out["organizations"]), 2)

    def test_lookup_clinician_unknown_is_empty(self):
        out = lookup_clinician(self.store, "9999999999")
        self.assertEqual(out["clinician"], [])
        self.assertEqual(out["years"], [])

    def test_lookup_organizations(self):
        out = lookup_organizations(self.store, "1234567893")
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["organizations"][0]["org_name"],
                         "ACME MEDICAL GROUP")

    def test_lookup_benchmarks_all_years_and_pinned_year(self):
        out = lookup_benchmarks(self.store, "001")
        self.assertEqual(out["count"], 3)
        out25 = lookup_benchmarks(self.store, "001", "2025")
        self.assertEqual(out25["count"], 2)
        self.assertEqual([b["submission_method"] for b in out25["benchmarks"]],
                         ["claims", "registry"])


if __name__ == "__main__":
    unittest.main()
