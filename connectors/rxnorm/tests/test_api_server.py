"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the RxNorm ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import RxNormStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = RxNormStore(":memory:")
        self.store.upsert("dim_rxnorm_concept", [
            {"rxcui": "1547220", "name": "pembrolizumab 25 MG/ML",
             "tty": "SCD", "ingredients": "pembrolizumab",
             "n_ingredients": "1", "atc_classes": "Antineoplastic agents",
             "class_source": "ATC", "source_endpoint": "ndc"}])
        self.store.upsert("xwalk_ndc_rxcui", [
            {"ndc": "00006-3026-02", "ndc_digits": "00006302602",
             "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
             "source_endpoint": "ndc"},
            {"ndc": "00006-3029-01", "ndc_digits": "00006302901",
             "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
             "source_endpoint": "ndc"}])
        self.store.upsert("xwalk_name_rxcui", [
            {"name_key": "keytruda", "query_name": "KEYTRUDA",
             "rxcui": "1547220", "resolved_name": "pembrolizumab 25 MG/ML",
             "matched_on": "KEYTRUDA", "match_type": "exact",
             "source_endpoint": "name"}])
        self.server, self.port = make_server(self.store)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
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
        self.assertEqual(row["connector"], "rxnorm")
        self.assertEqual(row["total_rows"], 4)
        self.assertEqual(row["tables"]["xwalk_ndc_rxcui"], 2)

    def test_datasets_auto_exposed_from_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertEqual(ids, {"rxnorm_ndc", "rxnorm_name", "rxnorm_concept"})

    def test_query_dataset_filter(self):
        status, body = self._get("/v1/query/rxnorm_ndc?rxcui=1547220")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/rxnorm_ndc/aggregate?group_by=rxcui")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"rxcui": "1547220", "count": 2})

    def test_lookup_ndc_route(self):
        status, body = self._get("/v1/lookup/rxnorm-ndc/00006-3026-02")
        self.assertEqual(status, 200)
        self.assertEqual(body["rxcui"], "1547220")
        self.assertEqual(body["concept"]["tty"], "SCD")

    def test_lookup_concept_route(self):
        status, body = self._get("/v1/lookup/rxnorm-concept/1547220")
        self.assertEqual(status, 200)
        self.assertEqual(body["n_ndcs"], 2)

    def test_lookup_name_route(self):
        status, body = self._get("/v1/lookup/rxnorm-name/keytruda")
        self.assertEqual(status, 200)
        self.assertEqual(body["match_type"], "exact")

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/rxnorm_ndc?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
