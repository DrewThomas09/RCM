"""Regression tests for the seeder hardening pass (Report-0264).

- MR1061: --overwrite refuses to clobber deals that do not trace to
  seeder provenance (the /data/ path heuristic alone lets a partner's
  real ~/portfolio.db through).
- MR1062: seed_random is actually consumed (it was documented as
  producing byte-for-byte identical output but never seeded any RNG).
- MR1063: the overwrite cleanup is transactional, covers
  covenant_metrics + quarterly_actuals (previously missed — covenant
  rows duplicated on every re-seed), and only tolerates
  "no such table".
"""
from __future__ import annotations

import os
import random
import tempfile
import unittest

from rcm_mc.dev.seed import SeederRefuseError, seed_demo_db
from rcm_mc.portfolio.store import PortfolioStore

_FAST = dict(deal_count=7, snapshot_quarters=2, write_export_files=False)


class TestOverwriteProvenanceGuard(unittest.TestCase):
    def test_overwrite_refuses_non_seed_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "demo.db")
            seed_demo_db(db, **_FAST)
            # A deal the seeder did not create — no seed-stamped
            # stage-history row.
            store = PortfolioStore(db)
            store.upsert_deal("partners_real_deal")
            with self.assertRaises(SeederRefuseError) as ctx:
                seed_demo_db(db, overwrite=True, **_FAST)
            self.assertIn("provenance", str(ctx.exception))
            # The refusal must leave the DB untouched.
            with store.connect() as con:
                self.assertIsNotNone(con.execute(
                    "SELECT 1 FROM deals WHERE deal_id='partners_real_deal'"
                ).fetchone())

    def test_force_overrides_provenance_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "demo.db")
            seed_demo_db(db, **_FAST)
            store = PortfolioStore(db)
            store.upsert_deal("partners_real_deal")
            result = seed_demo_db(db, overwrite=True, force=True, **_FAST)
            self.assertGreater(result.deals_inserted, 0)
            with store.connect() as con:
                self.assertIsNone(con.execute(
                    "SELECT 1 FROM deals WHERE deal_id='partners_real_deal'"
                ).fetchone())

    def test_pure_seed_db_overwrites_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "demo.db")
            seed_demo_db(db, **_FAST)
            result = seed_demo_db(db, overwrite=True, **_FAST)
            self.assertGreater(result.deals_inserted, 0)


class TestOverwriteCleanupCoverage(unittest.TestCase):
    def test_no_covenant_duplication_across_reseeds(self):
        # MR1063 regression: covenant_metrics was missing from the
        # cleanup list, so every re-seed doubled the covenant rows.
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "demo.db")
            seed_demo_db(db, **_FAST)
            store = PortfolioStore(db)
            with store.connect() as con:
                first = con.execute(
                    "SELECT COUNT(*) c FROM covenant_metrics").fetchone()["c"]
            seed_demo_db(db, overwrite=True, **_FAST)
            with store.connect() as con:
                second = con.execute(
                    "SELECT COUNT(*) c FROM covenant_metrics").fetchone()["c"]
            self.assertGreater(first, 0)
            self.assertEqual(first, second)


class TestSeedRandomConsumed(unittest.TestCase):
    def test_same_seed_same_rng_stream(self):
        # MR1062: the pipeline must reseed the global RNGs from
        # seed_random, so the next draw after two identical runs is
        # identical — regardless of what the suite did to the RNG
        # beforehand.
        with tempfile.TemporaryDirectory() as tmp:
            random.seed(999)
            seed_demo_db(os.path.join(tmp, "a.db"), seed_random=123, **_FAST)
            draw_a = random.random()
            random.seed(777)
            seed_demo_db(os.path.join(tmp, "b.db"), seed_random=123, **_FAST)
            draw_b = random.random()
            self.assertEqual(draw_a, draw_b)


if __name__ == "__main__":
    unittest.main()
