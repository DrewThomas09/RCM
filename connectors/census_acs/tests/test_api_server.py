"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the Census ACS ``/v1`` surface, fed through the real
fetch → normalize → upsert pipeline against the in-memory fake API.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..connector import CensusAcsConnector
from ..tables import CensusAcsStore
from ..transport import CensusAcsTransport
from .fakes import FakeCensusApi


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = CensusAcsStore(":memory:")
        conn = CensusAcsConnector(CensusAcsTransport(min_interval_s=0.0))
        for key in ("county_profile", "state_profile", "cbsa_profile"):
            conn.refresh(self.store, key, year=2023,
                         opener=FakeCensusApi.with_defaults())
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
        self.assertEqual(ids, {"census_acs_county_profile",
                               "census_acs_state_profile",
                               "census_acs_cbsa_profile"})
        self.assertTrue(all(d["source"] == "census_acs"
                            for d in body["datasets"]))

    def test_query_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/census_acs_county_profile"
            "?state_fips=48&sort=-total_pop&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["rows"][0]["fips5"], "48201")  # Harris biggest

    def test_query_field_op_grammar(self):
        # Values are TEXT; same-width operands keep the lexicographic
        # comparison numerically correct (the engine's one-type model).
        status, body = self._get(
            "/v1/query/census_acs_state_profile?median_age__gte=37.0")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["name"], "California")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/census_acs_county_profile/aggregate?group_by=state_fips")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"state_fips": "48", "count": 3})

    def test_lookup_county_demographics_route(self):
        status, body = self._get("/v1/lookup/county-demographics/48201")
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Harris County, Texas")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["profiles"][0]["county_key"], "48201:2023")
        # Parent-state context rides along.
        self.assertEqual(body["state"]["profiles"][0]["name"], "Texas")

    def test_lookup_state_demographics_route(self):
        status, body = self._get("/v1/lookup/state-demographics/48")
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Texas")
        self.assertEqual(body["counties"]["count"], 3)
        largest = body["counties"]["largest"]
        self.assertEqual(largest[0]["fips5"], "48201")  # numeric ordering

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/census_acs_county_profile?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
