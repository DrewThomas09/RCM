"""End-to-end CLI regression tests.

Exercises each major CLI flag at low n_sims via subprocess to catch whole-pipeline
breakage. Tests are focused on the flags a diligence analyst would actually use;
each run is small (n_sims=200) to keep the suite fast.

A failure here almost always means a downstream output, import, or argument-parsing
regression rather than a numerical bug.
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
N_SIMS = "200"


def _run(args: list, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run the CLI. Returns the CompletedProcess (stdout/stderr captured)."""
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
    cmd = [sys.executable, "-m", "rcm_mc.cli"] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestCLIRegression(unittest.TestCase):
    """One subprocess test per CLI flag path; tmp output dirs."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.outdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _base_args(self, outdir: Path = None) -> list:
        out = str(outdir or self.outdir)
        return [
            "--actual", ACTUAL,
            "--benchmark", BENCH,
            "--outdir", out,
            "--n-sims", N_SIMS,
            "--seed", "42",
        ]

    def _assert_clean(self, result: subprocess.CompletedProcess):
        self.assertEqual(
            result.returncode, 0,
            msg=f"CLI exited {result.returncode}\nSTDOUT:\n{result.stdout[-1500:]}\nSTDERR:\n{result.stderr[-1500:]}",
        )

    def test_base_run_writes_core_artifacts(self):
        result = _run(self._base_args() + ["--no-report"], cwd=BASE_DIR)
        self._assert_clean(result)
        for name in ("summary.csv", "simulations.csv", "provenance.json"):
            self.assertTrue((self.outdir / name).exists(), f"missing {name}")

    def test_report_html_generates(self):
        result = _run(self._base_args(), cwd=BASE_DIR)
        self._assert_clean(result)
        self.assertTrue((self.outdir / "report.html").exists())

    def test_screen_mode(self):
        result = _run(
            ["--actual", ACTUAL, "--benchmark", BENCH, "--outdir", str(self.outdir), "--screen"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)

    def test_validate_only(self):
        result = _run(
            ["--actual", ACTUAL, "--benchmark", BENCH, "--validate-only"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)

    def test_explain_config(self):
        result = _run(
            ["--actual", ACTUAL, "--benchmark", BENCH, "--explain-config"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)

    def test_attribution_oat(self):
        result = _run(
            self._base_args() + ["--no-report", "--attribution", "--attr-sims", "150"],
            cwd=BASE_DIR,
            timeout=240,
        )
        self._assert_clean(result)
        # Bundle sweeps attribution artifacts into _detail/
        self.assertTrue((self.outdir / "_detail" / "attribution_oat.csv").exists())
        self.assertTrue((self.outdir / "_detail" / "attribution_tornado.png").exists())

    def test_stress_tests(self):
        result = _run(
            self._base_args() + ["--no-report", "--stress", "--stress-sims", "150"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)
        self.assertTrue((self.outdir / "_detail" / "stress_tests.csv").exists())

    def test_initiatives_and_plan(self):
        result = _run(
            self._base_args() + ["--no-report", "--initiatives", "--initiative-sims", "100"],
            cwd=BASE_DIR,
            timeout=240,
        )
        self._assert_clean(result)
        self.assertTrue((self.outdir / "_detail" / "initiative_rankings.csv").exists())
        self.assertTrue((self.outdir / "_detail" / "hundred_day_plan.csv").exists())

    def test_markdown_and_json_outputs(self):
        result = _run(
            self._base_args() + ["--no-report", "--markdown", "--json-output"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)
        self.assertTrue((self.outdir / "report.md").exists())
        self.assertTrue((self.outdir / "summary.json").exists())

    def test_trace_iteration(self):
        result = _run(
            self._base_args() + ["--no-report", "--trace-iteration", "0"],
            cwd=BASE_DIR,
        )
        self._assert_clean(result)
        self.assertTrue((self.outdir / "_detail" / "simulation_trace.json").exists())

    def test_theme_dark(self):
        result = _run(self._base_args() + ["--theme", "dark"], cwd=BASE_DIR)
        self._assert_clean(result)
        self.assertTrue((self.outdir / "report.html").exists())

    def test_no_align_profile(self):
        result = _run(self._base_args() + ["--no-report", "--no-align-profile"], cwd=BASE_DIR)
        self._assert_clean(result)

    def test_calibrated_run_with_demo_data(self):
        demo_dir = str(BASE_DIR / "data_demo" / "target_pkg")
        result = _run(
            self._base_args() + ["--no-report", "--actual-data-dir", demo_dir],
            cwd=BASE_DIR,
            timeout=180,
        )
        self._assert_clean(result)
        self.assertTrue((self.outdir / "_detail" / "calibrated_actual.yaml").exists())
        self.assertTrue((self.outdir / "_detail" / "data_quality_report.json").exists())

    def test_pressure_test_produces_assessments_and_miss(self):
        plan_path = str(BASE_DIR / "scenarios" / "management_plan_example.yaml")
        result = _run(
            self._base_args() + ["--no-report", "--pressure-test", plan_path, "--pressure-sims", "200"],
            cwd=BASE_DIR,
            timeout=240,
        )
        self._assert_clean(result)
        # Pressure-test CSVs are detail artifacts (swept into _detail/)
        self.assertTrue((self.outdir / "_detail" / "pressure_test_assessments.csv").exists())
        self.assertTrue((self.outdir / "_detail" / "pressure_test_miss_scenarios.csv").exists())

    def test_ccn_in_config_triggers_peer_comparison(self):
        """hospital.ccn in actual.yaml → CLI auto-writes peer_comparison CSVs."""
        import yaml as _yaml
        # Copy shipped actual.yaml into tmp and add hospital.ccn
        with open(ACTUAL) as f:
            actual_cfg = _yaml.safe_load(f)
        actual_cfg.setdefault("hospital", {})["ccn"] = "360180"
        actual_path = self.outdir / "actual_with_ccn.yaml"
        with open(actual_path, "w") as f:
            _yaml.safe_dump(actual_cfg, f)
        result = _run(
            [
                "--actual", str(actual_path),
                "--benchmark", BENCH,
                "--outdir", str(self.outdir),
                "--n-sims", N_SIMS, "--seed", "42",
                "--no-report",
            ],
            cwd=BASE_DIR,
            timeout=180,
        )
        self._assert_clean(result)
        # B46+: peer artifacts stay at the top level so portfolio snapshots
        # can read them directly (they were in _detail/ prior to portfolio layer).
        self.assertTrue((self.outdir / "peer_comparison.csv").exists())
        self.assertTrue((self.outdir / "peer_target_percentiles.csv").exists())

    def test_bundle_artifacts_at_top_level(self):
        """Default run produces the workbook + data_requests at the top of outdir."""
        result = _run(self._base_args() + ["--no-report"], cwd=BASE_DIR)
        self._assert_clean(result)
        self.assertTrue((self.outdir / "diligence_workbook.xlsx").exists())
        self.assertTrue((self.outdir / "data_requests.md").exists())
        self.assertTrue((self.outdir / "summary.csv").exists())
        self.assertTrue((self.outdir / "_detail").is_dir())

    def test_no_bundle_keeps_everything_flat(self):
        """--no-bundle preserves the legacy layout for power users."""
        result = _run(self._base_args() + ["--no-report", "--no-bundle"], cwd=BASE_DIR)
        self._assert_clean(result)
        self.assertFalse((self.outdir / "diligence_workbook.xlsx").exists())
        self.assertFalse((self.outdir / "data_requests.md").exists())
        self.assertFalse((self.outdir / "_detail").exists())
        # Detail files stay at top-level
        self.assertTrue((self.outdir / "sensitivity.csv").exists())
