"""Report-0268: deal_id ingestion-boundary validation (defense-in-depth).

deal_id is partner-supplied and reaches URL path segments, filesystem
export paths, and (historically) HTML/JS sinks. Every sink is now
individually neutralized; this pins the durable class-closer — a safe-slug
validator at the single creation chokepoint (upsert_deal / clone_deal,
INSERT path only), with existing rows grandfathered.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore, is_valid_deal_id


class TestIsValidDealId(unittest.TestCase):
    def test_accepts_real_world_slugs(self):
        for good in ("DEAL_001", "acme_health_2026", "010001",
                     "ccf-2026", "extra_001", "a.b.c", "X"):
            self.assertTrue(is_valid_deal_id(good), good)

    def test_rejects_dangerous_and_empty(self):
        for bad in ("", "   ", "../escaped", "a/b", "a\\b",
                    "x');alert(1)//", "<img src=x>", 'a"b',
                    "a b", "a\x00b", "x" * 129):
            self.assertFalse(is_valid_deal_id(bad), bad)


class TestUpsertValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "p.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_deal_with_bad_id_rejected(self):
        with self.assertRaises(ValueError):
            self.store.upsert_deal("../evil", name="x")
        with self.assertRaises(ValueError):
            self.store.upsert_deal("x');alert(1)//", name="x")

    def test_new_deal_with_good_id_ok(self):
        self.store.upsert_deal("acme_2026", name="Acme")
        df = self.store.list_deals()
        self.assertIn("acme_2026", set(df.get("deal_id", [])))

    def test_existing_legacy_id_grandfathered(self):
        # Simulate a legacy DB row with an id the validator would now
        # reject, then confirm upsert_deal (called by owner/tag/note
        # refreshes) still works on it — validation only guards NEW rows.
        self.store.init_db()
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, profile_json) "
                "VALUES (?, ?, ?, ?)",
                ("legacy/odd id", "Legacy", "2026-01-01T00:00:00+00:00", "{}"),
            )
            con.commit()
        # Must NOT raise — the row already exists.
        self.store.upsert_deal("legacy/odd id", name="Legacy Renamed")
        with self.store.connect() as con:
            row = con.execute(
                "SELECT name FROM deals WHERE deal_id=?", ("legacy/odd id",)
            ).fetchone()
        self.assertEqual(row["name"], "Legacy Renamed")

    def test_clone_rejects_bad_new_id(self):
        self.store.upsert_deal("src_deal", name="Source")
        with self.assertRaises(ValueError):
            self.store.clone_deal("src_deal", "../evil")
        # A good new id clones fine.
        self.assertTrue(self.store.clone_deal("src_deal", "src_deal_copy"))


if __name__ == "__main__":
    unittest.main()
