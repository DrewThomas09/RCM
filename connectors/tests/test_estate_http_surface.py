"""Unified /v1 surface: status route, HTTP filter grammar, lookup binder.

Real ThreadingHTTPServer on a free port, real stores, urllib over a
socket — the same no-mocks convention as the rest of the estate suites.

Pins three estate-wide behaviors:

* ``/v1/status`` distinguishes "never fetched" from "fetched, empty" via
  row totals + MAX(ingested_at) vintage per connector;
* the query grammar over HTTP: numeric ``__gt`` compares numerically and
  ``__in`` accepts the comma-joined form (both were silent wrong-output
  bugs on every HTTP surface);
* every connector's lookup routes bind through the unified server (only
  3 of 16 connectors were ever exercised through the shared binder).
"""
import json
import re
import threading
import unittest
import urllib.error
import urllib.request

from .._spi import CONNECTOR_NAMES, load_all
from ..api_server import estate_status, make_server, open_stores


class _ServerCase(unittest.TestCase):
    def setUp(self):
        self.adapters = load_all()
        self.stores = open_stores(":memory:")
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


class StatusRouteTests(_ServerCase):
    def test_status_lists_every_connector_with_fetch_state(self):
        status, body = self._get("/v1/status")
        self.assertEqual(status, 200)
        rows = body["connectors"]
        self.assertEqual([r["connector"] for r in rows],
                         list(CONNECTOR_NAMES))
        for r in rows:
            for key in ("connector", "label", "db_path", "db_present",
                        "total_rows", "last_ingested_at"):
                self.assertIn(key, r)
            self.assertEqual(r["total_rows"], 0)
            self.assertIsNone(r["last_ingested_at"])
            self.assertFalse(r["db_present"])  # :memory: estate

    def test_status_reports_rows_and_vintage_after_ingest(self):
        self.stores["icd10"].upsert("dim_icd10_code", [
            {"code_key": "cm:E11.65", "code_type": "cm", "code": "E11.65",
             "name": "Type 2 diabetes mellitus with hyperglycemia",
             "source_endpoint": "cm",
             "ingested_at": "2026-07-01T00:00:00+00:00"}])
        status, body = self._get("/v1/status")
        self.assertEqual(status, 200)
        by_name = {r["connector"]: r for r in body["connectors"]}
        self.assertEqual(by_name["icd10"]["total_rows"], 1)
        self.assertEqual(by_name["icd10"]["last_ingested_at"],
                         "2026-07-01T00:00:00+00:00")
        # Sibling connectors stay honestly empty.
        self.assertEqual(by_name["openfda"]["total_rows"], 0)
        self.assertIsNone(by_name["openfda"]["last_ingested_at"])

    def test_estate_status_helper_matches_the_route(self):
        direct = estate_status(self.stores, self.adapters)
        _, body = self._get("/v1/status")
        self.assertEqual(direct, body["connectors"])


class HttpGrammarTests(_ServerCase):
    def _seed_events(self):
        self.stores["openfda"].upsert("fact_drug_adverse_event", [
            {"safetyreportid": "r1", "patient_age": "9",
             "occurcountry": "US", "source_endpoint": "drug_event"},
            {"safetyreportid": "r2", "patient_age": "10",
             "occurcountry": "CA", "source_endpoint": "drug_event"},
            {"safetyreportid": "r3", "patient_age": "40",
             "occurcountry": "FR", "source_endpoint": "drug_event"},
        ])

    def test_numeric_gt_over_http_orders_numerically(self):
        self._seed_events()
        status, body = self._get(
            "/v1/query/openfda_drug_event?patient_age__gt=9")
        self.assertEqual(status, 200)
        self.assertEqual({r["safetyreportid"] for r in body["rows"]},
                         {"r2", "r3"},
                         "lexicographic TEXT compare leaked through HTTP")

    def test_in_comma_list_over_http_matches_rows(self):
        self._seed_events()
        status, body = self._get(
            "/v1/query/openfda_drug_event?occurcountry__in=US,CA")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2,
                         "comma-joined __in silently matched nothing")
        self.assertEqual({r["safetyreportid"] for r in body["rows"]},
                         {"r1", "r2"})

    def test_between_comma_over_http(self):
        self._seed_events()
        status, body = self._get(
            "/v1/query/openfda_drug_event?patient_age__between=9,11")
        self.assertEqual(status, 200)
        self.assertEqual({r["safetyreportid"] for r in body["rows"]},
                         {"r1", "r2"})


