import unittest

from ..lookup import lookup_provider, lookup_taxonomy, validate
from ..query import QueryError, aggregate, query
from ..tables import NpiStore


def _seed_store(store: NpiStore) -> None:
    store.upsert("dim_provider", [
        {"npi": "1000000001", "enumeration_type": "NPI-1", "last_name": "DOE",
         "state": "MD", "primary_taxonomy_code": "207RC0000X",
         "source_endpoint": "provider_individual"},
        {"npi": "1000000002", "enumeration_type": "NPI-1", "last_name": "ROE",
         "state": "MD", "primary_taxonomy_code": "207R00000X",
         "source_endpoint": "provider_individual"},
        {"npi": "1000000003", "enumeration_type": "NPI-2",
         "organization_name": "GENERAL HOSPITAL", "state": "NY",
         "primary_taxonomy_code": "282N00000X",
         "source_endpoint": "provider_organization"}])
    store.upsert("fact_provider_taxonomy", [
        {"taxonomy_key": "1000000001:207RC0000X", "npi": "1000000001",
         "code": "207RC0000X", "desc": "Cardiovascular Disease", "is_primary": "1"},
        {"taxonomy_key": "1000000002:207RC0000X", "npi": "1000000002",
         "code": "207RC0000X", "desc": "Cardiovascular Disease", "is_primary": "0"}])
    store.upsert("fact_provider_address", [
        {"address_key": "1000000001:LOCATION", "npi": "1000000001",
         "address_purpose": "LOCATION", "city": "BALTIMORE", "state": "MD"}])


class StoreUpsertTests(unittest.TestCase):
    def setUp(self):
        self.store = NpiStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent_and_updates(self):
        self.store.upsert("dim_provider", [
            {"npi": "1000000001", "last_name": "OLD",
             "source_endpoint": "provider_individual"}])
        self.store.upsert("dim_provider", [
            {"npi": "1000000001", "last_name": "NEW",
             "source_endpoint": "provider_individual"}])
        self.assertEqual(self.store.count("dim_provider"), 1)
        row = self.store.fetchall("SELECT last_name FROM dim_provider")[0]
        self.assertEqual(row["last_name"], "NEW")


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = NpiStore(":memory:")
        _seed_store(self.store)

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "npi_provider", filters={"state": "MD"})
        self.assertEqual(res.total, 2)

    def test_like_filter(self):
        res = query(self.store, "npi_provider",
                    filters={"organization_name__like": "%HOSPITAL%"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["npi"], "1000000003")

    def test_in_filter(self):
        res = query(self.store, "npi_provider",
                    filters={"npi__in": ["1000000001", "1000000003"]})
        self.assertEqual(res.total, 2)

    def test_aggregate_by_state(self):
        res = aggregate(self.store, "npi_provider", group_by=["state"])
        top = {r["state"]: r["count"] for r in res.rows}
        self.assertEqual(top["MD"], 2)
        self.assertEqual(top["NY"], 1)

    def test_aggregate_by_primary_taxonomy(self):
        res = aggregate(self.store, "npi_provider",
                        group_by=["primary_taxonomy_code"])
        self.assertEqual(res.rows[0]["count"], 1)  # each distinct here

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "npi_provider", filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "npi_not_a_dataset")

    def test_limit_is_clamped(self):
        res = query(self.store, "npi_provider", limit=999999)
        self.assertEqual(res.limit, 1000)  # _MAX_LIMIT


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = NpiStore(":memory:")
        _seed_store(self.store)

    def tearDown(self):
        self.store.close()

    def test_lookup_provider_fans_out(self):
        out = lookup_provider(self.store, "1000000001")
        self.assertTrue(out["found"])
        self.assertEqual(out["provider"]["last_name"], "DOE")
        self.assertEqual(out["taxonomies"]["count"], 1)
        self.assertEqual(out["addresses"]["count"], 1)
        self.assertEqual(out["addresses"]["rows"][0]["city"], "BALTIMORE")

    def test_lookup_taxonomy_returns_primary_providers(self):
        out = lookup_taxonomy(self.store, "207RC0000X")
        # Only provider 1 has this as PRIMARY taxonomy.
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["providers"][0]["npi"], "1000000001")

    def test_validate_handler(self):
        self.assertTrue(validate(self.store, "1234567893")["valid"])
        self.assertFalse(validate(self.store, "1234567890")["valid"])


if __name__ == "__main__":
    unittest.main()
