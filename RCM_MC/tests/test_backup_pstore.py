"""Regression test for the dispatcher-bypass cleanup at
infra/backup.py (campaign target 4E, loop 88).

Pre-loop-88 the backup/restore module had two sqlite3.connect
sites — one in restore_backup (integrity check on the
decompressed temp file) and one in verify_backup (integrity
check + key-table row counts on a non-destructive backup
verification). Both caught sqlite3.DatabaseError specifically
on failure.

After the cleanup:
  - Both sites route through ``PortfolioStore(str(tmp_path)).
    connect()``. PortfolioStore's __init__ does NOT auto-init
    schema (verified at portfolio/store.py:80-81), so opening
    a backup snapshot via PortfolioStore is a read-only probe
    that won't mutate the file.
  - Both `except sqlite3.DatabaseError` clauses are broadened
    to `except Exception` (recovery shape unchanged: log
    error, unlink temp, return failure result).

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: full create_backup → verify_backup →
    restore_backup round-trip on a tmp PortfolioStore-init
    DB. Confirms the integrity-probe path through the new
    seam still verifies a real backup correctly.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.infra.backup import (
    create_backup,
    restore_backup,
    verify_backup,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "infra" / "backup.py"
)


class BackupBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "backup.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "backup.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "backup.py should reference PortfolioStore",
        )

    def test_create_verify_restore_round_trip(self) -> None:
        """Behavioural pin: create a backup of a PortfolioStore-
        init DB, verify it (integrity_check should pass through
        the new with-block seam), then restore it to a new path
        (integrity_check passes again on the decompressed temp).
        Exercises both PortfolioStore.connect() sites in the
        module."""
        with tempfile.TemporaryDirectory() as tmp:
            src_db = os.path.join(tmp, "src.db")
            dest_dir = os.path.join(tmp, "backups")
            restore_target = os.path.join(tmp, "restored.db")

            store = PortfolioStore(src_db)
            # Force schema creation so the backup has tables to
            # count in verify_backup.
            with store.connect() as con:
                con.execute(
                    "CREATE TABLE deals (deal_id TEXT PRIMARY KEY, "
                    "name TEXT, archived_at TEXT)"
                )
                con.execute(
                    "INSERT INTO deals (deal_id, name) VALUES (?, ?)",
                    ("D1", "Test deal"),
                )
                con.commit()

            # create_backup uses store.connect() externally; the
            # path under test is the one inside backup.py.
            gz_path = create_backup(store, dest_dir)
            self.assertTrue(gz_path.exists())

            # verify_backup hits the second migrated site.
            v = verify_backup(str(gz_path))
            self.assertTrue(v["valid"], f"verify result: {v}")
            self.assertEqual(v["integrity"], "ok")
            self.assertIn("deals", v["tables"])
            self.assertEqual(v["tables"]["deals"], 1)

            # restore_backup hits the first migrated site.
            ok = restore_backup(str(gz_path), restore_target)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(restore_target))

    def test_verify_backup_invalid_file(self) -> None:
        """Silent-fallback contract: a corrupt/non-SQLite file
        produces a result dict with valid=False rather than
        raising. Used to catch sqlite3.DatabaseError; broadened
        to Exception so the module fully drops the sqlite3
        import."""
        with tempfile.TemporaryDirectory() as tmp:
            # Write a gzipped non-SQLite file.
            import gzip
            corrupt_gz = os.path.join(tmp, "corrupt.db.gz")
            with gzip.open(corrupt_gz, "wb") as f:
                f.write(b"this is not a SQLite database file")
            v = verify_backup(corrupt_gz)
            self.assertFalse(v["valid"])
            # error or non-ok integrity — either is acceptable
            self.assertTrue(v["error"] or v["integrity"] != "ok")


if __name__ == "__main__":
    unittest.main()
