"""Regression test for the dispatcher-bypass cleanup at
server.py:3655-3656 — the /api/backup HTTP handler (campaign
target 4E, loop 91).

Pre-loop-91 the handler used a lazy local
``import sqlite3 as _sqlite3`` and called
``_sqlite3.connect(self.config.db_path)`` and
``_sqlite3.connect(backup_path)`` directly to drive the
native sqlite3 online-backup API (Connection.backup(target)).
After the cleanup, both connections route through
``PortfolioStore(...).connect()`` via the parenthesized
multi-context-manager form (Python 3.14):
    with (
        PortfolioStore(src_path).connect() as src,
        PortfolioStore(dst_path).connect() as dst,
    ):
        src.backup(dst)

Asserts:
  - Migration: the /api/backup handler block in server.py no
    longer contains ``_sqlite3.connect(`` or
    ``import sqlite3 as _sqlite3``.
  - PortfolioStore is referenced inside the handler (the
    server.py module already imports PortfolioStore at top
    level — the assertion checks the handler block itself).
  - Behavioural: a stand-alone reproduction of the migrated
    pattern works end-to-end. PortfolioStore.connect() yields
    a Connection that supports the native .backup(target) API
    and the resulting backup file contains all the rows from
    the source.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "server.py"
)


def _backup_handler_block(text: str) -> str:
    """Extract the /api/backup handler block from server.py."""
    # The handler starts at `if path == "/api/backup":` and ends
    # at the next top-level `if path == ` or `def ` line.
    start_re = re.compile(r'^\s+if path == "/api/backup":', re.M)
    m = start_re.search(text)
    if not m:
        return ""
    end_re = re.compile(r'^\s+if path == "/api/', re.M)
    end_m = end_re.search(text, m.end())
    end = end_m.start() if end_m else len(text)
    return text[m.start():end]


class ServerBackupHandlerBypassTests(unittest.TestCase):
    def test_backup_handler_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        block = _backup_handler_block(text)
        self.assertGreater(
            len(block), 0,
            "could not locate the /api/backup handler block",
        )
        self.assertNotIn(
            "_sqlite3.connect(", block,
            "/api/backup handler still contains _sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3 as _sqlite3", block,
            "/api/backup handler still imports sqlite3 as _sqlite3",
        )
        # Bare sqlite3.connect should also not appear
        self.assertNotIn(
            "sqlite3.connect(", block,
            "/api/backup handler still contains sqlite3.connect(",
        )

    def test_backup_handler_routes_through_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        block = _backup_handler_block(text)
        self.assertIn(
            "PortfolioStore", block,
            "/api/backup handler should reference PortfolioStore",
        )

    def test_online_backup_pattern_through_PortfolioStore(self) -> None:
        """Behavioural pin: the migrated pattern (parenthesized
        multi-context-manager wrapping src + dst PortfolioStore
        connections, then src.backup(dst)) actually works. After
        the call, the dst file contains the same rows as the src
        file. This is the exact pattern the handler now uses."""
        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, "src.db")
            dst_path = os.path.join(tmp, "dst.db")

            # Seed the source DB with a real row.
            src_store = PortfolioStore(src_path)
            with src_store.connect() as con:
                con.execute(
                    "CREATE TABLE deals (deal_id TEXT PRIMARY KEY, "
                    "name TEXT)"
                )
                con.execute(
                    "INSERT INTO deals (deal_id, name) VALUES (?, ?)",
                    ("D1", "Backup Target"),
                )
                con.commit()

            # Reproduce the migrated handler pattern:
            with (
                PortfolioStore(src_path).connect() as src,
                PortfolioStore(dst_path).connect() as dst,
            ):
                src.backup(dst)

            # Verify the dst file is a valid sqlite DB containing
            # the same row.
            self.assertTrue(os.path.exists(dst_path))
            with PortfolioStore(dst_path).connect() as con:
                row = con.execute(
                    "SELECT name FROM deals WHERE deal_id = ?",
                    ("D1",),
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "Backup Target")


if __name__ == "__main__":
    unittest.main()
