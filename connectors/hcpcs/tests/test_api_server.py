"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the HCPCS ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import HcpcsStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = HcpcsStore(":memory:")
        self.store.upsert("dim_hcpcs_code", [
            {"code_key": "lvl2:J9271", "code_type": "lvl2", "code": "J9271",
             "display": "Injection, pembrolizumab, 1 mg",
             "section": "J", "category": "J92", "source_endpoint": "lvl2"},
            {"code_key": "lvl2:J9299", "code_type": "lvl2", "code": "J9299",
             "display": "Injection, nivolumab, 1 mg",
             "section": "J", "category": "J92", "source_endpoint": "lvl2"},
            {"code_key": "lvl2:E0601", "code_type": "lvl2", "code": "E0601",
             "display": "Continuous positive airway pressure (CPAP) device",
             "section": "E", "category": "E06", "source_endpoint": "lvl2"},
            {"code_key": "lvl2:A0428", "code_type": "lvl2", "code": "A0428",
             "display": "Ambulance service, BLS, non-emergency",
             "section": "A", "category": "A04", "source_endpoint": "lvl2"}])
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
        self.assertEqual(row["connector"], "hcpcs")
        self.assertEqual(row["total_rows"], 4)

    def test_datasets_auto_exposed_from_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertEqual(ids, {"hcpcs_lvl2"})

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/hcpcs_lvl2?code__like=J92%25&sort=-code&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["code"], "J9299")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/hcpcs_lvl2/aggregate?group_by=section")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"section": "J", "count": 2})

    def test_lookup_code_route(self):
        status, body = self._get("/v1/lookup/hcpcs/J9271")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_key"], "lvl2:J9271")

    def test_lookup_section_route(self):
        status, body = self._get("/v1/lookup/hcpcs-section/J")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 2)

    def test_search_route(self):
        status, body = self._get("/v1/lookup/hcpcs-search/ambulance")
        self.assertEqual(status, 200)
        self.assertEqual([r["code"] for r in body["results"]], ["A0428"])

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/hcpcs_lvl2?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
