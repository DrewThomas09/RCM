"""Tests for the DataPoint / ProvenanceRegistry system (B163).

Covers:
- DataPoint construction, validation, serialization, rehydration
- Source enum coverage
- ProvenanceRegistry recording, lookup, all convenience recorders
- Calc confidence propagation (minimum-link rule)
- Recursive upstream tracing + cycle safety
- Dependency-graph export
- ``human_explain`` for each source type + missing metric
- SQLite persistence (save/load, latest-run fallback)
- Simulator & pe_math opt-in wiring (registry=None stays backwards compat)
- HTTP endpoints: ``/api/deals/<id>/provenance`` + single-metric
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import date
from http import HTTPStatus

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.provenance import DataPoint, ProvenanceRegistry, Source
from rcm_mc.provenance.registry import _ensure_provenance_table


# ────────────────────────────────────────────────────────────────────
# DataPoint
# ────────────────────────────────────────────────────────────────────

class TestDataPoint(unittest.TestCase):
    def test_basic_construction(self):
        dp = DataPoint(
            value=0.082, metric_name="denial_rate",
            source=Source.USER_INPUT, confidence=1.0,
        )
        self.assertEqual(dp.metric_name, "denial_rate")
        self.assertEqual(dp.value, 0.082)
        self.assertEqual(dp.source, Source.USER_INPUT)
        self.assertEqual(dp.upstream, [])

    def test_source_string_coerced_to_enum(self):
        dp = DataPoint(value=1.0, metric_name="x", source="HCRIS")
        self.assertIs(dp.source, Source.HCRIS)

    def test_empty_metric_name_rejected(self):
        with self.assertRaises(ValueError):
            DataPoint(value=1.0, metric_name="", source=Source.USER_INPUT)

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            DataPoint(value=1.0, metric_name="x",
                      source=Source.USER_INPUT, confidence=1.5)
        with self.assertRaises(ValueError):
            DataPoint(value=1.0, metric_name="x",
                      source=Source.USER_INPUT, confidence=-0.1)

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            DataPoint(value="not-a-number",  # type: ignore[arg-type]
                      metric_name="x", source=Source.USER_INPUT)

    def test_to_dict_serializes_upstream_as_names(self):
        parent = DataPoint(value=0.9, metric_name="clean_claim_rate",
                           source=Source.USER_INPUT)
        child = DataPoint(value=0.08, metric_name="denial_rate",
                          source=Source.REGRESSION_PREDICTED,
                          upstream=[parent])
        d = child.to_dict()
        self.assertEqual(d["upstream"], ["clean_claim_rate"])
        self.assertEqual(d["source"], "REGRESSION_PREDICTED")
        self.assertEqual(d["metric_name"], "denial_rate")

    def test_from_dict_roundtrips_with_lookup(self):
        parent = DataPoint(value=0.9, metric_name="p",
                           source=Source.USER_INPUT)
        child = DataPoint(value=0.08, metric_name="c",
                          source=Source.CALCULATED, upstream=[parent])
        rebuilt = DataPoint.from_dict(child.to_dict(),
                                       lookup={"p": parent})
        self.assertEqual(rebuilt.metric_name, "c")
        self.assertEqual(len(rebuilt.upstream), 1)
        self.assertEqual(rebuilt.upstream[0].metric_name, "p")

    def test_source_enum_has_all_seven_types(self):
        names = {s.name for s in Source}
        self.assertEqual(names, {
            "USER_INPUT", "HCRIS", "IRS990", "REGRESSION_PREDICTED",
            "BENCHMARK_MEDIAN", "MONTE_CARLO_P50", "CALCULATED",
        })


# ────────────────────────────────────────────────────────────────────
# ProvenanceRegistry — core
# ────────────────────────────────────────────────────────────────────

class TestRegistryCore(unittest.TestCase):
    def test_record_and_get(self):
        reg = ProvenanceRegistry(deal_id="d1", run_id="r1")
        dp = reg.record_user_input(0.08, "denial_rate")
        self.assertIs(reg.get("denial_rate"), dp)
        self.assertIn("denial_rate", reg)
        self.assertEqual(len(reg), 1)

    def test_missing_metric_returns_none(self):
        reg = ProvenanceRegistry()
        self.assertIsNone(reg.get("nope"))
        self.assertNotIn("nope", reg)

    def test_overwrite_last_write_wins(self):
        reg = ProvenanceRegistry()
        reg.record_user_input(0.08, "denial_rate")
        reg.record_user_input(0.09, "denial_rate")
        self.assertEqual(reg.get("denial_rate").value, 0.09)
        self.assertEqual(len(reg), 1)

    def test_record_rejects_non_datapoint(self):
        reg = ProvenanceRegistry()
        with self.assertRaises(TypeError):
            reg.record({"value": 1.0})  # type: ignore[arg-type]

    def test_all_recorder_shortcuts_tag_correct_source(self):
        reg = ProvenanceRegistry()
        reg.record_user_input(0.9, "clean_claim_rate")
        reg.record_hcris(50e6, "total_revenue", ccn="450321",
                          fiscal_year=2022)
        reg.record_irs990(52e6, "total_expenses", ein="123456789",
                           tax_year=2022)
        reg.record_benchmark_median(0.05, "denial_rate_median",
                                     cohort_description="300-bed AMCs",
                                     n_peers=42)
        parent = reg.get("clean_claim_rate")
        reg.record_regression(0.08, "denial_rate",
                               upstream=[parent],
                               r_squared=0.84, n_samples=47,
                               predictor_summary="clean claim rate")
        reg.record_mc(12.5e6, "ebitda_impact",
                       n_sims=10000, percentile=50, stddev=0.5e6)
        reg.record_calc(1.0, "derived", formula="a+b",
                         upstream=[parent])
        sources = {m: reg.get(m).source for m in reg.all_metrics()}
        self.assertEqual(sources["clean_claim_rate"], Source.USER_INPUT)
        self.assertEqual(sources["total_revenue"], Source.HCRIS)
        self.assertEqual(sources["total_expenses"], Source.IRS990)
        self.assertEqual(sources["denial_rate_median"],
                         Source.BENCHMARK_MEDIAN)
        self.assertEqual(sources["denial_rate"],
                         Source.REGRESSION_PREDICTED)
        self.assertEqual(sources["ebitda_impact"], Source.MONTE_CARLO_P50)
        self.assertEqual(sources["derived"], Source.CALCULATED)


class TestCalcConfidencePropagation(unittest.TestCase):
    def test_calc_inherits_min_confidence_when_unspecified(self):
        reg = ProvenanceRegistry()
        a = reg.record_user_input(1.0, "a")  # conf=1.0
        b = reg.record_regression(2.0, "b", upstream=[a],
                                  r_squared=0.6, n_samples=10)
        # b.confidence = 0.6
        c = reg.record_calc(3.0, "c", formula="a+b",
                             upstream=[a, b])
        self.assertAlmostEqual(c.confidence, 0.6, places=6)

    def test_calc_confidence_override_wins(self):
        reg = ProvenanceRegistry()
        a = reg.record_user_input(1.0, "a")
        c = reg.record_calc(2.0, "c", formula="2a",
                             upstream=[a], confidence=0.3)
        self.assertAlmostEqual(c.confidence, 0.3, places=6)

    def test_regression_clamps_negative_r_squared(self):
        reg = ProvenanceRegistry()
        dp = reg.record_regression(1.0, "x", upstream=[],
                                    r_squared=-0.4, n_samples=5)
        self.assertEqual(dp.confidence, 0.0)


# ────────────────────────────────────────────────────────────────────
# Trace / graph
# ────────────────────────────────────────────────────────────────────

class TestTrace(unittest.TestCase):
    def test_trace_returns_topological_order(self):
        reg = ProvenanceRegistry()
        # 3-level chain: ebitda ← revenue ← volume
        vol = reg.record_user_input(1000, "volume")
        rev = reg.record_calc(50_000_000, "revenue",
                               formula="volume * $50k",
                               upstream=[vol])
        eb = reg.record_calc(12_500_000, "ebitda",
                              formula="revenue * margin",
                              upstream=[rev])
        chain = reg.trace("ebitda")
        names = [d.metric_name for d in chain]
        self.assertEqual(names[-1], "ebitda")  # root is last
        self.assertEqual(names[0], "volume")  # leaves first
        self.assertEqual(set(names), {"volume", "revenue", "ebitda"})

    def test_trace_unknown_metric_empty(self):
        reg = ProvenanceRegistry()
        self.assertEqual(reg.trace("does_not_exist"), [])

    def test_trace_cycle_safe(self):
        # Artificially build a cycle by mutating upstream references.
        # DataPoints are frozen, but the list underlying .upstream is not —
        # we abuse that to force a cycle, then assert trace still terminates.
        reg = ProvenanceRegistry()
        a = reg.record_user_input(1.0, "a")
        b = reg.record_calc(2.0, "b", formula="a+1", upstream=[a])
        a.upstream.append(b)  # pylint: disable=no-member
        chain = reg.trace("a")
        names = {d.metric_name for d in chain}
        self.assertEqual(names, {"a", "b"})

    def test_dependency_graph_nodes_and_edges(self):
        reg = ProvenanceRegistry()
        a = reg.record_user_input(1.0, "a")
        b = reg.record_calc(2.0, "b", formula="a+1", upstream=[a])
        graph = reg.dependency_graph()
        node_names = {n["metric_name"] for n in graph["nodes"]}
        self.assertEqual(node_names, {"a", "b"})
        self.assertIn(["a", "b"], graph["edges"])
        # Round-trips through JSON
        json.dumps(graph)


# ────────────────────────────────────────────────────────────────────
# human_explain
# ────────────────────────────────────────────────────────────────────

class TestHumanExplain(unittest.TestCase):
    def test_unknown_metric_returns_friendly_fallback(self):
        reg = ProvenanceRegistry()
        text = reg.human_explain("does_not_exist")
        self.assertIn("No provenance recorded", text)
        self.assertIn("does_not_exist", text)

    def test_user_input_phrasing(self):
        reg = ProvenanceRegistry()
        reg.record_user_input(0.921, "clean_claim_rate")
        text = reg.human_explain("clean_claim_rate")
        self.assertIn("provided directly by the analyst", text)
        self.assertIn("92.1%", text)

    def test_regression_phrasing_mentions_r_squared_and_drivers(self):
        reg = ProvenanceRegistry()
        parent = reg.record_user_input(0.921, "clean_claim_rate")
        reg.record_regression(0.082, "denial_rate",
                              upstream=[parent],
                              r_squared=0.84, n_samples=47,
                              predictor_summary="clean claim rate")
        text = reg.human_explain("denial_rate")
        self.assertIn("regression", text.lower())
        self.assertIn("47 comparable hospitals", text)
        self.assertIn("r²=0.84", text.lower())
        self.assertIn("Clean claim rate", text)  # driver line
        self.assertIn("92.1%", text)             # parent formatted

    def test_hcris_phrasing_includes_year_and_ccn(self):
        reg = ProvenanceRegistry()
        reg.record_hcris(50_000_000, "total_revenue",
                         ccn="450321", fiscal_year=2022)
        text = reg.human_explain("total_revenue")
        self.assertIn("HCRIS", text)
        self.assertIn("2022", text)
        self.assertIn("450321", text)

    def test_calculated_phrasing_shows_formula_and_inputs(self):
        reg = ProvenanceRegistry()
        a = reg.record_user_input(1_000_000, "revenue")
        reg.record_calc(250_000, "ebitda",
                         formula="revenue * 0.25",
                         upstream=[a])
        text = reg.human_explain("ebitda")
        self.assertIn("revenue * 0.25", text)
        self.assertIn("Key drivers", text)
        self.assertIn("Revenue", text)

    def test_caps_drivers_at_six(self):
        reg = ProvenanceRegistry()
        parents = [
            reg.record_user_input(float(i), f"p{i}")
            for i in range(10)
        ]
        reg.record_calc(1.0, "agg", formula="sum(p0..p9)",
                         upstream=parents)
        text = reg.human_explain("agg")
        self.assertIn("plus 4 more inputs", text)


# ────────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────────

class TestPersistence(unittest.TestCase):
    def _store(self, tmp):
        return PortfolioStore(os.path.join(tmp, "p.db"))

    def test_save_requires_deal_and_run(self):
        reg = ProvenanceRegistry()
        reg.record_user_input(1.0, "x")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                reg.save(self._store(tmp))

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            reg = ProvenanceRegistry(deal_id="d1", run_id="r1")
            p = reg.record_user_input(0.9, "clean_claim_rate")
            reg.record_regression(0.08, "denial_rate",
                                   upstream=[p],
                                   r_squared=0.84, n_samples=47)
            reg.record_calc(50_000_000, "revenue",
                             formula="volume * psr",
                             upstream=[p])
            inserted = reg.save(store)
            self.assertEqual(inserted, 3)

            loaded = ProvenanceRegistry.load(store, deal_id="d1",
                                              run_id="r1")
            self.assertEqual(len(loaded), 3)
            dr = loaded.get("denial_rate")
            self.assertEqual(dr.source, Source.REGRESSION_PREDICTED)
            self.assertEqual(len(dr.upstream), 1)
            self.assertEqual(dr.upstream[0].metric_name,
                             "clean_claim_rate")

    def test_load_without_run_id_uses_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            r1 = ProvenanceRegistry(deal_id="d1", run_id="r1")
            r1.record_user_input(1.0, "old_metric")
            r1.save(store)
            # tiny sleep so autoincrement id ordering is deterministic
            time.sleep(0.01)
            r2 = ProvenanceRegistry(deal_id="d1", run_id="r2")
            r2.record_user_input(2.0, "new_metric")
            r2.save(store)
            loaded = ProvenanceRegistry.load(store, deal_id="d1")
            self.assertEqual(loaded.run_id, "r2")
            self.assertIn("new_metric", loaded)
            self.assertNotIn("old_metric", loaded)

    def test_load_unknown_deal_returns_empty_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            _ensure_provenance_table(store)
            loaded = ProvenanceRegistry.load(store, deal_id="ghost")
            self.assertEqual(len(loaded), 0)


# ────────────────────────────────────────────────────────────────────
# Simulator + pe_math opt-in wiring
# ────────────────────────────────────────────────────────────────────

class TestSimulatorWireIn(unittest.TestCase):
    def test_simulate_without_registry_still_works(self):
        """Back-compat: existing callers pass no registry and must still
        receive a DataFrame unharmed."""
        # Minimal smoke — we don't want a heavy sim here, just prove the
        # kwarg defaults to None and doesn't break callers.
        import inspect
        from rcm_mc.core.simulator import simulate
        sig = inspect.signature(simulate)
        self.assertIn("registry", sig.parameters)
        self.assertIsNone(sig.parameters["registry"].default)


class TestPeMathWireIn(unittest.TestCase):
    def test_value_creation_bridge_records_leaves_and_calcs(self):
        from rcm_mc.pe.pe_math import value_creation_bridge
        reg = ProvenanceRegistry()
        result = value_creation_bridge(
            entry_ebitda=50_000_000, uplift=5_000_000,
            entry_multiple=9.0, exit_multiple=10.0,
            hold_years=5.0, registry=reg,
        )
        self.assertIsNotNone(result)
        # Leaves + derived both recorded on the registry.
        self.assertIn("entry_ebitda", reg)
        self.assertIn("entry_multiple", reg)
        self.assertIn("exit_multiple", reg)
        self.assertIn("exit_ebitda", reg)
        self.assertIn("entry_ev", reg)
        # Pre-seeding an input as USER_INPUT is respected (not overwritten).
        reg2 = ProvenanceRegistry()
        reg2.record_user_input(50_000_000, "entry_ebitda")
        value_creation_bridge(entry_ebitda=50_000_000, uplift=5_000_000,
                               entry_multiple=9.0, exit_multiple=10.0,
                               hold_years=5.0, registry=reg2)
        self.assertEqual(reg2.get("entry_ebitda").source,
                         Source.USER_INPUT)

    def test_compute_returns_records_moic_and_irr(self):
        from rcm_mc.pe.pe_math import compute_returns
        reg = ProvenanceRegistry()
        compute_returns(entry_equity=100_000_000,
                         exit_proceeds=250_000_000,
                         hold_years=5.0, registry=reg)
        self.assertIn("moic", reg)
        self.assertIn("irr", reg)
        moic = reg.get("moic")
        self.assertEqual(moic.source, Source.CALCULATED)
        self.assertAlmostEqual(moic.value, 2.5, places=2)


# ────────────────────────────────────────────────────────────────────
# HTTP API
# ────────────────────────────────────────────────────────────────────

class TestProvenanceHttp(unittest.TestCase):
    def _start_server(self, tmp):
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                  db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); time.sleep(0.05)
        return server, port

    def _seed(self, tmp, deal_id="d1"):
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        store.upsert_deal(deal_id, name=deal_id.upper())
        reg = ProvenanceRegistry(deal_id=deal_id, run_id="r1")
        parent = reg.record_user_input(0.921, "clean_claim_rate")
        reg.record_regression(0.082, "denial_rate",
                               upstream=[parent],
                               r_squared=0.84, n_samples=47)
        reg.save(store)
        return store

    def test_full_graph_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)
            server, port = self._start_server(tmp)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/provenance"
                ) as r:
                    data = json.loads(r.read().decode())
                self.assertEqual(data["deal_id"], "d1")
                self.assertEqual(data["run_id"], "r1")
                node_names = {n["metric_name"]
                              for n in data["graph"]["nodes"]}
                self.assertEqual(node_names,
                                 {"clean_claim_rate", "denial_rate"})
                self.assertIn(["clean_claim_rate", "denial_rate"],
                              data["graph"]["edges"])
            finally:
                server.shutdown(); server.server_close()

    def test_single_metric_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)
            server, port = self._start_server(tmp)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/"
                    f"provenance/denial_rate"
                ) as r:
                    data = json.loads(r.read().decode())
                self.assertEqual(data["metric"], "denial_rate")
                self.assertEqual(data["datapoint"]["source"],
                                 "REGRESSION_PREDICTED")
                self.assertIn("regression", data["explain"].lower())
                trace_names = [t["metric_name"] for t in data["trace"]]
                self.assertIn("clean_claim_rate", trace_names)
                self.assertIn("denial_rate", trace_names)
            finally:
                server.shutdown(); server.server_close()

    def test_unknown_metric_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)
            server, port = self._start_server(tmp)
            try:
                try:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/d1/"
                        f"provenance/does_not_exist"
                    )
                    self.fail("expected 404")
                except urllib.error.HTTPError as exc:
                    self.assertEqual(exc.code, HTTPStatus.NOT_FOUND)
                    payload = json.loads(exc.read().decode())
                    self.assertEqual(payload["code"],
                                     "PROVENANCE_NOT_FOUND")
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
