"""End-to-end HTTP tests against a real server on a free port.

Matches the RCM-MC convention of exercising the real path over a socket
(no mocks for our own code) — here a live ``ThreadingHTTPServer`` serving
the CMS Open Data ``/v1`` surface.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server
from ..endpoints import get_endpoint
from ..normalize import normalize_catalog, normalize_curated, normalize_generic
from ..tables import CmsOpenDataStore
from .fakes import catalog_doc, cost_rows, phys_rows


def _seed(store):
    store.upsert("cms_open_data_catalog", normalize_catalog(catalog_doc()))

    spec = get_endpoint("mup_physician_by_provider")
    store.upsert(spec.target_table, normalize_curated(spec, phys_rows(3)))

    spec = get_endpoint("hospital_cost_report")
    store.upsert(spec.target_table, normalize_curated(spec, cost_rows()))

    spec = get_endpoint("mup_partd_prescriber_by_provider")
    store.upsert(spec.target_table, normalize_curated(spec, [
        {"PRSCRBR_NPI": "1003000126", "Prscrbr_Last_Org_Name": "Enkeshafi",
         "Prscrbr_State_Abrvtn": "MD", "Tot_Clms": "1029"}]))

    spec = get_endpoint("mup_partd_prescriber_by_provider_drug")
    store.upsert(spec.target_table, normalize_curated(spec, [
        {"Prscrbr_NPI": "1003000126", "Brnd_Name": "Eliquis",
         "Gnrc_Name": "Apixaban", "Tot_Clms": "222", "Tot_Benes": "28",
         "Tot_Drug_Cst": "128000.5", "Tot_Day_Suply": "9000"},
        {"Prscrbr_NPI": "1003000126", "Brnd_Name": "Lisinopril*",
         "Gnrc_Name": "Lisinopril", "Tot_Clms": "35", "Tot_Benes": "11",
         "Tot_Drug_Cst": "300.2", "Tot_Day_Suply": "1200"}]))

    spec = get_endpoint("hospital_enrollments")
    store.upsert(spec.target_table, normalize_curated(spec, [
        {"ENROLLMENT ID": "O20020812000015", "CCN": "440058",
         "NPI": "1467408781",
         "ORGANIZATION NAME": "SOUTHERN TENNESSEE MEDICAL CENTER LLC"}]))

    spec = get_endpoint("hospital_all_owners")
    store.upsert(spec.target_table, normalize_curated(spec, [
        {"ENROLLMENT ID": "O20020812000015", "ASSOCIATE ID - OWNER": "0244144871",
         "ROLE CODE - OWNER": "35", "ASSOCIATION DATE - OWNER": "2025-03-01",
         "ROLE TEXT - OWNER": "5% OR GREATER INDIRECT OWNERSHIP INTEREST"}]))

    store.upsert("cms_open_data_rows", normalize_generic(
        "hospital_provider_cost_report", cost_rows()))


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.store = CmsOpenDataStore(":memory:")
        _seed(self.store)
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
        self.assertEqual(len(body["datasets"]), 45)
        ids = {d["dataset_id"] for d in body["datasets"]}
        self.assertIn("cms_open_data_catalog", ids)
        self.assertIn("cms_open_data_mup_physician_by_provider", ids)
        self.assertIn("cms_open_data_fetched_rows", ids)
        self.assertTrue(all(d["source"] == "cms_open_data"
                            for d in body["datasets"]))

    def test_query_curated_dataset_with_sort(self):
        status, body = self._get(
            "/v1/query/cms_open_data_mup_physician_by_provider"
            "?sort=-tot_benes&limit=1&select=rndrng_npi,tot_benes")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["rows"][0]["tot_benes"], "330")

    def test_query_generic_rows_dataset(self):
        status, body = self._get(
            "/v1/query/cms_open_data_fetched_rows"
            "?dataset_key=hospital_provider_cost_report")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)

    def test_aggregate_route(self):
        status, body = self._get(
            "/v1/query/cms_open_data_mup_physician_by_provider/aggregate"
            "?group_by=rndrng_prvdr_state_abrvtn")
        self.assertEqual(status, 200)
        self.assertEqual(body["rows"][0],
                         {"rndrng_prvdr_state_abrvtn": "MD", "count": 3})

    def test_lookup_practice_route(self):
        status, body = self._get("/v1/lookup/practice/1003000126")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["practice"][0]["rndrng_prvdr_last_org_name"],
                         "Prov0")

    def test_lookup_prescriber_route_orders_drugs_by_claims(self):
        status, body = self._get("/v1/lookup/prescriber/1003000126")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        drugs = body["top_drugs"]["by_claims"]
        self.assertEqual([d["brnd_name"] for d in drugs],
                         ["Eliquis", "Lisinopril*"])

    def test_lookup_facility_cost_route(self):
        status, body = self._get("/v1/lookup/facility-cost/110130")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 2)
        # Most recent fiscal year first.
        self.assertEqual(body["hospital"][0]["fiscal_year_end_date"],
                         "2025-12-31")
        self.assertEqual(body["snf"], [])

    def test_lookup_ownership_route_resolves_ccn(self):
        status, body = self._get("/v1/lookup/ownership/440058")
        self.assertEqual(status, 200)
        self.assertIn("O20020812000015", body["enrollment_ids"])
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["hospital_owners"][0]["role_code_owner"], "35")

    def test_lookup_ownership_route_direct_enrollment_id(self):
        status, body = self._get("/v1/lookup/ownership/O20020812000015")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)

    def test_lookup_cms_dataset_route(self):
        status, body = self._get(
            "/v1/lookup/cms-dataset/hospital_provider_cost_report")
        self.assertEqual(status, 200)
        self.assertEqual(body["catalog"]["title"], "Hospital Provider Cost Report")
        self.assertEqual(body["curated"]["table"],
                         "cms_open_data_hospital_cost_report")
        self.assertEqual(body["curated"]["rows"], 2)
        self.assertEqual(body["generic_rows"], 2)
        self.assertTrue(body["ingested"])

    def test_lookup_cms_dataset_by_curated_key(self):
        status, body = self._get("/v1/lookup/cms-dataset/hospital_cost_report")
        self.assertEqual(status, 200)
        self.assertEqual(body["catalog"]["uuid"],
                         "bbbbbbbb-1111-2222-3333-444444444444")
        self.assertEqual(body["curated"]["rows"], 2)

    def test_bad_filter_field_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/query/cms_open_data_mup_physician_by_provider?nope=1")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/nonsense")
        self.assertEqual(ctx.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/v1/lookup/unknown-noun/xyz")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
