"""Tests for the management-plan pressure-test module."""
from __future__ import annotations

import os
import tempfile
import unittest

import yaml

from rcm_mc.infra.config import load_and_validate
from rcm_mc.data.intake import _blended_mean
from rcm_mc.analysis.pressure_test import (
    _build_scenario_cfg,
    assess_targets,
    assessments_to_dataframe,
    classify_target,
    load_initiative_library,
    load_management_plan,
    match_initiatives_for_target,
    run_miss_scenarios,
    run_pressure_test,
)


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ACTUAL_PATH = os.path.join(BASE_DIR, "configs", "actual.yaml")
BENCH_PATH = os.path.join(BASE_DIR, "configs", "benchmark.yaml")


def _sample_plan(**overrides) -> dict:
    plan = {
        "horizon_months": 12,
        "targets": {"idr_blended": 0.10, "fwr_blended": 0.25, "dar_blended": 45},
        "notes": "test plan",
    }
    plan.update(overrides)
    return plan


class TestClassifyTarget(unittest.TestCase):
    def test_tiny_step_is_conservative(self):
        # actual 0.14, bench 0.10; target 0.135 = 5% of gap = conservative
        self.assertEqual(classify_target(0.14, 0.10, 0.135), "conservative")

    def test_half_the_gap_is_stretch(self):
        # target 0.12 = 50% of (0.14 - 0.10) = stretch
        self.assertEqual(classify_target(0.14, 0.10, 0.12), "stretch")

    def test_near_benchmark_is_aggressive(self):
        # target 0.105 = 87.5% of gap = aggressive
        self.assertEqual(classify_target(0.14, 0.10, 0.105), "aggressive")

    def test_beyond_benchmark_is_aspirational(self):
        self.assertEqual(classify_target(0.14, 0.10, 0.08), "aspirational")

    def test_actual_already_better_than_benchmark(self):
        # Better than top-decile → any further reduction is aspirational
        self.assertEqual(classify_target(0.08, 0.10, 0.07), "aspirational")


class TestLoaders(unittest.TestCase):
    def test_load_management_plan_accepts_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump(_sample_plan(), f)
            plan = load_management_plan(path)
            self.assertEqual(plan["horizon_months"], 12)

    def test_load_management_plan_rejects_unknown_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"targets": {"denials_cured_per_fortnight": 9999}}, f)
            with self.assertRaises(ValueError):
                load_management_plan(path)

    def test_load_management_plan_rejects_empty_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"targets": {}}, f)
            with self.assertRaises(ValueError):
                load_management_plan(path)

    def test_load_management_plan_rejects_non_numeric_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"targets": {"idr_blended": "eleven percent"}}, f)
            with self.assertRaises(ValueError):
                load_management_plan(path)

    def test_load_management_plan_rejects_out_of_range_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"targets": {"fwr_blended": 1.25}}, f)
            with self.assertRaises(ValueError):
                load_management_plan(path)

    def test_load_management_plan_rejects_non_positive_horizon(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"horizon_months": 0, "targets": {"idr_blended": 0.10}}, f)
            with self.assertRaises(ValueError):
                load_management_plan(path)

    def test_load_initiative_library_returns_list(self):
        lib = load_initiative_library()
        self.assertIsInstance(lib, list)
        self.assertGreater(len(lib), 0)

    def test_load_initiative_library_missing_file_returns_empty(self):
        self.assertEqual(load_initiative_library("/nonexistent/path.yaml"), [])


class TestInitiativeMatching(unittest.TestCase):
    def setUp(self):
        self.lib = load_initiative_library()

    def test_idr_target_matches_prior_auth_initiative(self):
        matched = match_initiatives_for_target("idr_blended", self.lib)
        ids = [i.get("id") for i in matched]
        self.assertIn("prior_auth_improvement", ids)

    def test_fwr_target_matches_coding_initiative(self):
        matched = match_initiatives_for_target("fwr_blended", self.lib)
        ids = [i.get("id") for i in matched]
        self.assertIn("coding_cdi_improvement", ids)


