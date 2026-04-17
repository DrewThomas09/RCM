"""Fuzz tests: partial / incomplete configs should either run cleanly or fail loudly.

A diligence analyst will often hand us a YAML missing optional sections. We must
either (a) fill defaults and run, or (b) raise a clear ValueError naming the
missing field. What must NEVER happen: a cryptic KeyError / TypeError from deep
inside the simulator.
"""
from __future__ import annotations

import copy
import os
import tempfile
import unittest
from typing import Any, Dict

import yaml

from rcm_mc.infra.config import load_and_validate, validate_config


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ACTUAL_PATH = os.path.join(BASE_DIR, "configs", "actual.yaml")
BENCH_PATH = os.path.join(BASE_DIR, "configs", "benchmark.yaml")


def _load_actual() -> Dict[str, Any]:
    with open(ACTUAL_PATH) as f:
        return yaml.safe_load(f)


def _roundtrip_through_validate(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + return (raises ValueError on invalid; no cryptic errors allowed)."""
    return validate_config(cfg)


class TestConfigPartialInputs(unittest.TestCase):
    """Optional fields should be omittable without crashing."""

    def test_missing_scrub_section_is_accepted(self):
        """`scrub` is optional; the simulator falls back to internal defaults."""
        cfg = _load_actual()
        cfg.pop("scrub", None)
        _roundtrip_through_validate(cfg)  # should not raise

    def test_missing_claim_distribution_is_accepted(self):
        """`claim_distribution` at the top level is optional."""
        cfg = _load_actual()
        cfg.pop("claim_distribution", None)
        for payer_cfg in cfg.get("payers", {}).values():
            payer_cfg.pop("claim_distribution", None)
        _roundtrip_through_validate(cfg)

    def test_missing_appeals_section_is_caught_clearly(self):
        """appeals is required — a missing appeals block must raise ValueError, not KeyError."""
        cfg = _load_actual()
        cfg.pop("appeals", None)
        with self.assertRaises((ValueError, KeyError)) as ctx:
            _roundtrip_through_validate(cfg)
        # Either way, the message should mention 'appeals'
        self.assertIn("appeal", str(ctx.exception).lower())

    def test_missing_payers_fails_loudly(self):
        """Dropping payers must produce a clear, actionable ValueError."""
        cfg = _load_actual()
        cfg.pop("payers", None)
        with self.assertRaises(ValueError) as ctx:
            _roundtrip_through_validate(cfg)
        self.assertIn("payer", str(ctx.exception).lower())

    def test_missing_hospital_section_fails_loudly(self):
        cfg = _load_actual()
        cfg.pop("hospital", None)
        with self.assertRaises(ValueError):
            _roundtrip_through_validate(cfg)

    def test_payer_without_denials_block_accepted_when_include_denials_false(self):
        """Payers with include_denials: false should not require a denials block."""
        cfg = _load_actual()
        # Find or create a payer that opts out of denials
        for name, p in cfg.get("payers", {}).items():
            p["include_denials"] = False
            p.pop("denials", None)
            break
        _roundtrip_through_validate(cfg)

    def test_unknown_top_level_key_is_tolerated(self):
        """Extra keys (e.g., future fields or analyst notes) should not crash validation."""
        cfg = _load_actual()
        cfg["_analyst_notes"] = "this is a new comment field"
        cfg["future_extension"] = {"something": "here"}
        _roundtrip_through_validate(cfg)

    def test_roundtrip_then_cli_end_to_end_still_works(self):
        """Strip `scrub` and a payer's denial_types bias, then run the CLI via -m."""
        import subprocess
        import sys

        cfg = _load_actual()
        cfg.pop("scrub", None)
        # Strip optional per-payer extras that diligence extracts usually won't have
        for p in cfg.get("payers", {}).values():
            den = p.get("denials") or {}
            den.pop("denial_mix_concentration", None)
            types = den.get("denial_types") or {}
            for t in types.values():
                if isinstance(t, dict):
                    t.pop("stage_bias", None)
                    t.pop("fwr_odds_mult", None)

        with tempfile.TemporaryDirectory() as tmp:
            stripped_path = os.path.join(tmp, "actual_stripped.yaml")
            with open(stripped_path, "w") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)

            outdir = os.path.join(tmp, "out")
            env = os.environ.copy()
            env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
            result = subprocess.run(
                [
                    sys.executable, "-m", "rcm_mc.cli",
                    "--actual", stripped_path,
                    "--benchmark", BENCH_PATH,
                    "--outdir", outdir,
                    "--n-sims", "200",
                    "--no-report",
                    "--seed", "42",
                ],
                cwd=BASE_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=f"CLI failed on stripped config:\nSTDOUT:\n{result.stdout[-800:]}\nSTDERR:\n{result.stderr[-800:]}",
            )
            self.assertTrue(os.path.exists(os.path.join(outdir, "summary.csv")))


class TestLoadAndValidate(unittest.TestCase):
    """Full load+validate pipeline against the shipped configs."""

    def test_stock_actual_loads_cleanly(self):
        load_and_validate(ACTUAL_PATH)

    def test_stock_benchmark_loads_cleanly(self):
        load_and_validate(BENCH_PATH)
