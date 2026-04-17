"""Tests for `rcm-mc portfolio` CLI (Brick 49)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest

from rcm_mc.portfolio_cmd import main as portfolio_main


def _capture(argv):
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = portfolio_main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


class TestPortfolioCLI(unittest.TestCase):
    def test_register_and_list_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, out, _ = _capture([
                "--db", db, "register", "--deal-id", "x1", "--stage", "sourced",
            ])
            self.assertEqual(rc, 0)
            self.assertIn("Registered snapshot", out)

            rc2, out2, _ = _capture(["--db", db, "list"])
            self.assertEqual(rc2, 0)
            self.assertIn("x1", out2)
            self.assertIn("sourced", out2)

    def test_register_invalid_stage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            # argparse itself rejects choices — returns exit-2 via SystemExit
            with self.assertRaises(SystemExit):
                _capture(["--db", db, "register", "--deal-id", "x", "--stage", "bogus"])

    def test_register_with_run_dir_pulls_pe_math(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            run = os.path.join(tmp, "run")
            os.makedirs(run)
            with open(os.path.join(run, "pe_returns.json"), "w") as f:
                json.dump({"moic": 2.5, "irr": 0.20}, f)
            rc, _, _ = _capture([
                "--db", db, "register",
                "--deal-id", "ccf", "--stage", "loi", "--run-dir", run,
            ])
            self.assertEqual(rc, 0)
            rc2, out, _ = _capture(["--db", db, "list", "--json"])
            self.assertEqual(rc2, 0)
            rows = json.loads(out)
            self.assertEqual(rows[0]["moic"], 2.5)

    def test_show_audit_trail_across_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            for stage in ("sourced", "ioi", "loi"):
                _capture(["--db", db, "register",
                          "--deal-id", "ccf", "--stage", stage])
            rc, out, _ = _capture(["--db", db, "show", "--deal-id", "ccf"])
            self.assertEqual(rc, 0)
            self.assertIn("Audit trail", out)
            self.assertIn("sourced", out)
            self.assertIn("ioi", out)
            self.assertIn("loi", out)

    def test_show_unknown_deal_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, err = _capture(["--db", db, "show", "--deal-id", "nonexistent"])
            self.assertEqual(rc, 1)
            self.assertIn("No snapshots", err)

    def test_rollup_json_matches_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            _capture(["--db", db, "register",
                      "--deal-id", "a", "--stage", "hold"])
            rc, out, _ = _capture(["--db", db, "rollup", "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertEqual(payload["deal_count"], 1)
            self.assertEqual(payload["stage_funnel"]["hold"], 1)

    def test_empty_list_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, out, _ = _capture(["--db", db, "list"])
            self.assertEqual(rc, 1)
            self.assertIn("no deals", out.lower())
