"""Tests for the JSON summary + CSV column-docs writers.

`rcm_mc/infra/output_formats.py` ships two writers that emit
JSON artifacts alongside every simulation:

  - write_summary_json — turns summary_df into a v1-schema JSON
    document the downstream auditor reads
  - write_column_docs — emits the static column dictionary so
    every simulations.csv ships with its column meanings

Both had no direct test coverage. These tests use tempdirs +
synthetic summary DataFrames to lock the schema (filename, top-
level keys, NaN→None semantics, value coercion to float).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.infra.output_formats import (
    write_column_docs,
    write_summary_json,
)


class WriteSummaryJsonTests(unittest.TestCase):

    @staticmethod
    def _summary(data):
        return pd.DataFrame(data).T  # rows = metric × cols = stat

    def test_writes_to_summary_json_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({
                "ebitda_drag": {"mean": 1e6, "p10": 5e5, "p90": 2e6},
            })
            path = write_summary_json(df, tmp)
            self.assertEqual(os.path.basename(path), "summary.json")
            self.assertTrue(os.path.isfile(path))

    def test_emits_v1_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({
                "x": {"mean": 1.0, "p10": 0.5, "p90": 1.5},
            })
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(doc["schema"], "rcm_mc.summary/v1")

    def test_carries_n_sims_and_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({"x": {"mean": 1.0, "p10": 0,
                                       "p90": 2}})
            path = write_summary_json(df, tmp, n_sims=2000, seed=42)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(doc["n_sims"], 2000)
            self.assertEqual(doc["seed"], 42)

    def test_config_hashes_default_to_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({"x": {"mean": 1, "p10": 0, "p90": 2}})
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(doc["config_hashes"], {})

    def test_config_hashes_passed_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({"x": {"mean": 1, "p10": 0, "p90": 2}})
            hashes = {"actual": "abc123", "benchmark": "def456"}
            path = write_summary_json(df, tmp, config_hashes=hashes)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(doc["config_hashes"], hashes)

    def test_metrics_keyed_by_metric_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({
                "ebitda_drag": {"mean": 1.0, "p10": 0.5, "p90": 1.5},
                "economic_drag": {"mean": 2.0, "p10": 1.0, "p90": 3.0},
            })
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(
                set(doc["metrics"].keys()),
                {"ebitda_drag", "economic_drag"})

    def test_stats_coerced_to_float(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Use numpy types that aren't json-native.
            df = self._summary({
                "x": {"mean": np.int64(5), "p10": np.float32(0.5),
                       "p90": np.float64(1.5)},
            })
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            # All emitted as plain Python floats (JSON-safe)
            self.assertEqual(doc["metrics"]["x"]["mean"], 5.0)
            self.assertIsInstance(doc["metrics"]["x"]["mean"], float)

    def test_nan_stats_become_null(self):
        # NaN can't ship as JSON (allow_nan=False); the function
        # converts NaN → None before serialization.
        with tempfile.TemporaryDirectory() as tmp:
            df = self._summary({
                "x": {"mean": np.nan, "p10": 0.5, "p90": 1.5},
            })
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            self.assertIsNone(doc["metrics"]["x"]["mean"])
            self.assertEqual(doc["metrics"]["x"]["p10"], 0.5)

    def test_empty_summary_writes_empty_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = pd.DataFrame({"mean": [], "p10": [], "p90": []})
            path = write_summary_json(df, tmp)
            with open(path) as f:
                doc = json.load(f)
            self.assertEqual(doc["metrics"], {})


class WriteColumnDocsTests(unittest.TestCase):

    def test_writes_to_default_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_column_docs(tmp)
            self.assertEqual(os.path.basename(path),
                              "simulations_columns.json")
            self.assertTrue(os.path.isfile(path))

    def test_writes_to_custom_csv_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_column_docs(tmp, csv_name="actuals")
            self.assertEqual(os.path.basename(path),
                              "actuals_columns.json")

    def test_emits_documented_columns(self):
        # The dict written must contain documentation for the
        # standard simulator output columns. Catching a column
        # being dropped from _COLUMN_DOCS would silently strip
        # the explanation users see.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_column_docs(tmp)
            with open(path) as f:
                docs = json.load(f)
        expected = {
            "sim", "ebitda_drag", "economic_drag",
            "drag_denial_writeoff", "drag_underpay_leakage",
            "drag_denial_rework_cost", "drag_underpay_cost",
            "drag_dar_total",
            "actual_rcm_ebitda_impact",
            "bench_rcm_ebitda_impact",
        }
        self.assertTrue(
            expected.issubset(set(docs.keys())),
            f"missing columns: {expected - set(docs.keys())}")

    def test_each_column_has_description_and_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_column_docs(tmp)
            with open(path) as f:
                docs = json.load(f)
        for col, meta in docs.items():
            self.assertIn("description", meta,
                           f"{col!r} missing description")
            self.assertIn("unit", meta, f"{col!r} missing unit")
            self.assertTrue(meta["description"].strip())
            self.assertTrue(meta["unit"].strip())

    def test_output_is_json_safe(self):
        # write_column_docs writes a static dict — round-trip
        # without loss.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_column_docs(tmp)
            with open(path) as f:
                raw = f.read()
            # Round-trip without error
            json.loads(raw)


if __name__ == "__main__":
    unittest.main()
