"""Tests for ``rcm-mc deal new`` — the pipeline orchestrator.

Most of the logic delegates to existing subcommand entry points, so the
tests focus on:

- Deal directory / deal.yaml bookkeeping
- Step skipping and failure recovery
- End-to-end with pre-existing actual.yaml (skip-intake path, no TTY needed)
- End-to-end with a data source (ingest wired in)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
ACTUAL_PATH = str(BASE_DIR / "configs" / "actual.yaml")


def _claims_df() -> pd.DataFrame:
    return pd.DataFrame({
        "payer":       ["Medicare", "Medicaid", "Commercial", "SelfPay"],
        "net_revenue": [1.5e8, 8e7, 2.2e8, 2e7],
        "claim_count": [15000, 9000, 22000, 3000],
    })


def _denials_df() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_id":       ["A1", "A2", "A3"],
        "payer":          ["Medicare", "Commercial", "Medicaid"],
        "denial_amount":  [1500, 3200, 900],
        "stage":          ["L1", "L2", "L1"],
        "writeoff_amount": [500, 0, 900],
    })


def _ar_df() -> pd.DataFrame:
    return pd.DataFrame({"payer": ["Medicare", "Medicaid"], "ar_amount": [1.2e7, 6e6]})


class TestCreateDealSkipIntake(unittest.TestCase):
    """Non-TTY path: provide an existing actual.yaml, skip the wizard."""

    def test_skip_intake_requires_actual(self):
        from rcm_mc.deals.deal import main as deal_main
        with tempfile.TemporaryDirectory() as tmp:
            # --skip-intake without --actual → error
            rc = deal_main(["new", "--dir", tmp, "--skip-intake"])
            self.assertEqual(rc, 2)

    def test_end_to_end_with_existing_actual_and_skip_run(self):
        from rcm_mc.deals.deal import create_deal
        with tempfile.TemporaryDirectory() as tmp:
            state = create_deal(
                tmp,
                actual_path=ACTUAL_PATH,
                skip_intake=True,
                skip_run=True,      # skip the heavy simulation
            )
            self.assertEqual(state["deal"]["status"], "complete")
            self.assertEqual(state["files"]["actual_config"], ACTUAL_PATH)
            # deal.yaml is on disk and parseable
            deal_yaml = Path(tmp) / "deal.yaml"
            self.assertTrue(deal_yaml.exists())
            with open(deal_yaml) as f:
                reloaded = yaml.safe_load(f)
            self.assertEqual(reloaded["deal"]["status"], "complete")
            # Name should be pulled from the actual.yaml
            self.assertIn("hospital", reloaded["deal"]["name"].lower()) if reloaded["deal"]["name"] else None

    def test_full_run_with_existing_actual(self):
        """Skip intake, skip ingest, RUN the simulation — verifies orchestration."""
        from rcm_mc.deals.deal import create_deal
        with tempfile.TemporaryDirectory() as tmp:
            state = create_deal(
                tmp,
                actual_path=ACTUAL_PATH,
                skip_intake=True,
                skip_ingest=True,
                skip_run=False,
                partner_brief=False,   # saves a bit of time
                n_sims=200,
            )
            self.assertEqual(state["deal"]["status"], "complete")
            outputs_dir = Path(tmp) / "outputs"
            self.assertTrue(outputs_dir.exists())
            self.assertTrue((outputs_dir / "summary.csv").exists())
            self.assertTrue((outputs_dir / "provenance.json").exists())

    def test_ingest_integration(self):
        """With --data-source, ingest fills intake_data/ and calibration kicks in."""
        from rcm_mc.deals.deal import create_deal
        with tempfile.TemporaryDirectory() as deal_dir, tempfile.TemporaryDirectory() as src:
            _claims_df().to_csv(Path(src) / "claims.csv", index=False)
            _denials_df().to_csv(Path(src) / "denials.csv", index=False)
            _ar_df().to_csv(Path(src) / "aging.csv", index=False)

            state = create_deal(
                deal_dir,
                actual_path=ACTUAL_PATH,
                data_source=src,
                skip_intake=True,
                partner_brief=False,
                n_sims=200,
            )
            self.assertEqual(state["deal"]["status"], "complete")
            # intake_data/ populated with canonical files
            intake_data = Path(deal_dir) / "intake_data"
            self.assertTrue(intake_data.exists())
            for kind in ("claims_summary", "denials", "ar_aging"):
                self.assertTrue((intake_data / f"{kind}.csv").exists())
            # One of the steps should be ingest with status=ok
            ingest_steps = [s for s in state["steps"] if s.get("step") == "ingest"]
            self.assertTrue(ingest_steps)
            self.assertEqual(ingest_steps[0].get("status"), "ok")
            # Calibration artifacts should appear in outputs (proof calibration ran)
            outputs_dir = Path(deal_dir) / "outputs"
            self.assertTrue(
                any(f.startswith("data_quality_report") or f.startswith("calibrated")
                    for f in os.listdir(outputs_dir / "_detail")),
                msg=f"Expected calibration artifacts in _detail/; got {os.listdir(outputs_dir / '_detail')}",
            )

    def test_ingest_with_no_signature_match_continues_uncalibrated(self):
        """Data source that produces 0 classified tables → run continues, step marked no_data."""
        from rcm_mc.deals.deal import create_deal
        with tempfile.TemporaryDirectory() as deal_dir, tempfile.TemporaryDirectory() as src:
            pd.DataFrame({"foo": [1, 2], "bar": [3, 4]}).to_csv(
                Path(src) / "mystery.csv", index=False,
            )
            state = create_deal(
                deal_dir,
                actual_path=ACTUAL_PATH,
                data_source=src,
                skip_intake=True,
                partner_brief=False,
                n_sims=200,
            )
            # Deal still completes; ingest step marked no_data, not failed
            self.assertEqual(state["deal"]["status"], "complete")
            ingest_steps = [s for s in state["steps"] if s.get("step") == "ingest"]
            self.assertEqual(ingest_steps[0].get("status"), "no_data")


class TestDealYamlFailurePath(unittest.TestCase):
    """deal.yaml should always get written, even on failure."""

    def test_bad_actual_yaml_still_writes_deal_yaml(self):
        from rcm_mc.deals.deal import create_deal
        with tempfile.TemporaryDirectory() as deal_dir, tempfile.TemporaryDirectory() as bad_dir:
            bad_yaml = Path(bad_dir) / "invalid.yaml"
            bad_yaml.write_text("this: is: not: valid")  # malformed YAML
            with self.assertRaises(Exception):
                create_deal(
                    deal_dir,
                    actual_path=str(bad_yaml),
                    skip_intake=True,
                    partner_brief=False,
                    n_sims=200,
                )
            # Even on failure, deal.yaml exists and records the failure
            deal_file = Path(deal_dir) / "deal.yaml"
            self.assertTrue(deal_file.exists())
            with open(deal_file) as f:
                state = yaml.safe_load(f)
            self.assertIn("failed", state["deal"]["status"])


class TestDealCLI(unittest.TestCase):
    """Subprocess end-to-end tests via `python -m rcm_mc deal ...`."""

    def _run(self, args, timeout=240):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        return subprocess.run(
            [sys.executable, "-m", "rcm_mc", "deal"] + args,
            cwd=str(BASE_DIR), env=env,
            capture_output=True, text=True, timeout=timeout,
        )

    def test_help_exits_zero(self):
        # Note: deal has a sub-subparser, so top-level --help alone won't do it.
        # `rcm-mc deal new --help` is the per-step help.
        result = self._run(["new", "--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rcm-mc deal", result.stdout)

    def test_missing_action_returns_2(self):
        result = self._run([])
        self.assertEqual(result.returncode, 2)

    def test_end_to_end_skip_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run([
                "new", "--dir", tmp,
                "--actual", ACTUAL_PATH,
                "--skip-intake",
                "--n-sims", "200",
                "--no-partner-brief",
            ], timeout=240)
            self.assertEqual(
                result.returncode, 0,
                msg=f"STDOUT:{result.stdout[-800:]}\nSTDERR:{result.stderr[-800:]}",
            )
            self.assertTrue((Path(tmp) / "deal.yaml").exists())
            self.assertTrue((Path(tmp) / "outputs" / "summary.csv").exists())
