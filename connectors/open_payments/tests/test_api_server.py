"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer``
serving the Open Payments ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import OpenPaymentsStore
from .fakes import CATALOG_ITEMS, GENERAL_UUID, general_payment_row


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenPaymentsStore(":memory:")
        general = normalize(get_endpoint("general_payments_2024"), [
            # Amounts chosen so TEXT ordering matches numeric ordering —
            # the estate's one-type-model stores dollars as TEXT.
            general_payment_row("1", state="VT", amount="875.14"),
            general_payment_row("2", state="VT", amount="20.74",
                                npi="1111111111"),
            general_payment_row("3", state="CA", amount="5000.00",
                                manufacturer="MERCK SHARP & DOHME LLC"),
        ]).rows["op_general_payment"]
        self.store.upsert("op_general_payment", general)
        catalog = normalize(get_endpoint("catalog"),
                            CATALOG_ITEMS).rows["open_payments_catalog"]
        self.store.upsert("open_payments_catalog", catalog)
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
        self.assertEqual(len(body["datasets"]), 11)
        self.assertIn("open_payments_catalog", ids)
        self.assertIn("open_payments_general_payments_2024", ids)
        self.assertIn("open_payments_fetched_rows", ids)
        self.assertTrue(all(d["source"] == "open_payments"
                            for d in body["datasets"]))

    def test_query_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/open_payments_general_payments_2024"
            "?recipient_state=VT&sort=-total_amount_of_payment_usdollars"
            "&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["record_id"], "1")

    def test_query_catalog_dataset(self):
        status, body = self._get(
            "/v1/query/open_payments_catalog?select=identifier,title")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 3)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/open_payments_general_payments_2024/aggregate"
            "?group_by=recipient_state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0],
                         {"recipient_state": "VT", "count": 2})

    def test_lookup_physician_payments_route(self):
        status, body = self._get("/v1/lookup/physician-payments/1111111111")
        self.assertEqual(status, 200)
        self.assertEqual(body["general_payments"]["count"], 1)
        self.assertEqual(body["general_payments"]["sample"][0]["record_id"],
                         "2")
        self.assertEqual(body["general_payments"]["total_amount_usd"], 20.74)

    def test_lookup_manufacturer_route_is_substring_match(self):
        status, body = self._get("/v1/lookup/manufacturer/MERCK?limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(body["general_payments"]["count"], 1)
        self.assertEqual(body["matched_entities"][0]["name"],
                         "MERCK SHARP & DOHME LLC")

    def test_lookup_op_dataset_route(self):
        status, body = self._get(f"/v1/lookup/op-dataset/{GENERAL_UUID}")
        self.assertEqual(status, 200)
        self.assertEqual(body["found"], 1)
        self.assertEqual(body["dataset"]["title"], "2024 General Payment Data")
        # And a title-fragment fallback for humans:
        status2, body2 = self._get(
            "/v1/lookup/op-dataset/" + urllib.parse.quote("Research Payment"))
        self.assertEqual(status2, 200)
        self.assertGreaterEqual(body2["found"], 1)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/open_payments_general_payments_2024?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
