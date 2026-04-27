"""Regression test for the dispatcher-bypass cleanup at
data_public/deal_scorer.py (campaign target 4E, loop 81).

Pre-loop-81 _load_all called sqlite3.connect(corpus_db_path)
directly, set row_factory=Row by hand, and called con.close()
manually. After the cleanup, _load_all routes through
``PortfolioStore(corpus_db_path).connect()`` as a context
manager and the redundant import sqlite3 is dropped.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: score_corpus runs end-to-end against a tiny
    public_deals fixture stood up via PortfolioStore. A
    fully-populated seed-source deal scores higher than a
    manual deal missing financial fields. Confirms the
    row-factory contract (column-name access in
    _score_completeness) survives the migration.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.deal_scorer import (
    DealQualityScore,
    score_corpus,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "deal_scorer.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up a public_deals table with 2 fixture rows: one
    fully populated seed-source deal (high score expected),
    one sparse manual deal (low score expected)."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "source_id TEXT PRIMARY KEY, deal_name TEXT, year INTEGER, "
            "buyer TEXT, seller TEXT, source TEXT, "
            "ev_mm REAL, ebitda_at_entry_mm REAL, "
            "realized_moic REAL, realized_irr REAL, hold_years REAL, "
            "payer_mix TEXT)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO public_deals "
            "(source_id, deal_name, year, buyer, seller, source, "
            " ev_mm, ebitda_at_entry_mm, realized_moic, realized_irr, "
            " hold_years, payer_mix) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("FULL", "Full Acute Sys", 2018, "BuyerA", "SellerA",
                 "seed", 800.0, 100.0, 2.4, 0.18, 5.0,
                 json.dumps({"medicare": 0.4, "medicaid": 0.2,
                             "commercial": 0.4})),
                ("SPARSE", "Sparse Manual", 2019, None, None,
                 "manual", None, None, None, None, None, None),
            ],
        )
        con.commit()


class DealScorerBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "deal_scorer.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "deal_scorer.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "deal_scorer.py should reference PortfolioStore",
        )

    def test_score_corpus_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a 2-row fixture (one fully-populated
        seed-source deal, one sparse manual deal) produces
        DealQualityScore results sorted by total_score
        descending. The seed deal must score higher than the
        sparse manual one. Confirms the row-factory contract
        (column-name access in scoring helpers) survives."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            scores = score_corpus(db_path)
            self.assertEqual(len(scores), 2)
            for s in scores:
                self.assertIsInstance(s, DealQualityScore)
            # Sorted by total_score descending — full deal first.
            self.assertEqual(scores[0].source_id, "FULL")
            self.assertEqual(scores[1].source_id, "SPARSE")
            # Full deal should clearly outscore sparse one.
            self.assertGreater(
                scores[0].total_score,
                scores[1].total_score,
            )


if __name__ == "__main__":
    unittest.main()