class MetricsOverHttpTests(_ServerCase):
    def _seed_events(self):
        self.stores["openfda"].upsert("fact_drug_adverse_event", [
            {"safetyreportid": "r1", "patient_age": "9",
             "occurcountry": "US", "source_endpoint": "drug_event"},
            {"safetyreportid": "r2", "patient_age": "10",
             "occurcountry": "US", "source_endpoint": "drug_event"},
            {"safetyreportid": "r3", "patient_age": "40",
             "occurcountry": "FR", "source_endpoint": "drug_event"},
        ])

    def test_metric_param_computes_sum_avg_over_http(self):
        self._seed_events()
        status, body = self._get(
            "/v1/query/openfda_drug_event/aggregate"
            "?group_by=occurcountry&metric=sum:patient_age,avg:patient_age")
        self.assertEqual(status, 200)
        self.assertEqual(body["metrics"],
                         ["sum:patient_age", "avg:patient_age"])
        by_country = {r["occurcountry"]: r for r in body["rows"]}
        self.assertEqual(by_country["US"]["count"], 2)
        self.assertEqual(by_country["US"]["sum_patient_age"], 19.0)
        self.assertEqual(by_country["US"]["avg_patient_age"], 9.5)
        self.assertEqual(by_country["FR"]["sum_patient_age"], 40.0)

    def test_metric_param_absent_keeps_count_only_shape(self):
        self._seed_events()
        status, body = self._get(
            "/v1/query/openfda_drug_event/aggregate?group_by=occurcountry")
        self.assertEqual(status, 200)
        self.assertEqual(body["metrics"], [])
        for r in body["rows"]:
            self.assertEqual(set(r), {"occurcountry", "count"})

    def test_bad_metric_specs_return_400_with_error_shape(self):
        self._seed_events()
        for q in ("metric=median:patient_age", "metric=sum:nope",
                  "metric=sum"):
            status, body = self._get(
                f"/v1/query/openfda_drug_event/aggregate"
                f"?group_by=occurcountry&{q}")
            self.assertEqual(status, 400, q)
            self.assertIn("error", body, q)


class ParamHardeningTests(_ServerCase):
    def test_junk_limit_on_lookup_route_never_500s(self):
        # npi_registry's taxonomy lookup takes ?limit= through the unified
        # binder; a non-numeric value must clamp, not ValueError → 500.
        status, body = self._get("/v1/lookup/taxonomy/207Q00000X?limit=abc")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)

    def test_junk_limit_on_query_clamps_to_default(self):
        status, body = self._get("/v1/query/openfda_drug_event?limit=abc")
        self.assertEqual(status, 200)
        self.assertEqual(body["limit"], 50)

    def test_unknown_filter_field_is_a_400_not_500(self):
        status, body = self._get("/v1/query/openfda_drug_event?bogus=1")
        self.assertEqual(status, 400)
        self.assertIn("error", body)


class LookupBinderCoverageTests(_ServerCase):
    def test_every_lookup_route_binds_through_the_unified_server(self):
        # Data-driven over the live route tables so the 17th connector is
        # covered for free. Unseeded stores must still produce structured
        # 200 payloads (found-or-not), never a binder 404 or a 500.
        for name in CONNECTOR_NAMES:
            handlers = self.adapters[name].lookup_handlers(self.stores[name])
            self.assertTrue(handlers, f"{name} registered no lookups")
            for template in handlers:
                path = re.sub(r"\{[^}]+\}", "x", template)
                status, body = self._get(path)
                self.assertEqual(
                    status, 200,
                    f"{name} {template}: unified binder returned {status}")
                self.assertIsInstance(body, dict, f"{name} {template}")


if __name__ == "__main__":
    unittest.main()
