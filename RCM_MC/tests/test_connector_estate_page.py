"""Connector-estate integration — bridge + /connector-estate page.

The repo-root ``connectors/`` estate (13+ public healthcare API connectors,
~150 registered datasets — a moving target, so counts are floors here)
reaches the app only through the read-only bridge
``rcm_mc.data_public.connector_estate``. These tests pin:

  - the bridge finds the estate in-repo and degrades (no exception, empty
    results) when it is absent or not ingested;
  - owner resolution works for a dataset from every connector;
  - limits are clamped; sample queries never create stray db files;
  - the /connector-estate route serves every view over real HTTP;
  - the unavailable-estate path renders an editorial empty state, not a 500.

Env vars (RCM_MC_CONNECTORS_ROOT / RCM_MC_CONNECTORS_DB) are repointed to
temp dirs to exercise the absent/no-ingest paths — an external-input knob,
not a mock of our own code. Every test restores the environment so the
suite stays order-independent.
"""
from __future__ import annotations

import os
import socket
import tempfile
import unittest
from contextlib import closing

from rcm_mc.data_public import connector_estate as est

# One dataset id per connector (registration order) — pins owner resolution
# across the whole estate, including all nine round-1 connectors.
_ONE_PER_CONNECTOR = {
    "openfda": "openfda_device_510k",
    "cms_coverage": "cms_coverage_contractors",
    "npi_registry": "npi_provider",
    "icd10": "icd10_cm",
    "cms_open_data": "cms_open_data_catalog",
    "provider_data": "provider_data_catalog",
    "open_payments": "open_payments_catalog",
    "medicaid_data": "medicaid_data_nadac_2026",
    "healthcare_gov": "healthcare_gov_catalog",
    "cdc_data": "cdc_data_catalog",
    "hrsa_data": "hrsa_data_health_center_sites",
    "nih_reporter": "nih_reporter_projects",
    "census_acs": "census_acs_cbsa_profile",
}

_ENV_KEYS = ("RCM_MC_CONNECTORS_ROOT", "RCM_MC_CONNECTORS_DB")


class _EnvGuard(unittest.TestCase):
    """Save/restore the bridge env knobs around every test."""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in _ENV_KEYS}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class BridgeAvailabilityTests(_EnvGuard):
    def test_estate_available_in_repo(self):
        self.assertTrue(est.estate_available())
        self.assertIsNotNone(est.repo_root())

    def test_all_datasets_carries_the_estate(self):
        rows = est.all_datasets()
        self.assertGreaterEqual(len(rows), 90)
        # Uniform RegistryRow field names on every row.
        for field in ("dataset_id", "connector", "base_url", "endpoint",
                      "refresh_cadence", "join_keys", "target_table"):
            self.assertIn(field, rows[0])

    def test_owner_resolution_for_every_connector(self):
        for connector, dataset_id in _ONE_PER_CONNECTOR.items():
            self.assertEqual(est.dataset_owner(dataset_id), connector,
                             f"{dataset_id} should belong to {connector}")

    def test_connectors_summary_registration_order(self):
        # >= 13: the estate is a moving target (new connectors land at
        # the repo root without touching the app) — pin the original 13
        # plus registration order, not an exact count.
        names = [s["connector"] for s in est.connectors_summary()]
        self.assertGreaterEqual(len(names), 13)
        self.assertEqual(names[0], "openfda")
        for needed in _ONE_PER_CONNECTOR:
            self.assertIn(needed, names)

    def test_catalog_totals_agree(self):
        cat = est.estate_catalog()
        self.assertEqual(cat.get("n_connectors"),
                         len(est.connectors_summary()))
        self.assertEqual(cat.get("n_datasets"), len(est.all_datasets()))

    def test_unavailable_estate_degrades_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp  # no connectors/_spi.py
            self.assertFalse(est.estate_available())
            self.assertEqual(est.all_datasets(), [])
            self.assertEqual(est.connectors_summary(), [])
            self.assertEqual(est.estate_catalog(), {})
            self.assertIsNone(est.dataset_owner("icd10_cm"))
            self.assertEqual(est.sample_rows("icd10_cm"), {})
            self.assertEqual(est.aggregate("icd10_cm", "code"), {})
            self.assertEqual(est.ingested_counts(), {})


