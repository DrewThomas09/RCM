"""Tests for the PE value-plan blending math.

`rcm_mc/pe/value_plan.py` is the core 'PE value creation'
abstraction — take Actual + Benchmark configs and produce a
Target config with N% of the gap closed. The 4 untested public
functions are the building blocks:

  - load_value_plan(path) — YAML loader with hard validation
  - get_gap_closure(plan, payer, metric, default) — looks up the
    closure fraction with payer-specific override semantics
  - blend_dist_spec(actual, benchmark, k, direction, ...) — moves
    a distribution's mean toward benchmark, blends sd, preserves
    distribution family (beta/normal/triangular/lognormal/fixed)
  - blend_stage_mix(actual_mix, benchmark_mix, k) — share-vector
    blending with normalization
"""
from __future__ import annotations

import os
import tempfile
import unittest

import yaml

from rcm_mc.pe.value_plan import (
    ValuePlanError,
    blend_dist_spec,
    blend_stage_mix,
    get_gap_closure,
    load_value_plan,
)


class LoadValuePlanTests(unittest.TestCase):
    """``load_value_plan`` — YAML loader."""

    def test_loads_valid_yaml(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp:
            yaml.safe_dump({
                "gap_closure": {"idr": 0.5},
            }, tmp)
            path = tmp.name
        try:
            out = load_value_plan(path)
            self.assertEqual(out["gap_closure"]["idr"], 0.5)
        finally:
            os.unlink(path)

    def test_missing_path_raises(self):
        with self.assertRaises(ValuePlanError):
            load_value_plan("/nonexistent/path/that/should/fail.yaml")

    def test_malformed_yaml_raises(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp:
            tmp.write("not: valid: yaml:\n  -")
            path = tmp.name
        try:
            with self.assertRaises(ValuePlanError):
                load_value_plan(path)
        finally:
            os.unlink(path)

    def test_non_dict_yaml_raises(self):
        # A YAML list at the top level (not a dict) → ValuePlanError.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp:
            yaml.safe_dump(["a", "b", "c"], tmp)
            path = tmp.name
        try:
            with self.assertRaises(ValuePlanError):
                load_value_plan(path)
        finally:
            os.unlink(path)


class GetGapClosureTests(unittest.TestCase):
    """``get_gap_closure`` resolves k from a plan dict with
    payer-specific override semantics."""

    def test_top_level_default(self):
        plan = {"gap_closure": {"idr": 0.40, "fwr": 0.30}}
        self.assertAlmostEqual(
            get_gap_closure(plan, "Commercial", "idr"), 0.40)
        self.assertAlmostEqual(
            get_gap_closure(plan, "Commercial", "fwr"), 0.30)

    def test_payer_override_wins(self):
        # Payer-specific override > top-level default.
        plan = {
            "gap_closure": {"idr": 0.40},
            "gap_closure_by_payer": {
                "Commercial": {"idr": 0.70},
            },
        }
        self.assertAlmostEqual(
            get_gap_closure(plan, "Commercial", "idr"), 0.70)
        # Different payer falls back to top-level default.
        self.assertAlmostEqual(
            get_gap_closure(plan, "Medicare", "idr"), 0.40)

    def test_missing_metric_uses_default_arg(self):
        plan = {"gap_closure": {"idr": 0.40}}
        # No 'fwr' key anywhere → returns the function's default arg.
        self.assertAlmostEqual(
            get_gap_closure(plan, "X", "fwr", default=0.25), 0.25)

    def test_empty_plan_uses_default_arg(self):
        self.assertAlmostEqual(
            get_gap_closure({}, "Commercial", "idr", default=0.5), 0.5)

    def test_clipped_to_unit_interval(self):
        # k values outside [0,1] get clipped (defensive against
        # malformed plans).
        plan = {"gap_closure": {"idr": 1.5}}
        self.assertEqual(get_gap_closure(plan, "X", "idr"), 1.0)
        plan = {"gap_closure": {"idr": -0.5}}
        self.assertEqual(get_gap_closure(plan, "X", "idr"), 0.0)

    def test_non_dict_branches_handled(self):
        # If gap_closure_by_payer is not a dict, defensively skip.
        plan = {"gap_closure": {"idr": 0.4},
                "gap_closure_by_payer": "not a dict"}
        self.assertAlmostEqual(
            get_gap_closure(plan, "Commercial", "idr"), 0.4)


class BlendDistSpecTests(unittest.TestCase):
    """``blend_dist_spec`` moves a distribution's mean toward
    benchmark while preserving distribution family."""

    def test_blends_beta_mean_toward_benchmark(self):
        actual = {"dist": "beta", "mean": 0.10, "sd": 0.02}
        bench = {"dist": "beta", "mean": 0.05, "sd": 0.01}
        out = blend_dist_spec(actual, bench, k=0.5, direction="lower")
        # 0.10 + 0.5 × (0.05 - 0.10) = 0.075
        self.assertAlmostEqual(out["mean"], 0.075, places=4)
        # Family preserved
        self.assertEqual(out["dist"], "beta")

    def test_direction_lower_only_moves_down(self):
        # If benchmark is WORSE (higher) and direction='lower',
        # the actual should NOT be moved up (no anti-improvement).
        actual = {"dist": "beta", "mean": 0.05, "sd": 0.01}
        bench = {"dist": "beta", "mean": 0.10, "sd": 0.02}
        out = blend_dist_spec(actual, bench, k=0.5, direction="lower")
        # 'lower' direction caps the move at 0 if benchmark > actual.
        self.assertAlmostEqual(out["mean"], 0.05, places=4)

    def test_direction_higher_only_moves_up(self):
        actual = {"dist": "beta", "mean": 0.50, "sd": 0.05}
        bench = {"dist": "beta", "mean": 0.30, "sd": 0.05}
        out = blend_dist_spec(actual, bench, k=0.5,
                               direction="higher")
        # Bench is lower than actual → don't move (no
        # anti-improvement).
        self.assertAlmostEqual(out["mean"], 0.50, places=4)

    def test_direction_toward_moves_either_way(self):
        # The default 'toward' direction moves regardless of which
        # side is better.
        actual = {"dist": "normal", "mean": 10.0, "sd": 1.0}
        bench = {"dist": "normal", "mean": 5.0, "sd": 1.0}
        out = blend_dist_spec(actual, bench, k=0.5, direction="toward")
        self.assertAlmostEqual(out["mean"], 7.5)

    def test_k_clamped_to_unit_interval(self):
        # k > 1 → fully closed; k < 0 → no movement.
        actual = {"dist": "fixed", "value": 10.0}
        bench = {"dist": "fixed", "value": 0.0}
        out = blend_dist_spec(actual, bench, k=2.0, direction="lower")
        self.assertEqual(out["value"], 0.0)  # fully closed
        out = blend_dist_spec(actual, bench, k=-1.0, direction="lower")
        self.assertEqual(out["value"], 10.0)  # no movement

    def test_clamp_min_max_applied(self):
        actual = {"dist": "fixed", "value": 10.0}
        bench = {"dist": "fixed", "value": 0.0}
        out = blend_dist_spec(actual, bench, k=1.0,
                               direction="lower", clamp_min=3.0)
        # Would fully close to 0, but clamp_min=3.0
        self.assertEqual(out["value"], 3.0)

        actual2 = {"dist": "fixed", "value": 0.0}
        bench2 = {"dist": "fixed", "value": 100.0}
        out2 = blend_dist_spec(
            actual2, bench2, k=1.0, direction="higher",
            clamp_max=50.0)
        self.assertEqual(out2["value"], 50.0)

    def test_preserves_normal_family(self):
        actual = {"dist": "normal", "mean": 10.0, "sd": 2.0}
        bench = {"dist": "normal", "mean": 5.0, "sd": 1.0}
        out = blend_dist_spec(actual, bench, k=0.5, direction="lower")
        self.assertEqual(out["dist"], "normal")

    def test_preserves_triangular_family(self):
        actual = {"dist": "triangular", "low": 0.0, "mode": 5.0,
                  "high": 10.0}
        bench = {"dist": "triangular", "low": 0.0, "mode": 2.0,
                 "high": 4.0}
        out = blend_dist_spec(actual, bench, k=0.5, direction="lower")
        self.assertEqual(out["dist"], "triangular")
        # Mode should shift toward benchmark (5 → ~3.5)
        self.assertLess(out["mode"], 5.0)

    def test_preserves_lognormal_family(self):
        actual = {"dist": "lognormal", "mean": 100.0, "sd": 30.0}
        bench = {"dist": "lognormal", "mean": 50.0, "sd": 15.0}
        out = blend_dist_spec(actual, bench, k=0.5, direction="lower")
        self.assertEqual(out["dist"], "lognormal")
        # mean must stay > 0 for lognormal (floored at 1e-9)
        self.assertGreater(out["mean"], 0)

    def test_beta_mean_clamped_into_open_unit_interval(self):
        # Beta requires mean ∈ (0, 1) strictly — code clamps to
        # [1e-6, 1-1e-6].
        actual = {"dist": "beta", "mean": 0.99, "sd": 0.001}
        bench = {"dist": "beta", "mean": 0.999, "sd": 0.0001}
        out = blend_dist_spec(actual, bench, k=1.0,
                               direction="higher")
        self.assertLess(out["mean"], 1.0)
        self.assertGreater(out["mean"], 0.0)

    def test_unknown_dist_raises_via_dist_moments(self):
        # The function reads dist_moments() early; an unknown dist
        # name raises DistributionError from there BEFORE the
        # fallback-to-fixed branch can run. The fallback is dead
        # code on the public path; documenting that here.
        from rcm_mc.core.distributions import DistributionError
        actual = {"dist": "weird_unknown", "value": 10.0}
        bench = {"dist": "weird_unknown", "value": 5.0}
        with self.assertRaises(DistributionError):
            blend_dist_spec(actual, bench, k=0.5, direction="lower")

    def test_missing_specs_default_to_fixed_zero(self):
        # None inputs default to {dist: fixed, value: 0}
        out = blend_dist_spec(None, None, k=0.5, direction="toward")
        self.assertEqual(out["dist"], "fixed")
        self.assertEqual(out["value"], 0.0)


class BlendStageMixTests(unittest.TestCase):
    """``blend_stage_mix`` blends share vectors with normalization."""

    def test_basic_blend(self):
        actual = {"stage_a": 0.6, "stage_b": 0.4}
        bench = {"stage_a": 0.2, "stage_b": 0.8}
        out = blend_stage_mix(actual, bench, k=0.5)
        # 0.6 + 0.5 × (0.2 - 0.6) = 0.4
        # 0.4 + 0.5 × (0.8 - 0.4) = 0.6
        self.assertAlmostEqual(out["stage_a"], 0.4)
        self.assertAlmostEqual(out["stage_b"], 0.6)

    def test_shares_sum_to_one(self):
        actual = {"a": 0.5, "b": 0.3, "c": 0.2}
        bench = {"a": 0.2, "b": 0.5, "c": 0.3}
        for k in (0.0, 0.25, 0.5, 0.75, 1.0):
            out = blend_stage_mix(actual, bench, k=k)
            self.assertAlmostEqual(sum(out.values()), 1.0, places=5)

    def test_k_zero_returns_actual(self):
        actual = {"a": 0.7, "b": 0.3}
        bench = {"a": 0.1, "b": 0.9}
        out = blend_stage_mix(actual, bench, k=0.0)
        self.assertAlmostEqual(out["a"], 0.7)
        self.assertAlmostEqual(out["b"], 0.3)

    def test_k_one_returns_benchmark(self):
        actual = {"a": 0.7, "b": 0.3}
        bench = {"a": 0.1, "b": 0.9}
        out = blend_stage_mix(actual, bench, k=1.0)
        self.assertAlmostEqual(out["a"], 0.1)
        self.assertAlmostEqual(out["b"], 0.9)

    def test_negative_shares_clamped_to_zero(self):
        # If a key's blended value goes negative, it's clamped to 0
        # before normalization.
        actual = {"a": 0.05, "b": 0.95}
        bench = {"a": 0.0, "b": 1.0}
        out = blend_stage_mix(actual, bench, k=1.5)  # k clamped to 1
        # k=1 → 'a' = 0.0, 'b' = 1.0. Still normalized.
        self.assertAlmostEqual(out["a"], 0.0, places=5)
        self.assertAlmostEqual(out["b"], 1.0, places=5)

    def test_keys_unioned(self):
        # Keys missing from either side default to 0 and still appear
        # in the output.
        actual = {"a": 0.5, "b": 0.5}
        bench = {"b": 0.4, "c": 0.6}
        out = blend_stage_mix(actual, bench, k=0.5)
        self.assertEqual(set(out.keys()), {"a", "b", "c"})

    def test_zero_sum_falls_back_to_uniform(self):
        # If blending produces all-zero shares (k=1 with bench all 0),
        # function falls back to uniform 1/N.
        actual = {"a": 0.5, "b": 0.5}
        bench = {"a": 0.0, "b": 0.0}
        out = blend_stage_mix(actual, bench, k=1.0)
        self.assertAlmostEqual(out["a"], 0.5)
        self.assertAlmostEqual(out["b"], 0.5)

    def test_empty_inputs_safe(self):
        # All-empty inputs → empty dict (or uniform with no keys).
        out = blend_stage_mix({}, {}, k=0.5)
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
