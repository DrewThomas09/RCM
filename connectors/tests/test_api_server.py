"""End-to-end tests of the unified /v1 surface over all connectors.

A real ThreadingHTTPServer on a free port, one in-memory store per
connector seeded with a couple of canonical rows, exercised over a socket
with urllib — the same no-mocks convention as the per-connector suites.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from ..api_server import make_server, open_stores


def _seed(stores):
    """Put one canonical row into each connector so query/lookup return data."""
    stores["openfda"].upsert("dim_drug_product", [
        {"ndc": "0002-1200", "proprietary_name": "FOO", "rxcui": "1234",
         "source_endpoint": "drug_ndc"}])
    stores["cms_coverage"].upsert("dim_coverage_document", [
        {"document_key": "NCD:169:2", "document_id": "169",
         "document_type": "NCD", "title": "Home Use of Oxygen",
         "chapter": "240", "coverage_level": "national",
         "source_endpoint": "national_ncd"}])
    stores["npi_registry"].upsert("dim_provider", [
        {"npi": "1234567893", "enumeration_type": "NPI-1",
         "last_name": "DOE", "state": "MD", "primary_taxonomy_code": "207RC0000X",
         "source_endpoint": "individual"}])
    stores["icd10"].upsert("dim_icd10_code", [
        {"code_key": "cm:E11.65", "code_type": "cm", "code": "E11.65",
         "name": "Type 2 diabetes mellitus with hyperglycemia",
         "chapter": "E", "category": "E11", "source_endpoint": "cm"}])


class UnifiedServerTests(unittest.TestCase):
    def setUp(self):
        self.stores = open_stores(":memory:")
        _seed(self.stores)
        self.server, self.port = make_server(self.stores)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        for s in self.stores.values():
            s.close()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    # ── estate surface ────────────────────────────────────────────────
    def test_health_lists_connectors(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("icd10", body["connectors"])

    def test_connectors_endpoint(self):
        status, body = self._get("/v1/connectors")
        self.assertEqual(status, 200)
        names = {c["connector"] for c in body["connectors"]}
        self.assertEqual(names, {"openfda", "cms_coverage", "npi_registry", "icd10"})

    def test_datasets_merges_every_registry(self):
        status, body = self._get("/v1/datasets")
        self.assertEqual(status, 200)
        ids = {d["dataset_id"] for d in body["datasets"]}
        for did in ("openfda_drug_ndc", "cms_coverage_national_ncd",
                    "npi_provider", "icd10_cm"):
            self.assertIn(did, ids)

    # ── query dispatched to the owning connector ──────────────────────
    def test_query_openfda_dataset(self):
        status, body = self._get("/v1/query/openfda_drug_ndc?ndc=0002-1200")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["proprietary_name"], "FOO")

    def test_query_cms_dataset(self):
        status, body = self._get("/v1/query/cms_coverage_national_ncd")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["rows"][0]["document_id"], "169")

    def test_query_icd10_dataset(self):
        status, body = self._get("/v1/query/icd10_cm?code=E11.65")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)

    def test_aggregate_dispatched(self):
        status, body = self._get(
            "/v1/query/icd10_cm/aggregate?group_by=chapter")
        self.assertEqual(status, 200)
        self.assertEqual(body["group_by"], ["chapter"])
        self.assertEqual(body["rows"][0]["count"], 1)

    def test_unknown_dataset_is_404(self):
        status, body = self._get("/v1/query/nope_not_real")
        self.assertEqual(status, 404)
        self.assertIn("unknown dataset", body["error"])

    def test_bad_filter_field_is_400(self):
        status, body = self._get("/v1/query/icd10_cm?not_a_column=x")
        self.assertEqual(status, 400)

    # ── lookups delegated to the owning connector ─────────────────────
    def test_openfda_lookup_delegates(self):
        status, body = self._get("/v1/lookup/drug/0002-1200")
        self.assertEqual(status, 200)
        self.assertEqual(body["ndc"], "0002-1200")

    def test_icd10_code_lookup_delegates_with_type_alias(self):
        status, body = self._get("/v1/lookup/code/E11.65?type=cm")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_type"], "cm")

    def test_npi_validate_delegates(self):
        status, body = self._get("/v1/validate/npi/1234567893")
        self.assertEqual(status, 200)
        self.assertTrue(body["valid"])
        status, body = self._get("/v1/validate/npi/1234567890")
        self.assertEqual(status, 200)
        self.assertFalse(body["valid"])

    def test_icd10_search_delegates(self):
        status, body = self._get("/v1/search/cm?q=diabetes")
        self.assertEqual(status, 200)
        self.assertEqual(body["code_type"], "cm")
        self.assertTrue(any(r["code"] == "E11.65" for r in body["results"]))

    def test_unknown_route_is_404(self):
        status, body = self._get("/v1/nonsense/x/y")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
