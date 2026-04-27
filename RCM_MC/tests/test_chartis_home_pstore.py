"""Regression test for the dispatcher-bypass cleanup at
ui/chartis/home_page.py (campaign target 4E, loop 77).

Pre-loop-77 the chartis home page had 4 internal sqlite3.connect
sites — one per defensive panel (_alerts, _health_distribution,
_deadlines, _kpi_strip). Each set its own row_factory and called
con.close() manually. After the cleanup, every site routes
through ``PortfolioStore(db_path).connect()`` — the redundant
row_factory assignments are gone (PortfolioStore provides Row),
manual closes are gone (with-block handles them), and the
per-panel try/except contract for graceful degradation is
preserved verbatim.

Asserts:
  - Migration: the module no longer contains ``sqlite3.connect(``
    or ``import sqlite3`` (no lazy-local form either).
  - PortfolioStore is imported.
  - Behavioural: each of the 4 panel helpers runs end-to-end
    against a fresh PortfolioStore-init DB and returns a string
    (the empty-state branch in each case). Confirms the
    per-panel defensive contract still holds through the new
    seam — a missing table or empty result must produce an empty
    panel, never raise.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.chartis.home_page import (
    _alerts,
    _deadlines,
    _health_distribution,
    _kpi_strip,
)


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "chartis" / "home_page.py"
)


class _FakeStore:
    """Stand-in for the portfolio store passed to _kpi_strip — only
    needs a list_deals() method that returns something truthy.
    Returning an empty DataFrame-like list exercises the empty
    portfolio branch of the helper."""

    def list_deals(self):
        return []


class ChartisHomeBypassTests(unittest.TestCase):
    def test_module_no_longer_calls_sqlite3_connect(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "sqlite3.connect(", text,
            "chartis/home_page.py contains sqlite3.connect( — "
            "the PortfolioStore bypass has regressed",
        )
        self.assertNotIn(
            "import sqlite3", text,
            "chartis/home_page.py still imports sqlite3 somewhere",
        )

    def test_module_imports_PortfolioStore(self) -> None:
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "PortfolioStore", text,
            "chartis/home_page.py should reference PortfolioStore",
        )

    def test_panels_render_through_PortfolioStore(self) -> None:
        """Each panel helper must produce a string against a fresh
        PortfolioStore-init DB. The relevant tables (alerts,
        deal_health_scores, deal_deadlines) don't exist yet on a
        fresh portfolio store, so each helper hits its except
        branch and returns the empty-state placeholder. This
        confirms the per-panel try/except defensive contract still
        holds through the new with-block seam."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            PortfolioStore(db_path)

            alerts_html = _alerts(db_path)
            self.assertIsInstance(alerts_html, str)
            self.assertIn("No active alerts", alerts_html)

            health_html = _health_distribution(db_path)
            self.assertIsInstance(health_html, str)
            self.assertIn("No health scores", health_html)

            deadlines_html = _deadlines(db_path)
            self.assertIsInstance(deadlines_html, str)
            self.assertIn("No deadlines", deadlines_html)

            kpi_html = _kpi_strip(_FakeStore(), db_path)
            self.assertIsInstance(kpi_html, str)
            # n_alerts = 0 is the expected fallback when alerts
            # table is missing, so the rendered KPI string is
            # non-empty regardless.
            self.assertGreater(len(kpi_html), 0)


if __name__ == "__main__":
    unittest.main()