class TestAssessTargets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual_cfg = load_and_validate(ACTUAL_PATH)
        cls.bench_cfg = load_and_validate(BENCH_PATH)

    def test_returns_one_assessment_per_target(self):
        plan = _sample_plan()
        out = assess_targets(self.actual_cfg, self.bench_cfg, plan)
        self.assertEqual(len(out), 3)
        keys = {a.target_key for a in out}
        self.assertEqual(keys, {"idr_blended", "fwr_blended", "dar_blended"})

    def test_classification_attached(self):
        plan = _sample_plan()
        out = assess_targets(self.actual_cfg, self.bench_cfg, plan)
        for a in out:
            self.assertIn(a.classification, ("conservative", "stretch", "aggressive", "aspirational"))

    def test_matching_initiatives_populated_for_idr(self):
        plan = _sample_plan(targets={"idr_blended": 0.10})
        out = assess_targets(self.actual_cfg, self.bench_cfg, plan)
        self.assertTrue(out[0].matching_initiatives)

    def test_assess_targets_rejects_invalid_direct_plan_dict(self):
        with self.assertRaises(ValueError):
            assess_targets(
                self.actual_cfg,
                self.bench_cfg,
                {"targets": {"dar_blended": -5}},
            )


class TestBuildScenarioCfg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual_cfg = load_and_validate(ACTUAL_PATH)

    def test_zero_achievement_preserves_config(self):
        cfg = _build_scenario_cfg(self.actual_cfg, {"idr_blended": 0.10}, achievement=0.0)
        orig_blend = _blended_mean(self.actual_cfg, ("denials", "idr"))
        new_blend = _blended_mean(cfg, ("denials", "idr"))
        self.assertAlmostEqual(orig_blend, new_blend, places=3)

    def test_full_achievement_lands_on_target(self):
        cfg = _build_scenario_cfg(self.actual_cfg, {"idr_blended": 0.08}, achievement=1.0)
        new_blend = _blended_mean(cfg, ("denials", "idr"))
        self.assertAlmostEqual(new_blend, 0.08, places=3)

    def test_half_achievement_lands_halfway(self):
        actual_blend = _blended_mean(self.actual_cfg, ("denials", "idr"))
        target = 0.08
        cfg = _build_scenario_cfg(self.actual_cfg, {"idr_blended": target}, achievement=0.5)
        new_blend = _blended_mean(cfg, ("denials", "idr"))
        self.assertAlmostEqual(new_blend, actual_blend - 0.5 * (actual_blend - target), places=3)


class TestRunPressureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual_cfg = load_and_validate(ACTUAL_PATH)
        cls.bench_cfg = load_and_validate(BENCH_PATH)

    def test_end_to_end_small_run(self):
        plan = _sample_plan()
        results = run_pressure_test(
            self.actual_cfg, self.bench_cfg, plan,
            n_sims=200, seed=7,
        )
        self.assertIn("assessments_df", results)
        self.assertIn("miss_scenarios_df", results)
        miss = results["miss_scenarios_df"]
        self.assertEqual(set(miss.columns), {"achievement", "ebitda_drag_mean", "ebitda_drag_p10", "ebitda_drag_p90"})
        self.assertEqual(len(miss), 4)
        # Sanity: fully hitting the plan should reduce drag vs status quo
        status_quo = miss.loc[miss["achievement"] == 0.0, "ebitda_drag_mean"].iloc[0]
        full_hit = miss.loc[miss["achievement"] == 1.0, "ebitda_drag_mean"].iloc[0]
        self.assertLess(full_hit, status_quo)

    def test_aspirational_target_yields_risk_flag(self):
        # Target wildly beyond benchmark triggers the aspirational flag
        plan = _sample_plan(targets={"idr_blended": 0.005})
        results = run_pressure_test(
            self.actual_cfg, self.bench_cfg, plan,
            n_sims=100, seed=7,
        )
        flags = results["risk_flags"]
        self.assertTrue(any("aspirational" in f or "top-decile" in f for f in flags))

    def test_multiple_aggressive_targets_flagged(self):
        # Targets sit just shy of each metric's benchmark → aggressive classification.
        # Blended benchmarks in shipped configs: IDR ~0.113, FWR ~0.096, DAR ~28.8.
        plan = _sample_plan(targets={
            "idr_blended": 0.115,
            "fwr_blended": 0.100,
            "dar_blended": 30,
        })
        results = run_pressure_test(
            self.actual_cfg, self.bench_cfg, plan,
            n_sims=100, seed=7,
        )
        # At least two targets classified aggressive/aspirational → compound-risk flag
        classifications = [a.classification for a in results["assessments"]]
        aggressive_or_aspirational = [c for c in classifications if c in ("aggressive", "aspirational")]
        self.assertGreaterEqual(
            len(aggressive_or_aspirational), 2,
            msg=f"Expected 2+ aggressive/aspirational; got classifications={classifications}",
        )
        self.assertTrue(
            any("aggressive" in f for f in results["risk_flags"]),
            msg=f"Expected compound-risk flag; got {results['risk_flags']}",
        )

    def test_run_pressure_test_rejects_fractional_horizon(self):
        with self.assertRaises(ValueError):
            run_pressure_test(
                self.actual_cfg,
                self.bench_cfg,
                _sample_plan(horizon_months=12.5),
                n_sims=50,
                seed=7,
            )


class TestMissScenariosTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual_cfg = load_and_validate(ACTUAL_PATH)
        cls.bench_cfg = load_and_validate(BENCH_PATH)

    def test_monotonic_drag_reduction_with_achievement(self):
        plan = _sample_plan()
        df = run_miss_scenarios(
            self.actual_cfg, self.bench_cfg, plan,
            n_sims=200, seed=7,
        )
        drags = df.sort_values("achievement")["ebitda_drag_mean"].tolist()
        # Expect drag to decrease (or at least not increase) as achievement rises
        for a, b in zip(drags, drags[1:]):
            self.assertLessEqual(b, a + 5e4, msg=f"drag should be monotonic (noise tolerance 50k); got {drags}")

    def test_rejects_nan_achievement_level(self):
        with self.assertRaises(ValueError):
            run_miss_scenarios(
                self.actual_cfg, self.bench_cfg, _sample_plan(),
                n_sims=50, seed=7, achievement_levels=[float("nan")],
            )

    def test_rejects_out_of_range_achievement_level(self):
        with self.assertRaises(ValueError):
            run_miss_scenarios(
                self.actual_cfg, self.bench_cfg, _sample_plan(),
                n_sims=50, seed=7, achievement_levels=[1.25],
            )

    def test_rejects_empty_achievement_levels(self):
        with self.assertRaises(ValueError):
            run_miss_scenarios(
                self.actual_cfg, self.bench_cfg, _sample_plan(),
                n_sims=50, seed=7, achievement_levels=[],
            )

    def test_rejects_non_positive_n_sims(self):
        with self.assertRaises(ValueError):
            run_miss_scenarios(
                self.actual_cfg, self.bench_cfg, _sample_plan(),
                n_sims=0, seed=7,
            )


class TestAssessmentsDataframe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual_cfg = load_and_validate(ACTUAL_PATH)
        cls.bench_cfg = load_and_validate(BENCH_PATH)

    def test_columns(self):
        plan = _sample_plan()
        assessments = assess_targets(self.actual_cfg, self.bench_cfg, plan)
        df = assessments_to_dataframe(assessments)
        self.assertEqual(
            set(df.columns),
            {
                "target", "actual_blended", "benchmark_blended", "target_value",
                "progress_ratio", "classification",
                "matching_initiatives", "median_ramp_months",
            },
        )
