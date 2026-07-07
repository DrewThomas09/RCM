"""Estate-improvement round: honest hints, vintages, degraded states.

Pins the connector-estate front's app-side improvements:

  - ingest_hint(): manual-only connectors (refresh skips them) get their
    own-CLI pointer instead of the refresh command that can never work;
  - cli_query_hint(): the copy-ready CLI one-liner carries the storage
    flag (--root dir / --db file, before or after the verb per style) so
    it queries the ingested db instead of an empty default store;
  - dataset detail + connector cards surface a last-ingested vintage so
    "fresh pull" and "year-stale" are distinguishable;
  - a resolved-but-broken estate root renders a distinct failed-to-load
    state (with the cached import error) instead of the misleading
    "check out the full repository" copy;
  - the overview computes ingested_counts() once per request (it opens
    every connector's SQLite file), not three times.

Same env-knob conventions as tests/test_connector_estate_page.py: the
bridge env vars are repointed to temp dirs and restored after each test.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.data_public import connector_estate as est
from rcm_mc.ui.data_public.connector_estate_page import render_connector_estate

_ENV_KEYS = ("RCM_MC_CONNECTORS_ROOT", "RCM_MC_CONNECTORS_DB")


class _EnvGuard(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in _ENV_KEYS}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class IngestHintTests(_EnvGuard):
    def test_manual_only_connectors_get_own_cli_pointer(self):
        for name in ("openfda", "npi_registry", "icd10"):
            hint = est.ingest_hint(name)
            self.assertIs(hint.get("planned"), False, name)
            self.assertIn(f"connectors.{name}.cli", hint.get("command", ""))
            self.assertIn(f"connectors/{name}/README.md",
                          hint.get("readme", ""))

    def test_planned_connectors_get_scoped_refresh_command(self):
        for name in ("medicaid_data", "cms_coverage", "hrsa_data"):
            hint = est.ingest_hint(name)
            self.assertIs(hint.get("planned"), True, name)
            self.assertIn("connectors.cli refresh", hint.get("command", ""))
            self.assertIn(f"--connector {name}", hint.get("command", ""))

    def test_degrades_to_empty_when_estate_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            self.assertEqual(est.ingest_hint("openfda"), {})


class CliQueryHintTests(_EnvGuard):
    def test_root_style_flag_precedes_verb(self):
        hint = est.cli_query_hint("icd10_cm")
        self.assertEqual(
            hint,
            "python -m connectors.icd10.cli --root var/connectors "
            "query icd10_cm --limit 10")

    def test_subcommand_db_style_flag_follows_verb(self):
        hint = est.cli_query_hint("cms_open_data_catalog")
        self.assertEqual(
            hint,
            "python -m connectors.cms_open_data.cli query "
            "cms_open_data_catalog --limit 10 "
            "--db var/connectors/cms_open_data.db")

    def test_top_level_db_style_flag_precedes_verb(self):
        hint = est.cli_query_hint("medicaid_data_nadac_2026")
        self.assertEqual(
            hint,
            "python -m connectors.medicaid_data.cli "
            "--db var/connectors/medicaid_data.db "
            "query medicaid_data_nadac_2026 --limit 10")

    def test_unknown_dataset_or_absent_estate_is_empty_string(self):
        self.assertEqual(est.cli_query_hint("nope_not_real"), "")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            self.assertEqual(est.cli_query_hint("icd10_cm"), "")


class DetailPageHintTests(_EnvGuard):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._tmp.name  # nothing ingested

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def test_manual_only_dataset_page_never_advertises_refresh(self):
        h = render_connector_estate({"dataset": "openfda_drug_ndc"})
        self.assertIn("manual-only", h)
        self.assertIn("connectors/openfda/README.md", h)
        # The old copy-ready command that can never work for openfda:
        self.assertNotIn("connectors.cli refresh --db var/connectors</code> "
                         "from the repo root", h)
        self.assertNotIn("refresh --db var/connectors --connector openfda", h)

    def test_planned_dataset_page_scopes_refresh_to_the_connector(self):
        h = render_connector_estate({"dataset": "medicaid_data_nadac_2026"})
        self.assertIn("refresh --db var/connectors --connector medicaid_data",
                      h)
        self.assertNotIn("manual-only", h)

    def test_query_one_liner_carries_the_storage_flag(self):
        h = render_connector_estate({"dataset": "icd10_cm"})
        self.assertIn("--root var/connectors query icd10_cm --limit 10", h)
        h = render_connector_estate({"dataset": "cms_open_data_catalog"})
        self.assertIn("--db var/connectors/cms_open_data.db", h)


class VintageTests(_EnvGuard):
    _STAMP = "2026-07-01T08:00:00+00:00"

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._tmp.name
        adapter = est.adapter_for("icd10")
        self.assertIsNotNone(adapter)
        store = adapter.open_store(os.path.join(self._tmp.name, "icd10.db"))
        try:
            store.upsert("dim_icd10_code", [
                {"code_key": "cm:E11.9", "code_type": "cm", "code": "E11.9",
                 "name": "Type 2 diabetes mellitus without complications",
                 "source_endpoint": "cm", "ingested_at": self._STAMP}])
        finally:
            store.close()

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def test_connector_vintages_reports_max_ingested_at(self):
        vintages = est.connector_vintages()
        self.assertEqual(vintages.get("icd10"), self._STAMP)
        # Connectors without a db file are omitted, not zeroed.
        self.assertNotIn("openfda", vintages)

    def test_dataset_vintage_respects_the_source_filter_slice(self):
        self.assertEqual(est.dataset_vintage("icd10_cm"), self._STAMP)
        # Same table, different slice → no vintage for the pcs dataset.
        self.assertIsNone(est.dataset_vintage("icd10_pcs"))

    def test_dataset_vintage_none_when_not_ingested(self):
        self.assertIsNone(est.dataset_vintage("openfda_drug_ndc"))

    def test_detail_page_and_overview_render_the_vintage(self):
        h = render_connector_estate({"dataset": "icd10_cm"})
        self.assertIn(f"last ingested {self._STAMP}", h)
        h = render_connector_estate({})
        self.assertIn(f"last ingested {self._STAMP}", h)


class BrokenEstatePageTests(_EnvGuard):
    """A resolved-but-broken root must render the import error, not the
    'check out the full repository' copy (the tree IS checked out)."""

    def setUp(self):
        super().setUp()
        est.reset_for_tests()

    def tearDown(self):
        est.reset_for_tests()
        super().tearDown()

    @staticmethod
    def _make_broken_root(tmp: str) -> None:
        pkg = os.path.join(tmp, "connectors")
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "_spi.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(pkg, "__init__.py"), "w") as fh:
            fh.write("raise RuntimeError('estate deliberately broken "
                     "<script>alert(1)</script>')\n")

    def test_failed_load_renders_degraded_state_with_escaped_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_broken_root(tmp)
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp
            h = render_connector_estate({})
            self.assertIn("Connector estate failed to load", h)
            self.assertIn("RuntimeError", h)
            self.assertIn("estate deliberately broken", h)
            # html.escape'd — the raw script tag never reaches the page.
            self.assertNotIn("<script>alert(1)</script>", h)
            self.assertIn("&lt;script&gt;", h)
            # The misleading not-found copy stays off this branch.
            self.assertNotIn("Check out the full repository", h)
            self.assertNotIn("Connector estate not available", h)

    def test_missing_root_keeps_the_not_found_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp  # no connectors/_spi.py
            h = render_connector_estate({})
            self.assertIn("Connector estate not available", h)
            self.assertNotIn("Connector estate failed to load", h)


class SingleComputationTests(_EnvGuard):
    def test_overview_computes_ingested_counts_once_per_request(self):
        # Instrument the real function with a counting pass-through (the
        # real code still runs — this only counts invocations).
        real = est.ingested_counts
        calls = {"n": 0}

        def counting():
            calls["n"] += 1
            return real()

        est.ingested_counts = counting
        try:
            render_connector_estate({})
        finally:
            est.ingested_counts = real
        self.assertEqual(calls["n"], 1,
                         "overview must reuse one ingested_counts() result")


if __name__ == "__main__":
    unittest.main()
