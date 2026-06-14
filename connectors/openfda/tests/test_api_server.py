"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live `ThreadingHTTPServer` serving
the openFDA `/v1` surface.
"""
import json
import threading
import unittest
import urllib.request

from ..api_server import make_server
from ..tables import OpenFdaStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "device_class": "2",
             "decision_date": "2019-01-01", "decision_type": "SESE",
             "source_endpoint": "device_510k"},
            {"device_key": "K:2", "product_code": "ABC", "device_class": "2",
             "decision_date": "2020-01-01", "decision_type": "SESE",
             "source_endpoint": "device_510k"},
            {"device_key": "CLASS:ABC", "product_code": "ABC",
             "source_endpoint": "device_classification"}])
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "proprietary_name": "FOO", "rxcui": "1234",
             "source_endpoint": "drug_ndc"}])
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
        self.assertIn("openfda_device_510k", ids)
        self.assertEqual(len(body["datasets"]), 12)

    def test_query_dataset_slice_and_sort(self):
        status, body = self._get(
            "/v1/query/openfda_device_510k?product_code=ABC&sort=-decision_date&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)  # classification row excluded by slice
        self.assertEqual(body["rows"][0]["decision_date"], "2020-01-01")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/openfda_device_510k/aggregate?group_by=product_code")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"product_code": "ABC", "count": 2})

    def test_lookup_drug_route(self):
        status, body = self._get("/v1/lookup/drug/0002-1200")
        self.assertEqual(status, 200)
        self.assertEqual(body["rxcui"], "1234")

    def test_lookup_device_route(self):
        status, body = self._get("/v1/lookup/device/ABC")
        self.assertEqual(status, 200)
        self.assertEqual(body["clearance_count"], 2)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/openfda_device_510k?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
