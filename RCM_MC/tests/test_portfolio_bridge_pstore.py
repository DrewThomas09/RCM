"""Regression test for the dispatcher-bypass cleanup at
ui/portfolio_bridge_page.py (campaign target 4E, loop 40).

Pre-loop-40, the page called ``sqlite3.connect(db_path)`` directly
at line 54, bypassing PortfolioStore and missing PRAGMA
foreign_keys=ON, busy_timeout=5000, row_factory=Row. After the
cleanup, the call site routes through ``PortfolioStore.connect()``
as a context manager.

This file pins the contract:
  - Migration: portfolio_bridge_page.py contains no ``sqlite3.connect(``
    call (matches paren so my own comment about the legacy form
    doesn't trigger a false positive) and no ``import sqlite3``.
  - The PortfolioStore import is present at module top.
  - The same ``list_pipeline`` SQL the page used to run via
    sqlite3.connect now runs cleanly via PortfolioStore.connect()
    against a fresh temp DB and returns the canonical row_factory.

Mirrors the test pattern from tests/test_command_center_pstore.py
(loop 37). Direct unit + grep tests, no urllib — the page reaches
chartis_shell with several pages of computed bridge HTML; running
through the full server route would require seeding HCRIS data
that is out of scope for one bypass cleanup.
"""
from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "portfolio_bridge_page.py"
)


class PortfolioBridgePageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        """Match `sqlite3.connect(` with the open paren so a comment
        mentioning the legacy form (e.g. "the bare sqlite3.connect
        that misses all three") is not a false positive."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "portfolio_bridge_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertFalse(
            re.search(r"^import sqlite3\b", text, re.M),
            "portfolio_bridge_page.py imports sqlite3 directly",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ..portfolio.store import PortfolioStore", text,
            "portfolio_bridge_page.py should import PortfolioStore "
            "from ..portfolio.store",
        )

    def test_pipeline_seam_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: the same SQL the page used to run via
        sqlite3.connect(db_path) now runs through
        PortfolioStore.connect() and emits a Row-keyed cursor.
        Reproduces the page's first SQL operation (the
        list_pipeline path) to catch any regression where
        PortfolioStore stops yielding a Row-factoried connection.
        """
        from rcm_mc.data.pipeline import list_pipeline, _ensure_tables

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            store = PortfolioStore(db_path)
            with store.connect() as con:
                _ensure_tables(con)
                rows = list_pipeline(con)
                # Empty pipeline returns an empty list, not None
                self.assertEqual(rows, [])
                self.assertIs(con.row_factory, sqlite3.Row)


if __name__ == "__main__":
    unittest.main()
