"""Regression test for the dispatcher-bypass cleanup at
data_public/deals_corpus.py (campaign target 4E, loop 84).

Pre-loop-84 the DealsCorpus class had its own _connect()
context manager that called sqlite3.connect(self.db_path) and
set 4 PRAGMAs by hand (journal_mode=WAL, foreign_keys=ON,
busy_timeout=5000, row_factory=Row). After the cleanup,
_connect routes through ``PortfolioStore(self.db_path).
connect()`` for the canonical 3 PRAGMAs and explicitly sets
``PRAGMA journal_mode = WAL`` inside the with-block — WAL is
a database-file-level setting that PortfolioStore doesn't
apply by default but which the corpus relies on for
read/write concurrency between ingest writers and analyzer
readers.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: round-trip — a DealsCorpus instance can
    upsert a deal, get it back, list with filters, delete it,
    and stats() reflects the changes. Confirms the new
    _connect seam preserves the upsert + list + delete
    contract end-to-end.
  - Behavioural: WAL mode is still enabled on the DB after
    a connect. Confirms the explicit PRAGMA inside the
    with-block survives the migration.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.deals_corpus import DealsCorpus


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "deals_corpus.py"
)


class DealsCorpusBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "deals_corpus.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "deals_corpus.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "deals_corpus.py should reference PortfolioStore",
        )

    def test_corpus_round_trip_through_PortfolioStore(self) -> None:
        """Behavioural pin: upsert → get → list → delete →
        stats round-trip on a fresh DealsCorpus. Confirms the
        new _connect seam preserves the full read/write
        contract."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            corpus = DealsCorpus(db_path)
            deal = {
                "source_id": "TEST-001",
                "source": "seed",
                "deal_name": "Test Acute",
                "year": 2020,
                "buyer": "BuyerA",
                "seller": "SellerA",
                "ev_mm": 750.0,
                "ebitda_at_entry_mm": 90.0,
                "hold_years": 5.0,
                "realized_moic": 2.5,
                "realized_irr": 0.20,
                "payer_mix": {"medicare": 0.5, "commercial": 0.3,
                              "medicaid": 0.2},
            }
            corpus.upsert(deal)

            got = corpus.get("TEST-001")
            self.assertIsNotNone(got)
            self.assertEqual(got["deal_name"], "Test Acute")
            self.assertAlmostEqual(got["realized_moic"], 2.5)

            listed = corpus.list()
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["source_id"], "TEST-001")

            stats = corpus.stats()
            self.assertEqual(stats["total"], 1)
            self.assertEqual(stats["with_moic"], 1)

            corpus.delete("TEST-001")
            self.assertIsNone(corpus.get("TEST-001"))
            self.assertEqual(corpus.stats()["total"], 0)

    def test_journal_mode_wal_preserved(self) -> None:
        """Behavioural pin: after the new _connect seam runs,
        the DB still has journal_mode=WAL set. Confirms the
        explicit PRAGMA inside the with-block survives the
        migration — important because PortfolioStore does NOT
        set WAL by default."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            corpus = DealsCorpus(db_path)
            # Force at least one connect via the public API.
            _ = corpus.stats()
            # Inspect journal_mode on a separate PortfolioStore
            # connection (WAL is a database-file-level setting,
            # so any subsequent connection sees it).
            with PortfolioStore(db_path).connect() as con:
                row = con.execute("PRAGMA journal_mode").fetchone()
                # row may be a Row or a tuple — first column is mode
                mode = row[0] if row is not None else None
                self.assertEqual(
                    str(mode).lower(), "wal",
                    f"expected WAL mode, got {mode!r}",
                )


if __name__ == "__main__":
    unittest.main()
