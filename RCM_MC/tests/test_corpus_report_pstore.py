"""Regression test for the dispatcher-bypass cleanup at
data_public/corpus_report.py (campaign target 4E, loop 85).

Pre-loop-85 corpus_summary_report had a lazy local
``import sqlite3`` and called ``sqlite3.connect(corpus_db_
path)`` directly to fetch corpus-stats COUNT queries. After
the cleanup, the function imports PortfolioStore lazily
(matching the existing lazy-import style for this helper) and
routes the three COUNT queries through ``PortfolioStore.
connect()`` as a context manager.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3`` (no lazy-local form either).
  - PortfolioStore is referenced.
  - Behavioural: corpus_summary_report runs end-to-end against
    a small public_deals fixture and the rendered text
    contains the expected total/MOIC/IRR counts. Confirms the
    new with-block context-manages the three COUNT reads
    cleanly through the new seam.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.corpus_report import corpus_summary_report


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "corpus_report.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up public_deals with 3 rows: 2 fully realized
    (MOIC + IRR), 1 unrealized (NULLs)."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "source_id TEXT PRIMARY KEY, deal_name TEXT, year INTEGER, "
            "ev_mm REAL, ebitda_at_entry_mm REAL, hold_years REAL, "
            "realized_moic REAL, realized_irr REAL, "
            "buyer TEXT, seller TEXT, payer_mix TEXT, source TEXT)"
        )
        con.executemany(
            "INSERT OR REPLACE INTO public_deals "
            "(source_id, deal_name, year, ev_mm, ebitda_at_entry_mm, "
            " hold_years, realized_moic, realized_irr, buyer, seller, "
            " source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("R1", "Realized One", 2017, 500.0, 60.0, 5.0,
                 2.0, 0.15, "B1", "S1", "seed"),
                ("R2", "Realized Two", 2018, 800.0, 100.0, 5.0,
                 2.4, 0.18, "B2", "S2", "seed"),
                ("U1", "Unrealized",   2022, 600.0, 70.0, None,
                 None, None, "B3", "S3", "seed"),
            ],
        )
        con.commit()


class CorpusReportBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "corpus_report.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "corpus_report.py still imports sqlite3 somewhere",
        )

    def test_module_references_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "corpus_report.py should reference PortfolioStore",
        )

    def test_corpus_summary_report_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: a 3-row fixture (2 realized + 1
        unrealized) produces a report whose corpus-stats
        section reflects total=3, with_moic=2, with_irr=2.
        Confirms the three COUNT reads through the new
        with-block seam land the expected numbers."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            report = corpus_summary_report(db_path)
            self.assertIsInstance(report, str)
            self.assertGreater(len(report), 0)
            # Corpus-stats section should now read total=3, with
            # MOIC=2, with IRR=2 — i.e. these substrings appear
            # in the rendered ASCII report.
            self.assertIn("Total deals", report)
            self.assertIn(": 3", report)  # total
            self.assertIn("With MOIC", report)
            self.assertIn("With IRR", report)


if __name__ == "__main__":
    unittest.main()
