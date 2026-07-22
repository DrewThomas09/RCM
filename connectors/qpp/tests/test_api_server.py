"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the QPP ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import QppStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = QppStore(":memory:")
        self.store.upsert("qpp_clinician", [
            {"npi_year": "1234567893:2025", "npi": "1234567893",
             "year": "2025", "first_name": "JANE", "last_name": "DOE",
             "specialty_description": "Internal Medicine",
             "source_endpoint": "eligibility"}])
        self.store.upsert("qpp_organization", [
            {"org_key": "1234567893:2025:0", "npi": "1234567893",
             "year": "2025", "org_idx": "0",
             "org_name": "ACME MEDICAL GROUP",
             "source_endpoint": "organizations"}])
        self.store.upsert("qpp_benchmark", [
            {"benchmark_key": "2025:001:registry:2023", "measure_id": "001",
             "performance_year": "2025", "benchmark_year": "2023",
             "submission_method": "registry",
             "source_endpoint": "benchmarks"},
            {"benchmark_key": "2025:002:claims:2023", "measure_id": "002",
             "performance_year": "2025", "benchmark_year": "2023",
             "submission_method": "claims",
             "source_endpoint": "benchmarks"}])
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

    def test_status_row_shape(self):
        status, body = self._get("/v1/status")
        self.assertEqual(status, 200)
        row = body["connectors"][0]
        self.assertEqual(row["connector"], "qpp")
        self.assertEqual(row["total_rows"], 4)
        self.assertEqual(row["tables"]["qpp_benchmark"], 2)

    def test_datasets_auto_exposed_from_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertEqual(ids, {"qpp_eligibility", "qpp_organizations",
                               "qpp_benchmarks"})

    def test_query_dataset_filter(self):
        status, body = self._get(
            "/v1/query/qpp_benchmarks?submission_method=claims")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["measure_id"], "002")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/qpp_benchmarks/aggregate?group_by=performance_year")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0],
                         {"performance_year": "2025", "count": 2})

    def test_lookup_clinician_route(self):
        status, body = self._get("/v1/lookup/qpp-clinician/1234567893")
        self.assertEqual(status, 200)
        self.assertEqual(body["years"], ["2025"])
        self.assertEqual(len(body["organizations"]), 1)

    def test_lookup_organizations_route(self):
        status, body = self._get("/v1/lookup/qpp-organizations/1234567893")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)

    def test_lookup_benchmarks_route_with_year(self):
        status, body = self._get("/v1/lookup/qpp-benchmarks/001?year=2025")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/qpp_benchmarks?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
