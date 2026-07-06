"""Connector-estate integration — bridge + /connector-estate page.

The repo-root ``connectors/`` estate (13+ public healthcare API connectors,
~150 registered datasets — a moving target, so counts are floors here)
reaches the app only through the read-only bridge
``rcm_mc.data_public.connector_estate``. These tests pin:

  - the bridge finds the estate in-repo and degrades (no exception, empty
    results) when it is absent or not ingested;
  - owner resolution works for a dataset from every connector;
  - limits are clamped; sample queries never create stray db files;
  - warm_up() is idempotent, runs during build_server(), and closes the
    sys.modules swap window (a bounded stress loop pins the race fix);
  - a broken estate root is negatively cached — no swap re-runs per call;
  - shared-table datasets report source_filter-sliced ingested counts;
  - the /connector-estate route serves every view over real HTTP;
  - the unavailable-estate path renders an editorial empty state, not a 500.

Env vars (RCM_MC_CONNECTORS_ROOT / RCM_MC_CONNECTORS_DB) are repointed to
temp dirs to exercise the absent/no-ingest paths — an external-input knob,
not a mock of our own code. Every test restores the environment so the
suite stays order-independent.
"""
from __future__ import annotations

import importlib
import os
import socket
import sys
import tempfile
import threading
import time
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


class BridgeWarmupRaceTests(_EnvGuard):
    """Regression: the load-time sys.modules swap raced other threads.

    Before the fix, hammering bridge calls while another thread imported
    the in-app ``connectors.nppes`` reproduced 60k+ violations (estate
    bound under the in-app name, or ModuleNotFoundError) in ~2 seconds.
    warm_up() moves the swap into single-threaded server boot and the
    handle cache keeps every later call off interpreter state — so zero
    observations in the same bounded loop is a meaningful assertion.
    """

    def test_warm_up_is_idempotent(self):
        self.assertTrue(est.warm_up())
        handles = est._HANDLES
        self.assertIsNotNone(handles)
        self.assertTrue(est.warm_up())
        self.assertIs(est._HANDLES, handles)  # cache hit, not a reload

    def test_build_server_warms_the_bridge_before_serving(self):
        # The boot path must warm the bridge while still single-threaded:
        # build (but never start) a server from a cold bridge and assert
        # the handles already exist before any request could be served.
        from rcm_mc.server import build_server
        est.reset_for_tests()
        self.assertIsNone(est._HANDLES)
        with tempfile.TemporaryDirectory() as tmp:
            with closing(socket.socket()) as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            srv, _ = build_server(port=port,
                                  db_path=os.path.join(tmp, "p.db"),
                                  host="127.0.0.1")
            try:
                self.assertIsNotNone(est._HANDLES)
            finally:
                srv.server_close()

    def test_no_estate_leak_under_concurrent_inapp_imports(self):
        self.assertTrue(est.warm_up())
        root = est.repo_root()
        self.assertIsNotNone(root)
        estate_prefix = os.path.join(os.path.abspath(root),
                                     "connectors") + os.sep
        saved = {k: v for k, v in sys.modules.items()
                 if k == "connectors" or k.startswith("connectors.")}
        stop = threading.Event()
        violations: list[str] = []

        def hammer():
            while not stop.is_set():
                est.estate_available()
                est.connectors_summary()
                est.dataset_owner("icd10_cm")

        def importer():
            while not stop.is_set():
                sys.modules.pop("connectors.nppes", None)
                sys.modules.pop("connectors", None)
                try:
                    mod = importlib.import_module("connectors.nppes")
                except Exception as exc:
                    # Not just ModuleNotFoundError: the swap deleting
                    # sys.modules entries mid-import also surfaces as a
                    # raw KeyError('connectors') from the import
                    # machinery. Catch broadly or a regression would
                    # kill this thread silently and pass vacuously.
                    violations.append(
                        f"in-app import raised: "
                        f"{type(exc).__name__}: {exc}")
                    continue
                mod_file = os.path.abspath(
                    getattr(mod, "__file__", "") or "")
                if mod_file.startswith(estate_prefix):
                    violations.append(
                        f"estate leaked under in-app name: {mod_file}")

        threads = [threading.Thread(target=hammer, daemon=True)
                   for _ in range(4)]
        threads.append(threading.Thread(target=importer, daemon=True))
        try:
            for t in threads:
                t.start()
            time.sleep(2.0)
        finally:
            stop.set()
            for t in threads:
                t.join(timeout=10)
            # Restore the exact pre-test module state so later suites
            # (the NPPES CI gate) see the in-app package untouched.
            for k in [k for k in sys.modules
                      if k == "connectors" or k.startswith("connectors.")]:
                del sys.modules[k]
            sys.modules.update(saved)
        self.assertEqual(
            violations[:5], [],
            f"{len(violations)} cross-package import violations observed")


