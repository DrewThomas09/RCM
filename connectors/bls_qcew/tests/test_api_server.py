"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer``
serving the BLS QCEW ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import BlsQcewStore
from .fakes import area_48453_2024q1_rows, area_48453_rows, industry_622_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = BlsQcewStore(":memory:")
        for key, raw in (("industry_area", industry_622_rows()),
                         ("area_industry", area_48453_rows()),
                         ("area_industry", area_48453_2024q1_rows())):
            self.store.upsert(
                "qcew_industry_area",
                normalize(get_endpoint(key), raw).rows["qcew_industry_area"])
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
        self.assertEqual(ids, {"bls_qcew_industry_area",
                               "bls_qcew_area_industry"})
        self.assertTrue(all(d["source"] == "bls_qcew"
                            for d in body["datasets"]))
        # The pinned latest published quarter rides in default_params.
        by_id = {d["dataset_id"]: d for d in body["datasets"]}
        self.assertEqual(
            by_id["bls_qcew_industry_area"]["default_params"],
            {"industry": "62", "year": "2025", "qtr": "4"})

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/bls_qcew_industry_area"
            "?own_code=5&sort=-avg_wkly_wage&limit=2")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 5)
        self.assertEqual(body["rows"][0]["area_fips"], "US000")

    def test_query_field_op_grammar(self):
        status, body = self._get(
            "/v1/query/bls_qcew_area_industry?industry_code__like=62%25"
            "&year=2025")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 4)

    def test_query_slices_are_pinned_apart(self):
        _, ind = self._get("/v1/query/bls_qcew_industry_area")
        _, area = self._get("/v1/query/bls_qcew_area_industry")
        self.assertEqual(ind["total"], 6)
        self.assertEqual(area["total"], 7)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/bls_qcew_industry_area/aggregate?group_by=own_code")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"own_code": "5", "count": 5})

    def test_lookup_labor_market_route(self):
        status, body = self._get("/v1/lookup/labor-market/48453")
        self.assertEqual(status, 200)
        self.assertEqual(body["area_fips"], "48453")
        self.assertEqual((body["year"], body["qtr"]), ("2025", "4"))
        self.assertEqual(body["observations"], 4)
        self.assertEqual(body["industries"][0]["industry_code"], "62")
        self.assertEqual(body["industries"][0]["own_title"], "Private")

    def test_lookup_labor_market_year_qtr_and_limit_params(self):
        status, body = self._get(
            "/v1/lookup/labor-market/48453?year=2024&qtr=1&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual((body["year"], body["qtr"]), ("2024", "1"))
        self.assertEqual(len(body["industries"]), 1)
        self.assertEqual(body["industries"][0]["month3_emplvl"], "20000")

    def test_lookup_industry_employment_route(self):
        status, body = self._get("/v1/lookup/industry-employment/622")
        self.assertEqual(status, 200)
        self.assertEqual(body["industry_code"], "622")
        self.assertEqual(body["observations"], 6)
        self.assertEqual(body["top_areas"][0]["area_fips"], "US000")

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/bls_qcew_industry_area?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
