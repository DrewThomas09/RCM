"""Regression test for the dispatcher-bypass cleanup at
data_public/comparables.py (campaign target 4E, loop 80).

Pre-loop-80 _load_corpus called sqlite3.connect(corpus_db_path)
directly, set row_factory=Row by hand, and called con.close()
manually. After the cleanup, _load_corpus routes through
``PortfolioStore(corpus_db_path).connect()`` as a context
manager and the redundant import sqlite3 is dropped.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: find_comparables runs end-to-end against a
    tiny public_deals fixture stood up via PortfolioStore,
    returns the expected ComparableDeal results sorted by
    similarity score, and confirms the row-factory contract
    (column-name access in _extract_features) survives.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.comparables import (
    ComparableDeal,
    find_comparables,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "comparables.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up a public_deals table with 3 fixture rows
    spanning EV scale and payer mix."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "source_id TEXT PRIMARY KEY, deal_name TEXT, year INTEGER, "
            "ev_mm REAL, ebitda_at_entry_mm REAL, "
            "realized_moic REAL, realized_irr REAL, hold_years REAL, "
            "buyer TEXT, payer_mix TEXT)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO public_deals "
            "(source_id, deal_name, year, ev_mm, ebitda_at_entry_mm, "
            " realized_moic, realized_irr, hold_years, buyer, payer_mix) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("S1", "Small Acute", 2018, 200.0, 25.0, 1.8, 0.12, 4.0,
                 "BuyerA", json.dumps({"medicare": 0.5, "medicaid": 0.3,
                                        "commercial": 0.2})),
                ("S2", "Mid Acute",  2019, 800.0, 100.0, 2.4, 0.18, 5.0,
                 "BuyerB", json.dumps({"medicare": 0.4, "medicaid": 0.2,
                                        "commercial": 0.4})),
                ("S3", "Large Sys",  2020, 4000.0, 500.0, 3.0, 0.22, 6.0,
                 "BuyerC", json.dumps({"medicare": 0.3, "medicaid": 0.2,
                                        "commercial": 0.5})),
            ],
        )
        con.commit()


class ComparablesBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "comparables.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "comparables.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "comparables.py should reference PortfolioStore",
        )

    def test_find_comparables_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a 3-row public_deals fixture plus a
        query deal sized like S1 (small acute) returns
        comparables sorted by similarity score, with S1 itself
        ranking highest. Confirms the row-factory contract
        (column-name access in _extract_features and the
        json.loads(payer_mix) flow) survives the migration."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            query = {
                "source_id": "QUERY",
                "ev_mm": 220.0,
                "ebitda_at_entry_mm": 28.0,
                "hold_years": 4.0,
                "payer_mix": {"medicare": 0.5, "medicaid": 0.3,
                              "commercial": 0.2},
            }
            comps = find_comparables(
                query, db_path, n=3, min_score=0.0, exclude_self=True,
            )
            self.assertIsInstance(comps, list)
            self.assertGreaterEqual(len(comps), 1)
            for c in comps:
                self.assertIsInstance(c, ComparableDeal)
            # S1 is the closest fixture — should top the ranking.
            self.assertEqual(comps[0].source_id, "S1")
            # Scores should be ordered descending.
            scores = [c.similarity_score for c in comps]
            self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
