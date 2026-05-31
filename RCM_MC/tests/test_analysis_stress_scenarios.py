"""Tests for the stress-scenario factory functions.

`rcm_mc/analysis/stress.py` exposes 4 stress-scenario factories +
a default suite that the simulator runs at every checkpoint:

  - scenario_denial_rate_spike(payer, factor)
  - scenario_writeoff_worsens(payer, factor)
  - scenario_capacity_crunch(factor)
  - scenario_payer_mix_shift(delta_to_medicaid)
  - default_stress_suite()

Each factory returns a ``StressScenario`` whose ``apply_fn`` shocks
the (actual_cfg, bench_cfg) pair in a specific way. The full
simulator path is covered by integration tests, but these factories
+ their apply_fn mutations had no direct unit coverage at all.

These tests exercise the config-mutation logic without running the
Monte Carlo simulator (fast: ~10ms total). Lock the invariants:
the factories don't mutate inputs, name the scenario consistently,
and shock the correct config field.
"""
from __future__ import annotations

import copy
import unittest

from rcm_mc.analysis.stress import (
    StressScenario,
    default_stress_suite,
    scenario_capacity_crunch,
    scenario_denial_rate_spike,
    scenario_payer_mix_shift,
    scenario_writeoff_worsens,
)


def _minimal_cfg() -> dict:
    """Smallest config shape the scenario apply_fn paths read."""
    return {
        "payers": {
            "Commercial": {
                "revenue_share": 0.40,
                "include_denials": True,
                "denials": {
                    "idr": {"dist": "beta", "mean": 0.10, "sd": 0.02},
                    "fwr": {"dist": "beta", "mean": 0.05, "sd": 0.01},
                },
            },
            "Medicare": {
                "revenue_share": 0.40,
                "include_denials": True,
                "denials": {
                    "idr": {"dist": "beta", "mean": 0.08, "sd": 0.02},
                    "fwr": {"dist": "beta", "mean": 0.15, "sd": 0.03},
                },
            },
            "Medicaid": {
                "revenue_share": 0.20,
                "include_denials": False,
                "denials": {
                    "idr": {"dist": "beta", "mean": 0.12, "sd": 0.03},
                    "fwr": {"dist": "beta", "mean": 0.20, "sd": 0.03},
                },
            },
        },
        "operations": {
            "denial_capacity": {"enabled": False, "fte": 10.0,
                                 "mode": "infinite"},
        },
    }


