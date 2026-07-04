"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the CMS Coverage ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import CmsCoverageStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsCoverageStore(":memory:")
        self.store.upsert("dim_coverage_document", [
            {"document_key": "NCD:169:2", "document_id": "169",
             "document_version": "2", "document_type": "NCD",
             "title": "Home Use of Oxygen", "chapter": "240",
             "coverage_level": "national", "last_updated_sort": "20241202",
             "source_endpoint": "national_ncd"},
            {"document_key": "NCD:170:1", "document_id": "170",
             "document_type": "NCD", "title": "Oxygen Therapy", "chapter": "240",
             "coverage_level": "national", "last_updated_sort": "20230101",
             "source_endpoint": "national_ncd"},
            {"document_key": "LCD:39044:5", "document_id": "39044",
             "document_type": "LCD", "title": "MolDX", "chapter": "",
             "coverage_level": "local", "contractor_id": "236",
             "contractor_name": "CGS Administrators, LLC",
             "last_updated_sort": "20250115", "source_endpoint": "local_lcd"},
        ])
        self.store.upsert("dim_medicare_contractor", [
            {"contractor_key": "236:2", "contractor_id": "236",
             "contractor_version": "2", "contractor_name": "CGS Administrators, LLC",
             "contract_number": "15004", "source_endpoint": "contractors"}])
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
        self.assertIn("cms_coverage_national_ncd", ids)
        self.assertIn("cms_coverage_contractors", ids)
        self.assertEqual(len(body["datasets"]), 9)
        self.assertTrue(all(d["source"] == "cms_coverage" for d in body["datasets"]))

    def test_query_dataset_slice_and_sort(self):
        status, body = self._get(
            "/v1/query/cms_coverage_national_ncd?sort=-last_updated_sort&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)   # LCD row excluded by the slice
        self.assertEqual(body["rows"][0]["document_id"], "169")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/cms_coverage_national_ncd/aggregate?group_by=chapter")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"chapter": "240", "count": 2})

    def test_lookup_document_route(self):
        status, body = self._get("/v1/lookup/document/169")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["documents"][0]["document_key"], "NCD:169:2")

    def test_lookup_contractor_route(self):
        status, body = self._get("/v1/lookup/contractor/236")
        self.assertEqual(status, 200)
        self.assertEqual(body["contractor"]["contractor_name"],
                         "CGS Administrators, LLC")
        self.assertEqual(body["local_documents"]["count"], 1)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/cms_coverage_national_ncd?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
