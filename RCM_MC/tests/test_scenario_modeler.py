"""Tests for the scenario modeler."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=100):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY"], n),
        "beds": rng.randint(50, 500, n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 3e9, n),
        "operating_expenses": rng.uniform(4e7, 2.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 8e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class TestRunScenario(unittest.TestCase):

    def test_base_scenario(self):
        from rcm_mc.ui.scenario_modeler_page import _run_scenario, _PRESET_SCENARIOS
        base = _PRESET_SCENARIOS[0]
        r = _run_scenario(base, 400e6, 50e6, 0.40)
        self.assertGreater(r["adj_uplift"], 0)
        self.assertGreater(r["moic"], 0)
        self.assertGreater(r["irr"], -1)

    def test_downside_lower_returns(self):
        from rcm_mc.ui.scenario_modeler_page import _run_scenario, _PRESET_SCENARIOS
        base = next(s for s in _PRESET_SCENARIOS if s["id"] == "base")
        down = next(s for s in _PRESET_SCENARIOS if s["id"] == "downside")
        r_base = _run_scenario(base, 400e6, 50e6, 0.40)
        r_down = _run_scenario(down, 400e6, 50e6, 0.40)
        self.assertLess(r_down["moic"], r_base["moic"])

    def test_aggressive_higher_returns(self):
        from rcm_mc.ui.scenario_modeler_page import _run_scenario, _PRESET_SCENARIOS
        base = next(s for s in _PRESET_SCENARIOS if s["id"] == "base")
        agg = next(s for s in _PRESET_SCENARIOS if s["id"] == "aggressive")
        r_base = _run_scenario(base, 400e6, 50e6, 0.40)
        r_agg = _run_scenario(agg, 400e6, 50e6, 0.40)
        self.assertGreater(r_agg["moic"], r_base["moic"])

    def test_all_presets_run(self):
        from rcm_mc.ui.scenario_modeler_page import _run_scenario, _PRESET_SCENARIOS
        for sc in _PRESET_SCENARIOS:
            r = _run_scenario(sc, 300e6, 40e6, 0.35)
            self.assertIn("moic", r)
            self.assertIn("irr", r)


class TestScenarioModelerPage(unittest.TestCase):

    def test_renders(self):
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        df = _sample_hcris()
        html = render_scenario_modeler("000001", df, "scenarios=base,conservative")
        self.assertIn("Scenario Comparison", html)
        self.assertIn("Base Case", html)
        self.assertIn("Conservative", html)
        self.assertIn("MOIC", html)
        self.assertIn("IRR", html)

    def test_renders_all_presets(self):
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        df = _sample_hcris()
        html = render_scenario_modeler("000001", df,
            "scenarios=base,conservative,aggressive,downside,payer_renego,bed_expansion,merger_synergy,medicare_cut")
        self.assertIn("Merger", html)
        self.assertIn("Medicare", html)

    def test_not_found(self):
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        df = _sample_hcris(10)
        html = render_scenario_modeler("999999", df)
        self.assertIn("not found", html)

    def test_timing_comparison(self):
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        df = _sample_hcris()
        html = render_scenario_modeler("000001", df, "scenarios=base,aggressive")
        self.assertIn("Timing Comparison", html)
        self.assertIn("M12", html)


if __name__ == "__main__":
    unittest.main()
