"""Tests for ``build_mixed_config`` in pe/attribution.

`rcm_mc/pe/attribution.py:build_mixed_config` is the structural
heart of the value-attribution path: given an actual config + a
benchmark config + a set of 'bucket indices', return a new config
that's *actual everywhere* except for the named buckets which take
the benchmark's values. The OAT attribution loop uses this to
isolate each driver's contribution to total drag.

`run_oat_attribution` (the simulator-running wrapper) is exercised
by integration tests, but the structural build_mixed_config helper
had no direct unit coverage. These tests pin its non-mutation
contract + verify each bucket index does the right substitution.
"""
from __future__ import annotations

import copy
import unittest

from rcm_mc.pe.attribution import (
    BUCKET_NAMES,
    build_mixed_config,
)


def _basic_cfg(suffix: str = "A"):
    """Minimal config shape with payers + appeals so each bucket
    applier has something to swap."""
    return {
        "payers": {
            "Commercial": {
                "denials": {f"src": suffix,
                            "idr": {"mean": 0.10 if suffix == "A" else 0.05}},
                "underpayments": {f"src": suffix, "severity": 0.10},
                "dar_clean_days": {f"src": suffix, "mean": 45},
            },
            "Medicare": {
                "denials": {f"src": suffix,
                            "idr": {"mean": 0.08 if suffix == "A" else 0.04}},
                "underpayments": {f"src": suffix, "severity": 0.05},
                "dar_clean_days": {f"src": suffix, "mean": 55},
            },
            "Medicaid": {
                "denials": {f"src": suffix},
                "underpayments": {f"src": suffix},
                "dar_clean_days": {f"src": suffix, "mean": 60},
            },
        },
        "appeals": {f"src": suffix,
                    "stages": ["L1", "L2"]},
    }


class BuildMixedConfigBasicsTests(unittest.TestCase):

    def test_empty_buckets_returns_actual_copy(self):
        # No buckets specified → result equals actual_cfg (no
        # benchmark values folded in).
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        out = build_mixed_config(actual, bench, set())
        self.assertEqual(out, actual)
        # And it's a deep copy — not the same object.
        self.assertIsNot(out, actual)

    def test_does_not_mutate_inputs(self):
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        actual_snap = copy.deepcopy(actual)
        bench_snap = copy.deepcopy(bench)
        build_mixed_config(actual, bench, {0, 1, 7})
        self.assertEqual(actual, actual_snap)
        self.assertEqual(bench, bench_snap)

    def test_all_buckets_returns_benchmark_for_named_sections(self):
        # Use all 8 bucket indices → every bucketed section gets the
        # benchmark values (still actual elsewhere).
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        all_indices = set(range(len(BUCKET_NAMES)))
        out = build_mixed_config(actual, bench, all_indices)
        # Every payer's denials/underpayments/dar_clean → bench
        for payer in ("Commercial", "Medicare", "Medicaid"):
            self.assertEqual(
                out["payers"][payer]["denials"]["src"], "B")
            self.assertEqual(
                out["payers"][payer]["underpayments"]["src"], "B")
            self.assertEqual(
                out["payers"][payer]["dar_clean_days"]["src"], "B")
        # Appeals replaced too
        self.assertEqual(out["appeals"]["src"], "B")

    def test_out_of_range_index_ignored(self):
        # The applier indexes into a fixed list; OOB indices just
        # silently get skipped (defensive against caller bugs).
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        out = build_mixed_config(actual, bench, {0, 99, -1, 100})
        # Index 0 (commercial denials) still applied
        self.assertEqual(
            out["payers"]["Commercial"]["denials"]["src"], "B")
        # Nothing else swapped
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["src"], "A")


