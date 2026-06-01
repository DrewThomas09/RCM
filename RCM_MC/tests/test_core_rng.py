"""Tests for ``rcm_mc/core/rng.py`` — centralized RNG management.

``RNGManager`` is the load-bearing reproducibility primitive: every
simulation component spawns its independent stream by name, and the
docstring promises 'same name always gives the same stream regardless
of call order.'

That guarantee is what makes simulator runs auditable in diligence —
a deal team re-running with the same seed must get bit-for-bit
identical output for the partner brief to be defensible.

Module had no direct unit-test coverage. Lock the reproducibility
contract + the independence guarantee before any tweak silently
changes the manager's seeding logic.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.core.rng import RNGManager


class ConstructorTests(unittest.TestCase):

    def test_accepts_int_seed(self):
        m = RNGManager(42)
        self.assertEqual(m.seed, 42)

    def test_coerces_seed_to_int(self):
        # Float-or-string-numeric seed must coerce.
        m = RNGManager("123")
        self.assertEqual(m.seed, 123)
        self.assertIsInstance(m.seed, int)

    def test_seed_property_returns_base_seed(self):
        m = RNGManager(7)
        self.assertEqual(m.seed, 7)


class SpawnTests(unittest.TestCase):

    def test_spawn_returns_generator(self):
        m = RNGManager(42)
        rng = m.spawn("denials")
        self.assertIsInstance(rng, np.random.Generator)

    def test_same_name_returns_same_object(self):
        # 'Same name always gives same stream' — locked: identical
        # Generator instance is returned (cached).
        m = RNGManager(42)
        a = m.spawn("denials")
        b = m.spawn("denials")
        self.assertIs(a, b)

    def test_different_names_return_different_objects(self):
        m = RNGManager(42)
        a = m.spawn("denials")
        b = m.spawn("underpayments")
        self.assertIsNot(a, b)

    def test_different_names_produce_different_sequences(self):
        # Independence guarantee.
        m = RNGManager(42)
        a = m.spawn("denials").random(100)
        b = m.spawn("underpayments").random(100)
        # Probability of identical sequences with different seeds is
        # essentially zero. Verify they differ.
        self.assertFalse(np.array_equal(a, b))


class ReproducibilityTests(unittest.TestCase):
    """Two managers with the same seed must produce identical streams
    for every named child. This is the partner-brief reproducibility
    contract."""

    def test_same_seed_same_stream_for_named_child(self):
        m1 = RNGManager(42)
        m2 = RNGManager(42)
        a = m1.spawn("denials").random(1000)
        b = m2.spawn("denials").random(1000)
        np.testing.assert_array_equal(a, b)

    def test_same_seed_works_for_multiple_streams(self):
        m1 = RNGManager(42)
        m2 = RNGManager(42)
        for name in ("denials", "underpayments", "dar", "appeals"):
            s1 = m1.spawn(name).random(100)
            s2 = m2.spawn(name).random(100)
            np.testing.assert_array_equal(s1, s2, err_msg=f"stream {name}")

    def test_different_seeds_produce_different_streams(self):
        m1 = RNGManager(42)
        m2 = RNGManager(43)
        a = m1.spawn("denials").random(100)
        b = m2.spawn("denials").random(100)
        self.assertFalse(np.array_equal(a, b))

    def test_call_order_does_not_matter(self):
        # Spawning in different orders → same stream per name.
        # This is the key promise — 'regardless of call order'.
        m1 = RNGManager(42)
        _ = m1.spawn("denials")
        _ = m1.spawn("underpayments")
        order1_dar = m1.spawn("dar").random(100)

        m2 = RNGManager(42)
        _ = m2.spawn("underpayments")
        _ = m2.spawn("dar")
        _ = m2.spawn("denials")
        # The 'dar' stream is fresh in m2 — but should still produce
        # the same first 100 draws as m1.spawn('dar') did.
        # Get a fresh dar to compare from-the-start with m1's first draws.
        m3 = RNGManager(42)
        order3_dar = m3.spawn("dar").random(100)
        np.testing.assert_array_equal(order1_dar, order3_dar)


class SpawnPairTests(unittest.TestCase):
    """spawn_pair() returns the (actual, benchmark) pair convention.
    Must be deterministic + two distinct streams."""

    def test_returns_two_generators(self):
        m = RNGManager(42)
        a, b = m.spawn_pair()
        self.assertIsInstance(a, np.random.Generator)
        self.assertIsInstance(b, np.random.Generator)

    def test_pair_streams_are_independent(self):
        m = RNGManager(42)
        a, b = m.spawn_pair()
        sa = a.random(100)
        sb = b.random(100)
        self.assertFalse(np.array_equal(sa, sb))

    def test_pair_is_reproducible(self):
        m1 = RNGManager(42)
        m2 = RNGManager(42)
        a1, b1 = m1.spawn_pair()
        a2, b2 = m2.spawn_pair()
        np.testing.assert_array_equal(a1.random(50), a2.random(50))
        np.testing.assert_array_equal(b1.random(50), b2.random(50))

    def test_pair_is_idempotent_within_manager(self):
        # Calling spawn_pair twice on the same manager returns the
        # same two cached generators.
        m = RNGManager(42)
        a1, b1 = m.spawn_pair()
        a2, b2 = m.spawn_pair()
        self.assertIs(a1, a2)
        self.assertIs(b1, b2)

    def test_pair_uses_reserved_internal_names(self):
        # The pair uses __pair_actual__ / __pair_benchmark__ internally;
        # external callers asking for those exact names get the same
        # stream (documented edge — partner spawning a stream named
        # __pair_actual__ would collide with the pair). This locks the
        # current behavior so future renames are intentional.
        m = RNGManager(42)
        a_pair, b_pair = m.spawn_pair()
        a_direct = m.spawn("__pair_actual__")
        b_direct = m.spawn("__pair_benchmark__")
        self.assertIs(a_pair, a_direct)
        self.assertIs(b_pair, b_direct)


class HashIsolationTests(unittest.TestCase):
    """Streams must NOT depend on alphabetical or numerical name order;
    sha256-based hashing ensures even similar names diverge."""

    def test_similar_names_produce_unrelated_streams(self):
        m = RNGManager(42)
        # Names with a single-char diff must still produce
        # statistically independent streams.
        s_a = m.spawn("payer_a").random(1000)
        s_b = m.spawn("payer_b").random(1000)
        # Correlation should be near zero for truly independent streams.
        corr = float(np.corrcoef(s_a, s_b)[0, 1])
        self.assertLess(abs(corr), 0.1)

    def test_seed_zero_is_valid(self):
        # Edge case — seed=0 must still work.
        m = RNGManager(0)
        rng = m.spawn("x")
        self.assertIsInstance(rng, np.random.Generator)
        # And reproducible.
        m2 = RNGManager(0)
        np.testing.assert_array_equal(
            rng.random(50),
            m2.spawn("x").random(50),
        )


if __name__ == "__main__":
    unittest.main()
