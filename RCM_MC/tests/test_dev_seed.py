"""Unit tests for the demo database seeder.

Per SEEDER_PROPOSAL.md §C5 (resolved 2026-04-26): both unit and
integration tests, separate commits. This is the unit half — fast,
no HTTP server, asserts the seeded DB has the expected shape per the
proposal's §4 curation.

Integration tests (boots a server against the seeded DB and verifies
the rendered HTML contains marquee markers) live in
``test_dev_seed_integration.py`` and run separately.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.dev.seed import (
    SeederRefuseError,
    SeedResult,
    seed_demo_db,
    verify_seeded_db,
)
from rcm_mc.portfolio.portfolio_snapshots import latest_per_deal
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.rcm.initiative_tracking import (
    cross_portfolio_initiative_variance,
)


class TestSeederGuards(unittest.TestCase):
    """Production-target + overwrite guards."""

    def test_refuses_data_path_default(self) -> None:
        with self.assertRaises(SeederRefuseError):
            seed_demo_db("/data/foo.db")

    def test_refuses_seekingchartis_db(self) -> None:
        # Path doesn't have to exist for the guard to fire — the
        # filename match is what triggers it.
        with self.assertRaises(SeederRefuseError):
            seed_demo_db("seekingchartis.db")

    def test_force_flag_overrides_guard(self) -> None:
        # We don't actually want to seed /data/foo.db, but the guard
        # specifically should stop refusing when force=True.
        with tempfile.TemporaryDirectory() as t:
            # Pick a path that LOOKS like prod but is in tmp
            db = os.path.join(t, "seekingchartis.db")
            # Without force → refuses
            with self.assertRaises(SeederRefuseError):
                seed_demo_db(db)
            # With force → proceeds
            r = seed_demo_db(db, force=True)
            self.assertGreater(r.deals_inserted, 0)

    def test_refuses_non_empty_db_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, "demo.db")
            seed_demo_db(db)  # first seed succeeds
            # Re-seed without overwrite refuses
            with self.assertRaises(SeederRefuseError):
                seed_demo_db(db)

    def test_overwrite_flag_clears_and_reseeds(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, "demo.db")
            r1 = seed_demo_db(db)
            r2 = seed_demo_db(db, overwrite=True)
            # Same shape both times — determinism
            self.assertEqual(r1.deals_inserted, r2.deals_inserted)
            self.assertEqual(r1.snapshots_inserted, r2.snapshots_inserted)


class TestSeederShape(unittest.TestCase):
    """Asserts the seeded DB matches SEEDER_PROPOSAL §4 curation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.mkdtemp()
        cls.db = os.path.join(cls.tmp, "demo.db")
        cls.base = Path(cls.tmp) / "exports"
        cls.result = seed_demo_db(cls.db, base_dir=cls.base)
        cls.store = PortfolioStore(cls.db)

    def test_seven_curated_deals_inserted(self) -> None:
        self.assertEqual(self.result.deals_inserted, 7)

    def test_funnel_distribution_matches_proposal(self) -> None:
        df = latest_per_deal(self.store)
        stages = df.groupby("stage").size().to_dict()
        # Per proposal §4.2: 3 hold + 1 exit + 1 spa + 1 loi + 1 ioi
        self.assertEqual(stages.get("hold"), 3)
        self.assertEqual(stages.get("exit"), 1)
        self.assertEqual(stages.get("spa"), 1)
        self.assertEqual(stages.get("loi"), 1)
        self.assertEqual(stages.get("ioi"), 1)

    def test_covenant_trajectories_landed(self) -> None:
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT deal_id, MIN(covenant_leverage) AS lo, "
                "MAX(covenant_leverage) AS hi FROM deal_snapshots "
                "WHERE covenant_leverage IS NOT NULL GROUP BY deal_id"
            ).fetchall()
        cov = {r["deal_id"]: (r["lo"], r["hi"]) for r in rows}
        # ccf_2026 drifts safe (5.2) → watch (6.2)
        self.assertEqual(cov.get("ccf_2026"), (5.2, 6.2))
        # arr_2025 trips (5.8 → 7.0)
        self.assertEqual(cov.get("arr_2025"), (5.8, 7.0))
        # pma_2024 deleverages (5.0 → 4.3)
        self.assertEqual(cov.get("pma_2024"), (4.3, 5.0))

    def test_cross_portfolio_playbook_gap_fires(self) -> None:
        df = cross_portfolio_initiative_variance(self.store)
        self.assertFalse(df.empty, "cross-portfolio aggregator empty")
        # prior_auth_improvement should be a playbook gap (3 deals,
        # mean variance ~-40%)
        prior_auth = df[df["initiative_id"] == "prior_auth_improvement"]
        self.assertFalse(prior_auth.empty,
                         "prior_auth_improvement not in aggregator")
        row = prior_auth.iloc[0]
        self.assertEqual(int(row["n_deals"]), 3)
        self.assertTrue(bool(row["is_playbook_gap"]),
                        "prior_auth_improvement should fire playbook gap")
        self.assertLess(float(row["mean_variance_pct"]), -0.30,
                        "prior_auth mean variance should be below -30%")

    def test_single_deal_initiatives_do_not_fire_gap(self) -> None:
        df = cross_portfolio_initiative_variance(self.store)
        single = df[df["n_deals"] == 1]
        # All single-deal initiatives must NOT be playbook gaps,
        # regardless of variance — n_deals ≥ 2 is the rule
        for _, row in single.iterrows():
            self.assertFalse(
                bool(row["is_playbook_gap"]),
                f"{row['initiative_id']} fired gap with n_deals=1",
            )

    def test_packets_built_for_held_and_exit_deals(self) -> None:
        # 4 packets expected: ccf_2026, arr_2025, pma_2024, tlc_2023
        self.assertEqual(self.result.packets_built, 4)
        self.assertEqual(self.result.deals_skipped, [])

    def test_export_files_written_at_canonical_paths(self) -> None:
        files = list(self.base.rglob("*"))
        files = [f for f in files if f.is_file()]
        # 8 placeholder files per _EXPORT_SEEDS
        self.assertEqual(len(files), 8)
        # Each file should be under <base>/<deal_id>/<timestamp>_<name>
        # Filenames must NOT contain spaces or colons (FS-safe)
        for f in files:
            self.assertNotIn(" ", f.name,
                             f"FS-unsafe space in filename: {f.name}")
            self.assertNotIn(":", f.name,
                             f"FS-unsafe colon in filename: {f.name}")

    def test_no_export_files_knob_works(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, "demo2.db")
            base = Path(t) / "exports"
            r = seed_demo_db(db, base_dir=base, write_export_files=False)
            # Rows still inserted
            self.assertGreater(r.exports_inserted, 0)
            # But no files on disk
            self.assertEqual(r.export_files_written, 0)
            files = [f for f in base.rglob("*") if f.is_file()] if base.exists() else []
            self.assertEqual(len(files), 0)

    def test_determinism_same_seed_same_result(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db1 = os.path.join(t, "a.db")
            db2 = os.path.join(t, "b.db")
            r1 = seed_demo_db(db1)
            r2 = seed_demo_db(db2)
            self.assertEqual(r1.deals_inserted, r2.deals_inserted)
            self.assertEqual(r1.snapshots_inserted, r2.snapshots_inserted)
            self.assertEqual(r1.actuals_inserted, r2.actuals_inserted)
            self.assertEqual(r1.exports_inserted, r2.exports_inserted)


class TestVerify(unittest.TestCase):
    """The --verify path is the runtime version of these tests."""

    def test_verify_passes_against_seeded_db(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, "demo.db")
            seed_demo_db(db, base_dir=Path(t) / "exports")
            v = verify_seeded_db(db)
            self.assertTrue(
                v.all_passed,
                f"verify failed against fresh seed: {v.report()}",
            )
            self.assertEqual(len(v.checks), 5)

    def test_verify_fails_against_empty_db(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, "empty.db")
            # Initialize but don't seed
            from rcm_mc.infra.migrations import run_pending
            store = PortfolioStore(db)
            run_pending(store)
            v = verify_seeded_db(db)
            self.assertFalse(v.all_passed)


if __name__ == "__main__":
    unittest.main()
