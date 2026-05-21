"""Pins the pure-data extraction at ui/command_center.py.

PR #2 of the two-view Command Center work split the page's
number-crunching out of ``render_command_center`` into a pure
``build_command_center_model`` so the same model can feed multiple
compositions without re-deriving any numbers. These tests pin the
extraction's two load-bearing contracts:

  * the model carries every computed value the page needs, and
  * the refactor is presentation-neutral — the input frame is not
    mutated, and the derived market-highlight tables match what the
    page used to compute inline.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.command_center import (
    CommandCenterModel,
    build_command_center_model,
)


def _frame(n: int = 40, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "state": rng.choice(["CA", "TX", "NY", "FL", "OH", "WA"], n),
        "beds": rng.integers(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e6, 3e8, n),
        "operating_expenses": rng.uniform(1e6, 3e8, n),
    })


class BuildCommandCenterModelTests(unittest.TestCase):
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

    def test_returns_model_with_universe_stats(self) -> None:
        df = _frame()
        m = build_command_center_model(df, self.db_path)
        self.assertIsInstance(m, CommandCenterModel)
        self.assertEqual(m.n_hospitals, len(df))
        self.assertEqual(m.total_beds, int(df["beds"].fillna(0).sum()))
        self.assertAlmostEqual(
            m.total_revenue, float(df["net_patient_revenue"].fillna(0).sum()))
        self.assertEqual(m.n_states, 50)

    def test_empty_db_means_no_portfolio_or_pipeline(self) -> None:
        m = build_command_center_model(_frame(), self.db_path)
        self.assertEqual(m.deals, [])
        self.assertFalse(m.has_portfolio)
        self.assertFalse(m.has_pipeline)

    def test_input_frame_is_not_mutated(self) -> None:
        # The page attaches operating_margin / _dq_ok_margin to a COPY —
        # the caller's frame must come back untouched.
        df = _frame()
        before = list(df.columns)
        build_command_center_model(df, self.db_path)
        self.assertEqual(list(df.columns), before)
        self.assertNotIn("operating_margin", df.columns)
        self.assertNotIn("_dq_ok_margin", df.columns)

    def test_augmented_frame_carries_margin_columns(self) -> None:
        m = build_command_center_model(_frame(), self.db_path)
        self.assertIn("operating_margin", m.hcris_df.columns)
        self.assertIn("_dq_ok_margin", m.hcris_df.columns)

    def test_market_tables_match_inline_derivation(self) -> None:
        # top_states / size_data must equal what render computed inline
        # before the extraction, so the page is byte-identical.
        m = build_command_center_model(_frame(), self.db_path)
        aug = m.hcris_df
        expected_top = aug.groupby("state").agg(
            n=("ccn", "count"),
            med_margin=("operating_margin", "median"),
            total_rev=("net_patient_revenue", "sum"),
        ).sort_values("total_rev", ascending=False).head(8)
        pd.testing.assert_frame_equal(m.top_states, expected_top)

        beds = aug["beds"].dropna()
        self.assertEqual(m.size_data, {
            "< 50 beds": int((beds < 50).sum()),
            "50-99": int(((beds >= 50) & (beds < 100)).sum()),
            "100-249": int(((beds >= 100) & (beds < 250)).sum()),
            "250-499": int(((beds >= 250) & (beds < 500)).sum()),
            "500+": int((beds >= 500).sum()),
        })


if __name__ == "__main__":
    unittest.main()
