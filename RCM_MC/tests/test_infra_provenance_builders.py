"""Tests for provenance manifest + metrics-provenance builders.

`rcm_mc/infra/provenance.py` writes the JSON document that ships
alongside every simulation run for audit trail. Two public
builders had no direct test coverage:

  - build_run_manifest — top-level run metadata: timestamp, n_sims,
    seed, file SHAs, git revision, doc-link pointers
  - build_metrics_provenance — per-metric joined registry entries
    (formula, source_columns, code pointer, config_keys, caveats)

build_provenance_document + write_provenance_json wrap these but
delegate the contracted work to these two; testing the leaves
locks the schema the downstream auditor depends on.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.infra.provenance import (
    METRIC_REGISTRY,
    build_metrics_provenance,
    build_run_manifest,
)


class BuildRunManifestTests(unittest.TestCase):
    """Schema + behavior contract for ``build_run_manifest``."""

    def test_returns_dict_with_required_keys(self):
        out = build_run_manifest(
            outdir="/tmp/run",
            n_sims=1000,
            seed=42,
            align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        for k in ("generated_at_utc", "outdir", "n_sims", "seed",
                  "align_profile", "scrub_applied", "git_revision",
                  "inputs", "documentation"):
            self.assertIn(k, out, f"missing manifest key {k!r}")

    def test_coerces_numeric_inputs(self):
        # All numerics MUST be plain ints/bools for JSON safety.
        out = build_run_manifest(
            outdir="/tmp/run",
            n_sims="500",  # str → int
            seed="123",
            align_profile=1,   # truthy → bool
            actual_config_path=None,
            benchmark_config_path=None,
        )
        self.assertEqual(out["n_sims"], 500)
        self.assertIsInstance(out["n_sims"], int)
        self.assertEqual(out["seed"], 123)
        self.assertIs(out["align_profile"], True)
        self.assertIsInstance(out["align_profile"], bool)

    def test_outdir_absolutized(self):
        out = build_run_manifest(
            outdir="some/relative/path",
            n_sims=1, seed=1, align_profile=False,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        self.assertTrue(os.path.isabs(out["outdir"]))

    def test_scrub_applied_default_true(self):
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        self.assertTrue(out["scrub_applied"])

    def test_scrub_applied_can_be_disabled(self):
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
            scrub_applied=False,
        )
        self.assertFalse(out["scrub_applied"])

    def test_config_paths_recorded_when_provided(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml",
                                          delete=False) as a:
            a.write("k: v\n")
            apath = a.name
        try:
            out = build_run_manifest(
                outdir="/tmp", n_sims=1, seed=1, align_profile=True,
                actual_config_path=apath,
                benchmark_config_path=None,
            )
            self.assertEqual(out["inputs"]["actual_config_path"],
                              apath)
            # SHA computed from real file content
            self.assertIsNotNone(
                out["inputs"]["actual_config_sha256"])
            self.assertEqual(
                len(out["inputs"]["actual_config_sha256"]), 64)
            # Benchmark path None → SHA also None
            self.assertIsNone(out["inputs"]["benchmark_config_path"])
            self.assertIsNone(
                out["inputs"]["benchmark_config_sha256"])
        finally:
            os.unlink(apath)

    def test_missing_config_paths_handled(self):
        # Both paths None → SHAs both None, no crash.
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        self.assertIsNone(out["inputs"]["actual_config_path"])
        self.assertIsNone(out["inputs"]["actual_config_sha256"])

    def test_documentation_pointers_present(self):
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        self.assertEqual(
            out["documentation"]["metric_dictionary"],
            "docs/METRIC_PROVENANCE.md")
        self.assertEqual(
            out["documentation"]["improvement_guide"],
            "docs/MODEL_IMPROVEMENT.md")

    def test_timestamp_is_utc_iso(self):
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        # Format: YYYY-MM-DDTHH:MM:SSZ
        ts = out["generated_at_utc"]
        self.assertTrue(ts.endswith("Z"))
        # Should be parseable as ISO
        from datetime import datetime
        # Strip the Z and verify it's a valid timestamp
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_output_is_json_safe(self):
        # All values round-trip through json.dumps (no numpy types,
        # no datetimes, no Paths leaking).
        out = build_run_manifest(
            outdir="/tmp", n_sims=1, seed=1, align_profile=True,
            actual_config_path=None,
            benchmark_config_path=None,
        )
        s = json.dumps(out)
        loaded = json.loads(s)
        self.assertEqual(loaded["n_sims"], 1)


class BuildMetricsProvenanceTests(unittest.TestCase):
    """Schema + behavior contract for ``build_metrics_provenance``."""

    @staticmethod
    def _summary(metrics):
        # Build a summary_df with the columns the function reads.
        return pd.DataFrame(
            {"mean": [1.0] * len(metrics),
             "median": [1.0] * len(metrics),
             "p10": [0.5] * len(metrics),
             "p90": [1.5] * len(metrics),
             "p95": [1.7] * len(metrics)},
            index=metrics,
        )

    def test_returns_list_of_dicts(self):
        df = self._summary(["ebitda_drag", "economic_drag"])
        out = build_metrics_provenance(df)
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 2)
        for row in out:
            self.assertIsInstance(row, dict)

    def test_known_metric_carries_registry_fields(self):
        df = self._summary(["ebitda_drag"])
        out = build_metrics_provenance(df)
        row = out[0]
        # METRIC_REGISTRY['ebitda_drag'] populated
        self.assertEqual(row["metric"], "ebitda_drag")
        self.assertEqual(row["formula_id"], "drag_rcm_minus_agg")
        self.assertIn("ebitda_drag", row["source_columns"])
        self.assertIn("rcm_mc.breakdowns", row["code"]["module"])
        self.assertGreater(len(row["caveats"]), 0)

    def test_unknown_metric_falls_back_to_defaults(self):
        # A metric not in METRIC_REGISTRY gets sentinel values
        # instead of missing keys / KeyError.
        df = self._summary(["zzz_made_up_metric"])
        out = build_metrics_provenance(df)
        row = out[0]
        self.assertEqual(row["metric"], "zzz_made_up_metric")
        self.assertEqual(row["formula_id"], "custom_or_unknown")
        # source_columns defaults to [metric_name]
        self.assertEqual(row["source_columns"], ["zzz_made_up_metric"])
        self.assertEqual(row["caveats"], [])
        # code defaults to {} so JSON-safe
        self.assertEqual(row["code"], {})

    def test_aggregations_extracted_per_metric(self):
        df = self._summary(["ebitda_drag"])
        # Override with specific values to verify pass-through.
        df.loc["ebitda_drag", "mean"] = 1_000_000.0
        df.loc["ebitda_drag", "p90"] = 5_000_000.0
        out = build_metrics_provenance(df)
        agg = out[0]["aggregations"]
        self.assertEqual(agg["mean"], 1_000_000.0)
        self.assertEqual(agg["p90"], 5_000_000.0)
        # Schema: 5 keys present
        self.assertEqual(
            set(agg.keys()), {"mean", "median", "p10", "p90", "p95"})

    def test_nan_aggregations_become_none(self):
        # pd.notna(NaN) → False → value emitted as None (JSON-safe).
        import numpy as np
        df = self._summary(["ebitda_drag"])
        df.loc["ebitda_drag", "mean"] = np.nan
        out = build_metrics_provenance(df)
        self.assertIsNone(out[0]["aggregations"]["mean"])

    def test_empty_dataframe_returns_empty_list(self):
        df = pd.DataFrame(
            {"mean": [], "median": [], "p10": [], "p90": [], "p95": []},
        )
        out = build_metrics_provenance(df)
        self.assertEqual(out, [])

    def test_output_is_json_safe(self):
        df = self._summary(["ebitda_drag", "economic_drag"])
        out = build_metrics_provenance(df)
        s = json.dumps(out)
        loaded = json.loads(s)
        self.assertEqual(len(loaded), 2)

    def test_known_metrics_all_resolve_to_registry(self):
        # Every metric named in METRIC_REGISTRY round-trips through
        # the builder without falling back to 'custom_or_unknown'.
        names = list(METRIC_REGISTRY.keys())
        df = self._summary(names)
        out = build_metrics_provenance(df)
        for row in out:
            self.assertNotEqual(
                row["formula_id"], "custom_or_unknown",
                f"{row['metric']!r} hit the fallback path "
                "despite being in METRIC_REGISTRY")


if __name__ == "__main__":
    unittest.main()
