"""Regression test for the dispatcher-bypass cleanup at
data_public/base_rates.py (campaign target 4E, loop 79).

Pre-loop-79 the corpus base-rate API had its own private
_connect() factory that called sqlite3.connect(db_path), set
busy_timeout=5000, and assigned row_factory=Row by hand —
duplicating exactly what PortfolioStore.connect() provides.
After the cleanup, _connect is gone, _query_all routes through
``PortfolioStore(db_path).connect()`` as a context manager,
and the redundant import sqlite3 + sqlite3.Row type
annotations are dropped from the module top.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - The legacy _connect factory is removed (no longer in the
    module surface).
  - Behavioural: get_benchmarks runs end-to-end against a tiny
    public_deals fixture stood up via PortfolioStore.connect()
    and produces a Benchmarks dataclass with the expected
    realized_moic / realized_irr percentiles. Confirms the
    new seam preserves the row-factory contract that
    _compute_benchmarks depends on (rows accessed by column
    name like r["realized_moic"]).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.base_rates import (
    Benchmarks,
    get_benchmarks,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "base_rates.py"
)


def _seed_public_deals(db_path: str) -> None:
    """Stand up a minimal public_deals table with 4 rows
    spanning the realized return distribution. The schema only
    needs the columns _compute_benchmarks reads."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "deal_id TEXT PRIMARY KEY, "
            "realized_moic REAL, realized_irr REAL, "
            "ev_mm REAL, hold_years REAL, "
            "payer_mix TEXT, deal_type TEXT, buyer TEXT)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO public_deals "
            "(deal_id, realized_moic, realized_irr, ev_mm, hold_years) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("D1", 1.5, 0.10, 200.0, 4.0),
                ("D2", 2.0, 0.15, 800.0, 5.0),
                ("D3", 2.5, 0.20, 1500.0, 6.0),
                ("D4", 3.0, 0.25, 4000.0, 7.0),
            ],
        )
        con.commit()


class BaseRatesBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "base_rates.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "base_rates.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "base_rates.py should reference PortfolioStore",
        )

    def test_legacy_connect_factory_removed(self) -> None:
        """The private _connect helper is now redundant — its
        three responsibilities (sqlite3.connect, busy_timeout,
        row_factory) all live in PortfolioStore.connect()."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "def _connect(", text,
            "_connect factory should be removed — its job is "
            "now done by PortfolioStore.connect()",
        )

    def test_get_benchmarks_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a tiny 4-row public_deals fixture
        produces the expected percentile statistics through the
        new seam. Confirms the row-factory contract
        (r["column_name"] access) survives the migration."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_public_deals(db_path)
            bm = get_benchmarks(db_path)
            self.assertIsInstance(bm, Benchmarks)
            self.assertEqual(bm.n_deals, 4)
            self.assertEqual(bm.n_with_moic, 4)
            self.assertEqual(bm.n_with_irr, 4)
            # Median of [1.5, 2.0, 2.5, 3.0] is 2.25
            self.assertAlmostEqual(bm.moic_p50 or 0.0, 2.25, places=2)
            # Median of [0.10, 0.15, 0.20, 0.25] is 0.175
            self.assertAlmostEqual(bm.irr_p50 or 0.0, 0.175, places=3)


if __name__ == "__main__":
    unittest.main()
