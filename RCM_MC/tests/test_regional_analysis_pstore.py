"""Regression test for the dispatcher-bypass cleanup at
data_public/regional_analysis.py (campaign target 4E, loop 83).

Pre-loop-83 _load_corpus called sqlite3.connect(corpus_db_path)
directly, set row_factory=Row by hand, and called con.close()
manually. After the cleanup, _load_corpus routes through
``PortfolioStore(corpus_db_path).connect()`` as a context
manager and the redundant import sqlite3 is dropped.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3``.
  - PortfolioStore is imported.
  - Behavioural: get_all_regions runs end-to-end against a
    public_deals fixture spanning two regions (southeast +
    midwest) and returns the expected by-region aggregations.
    Confirms the row-factory contract (column-name access via
    dict(r) plus json.loads(payer_mix)) survives the
    migration.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.regional_analysis import (
    RegionStats,
    get_all_regions,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "data_public" / "regional_analysis.py"
)


def _seed_corpus(db_path: str) -> None:
    """Stand up public_deals with 4 fixture rows: 2 named to
    classify as southeast (atlanta / nashville), 2 to classify
    as midwest (chicago / cleveland)."""
    with PortfolioStore(db_path).connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS public_deals ("
            "deal_name TEXT, year INTEGER, buyer TEXT, seller TEXT, "
            "notes TEXT, ev_mm REAL, ebitda_at_entry_mm REAL, "
            "hold_years REAL, realized_moic REAL, realized_irr REAL, "
            "payer_mix TEXT)"
        )
        con.executemany(
            "INSERT INTO public_deals "
            "(deal_name, year, buyer, seller, notes, ev_mm, "
            " ebitda_at_entry_mm, hold_years, realized_moic, "
            " realized_irr, payer_mix) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("Atlanta General", 2018, "B1", "S1", "",
                 500.0, 60.0, 5.0, 2.0, 0.15,
                 json.dumps({"medicare": 0.4, "commercial": 0.4,
                             "medicaid": 0.2})),
                ("Nashville Health", 2019, "B2", "S2", "",
                 700.0, 80.0, 4.0, 2.4, 0.18,
                 json.dumps({"medicare": 0.5, "commercial": 0.3,
                             "medicaid": 0.2})),
                ("Chicago Acute", 2018, "B3", "S3", "",
                 800.0, 100.0, 5.0, 2.2, 0.16,
                 json.dumps({"medicare": 0.4, "commercial": 0.4,
                             "medicaid": 0.2})),
                ("Cleveland Sys", 2020, "B4", "S4", "",
                 900.0, 110.0, 4.5, 2.6, 0.20,
                 json.dumps({"medicare": 0.5, "commercial": 0.3,
                             "medicaid": 0.2})),
            ],
        )
        con.commit()


class RegionalAnalysisBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "regional_analysis.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "regional_analysis.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "regional_analysis.py should reference PortfolioStore",
        )

    def test_get_all_regions_runs_through_PortfolioStore(self) -> None:
        """Behavioural pin: 2 southeast deals + 2 midwest deals
        produce a dict with 'southeast' and 'midwest' keys, each
        n_deals=2. Confirms the row-factory + json.loads
        unpacking survives."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "corpus.db")
            _seed_corpus(db_path)
            regions = get_all_regions(db_path)
            self.assertIsInstance(regions, dict)
            self.assertIn("southeast", regions)
            self.assertIn("midwest", regions)
            self.assertEqual(regions["southeast"].n_deals, 2)
            self.assertEqual(regions["midwest"].n_deals, 2)
            for vs in regions.values():
                self.assertIsInstance(vs, RegionStats)


if __name__ == "__main__":
    unittest.main()
