"""Regression test for the dispatcher-bypass cleanup at
ui/pipeline_page.py (campaign target 4E, loop 43).

Pre-loop-43 the page called ``sqlite3.connect(db_path)`` directly
at line 53, bypassing PortfolioStore. After the cleanup, the call
site routes through ``PortfolioStore.connect()`` as a context
manager.

Mirrors the pattern from tests/test_command_center_pstore.py and
tests/test_portfolio_bridge_pstore.py — three asserts on the
file source + one behavioural reproduction of the page's first
SQL operation through the new seam.
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
    / "rcm_mc" / "ui" / "pipeline_page.py"
)


class PipelinePageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        """Match `sqlite3.connect(` with the open paren so a comment
        mentioning the legacy form is not a false positive."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "pipeline_page.py contains sqlite3.connect( — the "
            "PortfolioStore bypass has regressed",
        )
        self.assertFalse(
            re.search(r"^import sqlite3\b", text, re.M),
            "pipeline_page.py imports sqlite3 directly — should "
            "route through PortfolioStore",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ..portfolio.store import PortfolioStore", text,
            "pipeline_page.py should import PortfolioStore from "
            "..portfolio.store",
        )

    def test_pipeline_seam_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: reproduce the page's first SQL ops
        (list_searches + list_pipeline + pipeline_summary +
        get_activity) through the new canonical seam on a fresh
        temp DB. The data.pipeline helpers all take a
        sqlite3.Connection directly, so PortfolioStore.connect()'s
        yield must still provide one with row_factory=sqlite3.Row.
        """
        from rcm_mc.data.pipeline import (
            _ensure_tables, list_searches, list_pipeline,
            pipeline_summary, get_activity,
        )

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            store = PortfolioStore(db_path)
            with store.connect() as con:
                _ensure_tables(con)
                # All four helpers should run cleanly on an empty
                # pipeline DB and return container types (lists /
                # dicts), not None.
                self.assertEqual(list_searches(con), [])
                self.assertEqual(list_pipeline(con), [])
                self.assertIsInstance(pipeline_summary(con), dict)
                self.assertEqual(get_activity(con, limit=15), [])
                self.assertIs(con.row_factory, sqlite3.Row)


if __name__ == "__main__":
    unittest.main()
