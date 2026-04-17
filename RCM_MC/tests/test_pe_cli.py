"""Tests for `rcm-mc pe` CLI subcommand (Brick 45)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest

from rcm_mc.pe_cli import main as pe_main


def _capture(argv):
    """Run pe_main with argv, return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = pe_main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


class TestPEBridgeCLI(unittest.TestCase):
    def test_bridge_terminal_output(self):
        rc, out, _ = _capture([
            "bridge",
            "--entry-ebitda", "50e6", "--uplift", "8e6",
            "--entry-multiple", "9", "--exit-multiple", "10",
            "--hold-years", "5", "--organic-growth", "0.03",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Value Creation Bridge", out)
        self.assertIn("Exit EV", out)

    def test_bridge_json_roundtrip(self):
        rc, out, _ = _capture([
            "bridge",
            "--entry-ebitda", "50e6", "--uplift", "8e6",
            "--entry-multiple", "9", "--exit-multiple", "10",
            "--hold-years", "5", "--json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertIn("entry_ev", parsed)
        self.assertIn("exit_ev", parsed)
        self.assertIn("components", parsed)
        self.assertEqual(len(parsed["components"]), 5)  # Entry + 3 components + Exit

    def test_bridge_reads_from_run(self):
        """--from-run DIR pulls uplift from a prior summary.csv."""
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            pd.DataFrame(
                {"mean": [8e6, 1e6], "median": [7.5e6, 0.9e6]},
                index=["ebitda_uplift", "economic_drag"],
            ).to_csv(os.path.join(tmp, "summary.csv"))
            rc, out, _ = _capture([
                "bridge",
                "--entry-ebitda", "50e6",
                "--entry-multiple", "9", "--exit-multiple", "10",
                "--hold-years", "5", "--from-run", tmp, "--json",
            ])
            self.assertEqual(rc, 0)
            parsed = json.loads(out)
            self.assertAlmostEqual(parsed["inputs"]["uplift"], 8e6, places=2)


class TestPEReturnsCLI(unittest.TestCase):
    def test_returns_terminal_output(self):
        rc, out, _ = _capture([
            "returns",
            "--entry-equity", "100e6", "--exit-proceeds", "300e6",
            "--hold-years", "5",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("MOIC", out)
        self.assertIn("3.00x", out)

    def test_returns_with_interim_cashflows(self):
        rc, out, _ = _capture([
            "returns",
            "--entry-equity", "100e6", "--exit-proceeds", "250e6",
            "--hold-years", "5", "--interim", "0,50e6,0,0", "--json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertEqual(len(parsed["interim_cash_flows"]), 4)
        self.assertAlmostEqual(parsed["total_distributions"], 300e6, places=0)


class TestPEGridCLI(unittest.TestCase):
    def test_grid_with_uplift_ramp(self):
        rc, out, _ = _capture([
            "grid",
            "--entry-ebitda", "50e6",
            "--uplift-ramp", "3:5e6,5:8e6,7:9e6",
            "--entry-multiple", "9",
            "--exit-multiples", "8,9,10",
            "--hold-years", "3,5,7",
            "--entry-equity", "180e6",
            "--debt-at-entry", "270e6",
            "--debt-at-exit", "3:240e6,5:220e6,7:200e6",
            "--organic-growth", "0.03",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Hold-period", out)

    def test_grid_json_returns_all_scenarios(self):
        rc, out, _ = _capture([
            "grid",
            "--entry-ebitda", "50e6", "--uplift", "8e6",
            "--entry-multiple", "9", "--exit-multiples", "9,10",
            "--hold-years", "3,5", "--entry-equity", "180e6",
            "--json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertEqual(len(parsed), 4)  # 2 × 2 scenarios
        for row in parsed:
            self.assertIn("irr", row)
            self.assertIn("moic", row)

    def test_grid_requires_uplift_or_ramp(self):
        rc, _, err = _capture([
            "grid",
            "--entry-ebitda", "50e6",
            "--entry-multiple", "9", "--exit-multiples", "9,10",
            "--hold-years", "3,5", "--entry-equity", "180e6",
        ])
        self.assertEqual(rc, 2)
        self.assertIn("--uplift", err)


class TestPECovenantCLI(unittest.TestCase):
    def test_covenant_safe_case(self):
        rc, out, _ = _capture([
            "covenant",
            "--ebitda", "50e6", "--debt", "270e6",
            "--covenant-leverage", "6.5", "--interest-rate", "0.08",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("SAFE", out)
        self.assertIn("Interest coverage", out)

    def test_covenant_tripped_case_json(self):
        rc, out, _ = _capture([
            "covenant",
            "--ebitda", "30e6", "--debt", "270e6",
            "--covenant-leverage", "6.5", "--json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertLess(parsed["covenant_headroom_turns"], 0)