class ScenarioDenialRateSpikeTests(unittest.TestCase):
    """Multiply a payer's IDR mean by the given factor."""

    def test_returns_stress_scenario(self):
        sc = scenario_denial_rate_spike("Commercial", 1.25)
        self.assertIsInstance(sc, StressScenario)

    def test_name_carries_payer_and_factor(self):
        sc = scenario_denial_rate_spike("Commercial", 1.25)
        self.assertEqual(sc.name, "Commercial_IDR_x1.25")
        sc2 = scenario_denial_rate_spike("Medicare", 1.50)
        self.assertEqual(sc2.name, "Medicare_IDR_x1.50")

    def test_description_mentions_payer_and_pct(self):
        sc = scenario_denial_rate_spike("Commercial", 1.25)
        self.assertIn("Commercial", sc.description)
        self.assertIn("25%", sc.description)
        self.assertIn("initial denial rate", sc.description)

    def test_apply_does_not_mutate_input(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        a_snapshot = copy.deepcopy(a)
        b_snapshot = copy.deepcopy(b)
        sc = scenario_denial_rate_spike("Commercial", 1.25)
        sc.apply_fn(a, b)
        # Originals untouched
        self.assertEqual(a, a_snapshot)
        self.assertEqual(b, b_snapshot)

    def test_apply_shocks_idr_mean(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        sc = scenario_denial_rate_spike("Commercial", 1.25)
        a2, b2 = sc.apply_fn(a, b)
        # 0.10 × 1.25 = 0.125
        self.assertAlmostEqual(
            a2["payers"]["Commercial"]["denials"]["idr"]["mean"],
            0.125, places=5)
        self.assertAlmostEqual(
            b2["payers"]["Commercial"]["denials"]["idr"]["mean"],
            0.125, places=5)

    def test_apply_skips_payer_with_denials_disabled(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        sc = scenario_denial_rate_spike("Medicaid", 1.5)
        a2, _ = sc.apply_fn(a, b)
        # Medicaid has include_denials=False → unchanged
        self.assertEqual(
            a2["payers"]["Medicaid"]["denials"]["idr"]["mean"],
            0.12)

    def test_apply_clipped_to_idr_ceiling(self):
        # IDR shock is clipped at 0.50 (ceiling per the source).
        a = _minimal_cfg()
        b = _minimal_cfg()
        # Set IDR mean = 0.45, factor 2.0 → 0.90 clipped to 0.50
        a["payers"]["Commercial"]["denials"]["idr"]["mean"] = 0.45
        b["payers"]["Commercial"]["denials"]["idr"]["mean"] = 0.45
        sc = scenario_denial_rate_spike("Commercial", 2.0)
        a2, _ = sc.apply_fn(a, b)
        self.assertEqual(
            a2["payers"]["Commercial"]["denials"]["idr"]["mean"],
            0.50)


class ScenarioWriteoffWorsensTests(unittest.TestCase):
    """Multiply a payer's FWR (final write-off rate) mean by factor."""

    def test_name_format(self):
        sc = scenario_writeoff_worsens("Medicare", 1.20)
        self.assertEqual(sc.name, "Medicare_FWR_x1.20")

    def test_description_mentions_final_writeoff(self):
        sc = scenario_writeoff_worsens("Medicare", 1.20)
        self.assertIn("final write-off rate", sc.description)
        self.assertIn("Medicare", sc.description)

    def test_apply_shocks_fwr_mean(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        sc = scenario_writeoff_worsens("Medicare", 1.20)
        a2, b2 = sc.apply_fn(a, b)
        # 0.15 × 1.20 = 0.18
        self.assertAlmostEqual(
            a2["payers"]["Medicare"]["denials"]["fwr"]["mean"],
            0.18, places=4)
        self.assertAlmostEqual(
            b2["payers"]["Medicare"]["denials"]["fwr"]["mean"],
            0.18, places=4)

    def test_apply_clipped_to_fwr_ceiling(self):
        # FWR clipped at 0.95 (95% write-off ceiling).
        a = _minimal_cfg()
        b = _minimal_cfg()
        a["payers"]["Medicare"]["denials"]["fwr"]["mean"] = 0.80
        b["payers"]["Medicare"]["denials"]["fwr"]["mean"] = 0.80
        sc = scenario_writeoff_worsens("Medicare", 2.0)
        a2, _ = sc.apply_fn(a, b)
        self.assertEqual(
            a2["payers"]["Medicare"]["denials"]["fwr"]["mean"],
            0.95)


class ScenarioCapacityCrunchTests(unittest.TestCase):
    """Reduce denial-team FTE by `factor`, enabling queue mode."""

    def test_name_format(self):
        sc = scenario_capacity_crunch(0.70)
        self.assertEqual(sc.name, "Capacity_FTE_x0.70")

    def test_description_mentions_pct_reduction(self):
        sc = scenario_capacity_crunch(0.70)
        # (1 - 0.70) = 30% reduction
        self.assertIn("30%", sc.description)
        self.assertIn("FTE", sc.description)

    def test_apply_scales_fte_and_forces_queue_mode(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        sc = scenario_capacity_crunch(0.5)
        a2, b2 = sc.apply_fn(a, b)
        # 10 × 0.5 = 5.0
        self.assertAlmostEqual(
            a2["operations"]["denial_capacity"]["fte"], 5.0)
        self.assertAlmostEqual(
            b2["operations"]["denial_capacity"]["fte"], 5.0)
        # Always flips to enabled + queue mode (so the shock has
        # the chance to actually bite — infinite-capacity mode
        # would mask it).
        self.assertTrue(
            a2["operations"]["denial_capacity"]["enabled"])
        self.assertEqual(
            a2["operations"]["denial_capacity"]["mode"], "queue")

    def test_apply_default_fte_when_missing(self):
        a = _minimal_cfg()
        a["operations"]["denial_capacity"].pop("fte")
        b = _minimal_cfg()
        b["operations"]["denial_capacity"].pop("fte")
        sc = scenario_capacity_crunch(0.5)
        a2, _ = sc.apply_fn(a, b)
        # Default falls back to 12.0; 12 × 0.5 = 6.0
        self.assertAlmostEqual(
            a2["operations"]["denial_capacity"]["fte"], 6.0)

    def test_apply_does_not_mutate_input(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        a_snap = copy.deepcopy(a)
        sc = scenario_capacity_crunch(0.5)
        sc.apply_fn(a, b)
        self.assertEqual(a, a_snap)


class ScenarioPayerMixShiftTests(unittest.TestCase):
    """Move revenue share from Commercial → Medicaid."""

    def test_name_format(self):
        sc = scenario_payer_mix_shift(0.05)
        self.assertEqual(sc.name, "PayerMix_Medicaid_+5%")

    def test_description_mentions_shift(self):
        sc = scenario_payer_mix_shift(0.05)
        self.assertIn("Commercial", sc.description)
        self.assertIn("Medicaid", sc.description)
        self.assertIn("5%", sc.description)

    def test_apply_shifts_revenue_shares(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        sc = scenario_payer_mix_shift(0.05)
        a2, b2 = sc.apply_fn(a, b)
        # Commercial: 0.40 - 0.05 = 0.35
        self.assertAlmostEqual(
            a2["payers"]["Commercial"]["revenue_share"], 0.35)
        # Medicaid: 0.20 + 0.05 = 0.25
        self.assertAlmostEqual(
            a2["payers"]["Medicaid"]["revenue_share"], 0.25)

    def test_commercial_floored_at_zero(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        a["payers"]["Commercial"]["revenue_share"] = 0.02
        b["payers"]["Commercial"]["revenue_share"] = 0.02
        sc = scenario_payer_mix_shift(0.10)
        a2, _ = sc.apply_fn(a, b)
        # 0.02 - 0.10 → floored at 0.0 (can't have negative share)
        self.assertEqual(
            a2["payers"]["Commercial"]["revenue_share"], 0.0)

    def test_medicaid_capped_at_one(self):
        a = _minimal_cfg()
        b = _minimal_cfg()
        a["payers"]["Medicaid"]["revenue_share"] = 0.95
        b["payers"]["Medicaid"]["revenue_share"] = 0.95
        sc = scenario_payer_mix_shift(0.10)
        a2, _ = sc.apply_fn(a, b)
        # 0.95 + 0.10 → capped at 1.0
        self.assertEqual(
            a2["payers"]["Medicaid"]["revenue_share"], 1.0)

    def test_missing_payer_silently_skipped(self):
        # If Medicaid or Commercial is missing from the cfg, the
        # apply_fn returns unchanged (defensive).
        a = _minimal_cfg()
        a["payers"].pop("Medicaid")
        b = _minimal_cfg()
        b["payers"].pop("Medicaid")
        sc = scenario_payer_mix_shift(0.05)
        a2, _ = sc.apply_fn(a, b)
        # Commercial untouched (no Medicaid to shift TO)
        self.assertAlmostEqual(
            a2["payers"]["Commercial"]["revenue_share"], 0.40)


class DefaultStressSuiteTests(unittest.TestCase):
    """The standard 4-scenario suite the simulator runs at every
    checkpoint."""

    def test_returns_four_scenarios(self):
        suite = default_stress_suite()
        self.assertEqual(len(suite), 4)
        for sc in suite:
            self.assertIsInstance(sc, StressScenario)

    def test_scenarios_have_unique_names(self):
        suite = default_stress_suite()
        names = [sc.name for sc in suite]
        self.assertEqual(len(names), len(set(names)),
                         f"Duplicate scenario names: {names}")

    def test_suite_includes_each_factory_type(self):
        # Verify the suite covers the 4 distinct shock families.
        suite = default_stress_suite()
        # Each name has a recognizable family marker.
        names_joined = " ".join(sc.name for sc in suite)
        self.assertIn("IDR", names_joined)
        self.assertIn("FWR", names_joined)
        self.assertIn("Capacity", names_joined)
        self.assertIn("PayerMix", names_joined)


if __name__ == "__main__":
    unittest.main()
