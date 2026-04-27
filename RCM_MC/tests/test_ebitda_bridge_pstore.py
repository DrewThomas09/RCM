"""Regression test for the dispatcher-bypass cleanup at
ui/ebitda_bridge_page.py (campaign target 4E, loop 50).

Pre-loop-50 the helper ``_load_data_room_overrides`` had a lazy
local ``import sqlite3`` and called ``sqlite3.connect(db_path)``
directly. After the cleanup, the function imports PortfolioStore
locally (matching the lazy-import style) and routes through
``PortfolioStore.connect()`` as a context manager.

Three asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``.
  - PortfolioStore is referenced (lazy local import counts).
  - Behavioural: _load_data_room_overrides returns {} cleanly when
    db_path is empty (existing contract) and {} on a fresh empty
    DB (no calibrations, no entries).
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.ebitda_bridge_page import _load_data_room_overrides


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "ebitda_bridge_page.py"
)


class EbitdaBridgePageBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "ebitda_bridge_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        # Inline `import sqlite3` (lazy local) is gone too.
        self.assertNotIn(
            "import sqlite3", text,
            "ebitda_bridge_page.py still imports sqlite3 somewhere",
        )

    def test_module_references_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "ebitda_bridge_page.py should reference PortfolioStore",
        )

    def test_empty_db_path_returns_empty_dict(self) -> None:
        """Existing contract: an empty/None db_path means no data
        room is configured, return {} fast."""
        self.assertEqual(_load_data_room_overrides("", "010001"), {})
        self.assertEqual(_load_data_room_overrides(None, "010001"), {})

    def test_fresh_db_returns_empty_dict_through_PortfolioStore(self) -> None:
        """Behavioural pin: with a fresh PortfolioStore-initialized
        DB (no data_room_calibrations or data_room_entries tables
        populated yet), the helper falls through both try blocks
        and returns {} cleanly. Confirms PortfolioStore.connect()'s
        yielded connection works under the helper's existing
        try/except shape."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            # init the store so the DB file exists
            PortfolioStore(db_path)
            self.assertEqual(
                _load_data_room_overrides(db_path, "010001"), {},
            )


if __name__ == "__main__":
    unittest.main()
