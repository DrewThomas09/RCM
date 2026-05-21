"""Pins the editorial section headings on the command center page.

PR #3 of the two-view Command Center work. The page used to read as a
flat stack of dashboard cards; this PR adds editorial movement anchors
(``ck_eyebrow`` — caps eyebrow + thin teal rule) that group the page
into named memo sections. Copy-only: no card structure or data changed.

Contract pinned here:
  * "Market Intelligence" always anchors the universe view.
  * "Your Book" anchors the partner's pipeline/deals movement, and
    appears only when there is a book (a deal or tracked pipeline) —
    a brand-new user with an empty portfolio does not see it.
  * The anchors use the editorial ``ck-eyebrow`` chrome, not a
    dashboard-marketing card.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.command_center import render_command_center


def _frame(n: int = 40, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "state": rng.choice(["CA", "TX", "NY", "FL", "OH", "WA"], n),
        "beds": rng.integers(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e6, 3e8, n),
        "operating_expenses": rng.uniform(1e6, 3e8, n),
    })


class CommandCenterHeadingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "p.db")
        store = PortfolioStore(self.db_path)
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS deals ("
                "deal_id TEXT PRIMARY KEY, name TEXT, "
                "profile_json TEXT, created_at TEXT, archived_at TEXT)"
            )
            con.commit()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _add_deal(self) -> None:
        store = PortfolioStore(self.db_path)
        with store.connect() as con:
            con.execute(
                "INSERT INTO deals(deal_id,name,profile_json,created_at) "
                "VALUES('d1','Test Deal','{}','2026-01-01')"
            )
            con.commit()

    def test_market_intelligence_anchor_always_present(self) -> None:
        html = render_command_center(_frame(), self.db_path)
        self.assertIn("Market Intelligence", html)
        self.assertIn("ck-eyebrow", html)  # editorial anchor chrome

    def test_your_book_hidden_for_empty_portfolio(self) -> None:
        html = render_command_center(_frame(), self.db_path)
        self.assertNotIn("Your Book", html)

    def test_your_book_shown_when_book_exists(self) -> None:
        self._add_deal()
        html = render_command_center(_frame(), self.db_path)
        self.assertIn("Your Book", html)


if __name__ == "__main__":
    unittest.main()