class BridgeQueryTests(_EnvGuard):
    def setUp(self):
        super().setUp()
        # Point the store dir at an empty temp dir: no connector has an
        # ingested db, so every query runs on :memory: (empty but valid).
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def test_sample_rows_without_db_is_empty_not_an_error(self):
        out = est.sample_rows("icd10_cm")
        # Either {} or an empty-but-valid QueryResult dict is acceptable.
        self.assertEqual(out.get("rows", []), [])
        self.assertEqual(out.get("total", 0), 0)

    def test_sample_rows_never_creates_store_files(self):
        est.sample_rows("icd10_cm")
        est.aggregate("cms_coverage_contractors", "contractor_id")
        self.assertEqual(os.listdir(self._tmp.name), [])

    def test_unknown_dataset_returns_empty_dict(self):
        self.assertEqual(est.sample_rows("no_such_dataset"), {})
        self.assertEqual(est.aggregate("no_such_dataset", "x"), {})

    def test_limit_clamped_to_1_100(self):
        big = est.sample_rows("icd10_cm", limit=99_999)
        self.assertLessEqual(big.get("limit", 100), 100)
        small = est.sample_rows("icd10_cm", limit=-5)
        self.assertGreaterEqual(small.get("limit", 1), 1)
        bogus = est.sample_rows("icd10_cm", limit="abc")
        self.assertEqual(bogus.get("limit"), 10)

    def test_aggregate_rejects_bad_group_by_gracefully(self):
        self.assertEqual(est.aggregate("icd10_cm", "not_a_column"), {})
        self.assertEqual(est.aggregate("icd10_cm", []), {})

    def test_db_dir_honours_env_and_is_not_created(self):
        target = os.path.join(self._tmp.name, "does-not-exist")
        os.environ["RCM_MC_CONNECTORS_DB"] = target
        self.assertEqual(est.db_dir(), target)
        est.sample_rows("icd10_cm")
        self.assertFalse(os.path.exists(target))

    def test_round_trip_through_a_real_ingested_store(self):
        # Seed a real icd10 store (the connector's own store API via the
        # bridge adapter — no mocks) in the temp dir, then read it back
        # through the bridge. Not `import connectors...` — that top-level
        # name belongs to the in-app NPPES-universe package in this suite.
        row = est.dataset_row("icd10_cm")
        self.assertIsNotNone(row)
        adapter = est.adapter_for("icd10")
        self.assertIsNotNone(adapter)
        store = adapter.open_store(
            os.path.join(self._tmp.name, "icd10.db"))
        try:
            store.upsert("dim_icd10_code", [
                {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
                 "name": "Type 2 diabetes mellitus without complications",
                 "source_endpoint": row["source_filter"]},
                {"code_key": "cm:I10", "code_type": "cm", "code": "I10",
                 "name": "Essential (primary) hypertension",
                 "source_endpoint": row["source_filter"]},
            ])
        finally:
            store.close()
        out = est.sample_rows("icd10_cm", limit=10)
        self.assertEqual(out.get("total"), 2)
        self.assertEqual(len(out.get("rows", [])), 2)
        counts = est.ingested_counts()
        self.assertEqual(counts.get("icd10"), 2)
        self.assertEqual(est.dataset_ingested_count("icd10_cm"), 2)
        agg = est.aggregate("icd10_cm", "code_type", limit=5)
        self.assertEqual(agg.get("rows"), [{"code_type": "cm", "count": 2}])


