"""Compliance CLI regression tests.

Entry point: ``python -m rcm_mc.compliance <scan|verify-audit> ...``.

Exit-code contract (load-bearing for pre-commit / CI wiring):

  scan          — exit 0 on no findings, 1 on any finding, 2 on
                  unexpected error
  verify-audit  — exit 0 when chain is ok, 1 on any mismatch or
                  linkage break, 2 on store import failure

Also verifies:
- The scanner skips ignored directory names (__pycache__, .git,
  node_modules) so test suites don't self-flag
- Binary extensions are skipped; text files with no PHI pass
- --json emits a parseable JSON report
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _run(*args: str, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "rcm_mc.compliance", *args],
        capture_output=True, text=True, cwd=cwd,
    )


class ScanSubcommandTests(unittest.TestCase):

    def test_exit_zero_on_clean_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "readme.md").write_text("hello world")
            (Path(tmp) / "main.py").write_text("x = 42")
            r = _run("scan", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stderr + r.stdout)

    def test_exit_one_on_phi_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bad.py").write_text(
                "u = {'ssn': '123-45-6789'}"
            )
            r = _run("scan", tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("ssn", r.stdout.lower())

    def test_ignored_directories_skipped(self):
        """Common ignorable dirs (__pycache__, .git, .venv,
        node_modules) must not self-flag."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_text(
                "SSN: 123-45-6789"
            )
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(
                "SSN: 123-45-6789"
            )
            (root / "clean.py").write_text("x = 42")
            r = _run("scan", str(root))
            self.assertEqual(r.returncode, 0)

    def test_binary_extensions_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            # .db file with a PHI-looking string — should be skipped.
            (Path(tmp) / "store.db").write_text("SSN: 123-45-6789")
            (Path(tmp) / "img.png").write_text("SSN: 123-45-6789")
            r = _run("scan", tmp)
            self.assertEqual(r.returncode, 0)

    def test_json_output_is_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "leaky.py").write_text(
                "call (415) 555-1234"
            )
            r = _run("scan", "--json", tmp)
            self.assertEqual(r.returncode, 1)
            payload = json.loads(r.stdout)
            self.assertIn("findings_total", payload)
            self.assertIn("reports", payload)
            self.assertGreaterEqual(payload["findings_total"], 1)


class VerifyAuditSubcommandTests(unittest.TestCase):

    def test_exit_zero_on_empty_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            r = _run("verify-audit", "--db", db)
            self.assertEqual(r.returncode, 0, msg=r.stderr + r.stdout)
            payload = json.loads(r.stdout)
            self.assertTrue(payload["verification"]["ok"])

    def test_exit_zero_on_clean_chain(self):
        from rcm_mc.compliance.audit_chain import append_chained_event
        from rcm_mc.portfolio.store import PortfolioStore
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            for i in range(3):
                append_chained_event(
                    store, actor="at", action=f"a{i}", target="t",
                )
            r = _run("verify-audit", "--db", db)
            self.assertEqual(r.returncode, 0, msg=r.stderr + r.stdout)

    def test_exit_one_on_tamper(self):
        from rcm_mc.compliance.audit_chain import append_chained_event
        from rcm_mc.portfolio.store import PortfolioStore
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            eid, _ = append_chained_event(
                store, actor="at", action="approve", target="deal_1",
            )
            append_chained_event(store, actor="at", action="noop", target="t")
            # Mutate row 1's target.
            with store.connect() as con:
                con.execute(
                    "UPDATE audit_events SET target = ? WHERE id = ?",
                    ("deal_99", eid),
                )
                con.commit()
            r = _run("verify-audit", "--db", db)
            self.assertEqual(r.returncode, 1)
            payload = json.loads(r.stdout)
            self.assertFalse(payload["verification"]["ok"])


if __name__ == "__main__":
    unittest.main()
