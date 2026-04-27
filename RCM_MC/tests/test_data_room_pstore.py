"""Regression test for the dispatcher-bypass cleanup at
ui/data_room_page.py (campaign target 4E, loop 75).

Pre-loop-75 the page imported sqlite3 at the top and called
``sqlite3.connect(db_path)`` directly inside ``render_data_room``
to drive the seller-data calibration write path. After the
cleanup, the module imports PortfolioStore and routes through
``PortfolioStore(db_path).connect()`` as a context manager so the
read + calibrate write inherit busy_timeout=5000, foreign_keys=ON,
and row_factory=Row.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3`` (no lazy-local form either).
  - PortfolioStore is imported.
  - Behavioural: render_data_room runs end-to-end against a fresh
    PortfolioStore-init DB with empty ml_predictions and produces
    a non-empty HTML string. Confirms the new seam wraps the
    full read + calibrate + commit path without raising.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.data_room_page import render_data_room


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "data_room_page.py"
)


class DataRoomPageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "data_room_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "data_room_page.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "data_room_page.py should reference PortfolioStore",
        )

    def test_render_data_room_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a fresh PortfolioStore-init DB plus
        empty ml_predictions exercises the read + calibrate + commit
        path through the new with-block. Render must succeed and
        produce a non-trivial HTML string."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            PortfolioStore(db_path)
            html = render_data_room(
                ccn="010001",
                hospital_name="TEST HOSPITAL",
                beds=200.0,
                state="CA",
                ml_predictions={},
                db_path=db_path,
            )
            self.assertIsInstance(html, str)
            self.assertGreater(len(html), 100)
            self.assertIn("TEST HOSPITAL", html)


if __name__ == "__main__":
    unittest.main()
