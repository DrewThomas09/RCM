"""End-to-end HTTP tests against a real server on a free port.

Matches the estate convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer``
serving the healthcare.gov ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import HealthcareGovStore
from .fakes import (
    BENEFITS_ROWS,
    PLAN_ATTRIBUTES_ROWS,
    QUALITY_ROWS,
    RATES_ROWS,
    SERVICE_AREA_ROWS,
)


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = HealthcareGovStore(":memory:")
        for key, rows in (
                ("plan_attributes_py2026", PLAN_ATTRIBUTES_ROWS),
                ("benefits_cost_sharing_py2026", BENEFITS_ROWS),
                ("rate_puf_py2026", RATES_ROWS),
                ("quality_puf_py2026", QUALITY_ROWS),
                ("service_area_puf_py2026", SERVICE_AREA_ROWS)):
            spec = get_endpoint(key)
            for table, trows in normalize(spec, rows).rows.items():
                self.store.upsert(table, trows)
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
        self.assertEqual(len(body["datasets"]), 7)
        self.assertIn("healthcare_gov_catalog", ids)
        self.assertIn("healthcare_gov_plan_attributes_py2026", ids)
        self.assertIn("healthcare_gov_fetched_rows", ids)
        self.assertTrue(all(d["source"] == "healthcare_gov"
                            for d in body["datasets"]))

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/healthcare_gov_plan_attributes_py2026"
            "?statecode=AK&sort=-planid&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["planid"], "21989AK0030001-01")

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/healthcare_gov_plan_attributes_py2026/aggregate"
            "?group_by=statecode")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"statecode": "AK", "count": 2})

    def test_lookup_marketplace_plan_route(self):
        status, body = self._get("/v1/lookup/marketplace-plan/21989AK0030001")
        self.assertEqual(status, 200)
        self.assertTrue(body["found"])
        self.assertEqual(body["plan_variants"]["count"], 2)
        self.assertEqual(body["quality_ratings"]["overallratingvalue"], "4")
        self.assertEqual(body["rates"]["count"], 2)
        self.assertEqual(body["benefits"]["count"], 2)

    def test_lookup_marketplace_plan_accepts_variant_id(self):
        status, body = self._get(
            "/v1/lookup/marketplace-plan/21989AK0030001-01?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["standard_component_id"], "21989AK0030001")
        self.assertEqual(len(body["rates"]["sample"]), 1)

    def test_lookup_county_plans_route_includes_statewide(self):
        # 02170 is covered explicitly by AKS002 and statewide by AKS001;
        # the AK dental plans ride on AKS001.
        status, body = self._get("/v1/lookup/county-plans/02170")
        self.assertEqual(status, 200)
        self.assertEqual(body["states"], ["AK"])
        self.assertEqual(body["service_areas"]["county_rows"], 1)
        self.assertEqual(body["service_areas"]["statewide_rows"], 1)
        self.assertEqual(body["plans"]["count"], 2)
        planids = {p["planid"] for p in body["plans"]["sample"]}
        self.assertEqual(planids,
                         {"21989AK0030001-00", "21989AK0030001-01"})

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/healthcare_gov_plan_attributes_py2026?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
