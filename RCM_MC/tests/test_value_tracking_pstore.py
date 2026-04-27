"""Regression test for the dispatcher-bypass cleanup at
ui/value_tracking_page.py (campaign target 4E, loop 51).

Pre-loop-51 the page imported sqlite3 at the top and called
``sqlite3.connect(db_path)`` directly inside ``render_value_tracker``.
After the cleanup, the module imports PortfolioStore from
``..portfolio.store`` and routes the read through
``PortfolioStore(db_path).connect()`` as a context manager so the
connection inherits busy_timeout=5000, foreign_keys=ON, and
row_factory=Row.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3`` (the lazy local form too).
  - PortfolioStore is imported.
  - Behavioural: render_value_tracker returns the no-plan branch
    cleanly when the deal has no frozen plan in a fresh
    PortfolioStore-init DB. This exercises the new seam end-to-end.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.value_tracking_page import render_value_tracker


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "value_tracking_page.py"
)


class ValueTrackingPageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "value_tracking_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "value_tracking_page.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "value_tracking_page.py should reference PortfolioStore",
        )

    def test_no_plan_branch_renders_through_PortfolioStore(self) -> None:
        """Behavioural pin: with a fresh PortfolioStore-initialized
        DB (no value-tracker plan rows), render_value_tracker hits
        the no-plan branch and returns a non-empty HTML string.
        Confirms the new with-block context-manages the read
        cleanly from end to end."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            PortfolioStore(db_path)
            html = render_value_tracker("DEAL-XXXX", db_path)
            self.assertIsInstance(html, str)
            self.assertGreater(len(html), 0)
            # The no-plan branch always renders this header.
            self.assertIn("No Value Creation Plan", html)


if __name__ == "__main__":
    unittest.main()
