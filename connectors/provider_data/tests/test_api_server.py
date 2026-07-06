"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the Provider Data ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import ProviderDataStore
from .fakes import catalog_items, clinician_rows, hospital_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = ProviderDataStore(":memory:")
        self.store.upsert("provider_data_catalog", normalize(
            get_endpoint("catalog"), catalog_items()
        ).rows["provider_data_catalog"])
        self.store.upsert("hospital_general", normalize(
            get_endpoint("hospital_general"), hospital_rows(5)
        ).rows["hospital_general"])
        self.store.upsert("dac_national", normalize(
            get_endpoint("dac_national"), clinician_rows()
        ).rows["dac_national"])
        self.store.upsert("provider_data_rows", [
            {"row_key": "77hc-ibv8:0", "dataset_key": "77hc-ibv8",
             "row_idx": 0, "row_json": "{}",
             "fetched_at": "2026-07-06T00:00:00+00:00",
             "source_endpoint": "77hc-ibv8"}])
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

    def test_datasets_auto_exposed_from_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertIn("provider_data_catalog", ids)
        self.assertIn("provider_data_dac_national", ids)
        self.assertEqual(len(body["datasets"]), 36)
        self.assertTrue(all(d["source"] == "provider_data"
                            for d in body["datasets"]))

    def test_query_with_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/provider_data_hospital_general"
            "?state=TX&sort=-facility_id&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["state"], "TX")

    def test_query_catalog(self):
        status, body = self._get(
            "/v1/query/provider_data_catalog?themes__like=%25Hospitals%25")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/provider_data_hospital_general/aggregate?group_by=state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0]["count"], 2)   # AL and TX have 2 each

    def test_lookup_hospital_route(self):
        status, body = self._get("/v1/lookup/hospital/010001")
        self.assertEqual(status, 200)
        self.assertTrue(body["found"])
        self.assertEqual(body["hospital"]["facility_name"],
                         "TEST MEDICAL CENTER 1")
        self.assertEqual(body["overall_star_rating"], "2")

    def test_lookup_clinician_route(self):
        status, body = self._get("/v1/lookup/clinician/1659447118")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["organizations"]), 2)

    def test_lookup_pdc_dataset_route(self):
        status, body = self._get("/v1/lookup/pdc-dataset/77hc-ibv8")
        self.assertEqual(status, 200)
        self.assertTrue(body["found"])
        self.assertEqual(body["fetched_rows"], 1)
        self.assertIn("Infections", body["dataset"]["title"])

    def test_lookup_miss_is_200_with_found_false(self):
        status, body = self._get("/v1/lookup/hospice/999999")
        self.assertEqual(status, 200)
        self.assertFalse(body["found"])

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/provider_data_hospital_general?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)

    def test_unknown_lookup_noun_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/lookup/starship/enterprise")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