class BuildMixedConfigPerBucketTests(unittest.TestCase):
    """One test per bucket index to lock the index→action mapping
    (a future reorder of _BUCKET_APPLIERS would silently change the
    OAT attribution result without this test)."""

    def setUp(self):
        self.actual = _basic_cfg("A")
        self.bench = _basic_cfg("B")

    def _src(self, cfg, payer, section):
        return cfg["payers"][payer][section]["src"]

    def test_bucket_0_swaps_commercial_denials(self):
        out = build_mixed_config(self.actual, self.bench, {0})
        self.assertEqual(self._src(out, "Commercial", "denials"), "B")
        # Medicare/Medicaid denials untouched
        self.assertEqual(self._src(out, "Medicare", "denials"), "A")
        self.assertEqual(self._src(out, "Medicaid", "denials"), "A")

    def test_bucket_1_swaps_medicare_denials(self):
        out = build_mixed_config(self.actual, self.bench, {1})
        self.assertEqual(self._src(out, "Medicare", "denials"), "B")
        self.assertEqual(self._src(out, "Commercial", "denials"), "A")
        self.assertEqual(self._src(out, "Medicaid", "denials"), "A")

    def test_bucket_2_swaps_medicaid_denials(self):
        out = build_mixed_config(self.actual, self.bench, {2})
        self.assertEqual(self._src(out, "Medicaid", "denials"), "B")
        self.assertEqual(self._src(out, "Commercial", "denials"), "A")
        self.assertEqual(self._src(out, "Medicare", "denials"), "A")

    def test_bucket_3_swaps_commercial_underpayments(self):
        out = build_mixed_config(self.actual, self.bench, {3})
        self.assertEqual(
            self._src(out, "Commercial", "underpayments"), "B")
        self.assertEqual(
            self._src(out, "Medicare", "underpayments"), "A")
        # Denials untouched
        self.assertEqual(self._src(out, "Commercial", "denials"), "A")

    def test_bucket_4_swaps_medicare_underpayments(self):
        out = build_mixed_config(self.actual, self.bench, {4})
        self.assertEqual(
            self._src(out, "Medicare", "underpayments"), "B")

    def test_bucket_5_swaps_medicaid_underpayments(self):
        out = build_mixed_config(self.actual, self.bench, {5})
        self.assertEqual(
            self._src(out, "Medicaid", "underpayments"), "B")

    def test_bucket_6_swaps_dar_clean_for_every_payer(self):
        # _apply_dar_clean walks every payer, swapping dar_clean_days
        # when the benchmark has it.
        out = build_mixed_config(self.actual, self.bench, {6})
        for payer in ("Commercial", "Medicare", "Medicaid"):
            self.assertEqual(
                self._src(out, payer, "dar_clean_days"), "B")
        # Denials/underpayments untouched
        self.assertEqual(self._src(out, "Commercial", "denials"), "A")

    def test_bucket_7_swaps_appeals_when_benchmark_has_stages(self):
        out = build_mixed_config(self.actual, self.bench, {7})
        self.assertEqual(out["appeals"]["src"], "B")
        # Payer sections untouched
        self.assertEqual(self._src(out, "Commercial", "denials"), "A")

    def test_bucket_7_skipped_when_benchmark_appeals_lacks_stages(self):
        # The appeals applier requires 'stages' in benchmark; if
        # absent (older fixtures), it silently skips.
        bench_no_stages = _basic_cfg("B")
        bench_no_stages["appeals"] = {"src": "B"}  # no 'stages'
        out = build_mixed_config(self.actual, bench_no_stages, {7})
        # Actual appeals preserved
        self.assertEqual(out["appeals"]["src"], "A")


class BuildMixedConfigDefensiveTests(unittest.TestCase):

    def test_missing_payer_in_actual_skipped(self):
        # If actual doesn't have Commercial, the commercial-denials
        # applier silently does nothing (defensive).
        actual = _basic_cfg("A")
        actual["payers"].pop("Commercial")
        bench = _basic_cfg("B")
        out = build_mixed_config(actual, bench, {0})
        # Commercial still absent
        self.assertNotIn("Commercial", out["payers"])

    def test_missing_payer_in_benchmark_skipped(self):
        # Symmetric: if benchmark lacks Medicare denials, the swap
        # silently doesn't happen → actual values preserved.
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        bench["payers"]["Medicare"].pop("denials")
        out = build_mixed_config(actual, bench, {1})
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["src"], "A")

    def test_returns_deep_copy_even_with_buckets(self):
        # Modifying the returned dict must not bleed into the input.
        actual = _basic_cfg("A")
        bench = _basic_cfg("B")
        out = build_mixed_config(actual, bench, {0})
        out["payers"]["Commercial"]["denials"]["src"] = "C"
        # bench unchanged (because of deepcopy inside the applier)
        self.assertEqual(
            bench["payers"]["Commercial"]["denials"]["src"], "B")
        # actual unchanged
        self.assertEqual(
            actual["payers"]["Commercial"]["denials"]["src"], "A")


class BucketNamesContract(unittest.TestCase):

    def test_bucket_count_matches_applier_count(self):
        from rcm_mc.pe.attribution import _BUCKET_APPLIERS
        self.assertEqual(len(BUCKET_NAMES), len(_BUCKET_APPLIERS))

    def test_bucket_names_are_unique_and_non_empty(self):
        self.assertEqual(len(BUCKET_NAMES), len(set(BUCKET_NAMES)))
        for n in BUCKET_NAMES:
            self.assertIsInstance(n, str)
            self.assertTrue(n.strip())


if __name__ == "__main__":
    unittest.main()
