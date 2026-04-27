"""Regression test for the dispatcher-bypass cleanup at
ui/provenance.py (campaign target 4E, loop 78).

Pre-loop-78 build_provenance_profile had a lazy local
``import sqlite3`` and called ``sqlite3.connect(db_path)``
directly to load seller data + calibrations. After the
cleanup, the function imports PortfolioStore lazily (matching
the existing lazy-import style for this helper) and routes
through ``PortfolioStore.connect()`` as a context manager.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3`` (lazy local form too).
  - PortfolioStore is referenced.
  - Behavioural: build_provenance_profile returns a non-empty
    dict when called with db_path=None (no DB path: the seller
    data branch is skipped, profile is built from HCRIS + ML
    predictions only — existing contract).
  - Behavioural: build_provenance_profile runs cleanly through
    the new seam against a fresh PortfolioStore-init DB. The
    seller_data lookup falls through both queries (tables don't
    exist on a fresh store) and the function still returns the
    HCRIS/ML-driven profile.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.provenance import build_provenance_profile


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "provenance.py"
)


class ProvenanceBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "provenance.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "provenance.py still imports sqlite3 somewhere",
        )

    def test_module_references_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "provenance.py should reference PortfolioStore",
        )

    def test_no_db_path_skips_seller_data_branch(self) -> None:
        """Existing contract: db_path=None means no data room is
        configured, so the seller_data + calibrations branch is
        skipped entirely. Profile still builds from HCRIS + ML."""
        profile = build_provenance_profile(
            ccn="010001",
            hcris_profile={"beds": 200, "net_patient_revenue": 1.0e8},
            ml_predictions={},
            db_path=None,
        )
        self.assertIsInstance(profile, dict)
        self.assertGreater(len(profile), 0)

    def test_fresh_db_falls_through_PortfolioStore_seam(self) -> None:
        """Behavioural pin: with a fresh PortfolioStore-init DB
        (no data_room tables yet), the seller_data + calibrations
        loop hits the except branch silently. Function still
        returns the HCRIS/ML-driven profile through the new seam
        without raising."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            PortfolioStore(db_path)
            profile = build_provenance_profile(
                ccn="010001",
                hcris_profile={"beds": 200, "net_patient_revenue": 1.0e8},
                ml_predictions={},
                db_path=db_path,
            )
            self.assertIsInstance(profile, dict)
            self.assertGreater(len(profile), 0)


if __name__ == "__main__":
    unittest.main()
