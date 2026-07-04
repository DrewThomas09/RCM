"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM convention of exercising the real path over a socket
(no mocks for our own code) — a live ``ThreadingHTTPServer`` serving the
NPI ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import NpiStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = NpiStore(":memory:")
        self.store.upsert("dim_provider", [
            {"npi": "1000000001", "enumeration_type": "NPI-1", "last_name": "DOE",
             "state": "MD", "primary_taxonomy_code": "207RC0000X",
             "source_endpoint": "provider_individual"},
            {"npi": "1000000002", "enumeration_type": "NPI-1", "last_name": "ROE",
             "state": "MD", "primary_taxonomy_code": "207RC0000X",
             "source_endpoint": "provider_individual"}])
        self.store.upsert("fact_provider_taxonomy", [
            {"taxonomy_key": "1000000001:207RC0000X", "npi": "1000000001",
             "code": "207RC0000X", "desc": "Cardiovascular Disease",
             "is_primary": "1"}])
        self.store.upsert("fact_provider_address", [
            {"address_key": "1000000001:LOCATION", "npi": "1000000001",
             "address_purpose": "LOCATION", "city": "BALTIMORE", "state": "MD"}])
        self.server, self.port = make_server(self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.store.close()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_health(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_datasets_auto_exposed_from_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertEqual(
            ids, {"npi_provider", "npi_provider_taxonomy", "npi_provider_address"})
        self.assertTrue(all(d["source"] == "npi_registry" for d in body["datasets"]))

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/npi_provider?state=MD&sort=-last_name&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["last_name"], "ROE")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/npi_provider/aggregate?group_by=primary_taxonomy_code")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0],
                         {"primary_taxonomy_code": "207RC0000X", "count": 2})

    def test_lookup_provider_route(self):
        status, body = self._get("/v1/lookup/provider/1000000001")
        self.assertEqual(status, 200)
        self.assertTrue(body["found"])
        self.assertEqual(body["taxonomies"]["count"], 1)
        self.assertEqual(body["addresses"]["rows"][0]["city"], "BALTIMORE")

    def test_validate_route(self):
        status, body = self._get("/v1/validate/npi/1234567893")
        self.assertEqual(status, 200)
        self.assertTrue(body["valid"])
        status, body = self._get("/v1/validate/npi/1234567890")
        self.assertEqual(status, 200)
        self.assertFalse(body["valid"])

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/npi_provider?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
