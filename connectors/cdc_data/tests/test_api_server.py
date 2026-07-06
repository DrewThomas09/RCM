"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer``
serving the cdc_data ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import ENDPOINTS
from ..normalize import normalize, normalize_generic
from ..endpoints import get_endpoint
from ..tables import CdcDataStore
from .fakes import catalog_items, drug_poisoning_rows, heart_disease_rows, places_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = CdcDataStore(":memory:")
        self.store.upsert(
            "cdc_places_county",
            normalize(get_endpoint("places_county"),
                      places_rows()).rows["cdc_places_county"])
        self.store.upsert(
            "cdc_drug_poisoning_county",
            normalize(get_endpoint("drug_poisoning_county"),
                      drug_poisoning_rows()).rows["cdc_drug_poisoning_county"])
        self.store.upsert(
            "cdc_heart_disease_mortality",
            normalize(get_endpoint("heart_disease_mortality_county"),
                      heart_disease_rows()).rows["cdc_heart_disease_mortality"])
        cat = catalog_items(2)
        cat[0]["id"] = "swc5-untb"     # so the lookup can see a curated match
        self.store.upsert(
            "cdc_data_catalog",
            normalize(get_endpoint("catalog"), cat).rows["cdc_data_catalog"])
        self.store.upsert("cdc_data_rows",
                          normalize_generic("swc5-untb", [{"a": 1}]))
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
        self.assertIn("cdc_data_catalog", ids)
        self.assertIn("cdc_data_places_county", ids)
        self.assertIn("cdc_data_fetched_rows", ids)
        self.assertEqual(len(body["datasets"]), len(ENDPOINTS))
        self.assertTrue(all(d["source"] == "cdc_data" for d in body["datasets"]))

    def test_query_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/cdc_data_places_county"
            "?stateabbr=AR&sort=-data_value&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["data_value"], "29.9")

    def test_query_generic_rows_by_dataset_key(self):
        status, body = self._get(
            "/v1/query/cdc_data_fetched_rows?dataset_key=swc5-untb")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["row_key"], "swc5-untb:0")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/cdc_data_places_county/aggregate?group_by=stateabbr")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"stateabbr": "AR", "count": 2})

    def test_lookup_county_health_route(self):
        status, body = self._get("/v1/lookup/county-health/01073")
        self.assertEqual(status, 200)
        self.assertEqual(body["county"], "Jefferson")
        self.assertEqual(body["state"], "AL")
        self.assertEqual(body["places"]["count"], 1)
        # NCHS drug-poisoning stores FIPS unpadded; the lookup bridges that.
        self.assertEqual(body["drug_poisoning"]["count"], 1)
        self.assertEqual(body["heart_disease_mortality"]["count"], 1)

    def test_lookup_cdc_dataset_route(self):
        status, body = self._get("/v1/lookup/cdc-dataset/swc5-untb")
        self.assertEqual(status, 200)
        self.assertEqual(body["catalog"]["dataset_uid"], "swc5-untb")
        self.assertEqual(body["curated_as"][0]["dataset_id"],
                         "cdc_data_places_county")
        self.assertEqual(body["fetched_rows"]["count"], 1)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/cdc_data_places_county?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
