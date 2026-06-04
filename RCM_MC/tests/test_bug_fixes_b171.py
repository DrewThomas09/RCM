"""b171 — delete_deal raised IntegrityError on deals with snapshots/actuals.

``PortfolioStore.delete_deal`` clears a hard-coded list of child tables and
then runs ``DELETE FROM deals``. Three child tables that FK ``deals(deal_id)``
*without* ``ON DELETE CASCADE`` were missing from that list:

  - ``deal_snapshots``
  - ``quarterly_actuals``
  - ``initiative_actuals``

So any deal that had a snapshot, a quarter of actuals, or an initiative actual
— i.e. essentially every real deal, and every KKR demo deal — could not be
deleted: the final ``DELETE FROM deals`` raised
``sqlite3.IntegrityError: FOREIGN KEY constraint failed``. The demo's new
unload action surfaced it (load the demo, try to clear it → crash).

Fix: add the three tables to the cascade-cleanup list. This test seeds a deal
with all three child kinds and asserts the delete now succeeds and leaves no
orphans.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class TestDeleteDealClearsSnapshotsAndActuals(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_delete_deal_with_snapshot_and_actuals(self):
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
        did = "dx"
        self.store.upsert_deal(did, name="Deal X")
        # A snapshot (deal_snapshots) + a quarter of actuals (quarterly_actuals)
        # — the two child kinds that used to block deletion.
        run_dir = os.path.join(self.tmp.name, "run")
        os.makedirs(run_dir, exist_ok=True)
        try:
            register_snapshot(self.store, did, "hold", run_dir=run_dir,
                              notes="t")
        except Exception:
            pass  # snapshot is best-effort; the actuals row alone reproduces it
        record_quarterly_actuals(self.store, did, "2026Q1",
                                 actuals={"ebitda": 1.0}, plan={"ebitda": 1.0})
        # Used to raise sqlite3.IntegrityError.
        self.assertTrue(self.store.delete_deal(did))
        with self.store.connect() as con:
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM deals WHERE deal_id=?",
                            (did,)).fetchone()[0], 0)
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM quarterly_actuals "
                            "WHERE deal_id=?", (did,)).fetchone()[0], 0)
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM deal_snapshots "
                            "WHERE deal_id=?", (did,)).fetchone()[0], 0)

    def test_unload_demo_round_trip(self):
        # Seed the full KKR demo, then unload it: every deal + child row gone.
        from rcm_mc.demo.kkr_demo import (
            seed_kkr_demo, unload_kkr_demo, KKR_DEMO_DEALS,
        )
        seed_kkr_demo(self.store, run_dir=os.path.join(self.tmp.name, "r"))
        removed = unload_kkr_demo(self.store)
        self.assertEqual(removed, len(KKR_DEMO_DEALS))
        ids = [s["id"] for s in KKR_DEMO_DEALS]
        placeholders = ",".join("?" * len(ids))
        with self.store.connect() as con:
            for tbl in ("deals", "deal_snapshots", "quarterly_actuals",
                        "deal_notes", "deal_deadlines", "deal_overrides",
                        "alert_acks", "analysis_runs"):
                n = con.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE deal_id IN ({placeholders})",
                    ids).fetchone()[0]
                self.assertEqual(n, 0, f"{tbl} left {n} orphan rows after unload")


if __name__ == "__main__":
    unittest.main()
