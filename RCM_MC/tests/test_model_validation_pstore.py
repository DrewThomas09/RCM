"""Regression test for the dispatcher-bypass cleanup at
ui/model_validation_page.py (campaign target 4E, loop 47).

Pre-loop-47 the page called ``sqlite3.connect(db_path)`` directly
at line 43 and held the connection open across ~200 lines of body
code, ending with a manual ``con.close()`` at line 243. After the
cleanup, the connection comes from ``PortfolioStore(db_path)
.connect()`` via manual ``__enter__/__exit__`` — the function body
keeps its existing flat structure so the diff is two changed
hunks, not a 200-line indent.

Same exception-handling contract as the prior bare-sqlite3 form
(no try/finally was there before; an exception during the body
leaks the connection in both versions). This loop is invariant-
preserving on that front while fixing the bypass.

Mirrors tests/test_command_center_pstore.py / test_pipeline_page_
pstore.py / test_portfolio_bridge_pstore.py.
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
    / "rcm_mc" / "ui" / "model_validation_page.py"
)


class ModelValidationPageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        """Match `sqlite3.connect(` with the open paren so any
        comment mentioning the legacy form is not a false
        positive."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "model_validation_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertFalse(
            re.search(r"^import sqlite3\b", text, re.M),
            "model_validation_page.py imports sqlite3 directly",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ..portfolio.store import PortfolioStore", text,
            "model_validation_page.py should import PortfolioStore "
            "from ..portfolio.store",
        )

    def test_pstore_seam_yields_row_factory_and_supports_manual_enter_exit(self) -> None:
        """Behavioural pin: PortfolioStore.connect()'s context-
        manager protocol can be driven manually via
        __enter__/__exit__ (which is what the page does to avoid
        re-indenting 200 lines of body), and the yielded
        connection has row_factory=Row + busy_timeout set."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            cm = PortfolioStore(db_path).connect()
            con = cm.__enter__()
            try:
                self.assertIs(con.row_factory, sqlite3.Row)
                # busy_timeout PRAGMA persists per-connection
                bt = con.execute("PRAGMA busy_timeout").fetchone()[0]
                self.assertEqual(bt, 5000)
                # foreign_keys PRAGMA is on
                fk = con.execute("PRAGMA foreign_keys").fetchone()[0]
                self.assertEqual(fk, 1)
            finally:
                cm.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()
