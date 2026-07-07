"""Per-connector ``/v1/status`` parity with the unified estate surface.

Every standalone connector server now exposes ``/v1/status`` with the
same envelope and row shape as the unified server's route (a
``{"connectors": [row]}`` list of one), so a caller can read fetch state
identically whichever surface it hits. Data-driven over
``CONNECTOR_NAMES`` — the 17th connector is covered for free.

Real ThreadingHTTPServer on a free port per connector, real stores,
urllib over a socket — the estate's no-mocks convention.
"""
import importlib
import json
import threading
import unittest
import urllib.error
import urllib.request

from .._spi import CONNECTOR_LABELS, CONNECTOR_NAMES, load_all

# The unified /v1/status row contract (api_server.estate_status).
_UNIFIED_KEYS = {"connector", "label", "db_path", "db_present",
                 "total_rows", "last_ingested_at"}


def _get(port, path):
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class PerConnectorStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def _serve(self, name, store):
        mod = importlib.import_module(f"connectors.{name}.api_server")
        server, port = mod.make_server(store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, port

    def test_status_module_constants_match_the_estate(self):
        # The standalone servers carry their name/label locally (the
        # packages stay self-contained, no cross-import) — pin them to
        # the estate's registry so the copies can never drift.
        for name in CONNECTOR_NAMES:
            mod = importlib.import_module(f"connectors.{name}.api_server")
            self.assertEqual(mod._CONNECTOR_NAME, name)
            self.assertEqual(mod._CONNECTOR_LABEL, CONNECTOR_LABELS[name])

    def test_every_connector_reports_status_identically(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            store = adapter.open_store(":memory:")
            server, port = self._serve(name, store)
            try:
                status, body = _get(port, "/v1/status")
                self.assertEqual(status, 200, name)
                rows = body["connectors"]
                self.assertEqual(len(rows), 1, name)
                row = rows[0]
                # Same keys as one unified-status entry, plus the
                # per-table breakdown this surface adds.
                self.assertTrue(_UNIFIED_KEYS <= set(row), name)
                self.assertEqual(row["connector"], name)
                self.assertEqual(row["label"], CONNECTOR_LABELS[name])
                self.assertFalse(row["db_present"], name)  # :memory:
                self.assertEqual(row["total_rows"], 0, name)
                self.assertIsNone(row["last_ingested_at"], name)
                self.assertEqual(
                    set(row["tables"]),
                    set(adapter.tables_mod.TABLES), name)
            finally:
                server.shutdown()
                server.server_close()
                store.close()

    def test_status_reports_rows_and_vintage_after_ingest(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            store = adapter.open_store(":memory:")
            tname, tdef = next(iter(adapter.tables_mod.TABLES.items()))
            store.upsert(tname, [{tdef.pk: "status-probe-1"}])
            server, port = self._serve(name, store)
            try:
                status, body = _get(port, "/v1/status")
                self.assertEqual(status, 200, name)
                row = body["connectors"][0]
                self.assertEqual(row["total_rows"], 1, name)
                self.assertIsNotNone(row["last_ingested_at"], name)
                self.assertEqual(row["tables"][tname], 1, name)
            finally:
                server.shutdown()
                server.server_close()
                store.close()


class PerConnectorMetricAndHardeningTests(unittest.TestCase):
    """The standalone servers carry the new metric grammar + 400 shapes."""

    def test_metric_param_on_a_standalone_server(self):
        from connectors.bls_qcew.api_server import make_server
        from connectors.bls_qcew.tables import BlsQcewStore
        store = BlsQcewStore(":memory:")
        store.upsert("qcew_industry_area", [
            {"qcew_key": "k1", "area_fips": "01000", "avg_wkly_wage": "100",
             "source_endpoint": "industry_area"},
            {"qcew_key": "k2", "area_fips": "01000", "avg_wkly_wage": "50",
             "source_endpoint": "industry_area"},
        ])
        server, port = make_server(store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, body = _get(
                port, "/v1/query/bls_qcew_industry_area/aggregate"
                      "?group_by=area_fips&metric=sum:avg_wkly_wage")
            self.assertEqual(status, 200)
            self.assertEqual(body["metrics"], ["sum:avg_wkly_wage"])
            self.assertEqual(body["rows"][0]["sum_avg_wkly_wage"], 150.0)
            status, body = _get(
                port, "/v1/query/bls_qcew_industry_area/aggregate"
                      "?group_by=area_fips&metric=median:avg_wkly_wage")
            self.assertEqual(status, 400)
            self.assertIn("error", body)
        finally:
            server.shutdown()
            server.server_close()
            store.close()

    def test_openfda_companies_junk_limit_never_500s(self):
        from connectors.openfda.api_server import make_server
        from connectors.openfda.tables import OpenFdaStore
        store = OpenFdaStore(":memory:")
        server, port = make_server(store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, body = _get(port, "/v1/companies?q=acme&limit=abc")
            self.assertEqual(status, 200)
            self.assertEqual(body, {"companies": []})
        finally:
            server.shutdown()
            server.server_close()
            store.close()


if __name__ == "__main__":
    unittest.main()
