"""Regression test for the dispatcher-bypass cleanup at
infra/run_history.py (campaign target 4E, loop 87).

Pre-loop-87 the run-history store had two sqlite3.connect
sites — record_run (write path) and list_runs (read path).
The read path also assigned row_factory=Row by hand. After
the cleanup, both sites route through ``PortfolioStore
(db_path).connect()`` as a context manager. Row factory is
provided by PortfolioStore so the manual assignment is gone;
the explicit conn.commit() in record_run is preserved inside
the with-block (PortfolioStore.connect() closes but doesn't
auto-commit).

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: record_run + list_runs round-trip on a
    temporary outdir produces the expected row shape.
    Confirms both the write path (with explicit commit) and
    the read path (with row_factory access via dict(r))
    survive the migration.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.infra.run_history import list_runs, record_run


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "infra" / "run_history.py"
)


class RunHistoryBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "run_history.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "run_history.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "run_history.py should reference PortfolioStore",
        )

    def test_record_and_list_round_trip(self) -> None:
        """Behavioural pin: a record_run write followed by
        list_runs returns the row with the expected fields.
        Confirms the explicit commit inside the new with-block
        flushes correctly and the read path's dict(r) access
        works through PortfolioStore's Row factory."""
        with tempfile.TemporaryDirectory() as outdir:
            record_run(
                outdir,
                n_sims=1000,
                seed=42,
                ebitda_drag_mean=0.05,
                ebitda_drag_p10=0.01,
                ebitda_drag_p90=0.10,
                ev_impact=-1.5e6,
                hospital_name="Test General",
                notes="loop-87 regression",
            )
            rows = list_runs(outdir, limit=10)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertIsInstance(row, dict)
            self.assertEqual(row["n_sims"], 1000)
            self.assertEqual(row["seed"], 42)
            self.assertAlmostEqual(row["ebitda_drag_mean"], 0.05)
            self.assertEqual(row["hospital_name"], "Test General")
            self.assertEqual(row["notes"], "loop-87 regression")
            self.assertEqual(row["output_dir"], outdir)

    def test_list_runs_empty_when_no_history(self) -> None:
        """list_runs returns [] when the runs.sqlite file
        doesn't exist yet (this branch is in the source, no
        connect happens)."""
        with tempfile.TemporaryDirectory() as outdir:
            self.assertEqual(list_runs(outdir), [])


if __name__ == "__main__":
    unittest.main()
