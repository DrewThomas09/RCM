"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the OIG LEIE ``/v1`` surface.
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
from ..tables import OigLeieStore
from .fakes import supplement_rein_rows, updated_rows


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = OigLeieStore(":memory:")
        self.store.upsert("oig_exclusions", normalize(
            get_endpoint("exclusions"), updated_rows()).rows["oig_exclusions"])
        self.store.upsert("oig_reinstatements", normalize(
            get_endpoint("reinstatements"), supplement_rein_rows(),
            month_tag="2026-05").rows["oig_reinstatements"])
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
        self.assertEqual(ids, {"oig_leie_exclusions",
                               "oig_leie_supplement",
                               "oig_leie_reinstatements"})
        self.assertTrue(all(d["source"] == "oig_leie"
                            for d in body["datasets"]))
        self.assertTrue(all(d["join_keys"] == ["npi"]
                            for d in body["datasets"]))

    def test_query_dataset_filter_and_sort(self):
        status, body = self._get(
            "/v1/query/oig_leie_exclusions?state=NY&sort=-excldate&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["rows"][0]["busname"],
                         "101 FIRST CARE PHARMACY INC")

    def test_query_field_op_grammar(self):
        status, body = self._get(
            "/v1/query/oig_leie_exclusions?excldate__gte=2020-01-01")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 3)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/oig_leie_exclusions/aggregate?group_by=state")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0]["count"], 2)   # NY twice

    def test_query_reinstatements_dataset(self):
        status, body = self._get(
            "/v1/query/oig_leie_reinstatements?npi=1234567893")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["lastname"], "ACHU")

    def test_lookup_exclusion_route_real_npi(self):
        status, body = self._get("/v1/lookup/exclusion/1234567893")
        self.assertEqual(status, 200)
        self.assertTrue(body["matchable"])
        self.assertTrue(body["excluded"])
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["exclusions"][0]["lastname"], "SMITH")
        # The reinstatement fixture shares this NPI — a screen sees both.
        self.assertEqual(body["reinstatements"]["count"], 1)

    def test_lookup_exclusion_zero_npi_never_matches(self):
        status, body = self._get("/v1/lookup/exclusion/0000000000")
        self.assertEqual(status, 200)
        self.assertFalse(body["matchable"])
        self.assertFalse(body["excluded"])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["exclusions"], [])

    def test_lookup_exclusion_clean_npi_no_hit(self):
        status, body = self._get("/v1/lookup/exclusion/1999999992")
        self.assertEqual(status, 200)
        self.assertTrue(body["matchable"])
        self.assertFalse(body["excluded"])
        self.assertEqual(body["count"], 0)

    def test_lookup_exclusion_name_matches_business_and_person(self):
        q = urllib.parse.quote("MARKETING")
        status, body = self._get(f"/v1/lookup/exclusion-name/{q}")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["matches"][0]["busname"],
                         "#1 MARKETING SERVICE, INC")
        # Case-insensitive over lastname too.
        status, body = self._get("/v1/lookup/exclusion-name/smith")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["matches"][0]["npi"], "1234567893")

    def test_lookup_exclusion_name_first_param_narrows(self):
        status, body = self._get("/v1/lookup/exclusion-name/SMITH?first=JOHN")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        status, body = self._get("/v1/lookup/exclusion-name/SMITH?first=JANE")
        self.assertEqual(body["count"], 0)

    def test_lookup_exclusion_name_limit_param(self):
        status, body = self._get("/v1/lookup/exclusion-name/A?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["matches"]), 1)
        self.assertGreaterEqual(body["count"], 2)   # count is unaffected

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/oig_leie_exclusions?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
