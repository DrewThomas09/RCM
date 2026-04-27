"""Regression test for the dispatcher-bypass cleanup at
data_public/backtester.py (campaign target 4E, loop 86 — FINAL
data_public module).

Pre-loop-86 backtester had its own private _connect() factory
that called sqlite3.connect(db_path), set busy_timeout=5000,
and assigned row_factory=Row by hand — duplicating exactly
what PortfolioStore.connect() provides. Three helpers
(_load_corpus_deals, _load_platform_deals, _load_latest_run)
went through this factory; two of them caught
sqlite3.OperationalError on missing-table.

After the cleanup:
  - _connect factory is removed entirely.
  - All three helpers route through PortfolioStore.connect().
  - The two `except sqlite3.OperationalError` clauses are
    broadened to `except Exception` (recovery shape unchanged
    — return empty/None on any failure — but lets the module
    fully drop the sqlite3 import).

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - The legacy _connect factory is removed.
  - Behavioural: _load_corpus_deals returns the expected
    realized-only filter against a public_deals fixture.
  - Behavioural: _load_platform_deals returns empty on a fresh
    DB without a deals table (silent-fallback contract).
  - Behavioural: _load_latest_run returns None on a fresh DB
    without a runs table.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.backtester import (
    _load_corpus_deals,
    _load_latest_run,
    _load_platform_deals,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "backtester.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up public_deals with 3 rows: 2 realized (have
    MOIC or IRR), 1 unrealized (NULLs)."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "source_id TEXT PRIMARY KEY, deal_name TEXT, year INTEGER, "
            "realized_moic REAL, realized_irr REAL)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO public_deals "
            "(source_id, deal_name, year, realized_moic, realized_irr) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("R1", "Realized One", 2017, 2.0, 0.15),
                ("R2", "Realized Two", 2018, 2.4, None),
                ("U1", "Unrealized",   2022, None, None),
            ],
        )
        con.commit()


class BacktesterBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "backtester.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "backtester.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "backtester.py should reference PortfolioStore",
        )

    def test_legacy_connect_factory_removed(self) -> None:
        """The private _connect helper is now redundant — its
        two responsibilities (busy_timeout, row_factory) live
        in PortfolioStore.connect()."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "def _connect(", text,
            "_connect factory should be removed — its job is "
            "now done by PortfolioStore.connect()",
        )

    def test_load_corpus_deals_filters_realized(self) -> None:
        """Behavioural pin: _load_corpus_deals only returns
        rows with at least one of realized_moic or realized_irr
        non-NULL. Confirms the filter SQL survives."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            rows = _load_corpus_deals(db_path)
            # 2 realized rows, 1 unrealized excluded
            self.assertEqual(len(rows), 2)
            ids = {r["source_id"] for r in rows}
            self.assertEqual(ids, {"R1", "R2"})

    def test_load_platform_deals_empty_on_fresh_db(self) -> None:
        """Silent-fallback contract: a fresh PortfolioStore-
        init DB has no `deals` table populated yet; the helper
        returns an empty list rather than raising. Used to
        catch sqlite3.OperationalError; now broadened to
        Exception."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "store.db")
            PortfolioStore(db_path)
            result = _load_platform_deals(db_path)
            self.assertEqual(result, [])

    def test_load_latest_run_none_on_fresh_db(self) -> None:
        """Silent-fallback contract: a fresh PortfolioStore-
        init DB has no `runs` table; the helper returns None
        rather than raising."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "store.db")
            PortfolioStore(db_path)
            result = _load_latest_run(db_path, "DEAL-001")
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
