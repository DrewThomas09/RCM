"""
Tests for the initiatives library and optimizer.
"""
from __future__ import annotations

import os
import unittest

from rcm_mc.infra.config import load_and_validate
from rcm_mc.rcm.initiatives import (
    get_initiative,
    initiative_to_scenario,
    load_initiatives_library,
    get_all_initiatives,
)
from rcm_mc.rcm.initiative_optimizer import rank_initiatives, build_100_day_plan


class TestInitiatives(unittest.TestCase):
    def test_load_initiatives_library(self):
        initiatives = load_initiatives_library()
        self.assertGreaterEqual(len(initiatives), 8)
        self.assertLessEqual(len(initiatives), 15)

    def test_initiative_schema(self):
        initiatives = get_all_initiatives()
        for i in initiatives:
            self.assertIn("id", i)
            self.assertIn("name", i)
            self.assertIn("affected_parameters", i)
            self.assertIn("one_time_cost", i)
            self.assertIn("annual_run_rate", i)
            self.assertIn("ramp_months", i)
            self.assertIn("confidence", i)
            for ap in i["affected_parameters"]:
                self.assertIn("payer", ap)
                self.assertIn("param", ap)
                self.assertIn("delta_type", ap)

    def test_get_initiative(self):
        initiatives = get_all_initiatives()
        inv = get_initiative(initiatives, "prior_auth_improvement")
        self.assertIsNotNone(inv)
        self.assertEqual(inv["id"], "prior_auth_improvement")
        inv_missing = get_initiative(initiatives, "nonexistent")
        self.assertIsNone(inv_missing)

    def test_initiative_to_scenario(self):
        initiatives = get_all_initiatives()
        inv = get_initiative(initiatives, "prior_auth_improvement")
        self.assertIsNotNone(inv)
        scenario = initiative_to_scenario(inv)
        self.assertIn("name", scenario)
        self.assertIn("shocks", scenario)
        self.assertGreater(len(scenario["shocks"]), 0)


class TestInitiativeOptimizer(unittest.TestCase):
    def test_rank_initiatives(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = load_and_validate(os.path.join(base_dir, "configs", "actual.yaml"))
        benchmark = load_and_validate(os.path.join(base_dir, "configs", "benchmark.yaml"))
        df = rank_initiatives(actual, benchmark, n_sims=100, seed=99, ev_multiple=8.0)
        self.assertGreater(len(df), 0)
        self.assertIn("rank", df.columns)
        self.assertIn("ev_uplift_mean", df.columns)
        self.assertIn("payback_months", df.columns)
        self.assertEqual(df["rank"].iloc[0], 1)

    def test_build_100_day_plan(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = load_and_validate(os.path.join(base_dir, "configs", "actual.yaml"))
        benchmark = load_and_validate(os.path.join(base_dir, "configs", "benchmark.yaml"))
        rank_df = rank_initiatives(actual, benchmark, n_sims=100, seed=88, ev_multiple=8.0)
        plan_df = build_100_day_plan(rank_df)
        self.assertGreater(len(plan_df), 0)
        self.assertIn("kpi", plan_df.columns)
        self.assertIn("phase", plan_df.columns)
        self.assertIn("owner", plan_df.columns)


if __name__ == "__main__":
    unittest.main()
