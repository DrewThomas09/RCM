"""Regression test for the dispatcher-bypass cleanup at
ui/team_page.py (campaign target 4E, loop 76).

Pre-loop-76 the page imported sqlite3 at the top and called
``sqlite3.connect(db_path)`` directly inside
``render_team_dashboard``. After the cleanup, the module imports
PortfolioStore and routes through ``PortfolioStore(db_path)
.connect()`` as a context manager. Read-only, so no commit needed
inside the with-block.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: render_team_dashboard runs end-to-end against a
    fresh PortfolioStore-init DB and renders the empty-state
    activity feed cleanly through the new seam.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.team_page import render_team_dashboard


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "team_page.py"
)


class TeamPageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "team_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "team_page.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "team_page.py should reference PortfolioStore",
        )

    def test_render_team_dashboard_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a fresh PortfolioStore-init DB
        exercises the activity-feed + pipeline read path through
        the new with-block. Render must succeed and produce a
        non-trivial HTML string with the empty-state copy."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            PortfolioStore(db_path)
            html = render_team_dashboard(db_path)
            self.assertIsInstance(html, str)
            self.assertGreater(len(html), 100)
            # Empty-state copy in the activity feed.
            self.assertIn("No team activity yet", html)


if __name__ == "__main__":
    unittest.main()
