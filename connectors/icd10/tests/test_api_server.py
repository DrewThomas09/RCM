"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the ICD-10 ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import Icd10Store


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = Icd10Store(":memory:")
        self.store.upsert("dim_icd10_code", [
            {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
             "name": "Type 2 diabetes mellitus without complications",
             "chapter": "E", "category": "E11", "source_endpoint": "cm"},
            {"code_key": "cm:E11.65", "code_type": "cm", "code": "E11.65",
             "name": "Type 2 diabetes mellitus with hyperglycemia",
             "chapter": "E", "category": "E11", "source_endpoint": "cm"},
            {"code_key": "cm:A00.0", "code_type": "cm", "code": "A00.0",
             "name": "Cholera", "chapter": "A", "category": "A00",
             "source_endpoint": "cm"},
            {"code_key": "pcs:0DTJ4ZZ", "code_type": "pcs", "code": "0DTJ4ZZ",
             "name": "Resection of Appendix", "chapter": "0", "category": "0DT",
             "source_endpoint": "pcs"}])
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
        self.assertEqual(ids, {"icd10_cm", "icd10_pcs"})

    def test_query_dataset_slice_and_sort(self):
        status, body = self._get(
            "/v1/query/icd10_cm?code__like=E11%25&sort=-code&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)      # PCS + A00 excluded
        self.assertEqual(body["rows"][0]["code"], "E11.9")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/icd10_cm/aggregate?group_by=chapter")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"chapter": "E", "count": 2})

    def test_lookup_code_route(self):
        status, body = self._get("/v1/lookup/code/E11.65")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_key"], "cm:E11.65")

    def test_lookup_code_pcs_via_type_param(self):
        status, body = self._get("/v1/lookup/code/0DTJ4ZZ?type=pcs")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_type"], "pcs")

    def test_lookup_category_route(self):
        status, body = self._get("/v1/lookup/category/E11")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 2)

    def test_search_route(self):
        status, body = self._get("/v1/search/cm?q=cholera")
        self.assertEqual(status, 200)
        self.assertEqual([r["code"] for r in body["results"]], ["A00.0"])

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/icd10_cm?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
