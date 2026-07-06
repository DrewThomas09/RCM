"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the medicaid_data ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import ENDPOINTS, get_endpoint
from ..normalize import normalize
from ..tables import MedicaidDataStore
from .fakes import NADAC_2026_ID, catalog_item, nadac_row, sdud_row


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = MedicaidDataStore(":memory:")
        self.store.upsert("medicaid_data_catalog", normalize(
            get_endpoint("catalog"),
            [catalog_item()]).rows["medicaid_data_catalog"])
        self.store.upsert("medicaid_nadac", normalize(
            get_endpoint("nadac_2026"), [
                nadac_row(ndc="00000000001", as_of="2026-01-07"),
                nadac_row(ndc="00000000001", as_of="2026-01-14",
                          per_unit="0.30000"),
            ]).rows["medicaid_nadac"] + normalize(
            get_endpoint("nadac_2025"), [
                nadac_row(ndc="00000000001", effective="2024-12-18",
                          as_of="2025-01-01"),
            ]).rows["medicaid_nadac"])
        self.store.upsert("medicaid_sdud", normalize(
            get_endpoint("sdud_2025"), [
                sdud_row(state="AK", total="100.00"),
                sdud_row(state="AK", ndc="99999999999", total="900.00",
                         product="OZEMPIC"),
                sdud_row(state="AK", ndc="88888888888", suppressed="true"),
            ]).rows["medicaid_sdud"])
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
        self.assertIn("medicaid_data_catalog", ids)
        self.assertIn("medicaid_data_nadac_2026", ids)
        self.assertIn("medicaid_data_fetched_rows", ids)
        self.assertEqual(len(body["datasets"]), len(ENDPOINTS))
        self.assertTrue(all(d["source"] == "medicaid_data"
                            for d in body["datasets"]))

    def test_query_dataset_slice_and_sort(self):
        status, body = self._get(
            "/v1/query/medicaid_data_nadac_2026?sort=-as_of_date&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)   # 2025 slice excluded
        self.assertEqual(body["rows"][0]["as_of_date"], "2026-01-14")

    def test_query_filter_grammar_over_http(self):
        status, body = self._get(
            "/v1/query/medicaid_data_nadac_2026?as_of_date__gte=2026-01-10")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/medicaid_data_sdud_2025/aggregate?group_by=state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"state": "AK", "count": 3})

    def test_lookup_ndc_cost_route(self):
        status, body = self._get("/v1/lookup/ndc-cost/00000000001")
        self.assertEqual(status, 200)
        self.assertEqual(body["costs"]["count"], 3)
        # Latest = most recent as_of snapshot.
        self.assertEqual(body["latest"]["as_of_date"], "2026-01-14")

    def test_lookup_state_drug_route(self):
        status, body = self._get("/v1/lookup/state-drug/ak")   # case-folded
        self.assertEqual(status, 200)
        self.assertEqual(body["state"], "AK")
        self.assertEqual(body["rows"], 3)
        self.assertEqual(body["suppressed_rows"], 1)
        top = body["top_drugs_by_spend"][0]
        self.assertEqual(top["product_name"], "OZEMPIC")   # 900 > 100

    def test_lookup_medicaid_dataset_route(self):
        status, body = self._get(f"/v1/lookup/medicaid-dataset/{NADAC_2026_ID}")
        self.assertEqual(status, 200)
        self.assertTrue(body["found"])
        self.assertEqual(body["dataset"]["identifier"], NADAC_2026_ID)
        # The catalog row cross-references its curated registration.
        self.assertEqual(body["curated_datasets"][0]["dataset_id"],
                         "medicaid_data_nadac_2026")

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/medicaid_data_nadac_2026?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
