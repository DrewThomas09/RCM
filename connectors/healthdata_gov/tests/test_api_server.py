"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer``
serving the healthdata_gov ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import ENDPOINTS, get_endpoint
from ..normalize import normalize, normalize_generic
from ..tables import HealthdataGovStore
from .fakes import catalog_items, facility_capacity_rows, hhs_ids_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthdataGovStore(":memory:")
        self.store.upsert(
            "hhs_hospital_capacity_facility",
            normalize(get_endpoint("hospital_capacity_facility"),
                      facility_capacity_rows()
                      ).rows["hhs_hospital_capacity_facility"])
        self.store.upsert(
            "hhs_hospital_ids",
            normalize(get_endpoint("hospital_ids"),
                      hhs_ids_rows()).rows["hhs_hospital_ids"])
        cat = catalog_items(2)
        cat[0]["id"] = "anag-cw7u"     # so the lookup can see a curated match
        self.store.upsert(
            "healthdata_gov_catalog",
            normalize(get_endpoint("catalog"), cat
                      ).rows["healthdata_gov_catalog"])
        self.store.upsert("healthdata_gov_rows",
                          normalize_generic("anag-cw7u", [{"a": 1}]))
        self.server, self.port = make_server(self.store)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()   # release the listening socket
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
        self.assertIn("healthdata_gov_catalog", ids)
        self.assertIn("healthdata_gov_hospital_capacity_facility", ids)
        self.assertIn("healthdata_gov_fetched_rows", ids)
        self.assertEqual(len(body["datasets"]), len(ENDPOINTS))
        self.assertTrue(all(d["source"] == "healthdata_gov"
                            for d in body["datasets"]))

    def test_query_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/healthdata_gov_hospital_capacity_facility"
            "?state=AL&sort=-collection_week&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["collection_week"],
                         "2024-04-21T00:00:00.000")

    def test_query_generic_rows_by_dataset_key(self):
        status, body = self._get(
            "/v1/query/healthdata_gov_fetched_rows?dataset_key=anag-cw7u")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["row_key"], "anag-cw7u:0")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/healthdata_gov_hospital_capacity_facility/aggregate"
            "?group_by=state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"state": "AL", "count": 2})

    def test_lookup_hospital_capacity_route(self):
        status, body = self._get("/v1/lookup/hospital-capacity/010039")
        self.assertEqual(status, 200)
        self.assertEqual(body["hospital_name"], "HUNTSVILLE HOSPITAL")
        self.assertEqual(body["state"], "AL")
        # Two HHS-ID crosswalk rows share CCN 010039.
        self.assertEqual(body["hhs_ids"]["count"], 2)
        # Two weekly capacity rows, most recent first.
        self.assertEqual(body["weekly_capacity"]["count"], 2)
        self.assertEqual(
            body["weekly_capacity"]["rows"][0]["collection_week"],
            "2024-04-21T00:00:00.000")

    def test_lookup_hospital_capacity_matches_hhs_id_too(self):
        status, body = self._get("/v1/lookup/hospital-capacity/H450054")
        self.assertEqual(status, 200)
        self.assertEqual(body["hhs_ids"]["count"], 1)
        self.assertEqual(body["hhs_ids"]["rows"][0]["ccn"], "450054")

    def test_lookup_hhs_dataset_route(self):
        status, body = self._get("/v1/lookup/hhs-dataset/anag-cw7u")
        self.assertEqual(status, 200)
        self.assertEqual(body["catalog"]["dataset_uid"], "anag-cw7u")
        # Hub-native fixture: HHS's own hub record, HHS attribution.
        self.assertTrue(body["hhs_hub"])
        self.assertEqual(body["domain"], "datahub.hhs.gov")
        self.assertEqual(body["curated_as"][0]["dataset_id"],
                         "healthdata_gov_hospital_capacity_facility")
        self.assertEqual(body["fetched_rows"]["count"], 1)

    def test_lookup_hhs_dataset_mirror_entry_reports_attribution(self):
        # aaa1-bbb1 is the federal-portal mirror fixture (hub record,
        # attribution data.cdc.gov) — the lookup surfaces the real home
        # so callers can route to the estate's cdc_data connector.
        status, body = self._get("/v1/lookup/hhs-dataset/aaa1-bbb1")
        self.assertEqual(status, 200)
        self.assertTrue(body["hhs_hub"])
        self.assertEqual(body["attribution"], "data.cdc.gov")
        self.assertEqual(body["curated_as"], [])

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/healthdata_gov_hospital_ids?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
