"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the NIH RePORTER ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..tables import NihReporterStore


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = NihReporterStore(":memory:")
        self.store.upsert("nih_projects", [
            {"appl_id": "11184227", "project_num": "5R37GM070977-24",
             "core_project_num": "R37GM070977", "fiscal_year": "2025",
             "project_title": "Genetic analysis of innate immunity",
             "org_name": "UNIVERSITY OF TX MD ANDERSON CAN CTR",
             "org_city": "HOUSTON", "org_state": "TX",
             "agency_ic_admin": "NIGMS", "activity_code": "R37",
             "award_amount": "408750", "source_endpoint": "projects"},
            {"appl_id": "11000001", "project_num": "1R01CA123456-01",
             "core_project_num": "R01CA123456", "fiscal_year": "2025",
             "project_title": "Tumor microenvironment",
             "org_name": "BAYLOR COLLEGE OF MEDICINE",
             "org_city": "HOUSTON", "org_state": "TX",
             "agency_ic_admin": "NCI", "activity_code": "R01",
             "award_amount": "550000", "source_endpoint": "projects"},
            {"appl_id": "11000002", "project_num": "5R01CA999999-03",
             "core_project_num": "R01CA999999", "fiscal_year": "2024",
             "project_title": "Immunotherapy resistance",
             "org_name": "STANFORD UNIVERSITY",
             "org_city": "STANFORD", "org_state": "CA",
             "agency_ic_admin": "NCI", "activity_code": "R01",
             "award_amount": "410000", "source_endpoint": "projects"},
        ])
        self.store.upsert("nih_publications", [
            {"pub_key": "23959030:10247478", "pmid": "23959030",
             "appl_id": "10247478", "core_project_num": "R37GM070977",
             "source_endpoint": "publications"},
            {"pub_key": "20668681:11184227", "pmid": "20668681",
             "appl_id": "11184227", "core_project_num": "R37GM070977",
             "source_endpoint": "publications"},
        ])
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
        self.assertEqual(ids, {"nih_reporter_projects",
                               "nih_reporter_publications"})
        self.assertTrue(all(d["source"] == "nih_reporter"
                            for d in body["datasets"]))

    def test_query_filters_and_sort(self):
        status, body = self._get(
            "/v1/query/nih_reporter_projects"
            "?org_state=TX&sort=-award_amount&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["appl_id"], "11000001")

    def test_query_field_op_grammar(self):
        status, body = self._get(
            "/v1/query/nih_reporter_projects?fiscal_year__gte=2025")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/nih_reporter_projects/aggregate?group_by=org_state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0], {"org_state": "TX", "count": 2})

    def test_lookup_grant_route_accepts_core_project_num(self):
        status, body = self._get("/v1/lookup/grant/R37GM070977")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["awards"][0]["appl_id"], "11184227")
        self.assertEqual(body["publications"]["count"], 2)
        self.assertEqual(body["total_award_amount"], 408750.0)

    def test_lookup_grant_route_accepts_full_project_num(self):
        status, body = self._get("/v1/lookup/grant/5R37GM070977-24")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["core_project_nums"], ["R37GM070977"])

    def test_lookup_grantee_org_route_like_aggregate(self):
        status, body = self._get("/v1/lookup/grantee-org/HOUSTON")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 0)   # HOUSTON is a city, not an org
        status, body = self._get("/v1/lookup/grantee-org/BAYLOR")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        org = body["organizations"][0]
        self.assertEqual(org["org_name"], "BAYLOR COLLEGE OF MEDICINE")
        self.assertEqual(org["n_projects"], 1)
        self.assertEqual(org["total_award_amount"], 550000.0)
        self.assertEqual(body["totals"]["n_projects"], 1)

    def test_lookup_grantee_org_limit_param(self):
        status, body = self._get("/v1/lookup/grantee-org/UNIVERSITY?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/nih_reporter_projects?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
