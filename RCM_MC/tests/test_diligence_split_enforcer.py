"""Provider-disjoint three-way split — no ID appears in two buckets.

Conformal CIs are invalid if the same provider's rows land in both
train and calibration. This test enforces the contract for pool
sizes from tiny (3 providers) to real (hundreds), and confirms that
deterministic seeding produces identical splits across runs.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.integrity import (
    ProviderSplit, SplitViolation, assert_provider_disjoint,
    make_three_way_split,
)
from rcm_mc.diligence.integrity.split_enforcer import rows_in_bucket


class SplitEnforcerTests(unittest.TestCase):

    def test_target_always_in_test(self):
        split = make_three_way_split(
            target_provider_id="T-999",
            provider_pool=[f"P-{i:03d}" for i in range(20)],
        )
        self.assertIn("T-999", split.test)
        self.assertNotIn("T-999", split.train)
        self.assertNotIn("T-999", split.calibration)

    def test_three_buckets_are_pairwise_disjoint(self):
        split = make_three_way_split(
            target_provider_id="T-001",
            provider_pool=[f"P-{i:04d}" for i in range(200)],
        )
        self.assertEqual(len(split.train & split.calibration), 0)
        self.assertEqual(len(split.train & split.test), 0)
        self.assertEqual(len(split.calibration & split.test), 0)

    def test_sum_of_sizes_equals_pool_plus_target(self):
        pool = [f"P-{i:03d}" for i in range(50)]
        split = make_three_way_split(
            target_provider_id="T-1", provider_pool=pool,
        )
        total = len(split.train) + len(split.calibration) + len(split.test)
        self.assertEqual(total, 50 + 1)  # pool + target

    def test_deterministic_under_same_seed(self):
        pool = [f"P-{i:03d}" for i in range(30)]
        split_a = make_three_way_split(
            target_provider_id="T-0", provider_pool=pool, random_seed=42,
        )
        split_b = make_three_way_split(
            target_provider_id="T-0", provider_pool=pool, random_seed=42,
        )
        self.assertEqual(split_a.train, split_b.train)
        self.assertEqual(split_a.calibration, split_b.calibration)
        self.assertEqual(split_a.test, split_b.test)

    def test_different_seed_yields_different_split(self):
        pool = [f"P-{i:03d}" for i in range(30)]
        a = make_three_way_split(target_provider_id="T", provider_pool=pool, random_seed=1)
        b = make_three_way_split(target_provider_id="T", provider_pool=pool, random_seed=99)
        self.assertNotEqual(a.train, b.train)

    # ── Invariant assertions ────────────────────────────────────────

    def test_assert_catches_hand_built_violation(self):
        bad = ProviderSplit(
            train={"P-1", "P-2"},
            calibration={"P-2"},    # duplicate P-2 in both
            test={"T"},
            target_provider_id="T",
        )
        with self.assertRaises(SplitViolation):
            assert_provider_disjoint(bad)

    def test_assert_catches_target_leaked_into_train(self):
        bad = ProviderSplit(
            train={"T", "P-1"}, calibration={"P-2"}, test={"T"},
            target_provider_id="T",
        )
        with self.assertRaises(SplitViolation):
            assert_provider_disjoint(bad)

    # ── Degenerate inputs ──────────────────────────────────────────

    def test_pool_too_small_raises(self):
        with self.assertRaises(SplitViolation):
            make_three_way_split(
                target_provider_id="T",
                provider_pool=["P-1", "P-2"],     # pool size 2 < 3
            )

    def test_train_plus_calibration_must_leave_test(self):
        with self.assertRaises(SplitViolation):
            make_three_way_split(
                target_provider_id="T", provider_pool=[f"P-{i}" for i in range(10)],
                train_fraction=0.6, calibration_fraction=0.6,
            )

    def test_rows_filter_by_bucket(self):
        split = make_three_way_split(
            target_provider_id="T-0",
            provider_pool=["P-001", "P-002", "P-003", "P-004", "P-005"],
        )
        rows = [
            {"provider_id": "P-001", "dar": 30.0},
            {"provider_id": "P-002", "dar": 45.0},
            {"provider_id": "P-003", "dar": 28.0},
            {"provider_id": "P-004", "dar": 50.0},
            {"provider_id": "P-005", "dar": 40.0},
        ]
        train_rows = rows_in_bucket(rows, bucket=split.train)
        cal_rows = rows_in_bucket(rows, bucket=split.calibration)
        test_rows = rows_in_bucket(rows, bucket=split.test)
        # All rows accounted for.
        self.assertEqual(
            len(train_rows) + len(cal_rows) + len(test_rows),
            len(rows),
        )
        # No row in two buckets.
        train_pids = {r["provider_id"] for r in train_rows}
        cal_pids = {r["provider_id"] for r in cal_rows}
        test_pids = {r["provider_id"] for r in test_rows}
        self.assertEqual(train_pids & cal_pids, set())
        self.assertEqual(train_pids & test_pids, set())
        self.assertEqual(cal_pids & test_pids, set())


if __name__ == "__main__":
    unittest.main()
