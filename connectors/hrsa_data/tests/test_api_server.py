"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the HRSA data ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import HrsaDataStore
from .fakes import hpsa_pc_rows, mua_rows, sites_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = HrsaDataStore(":memory:")
        self.store.upsert("hrsa_hpsa", normalize(
            get_endpoint("hpsa_primary_care"), hpsa_pc_rows()).rows["hrsa_hpsa"])
        self.store.upsert("hrsa_mua", normalize(
            get_endpoint("mua"), mua_rows()).rows["hrsa_mua"])
        self.store.upsert("hrsa_health_center_sites", normalize(
            get_endpoint("health_center_sites"),
            sites_rows()).rows["hrsa_health_center_sites"])
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
        self.assertEqual(ids, {"hrsa_data_hpsa_primary_care",
                               "hrsa_data_hpsa_dental",
                               "hrsa_data_hpsa_mental_health",
                               "hrsa_data_mua",
                               "hrsa_data_health_center_sites"})
        self.assertTrue(all(d["source"] == "hrsa_data"
                            for d in body["datasets"]))

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/hrsa_data_hpsa_primary_care"
            "?common_state_abbreviation=TX&sort=-hpsa_score&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["hpsa_name"], "Deaf Smith County")

    def test_query_field_op_grammar(self):
        status, body = self._get(
            "/v1/query/hrsa_data_hpsa_primary_care?hpsa_score__gte=20")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/hrsa_data_hpsa_primary_care/aggregate"
            "?group_by=common_state_abbreviation")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0],
                         {"common_state_abbreviation": "TX", "count": 2})

    def test_query_mua_dataset(self):
        status, body = self._get(
            "/v1/query/hrsa_data_mua?mua_p_status_description=Designated")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_lookup_shortage_area_route(self):
        status, body = self._get("/v1/lookup/shortage-area/tx")
        self.assertEqual(status, 200)
        self.assertEqual(body["state"], "TX")     # case-normalised
        self.assertEqual(body["hpsa"]["count"], 2)
        top = body["hpsa"]["top_scored_sample"][0]
        self.assertEqual(top["hpsa_name"], "Deaf Smith County")  # score 21
        self.assertEqual(body["hpsa"]["by_discipline"][0]["count"], 2)
        self.assertEqual(body["mua"]["count"], 0)

    def test_lookup_shortage_area_limit_param(self):
        status, body = self._get("/v1/lookup/shortage-area/TX?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["hpsa"]["top_scored_sample"]), 1)
        self.assertEqual(body["hpsa"]["count"], 2)  # count is unaffected

    def test_lookup_health_center_route(self):
        status, body = self._get("/v1/lookup/health-center/OH")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["sites"][0]["site_name"], "YWCA Cincinnati")
        self.assertEqual(body["sites"][0]["fqhc_site_npi_number"],
                         "1234567893")
        self.assertEqual(body["by_status"][0],
                         {"site_status_description": "Active", "count": 1})

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/hrsa_data_mua?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