class BridgeNegativeCacheTests(_EnvGuard):
    """Regression: a failed estate load was never cached, so every bridge
    call re-ran the full sys.modules swap (the race window) while holding
    the global lock. The failure must be cached per resolved root, be
    cleared by an RCM_MC_CONNECTORS_ROOT repoint, and be clearable via
    reset_for_tests().
    """

    def setUp(self):
        super().setUp()
        est.reset_for_tests()

    def tearDown(self):
        est.reset_for_tests()
        super().tearDown()

    @staticmethod
    def _make_broken_root(tmp: str) -> None:
        """A root that RESOLVES (has connectors/_spi.py) but fails import.

        The broken __init__ appends one byte to attempts.log per import
        attempt — the counter that proves the negative cache short-
        circuits the retry.
        """
        pkg = os.path.join(tmp, "connectors")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "_spi.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(pkg, "__init__.py"), "w") as fh:
            fh.write(
                "import os\n"
                "_log = os.path.join(os.path.dirname(__file__),"
                " 'attempts.log')\n"
                "with open(_log, 'a') as fh:\n"
                "    fh.write('x')\n"
                "raise RuntimeError('estate deliberately broken')\n")

    @staticmethod
    def _attempts(root: str) -> int:
        path = os.path.join(root, "connectors", "attempts.log")
        if not os.path.isfile(path):
            return 0
        with open(path) as fh:
            return len(fh.read())

    def test_failed_load_is_cached_and_cleared_on_repoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_broken_root(tmp)
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            self.assertFalse(est.estate_available())
            self.assertEqual(self._attempts(tmp), 1)
            # Repeat calls answer from the negative cache — no re-import,
            # no sys.modules swap, still gracefully degraded.
            self.assertFalse(est.estate_available())
            self.assertEqual(est.all_datasets(), [])
            self.assertEqual(est.ingested_counts(), {})
            self.assertEqual(self._attempts(tmp), 1)
            # The exception summary is preserved for diagnostics.
            failure = est.load_failure()
            self.assertIsNotNone(failure)
            self.assertIn("RuntimeError", failure)
            self.assertIn("estate deliberately broken", failure)
            # reset_for_tests() clears the negative cache → one retry.
            est.reset_for_tests()
            self.assertFalse(est.estate_available())
            self.assertEqual(self._attempts(tmp), 2)
            # Repointing to the real estate bypasses AND clears the
            # cached failure...
            os.environ.pop("RCM_MC_CONNECTORS_ROOT", None)
            self.assertTrue(est.estate_available())
            self.assertIsNone(est.load_failure())
            # ...so pointing back at the broken root retries it fresh.
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            self.assertFalse(est.estate_available())
            self.assertEqual(self._attempts(tmp), 3)

    def test_load_failure_is_none_on_healthy_estate(self):
        self.assertTrue(est.estate_available())
        self.assertIsNone(est.load_failure())


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

    def test_shared_table_counts_respect_source_filter(self):
        # medicaid NADAC: per-year datasets share ONE physical table,
        # sliced by source_endpoint (the estate's documented shared-table
        # pattern). The per-dataset ingested count must count only its
        # slice — before the fix every year-slice reported the whole
        # table (5 here).
        row_2026 = est.dataset_row("medicaid_data_nadac_2026")
        row_2025 = est.dataset_row("medicaid_data_nadac_2025")
        self.assertIsNotNone(row_2026)
        self.assertIsNotNone(row_2025)
        self.assertEqual(row_2026["target_table"], row_2025["target_table"])
        self.assertNotEqual(row_2026["source_filter"],
                            row_2025["source_filter"])
        adapter = est.adapter_for("medicaid_data")
        self.assertIsNotNone(adapter)
        store = adapter.open_store(
            os.path.join(self._tmp.name, "medicaid_data.db"))

        def _row(key, ndc, as_of, src):
            return {"nadac_key": key, "ndc": ndc, "as_of_date": as_of,
                    "effective_date": as_of, "nadac_per_unit": "1.00",
                    "source_endpoint": src}

        try:
            store.upsert(row_2026["target_table"], [
                _row("26a", "00000000001", "2026-01-07",
                     row_2026["source_filter"]),
                _row("26b", "00000000002", "2026-01-07",
                     row_2026["source_filter"]),
                _row("25a", "00000000001", "2025-06-04",
                     row_2025["source_filter"]),
                _row("25b", "00000000002", "2025-06-04",
                     row_2025["source_filter"]),
                _row("25c", "00000000003", "2025-06-04",
                     row_2025["source_filter"]),
            ])
        finally:
            store.close()
        self.assertEqual(
            est.dataset_ingested_count("medicaid_data_nadac_2026"), 2)
        self.assertEqual(
            est.dataset_ingested_count("medicaid_data_nadac_2025"), 3)
        # The connector-level rollup still counts the whole table once.
        self.assertEqual(est.ingested_counts().get("medicaid_data"), 5)
        # And the estate-page detail view's LOCAL STORE section renders
        # the slice count, not the shared table's total. (The page-title
        # meta still says "5 rows ingested locally" — that one is the
        # estate-wide rollup and stays a whole-table sum by design.)
        from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate
        h = render_connector_estate({"dataset": "medicaid_data_nadac_2026"})
        self.assertIn("2 rows ingested · first 10 shown", h)
        self.assertNotIn("5 rows ingested · first 10 shown", h)


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
