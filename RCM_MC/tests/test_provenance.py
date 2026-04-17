"""Tests for provenance.json and optional simulation trace export."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.infra.config import load_and_validate
from rcm_mc.infra.provenance import METRIC_REGISTRY, build_provenance_document, write_provenance_json
from rcm_mc.infra.trace import export_iteration_trace


def test_metric_registry_covers_summary_metrics():
    expected = [
        "ebitda_drag",
        "economic_drag",
        "drag_denial_writeoff",
        "drag_underpay_leakage",
        "drag_denial_rework_cost",
        "drag_underpay_cost",
        "drag_dar_total",
        "actual_rcm_ebitda_impact",
        "bench_rcm_ebitda_impact",
    ]
    for m in expected:
        assert m in METRIC_REGISTRY, f"missing registry entry for {m}"


def test_write_provenance_json_roundtrip():
    rows = []
    for m in ["ebitda_drag", "drag_denial_writeoff"]:
        rows.append(
            {
                "metric": m,
                "mean": 1.0e6,
                "median": 0.9e6,
                "p10": 0.5e6,
                "p90": 1.5e6,
                "p95": 1.7e6,
            }
        )
    df = pd.DataFrame(rows).set_index("metric")
    with tempfile.TemporaryDirectory() as td:
        path = write_provenance_json(
            td,
            df,
            n_sims=100,
            seed=42,
            align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        assert os.path.isfile(path)
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        assert doc["schema"] == "rcm_mc.provenance/v1"
        assert doc["run"]["n_sims"] == 100
        assert doc["run"]["seed"] == 42
        assert len(doc["metrics"]) == 2
        names = {x["metric"] for x in doc["metrics"]}
        assert names == {"ebitda_drag", "drag_denial_writeoff"}


def test_build_provenance_document_has_formulas():
    df = pd.DataFrame(
        [{"metric": "ebitda_drag", "mean": 1.0, "median": 1.0, "p10": 0.5, "p90": 1.5, "p95": 1.6}]
    ).set_index("metric")
    doc = build_provenance_document(
        summary_df=df,
        outdir="/tmp",
        n_sims=10,
        seed=1,
        align_profile=True,
        actual_config_path="a.yaml",
        benchmark_config_path="b.yaml",
    )
    m0 = doc["metrics"][0]
    assert m0["metric"] == "ebitda_drag"
    assert "formula" in m0
    assert m0["formula_id"]


def test_export_iteration_trace_iteration_zero():
    root = os.path.dirname(os.path.dirname(__file__))
    actual = os.path.join(root, "configs", "actual.yaml")
    bench = os.path.join(root, "configs", "benchmark.yaml")
    if not os.path.isfile(actual) or not os.path.isfile(bench):
        raise unittest.SkipTest("configs/actual.yaml or benchmark.yaml not found")
    a = load_and_validate(actual)
    b = load_and_validate(bench)
    doc = export_iteration_trace(a, b, iteration=0, seed=123, align_profile=True)
    assert doc["schema"] == "rcm_mc.trace/v1"
    assert doc["iteration"] == 0
    assert "actual" in doc and "benchmark" in doc
    assert doc["ebitda_drag"] == doc["drag_totals"].get("rcm_ebitda_impact")
    assert len(doc["actual"]["payers"]) >= 1
