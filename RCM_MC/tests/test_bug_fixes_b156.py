"""Regression test for B156: latest_per_deal order stability on ties."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import latest_per_deal


class TestLatestPerDealStableOnTies(unittest.TestCase):
    def test_same_timestamp_picks_highest_snapshot_id(self):
        """If two snapshots share created_at, the one with the larger
        snapshot_id (more recently inserted) must always win —
        deterministically, across repeated calls."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            store.init_db()
            # Ensure snapshot table
            from rcm_mc.portfolio.portfolio_snapshots import _ensure_snapshot_table
            _ensure_snapshot_table(store)
            # Insert two snapshots for same deal with identical created_at
            ts = "2026-04-15T10:00:00+00:00"
            with store.connect() as con:
                store.upsert_deal("ccf")
                con.execute(
                    "INSERT INTO deal_snapshots "
                    "(deal_id, stage, created_at, notes) "
                    "VALUES (?, ?, ?, ?)",
                    ("ccf", "loi", ts, "first"),
                )
                con.execute(
                    "INSERT INTO deal_snapshots "
                    "(deal_id, stage, created_at, notes) "
                    "VALUES (?, ?, ?, ?)",
                    ("ccf", "hold", ts, "second"),
                )
                con.commit()
            # Repeated calls — always pick the latter (snapshot_id=2)
            for _ in range(5):
                df = latest_per_deal(store)
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["stage"], "hold")
                self.assertEqual(df.iloc[0]["notes"], "second")


if __name__ == "__main__":
    unittest.main()