class PageRenderTests(_EnvGuard):
    def test_overview_lists_every_connector_label(self):
        from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate
        h = render_connector_estate({})
        for label in ("openFDA (drug + device)",
                      "CMS Medicare Coverage Database",
                      "Medicaid Open Data (data.medicaid.gov)",
                      "NIH RePORTER (grants + publications)",
                      "US Census ACS 5-year (demographics)"):
            self.assertIn(label, h, f"{label!r} missing from overview")
        self.assertIn("Connector Estate", h)

    def test_detail_view_has_registry_api_and_cli(self):
        from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate
        h = render_connector_estate({"dataset": "cms_open_data_catalog"})
        self.assertIn("/v1/query/cms_open_data_catalog", h)
        self.assertIn("python -m connectors.cms_open_data.cli query", h)
        self.assertIn("cms_open_data_catalog", h)

    def test_unknown_dataset_renders_empty_state_not_500(self):
        from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate
        h = render_connector_estate({"dataset": "<bogus & weird>"})
        self.assertIn("Unknown dataset", h)
        self.assertNotIn("<bogus", h)  # escaped

    def test_unavailable_estate_renders_full_page_empty_state(self):
        from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            h = render_connector_estate({})
            self.assertIn("Connector estate not available", h)
            self.assertIn("ck-empty-state", h)
            self.assertIn("connectors.cli", h)


class HttpRouteTests(_EnvGuard):
    @classmethod
    def setUpClass(cls):
        import threading
        import time

        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            cls._port = s.getsockname()[1]
        srv, _ = build_server(port=cls._port,
                              db_path=os.path.join(cls._tmp.name, "p.db"),
                              host="127.0.0.1")
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _get(self, path):
        import urllib.error
        import urllib.request
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{path}", timeout=10)
        except urllib.error.HTTPError as exc:
            return exc

    def test_overview_serves_200_with_connector_labels(self):
        resp = self._get("/connector-estate")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Connector Estate", body)
        self.assertIn("openFDA (drug + device)", body)
        self.assertIn("CMS Medicare Coverage Database", body)

    def test_dataset_detail_serves_200(self):
        resp = self._get("/connector-estate?dataset=cms_open_data_catalog")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("cms_open_data_catalog", body)
        self.assertIn("/v1/query/cms_open_data_catalog", body)

    def test_search_nadac_serves_200_and_finds_medicaid(self):
        resp = self._get("/connector-estate?q=nadac")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("medicaid", body)

    def test_connector_filter_serves_200(self):
        resp = self._get("/connector-estate?connector=hrsa_data")
        self.assertEqual(resp.status, 200)
        self.assertIn("hrsa_data_health_center_sites", resp.read().decode())

    def test_unavailable_estate_serves_empty_state_not_500(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            try:
                resp = self._get("/connector-estate")
                self.assertEqual(resp.status, 200)
                self.assertIn("Connector estate not available",
                              resp.read().decode())
            finally:
                os.environ.pop("RCM_MC_CONNECTORS_ROOT", None)

    def test_cms_sources_estate_section_serves(self):
        resp = self._get("/cms-sources")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("ESTATE CONNECTORS", body)
        self.assertIn("/connector-estate?dataset=", body)


class WiringTests(unittest.TestCase):
    def test_route_in_nav_palette_and_breadcrumb(self):
        import inspect

        from rcm_mc.ui import _chartis_kit as kit
        src = inspect.getsource(kit)
        self.assertIn('"/connector-estate"', src)
        self.assertIn('"/connector-estate": "research"', src)

    def test_palette_and_sub_nav_entries(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES, _SUB_NAV, _resolve_sub_section
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/connector-estate", routes)
        research = {e["href"] for e in _SUB_NAV["research"]}
        self.assertIn("/connector-estate", research)
        self.assertEqual(_resolve_sub_section("/connector-estate"), "research")

    def test_public_api_catalog_represents_all_13_connectors(self):
        # Superset, not equality: later estate connectors may be added
        # to the catalog without touching this test.
        from rcm_mc.data_public import public_api_catalog as cat
        estate_modules = {s.client_module for s in cat.all_sources()
                          if s.client_module.startswith("connectors.")}
        expected = {
            f"connectors.{n}" for n in (
                "openfda", "cms_coverage", "npi_registry", "icd10",
                "cms_open_data", "provider_data", "open_payments",
                "medicaid_data", "healthcare_gov", "cdc_data",
                "hrsa_data", "nih_reporter", "census_acs")}
        self.assertTrue(expected.issubset(estate_modules),
                        f"missing: {expected - estate_modules}")


if __name__ == "__main__":
    unittest.main()
