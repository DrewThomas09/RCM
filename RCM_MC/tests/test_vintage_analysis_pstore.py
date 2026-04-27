"""Regression test for the dispatcher-bypass cleanup at
data_public/vintage_analysis.py (campaign target 4E, loop 82).

Pre-loop-82 _load_corpus called sqlite3.connect(corpus_db_path)
directly, set row_factory=Row by hand, and called con.close()
manually. After the cleanup, _load_corpus routes through
``PortfolioStore(corpus_db_path).connect()`` as a context
manager and the redundant import sqlite3 is dropped.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: get_all_vintages and macro_cycle_summary run
    end-to-end against a small public_deals fixture spanning
    two macro cycles (aca_era 2018 + covid_era 2021) and
    return the expected by-year and by-cycle aggregations.
    Confirms the row-factory contract (column-name access via
    dict(r)) survives the migration.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.vintage_analysis import (
    VintageStats,
    get_all_vintages,
    macro_cycle_summary,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "vintage_analysis.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up public_deals with 4 fixture rows: 2 in 2018
    (aca_era cycle), 2 in 2021 (covid_era cycle)."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "deal_name TEXT, year INTEGER, "
            "ev_mm REAL, ebitda_at_entry_mm REAL, hold_years REAL, "
            "realized_moic REAL, realized_irr REAL, buyer TEXT)"
        )
        con.executemany(
            "INSERT INTO public_deals "
            "(deal_name, year, ev_mm, ebitda_at_entry_mm, hold_years, "
            " realized_moic, realized_irr, buyer) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACA-One", 2018, 500.0, 60.0, 5.0, 2.0, 0.15, "B1"),
                ("ACA-Two", 2018, 700.0, 80.0, 4.0, 2.4, 0.18, "B2"),
                ("Covid-One", 2021, 900.0, 100.0, 4.0, 2.8, 0.22, "B3"),
                ("Covid-Two", 2021, 1100.0, 130.0, 3.5, 3.2, 0.25, "B4"),
            ],
        )
        con.commit()


class VintageAnalysisBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "vintage_analysis.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "vintage_analysis.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "vintage_analysis.py should reference PortfolioStore",
        )

    def test_get_all_vintages_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: 2 vintages × 2 deals = 2 VintageStats
        entries, each with n_deals=2. Confirms the row-factory
        contract (dict(r) access) survives."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            vintages = get_all_vintages(db_path)
            self.assertIsInstance(vintages, dict)
            self.assertIn(2018, vintages)
            self.assertIn(2021, vintages)
            self.assertEqual(vintages[2018].n_deals, 2)
            self.assertEqual(vintages[2021].n_deals, 2)
            for vs in vintages.values():
                self.assertIsInstance(vs, VintageStats)

    def test_macro_cycle_summary_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: 2018 deals → aca_era, 2021 deals →
        covid_era. macro_cycle_summary aggregates to two
        cycle-keyed entries, each n_deals=2."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            cycles = macro_cycle_summary(db_path)
            self.assertIn("aca_era", cycles)
            self.assertIn("covid_era", cycles)
            self.assertEqual(cycles["aca_era"].n_deals, 2)
            self.assertEqual(cycles["covid_era"].n_deals, 2)


if __name__ == "__main__":
    unittest.main()
