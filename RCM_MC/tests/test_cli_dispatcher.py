"""Tests for the top-level ``rcm-mc`` subcommand dispatcher.

Covers: subcommand routing (run/intake/lookup/hcris), top-level help,
unknown-subcommand error path, and back-compat with the legacy flat form
(``rcm-mc --actual X --benchmark Y`` with no explicit subcommand).
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
ACTUAL = str(BASE_DIR / "configs" / "actual.yaml")
BENCH = str(BASE_DIR / "configs" / "benchmark.yaml")


def _run_module(args, timeout=60, cwd=BASE_DIR):
    """Run `python -m rcm_mc ...` and return CompletedProcess."""
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
    return subprocess.run(
        [sys.executable, "-m", "rcm_mc"] + list(args),
        cwd=str(cwd), env=env,
        capture_output=True, text=True, timeout=timeout,
    )


class TestTopLevelHelp(unittest.TestCase):
    def test_no_args_prints_help_and_exits_zero(self):
        result = _run_module([])
        self.assertEqual(result.returncode, 0)
        self.assertIn("RCM Monte Carlo", result.stdout)
        self.assertIn("Commands:", result.stdout)
        for cmd in ("run", "intake", "lookup", "hcris"):
            self.assertIn(cmd, result.stdout, msg=f"{cmd} missing from help")

    def test_help_flag_prints_same_help(self):
        r1 = _run_module([])
        r2 = _run_module(["--help"])
        r3 = _run_module(["-h"])
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r3.returncode, 0)
        # Help is identical across entry points
        self.assertEqual(r1.stdout, r2.stdout)
        self.assertEqual(r1.stdout, r3.stdout)

    def test_unknown_subcommand_returns_2(self):
        result = _run_module(["totally-not-a-real-command"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown command", result.stderr)


class TestSubcommandDispatch(unittest.TestCase):
    def test_lookup_subcommand_routes(self):
        result = _run_module(["lookup", "--ccn", "360180"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("CLEVELAND CLINIC", result.stdout)

    def test_lookup_subcommand_help_shows_correct_prog(self):
        result = _run_module(["lookup", "--help"])
        self.assertEqual(result.returncode, 0)
        # With prog= parameterization, help should read `rcm-mc lookup` not `rcm-lookup`
        self.assertIn("rcm-mc lookup", result.stdout)

    def test_hcris_subcommand_routes(self):
        # The `hcris` subcommand has its own subcommand ("refresh").
        # `rcm-mc hcris` with no arg should show its help (argparse default).
        result = _run_module(["hcris", "--help"])
        self.assertEqual(result.returncode, 0)
        # prog parameterization: help shows `rcm-mc hcris`
        self.assertIn("rcm-mc hcris", result.stdout)

    def test_run_subcommand_produces_outputs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_module(
                ["run", "--actual", ACTUAL, "--benchmark", BENCH,
                 "--outdir", tmp, "--n-sims", "150", "--no-report", "--seed", "42"],
                timeout=120,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=f"STDOUT:{result.stdout[-800:]}\nSTDERR:{result.stderr[-800:]}",
            )
            self.assertTrue(os.path.exists(os.path.join(tmp, "summary.csv")))

    def test_intake_subcommand_refuses_non_tty(self):
        # intake requires an interactive terminal; piped stdin should error gracefully
        result = _run_module(["intake", "--out", "/tmp/rcm_dispatch_test.yaml"])
        # Exit code 2 with guidance on stderr
        self.assertEqual(result.returncode, 2)
        self.assertIn("interactive terminal", result.stderr)


class TestBackCompatFlatForm(unittest.TestCase):
    """Legacy ``rcm-mc --actual X --benchmark Y`` (no explicit subcommand) routes to run."""

    def test_flat_form_still_works(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_module(
                ["--actual", ACTUAL, "--benchmark", BENCH,
                 "--outdir", tmp, "--n-sims", "150", "--no-report", "--seed", "42"],
                timeout=120,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=f"STDOUT:{result.stdout[-800:]}\nSTDERR:{result.stderr[-800:]}",
            )
            self.assertTrue(os.path.exists(os.path.join(tmp, "summary.csv")))

    def test_flat_form_and_run_subcommand_produce_same_outputs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            flat = _run_module(
                ["--actual", ACTUAL, "--benchmark", BENCH,
                 "--outdir", tmp1, "--n-sims", "150", "--no-report", "--seed", "42"],
                timeout=120,
            )
            sub = _run_module(
                ["run", "--actual", ACTUAL, "--benchmark", BENCH,
                 "--outdir", tmp2, "--n-sims", "150", "--no-report", "--seed", "42"],
                timeout=120,
            )
            self.assertEqual(flat.returncode, 0)
            self.assertEqual(sub.returncode, 0)
            # Same seed → identical summary rows
            with open(os.path.join(tmp1, "summary.csv")) as f:
                s1 = f.read()
            with open(os.path.join(tmp2, "summary.csv")) as f:
                s2 = f.read()
            self.assertEqual(s1, s2)


class TestLegacyEntryPointsStillWork(unittest.TestCase):
    """rcm-intake and rcm-lookup remain functional as aliases (one-release deprecation window)."""

    @staticmethod
    def _run_module_direct(module, args, timeout=30):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        return subprocess.run(
            [sys.executable, "-m", module] + list(args),
            cwd=str(BASE_DIR), env=env,
            capture_output=True, text=True, timeout=timeout,
        )

    def test_rcm_mc_lookup_module_still_works(self):
        result = self._run_module_direct("rcm_mc.lookup", ["--ccn", "360180"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("CLEVELAND CLINIC", result.stdout)

    def test_rcm_mc_cli_module_still_works(self):
        result = self._run_module_direct("rcm_mc.cli", ["--help"])
        self.assertEqual(result.returncode, 0)
        # `python -m rcm_mc.cli --help` goes through the dispatcher, not the flat ap,
        # because __name__ == "__main__" calls main() which is the dispatcher.
        self.assertIn("Commands:", result.stdout)
