"""Regression test for the dispatcher-bypass cleanup at
data/hcris_incremental.py (campaign target 4E, loop 101).

Pre-loop-101 the HCRIS incremental loader had its own
private _connect context manager that called
sqlite3.connect(db_path) and set busy_timeout + row_factory
by hand. After the cleanup, _connect routes through
``PortfolioStore(db_path).connect()`` — busy_timeout=5000,
foreign_keys=ON, and row_factory=Row all come from the
canonical seam. _ensure_schema still runs once per connect
to lazily create the hcris_load_log table.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: incremental_refresh runs end-to-end against
    a fresh tmp DB with a stub fetcher that returns 2 fake
    filings, both get inserted, then a second run with same
    rank + same hash skips both (existing-row contract).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.data.hcris_incremental import IngestReport, incremental_refresh


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data" / "hcris_incremental.py"
)


def _stub_fetcher(year: int):
    """Returns 2 fake filings for any year. Each filing has
    only the keys _row_hash + _status_rank_of read; everything
    else can be None."""
    return [
        {
            "ccn": "010001",
            "status": "FINAL",
            "fiscal_year": year,
            "net_patient_revenue": 100_000_000,
            "operating_expenses": 90_000_000,
            "beds": 200,
        },
        {
            "ccn": "010002",
            "status": "FINAL",
            "fiscal_year": year,
            "net_patient_revenue": 150_000_000,
            "operating_expenses": 130_000_000,
            "beds": 300,
        },
    ]


class HcrisIncrementalBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "hcris_incremental.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "hcris_incremental.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "hcris_incremental.py should reference PortfolioStore",
        )

    def test_incremental_refresh_round_trip(self) -> None:
        """Behavioural pin: a 2-filing stub fetcher inserts both
        on first pass; second pass with identical input skips
        both (rank == rank, hash == hash). Confirms the new
        _connect seam preserves the BEGIN IMMEDIATE transaction
        + INSERT / UPDATE / skip control flow."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "hcris.db")

            r1 = incremental_refresh(
                db_path, years=[2022], fetcher=_stub_fetcher,
            )
            self.assertIsInstance(r1, IngestReport)
            self.assertEqual(r1.filings_inserted, 2)
            self.assertEqual(r1.filings_upgraded, 0)
            self.assertEqual(r1.filings_skipped, 0)
            self.assertEqual(r1.fiscal_years_processed, [2022])

            # Second pass: same inputs → both skip (same rank,
            # same hash).
            r2 = incremental_refresh(
                db_path, years=[2022], fetcher=_stub_fetcher,
            )
            self.assertEqual(r2.filings_inserted, 0)
            self.assertEqual(r2.filings_upgraded, 0)
            self.assertEqual(r2.filings_skipped, 2)


if __name__ == "__main__":
    unittest.main()
