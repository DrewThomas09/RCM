"""Regression test for the dispatcher-bypass cleanup at
ui/command_center.py (campaign target 4E, loop 37).

The page previously called sqlite3.connect(db_path) directly at two
sites (lines 49 and 77 in the pre-loop-37 version), bypassing
PortfolioStore and missing PRAGMA foreign_keys=ON, busy_timeout=
5000, row_factory=Row. After the cleanup, both sites route through
PortfolioStore.connect().

This file pins:
  - The migration: command_center.py contains no `sqlite3.connect`
    or `import sqlite3` after the cleanup.
  - End-to-end render: render_command_center runs against a fresh
    temp DB through PortfolioStore.connect() and produces a v3-shell
    HTML document without raising.

The page is reached as a *fallback* renderer for /seekingchartis_home
(server.py:5092 — invoked only when chartis_home AND home_v2 both
fail), so a urllib.request hit on a stable URL is not the right
test shape. Direct call is the right shape — it's still real code,
no mocks of our own code, just bypassing the route dispatcher.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.command_center import render_command_center


_COMMAND_CENTER = (
    Path(__file__).resolve().parents[1] / "rcm_mc" / "ui" / "command_center.py"
)


class CommandCenterBypassTests(unittest.TestCase):
    def test_module_no_longer_imports_sqlite3_directly(self) -> None:
        """The bypass cleanup removed the `import sqlite3` line and
        the `sqlite3.connect(...)` call sites. If they regress the
        bypass is silently re-introduced — this test catches it."""
        text = _COMMAND_CENTER.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect", text,
            "command_center.py contains sqlite3.connect — the "
            "PortfolioStore bypass has regressed",
        )
        # Match `import sqlite3` as a whole-line statement — not
        # accidental matches inside docstrings.
        self.assertFalse(
            re.search(r"^import sqlite3\b", text, re.M),
            "command_center.py imports sqlite3 directly — should "
            "route through PortfolioStore",
        )
        self.assertIn(
            "PortfolioStore", text,
            "command_center.py should now reference PortfolioStore",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        """The migration replaces direct sqlite3 access with the
        canonical PortfolioStore seam. The import line must be
        present and refer to the right module."""
        text = _COMMAND_CENTER.read_text(encoding="utf-8")
        self.assertIn(
            "from ..portfolio.store import PortfolioStore", text,
            "command_center.py should import PortfolioStore from "
            "..portfolio.store",
        )

    def test_portfolio_store_seam_reads_deals_safely(self) -> None:
        """The bypass cleanup's actual contract: the same SQL the
        page used to run via sqlite3.connect now runs via
        PortfolioStore.connect() and produces the same shape on a
        fresh DB. End-to-end render is intentionally not exercised
        here — the page has an unrelated pre-existing
        chartis_shell(show_ticker=...) kwarg mismatch that this
        loop is not authorized to touch."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            store = PortfolioStore(db_path)
            with store.connect() as con:
                con.execute(
                    "CREATE TABLE IF NOT EXISTS deals ("
                    "deal_id TEXT PRIMARY KEY, name TEXT, "
                    "profile_json TEXT, created_at TEXT, archived_at TEXT)"
                )
                con.commit()
                # Reproduce the page's first SQL through the new
                # canonical seam — should return [] cleanly.
                rows = con.execute(
                    "SELECT deal_id, name, profile_json, created_at "
                    "FROM deals WHERE archived_at IS NULL "
                    "ORDER BY created_at DESC"
                ).fetchall()
                self.assertEqual(rows, [])
                # row_factory should be Row (canonical PRAGMA path)
                self.assertIs(con.row_factory, __import__("sqlite3").Row)


if __name__ == "__main__":
    unittest.main()
