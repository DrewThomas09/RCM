"""Tests for ``rcm_mc/scenarios/scenario_builder.py``.

``ScenarioBuilder`` is the fluent what-if API used everywhere from
the CLI ``--scenario`` flag to the partner-facing Scenario Explorer
page. Each adjust_*() method modifies a config dict in place + keeps
a human-readable trail in ``description``. Module had no direct
unit-test coverage.

Two surfaces:

  * ``ScenarioBuilder`` — fluent chained adjustments, returns the
    modified cfg via ``.build()``
  * ``apply_scenario_dict`` — flat dict-of-adjustments → modified cfg
    (used by the CLI for JSON scenario input)

Lock the clip bounds (IDR 0.01..0.50, FWR 0.01..0.95, UPR 0.001..0.50,
FTE ≥ 1) before any tweak silently changes the scenario math.
"""
from __future__ import annotations

import unittest
from copy import deepcopy

from rcm_mc.scenarios.scenario_builder import (
    ScenarioBuilder,
    apply_scenario_dict,
)


def _base_cfg() -> dict:
    """Minimal cfg covering every adjust_* code path."""
    return {
        "payers": {
            "Medicare": {
                "denials": {
                    "idr": {"mean": 0.10},
                    "fwr": {"mean": 0.05},
                },
                "underpayments": {
                    "upr": {"mean": 0.05},
                },
            },
            "Commercial": {
                "denials": {
                    "idr": {"mean": 0.14},
                    "fwr": {"mean": 0.04},
                },
            },
        },
        "hospital": {"annual_revenue": 500_000_000},
        "operations": {"denial_capacity": {"fte": 12}},
    }


# ---------------------------------------------------------------------------
# ScenarioBuilder — fluent API
# ---------------------------------------------------------------------------


class FluentApiTests(unittest.TestCase):

    def test_returns_self_for_chaining(self):
        sb = ScenarioBuilder(_base_cfg())
        # Each method returns self.
        self.assertIs(sb.adjust_idr("Medicare", -0.02), sb)
        self.assertIs(sb.adjust_fwr("Medicare", -0.01), sb)
        self.assertIs(sb.set_revenue(600_000_000), sb)
        self.assertIs(sb.set_fte(15), sb)
        self.assertIs(sb.adjust_upr("Medicare", -0.01), sb)

    def test_does_not_mutate_input_cfg(self):
        # deepcopy guarantee — the builder must own its own copy.
        base = _base_cfg()
        original_idr = base["payers"]["Medicare"]["denials"]["idr"]["mean"]
        sb = ScenarioBuilder(base)
        sb.adjust_idr("Medicare", -0.05).build()
        # Base unchanged.
        self.assertEqual(
            base["payers"]["Medicare"]["denials"]["idr"]["mean"],
            original_idr,
        )


class AdjustIdrTests(unittest.TestCase):

    def test_adjusts_idr_mean_by_delta(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_idr(
            "Medicare", -0.03).build()
        # 0.10 - 0.03 = 0.07
        self.assertAlmostEqual(
            cfg["payers"]["Medicare"]["denials"]["idr"]["mean"],
            0.07, places=4,
        )

    def test_clamps_idr_at_lower_bound(self):
        # 0.10 - 0.50 → would be negative → clamps to 0.01
        cfg = ScenarioBuilder(_base_cfg()).adjust_idr(
            "Medicare", -0.50).build()
        self.assertEqual(
            cfg["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.01)

    def test_clamps_idr_at_upper_bound(self):
        # 0.10 + 0.80 = 0.90 → clamps to 0.50
        cfg = ScenarioBuilder(_base_cfg()).adjust_idr(
            "Medicare", 0.80).build()
        self.assertEqual(
            cfg["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.50)

    def test_unknown_payer_silently_skipped(self):
        sb = ScenarioBuilder(_base_cfg()).adjust_idr("Aetna", -0.02)
        # No adjustment recorded.
        self.assertEqual(sb.description, "No changes")

    def test_payer_without_idr_silently_skipped(self):
        cfg = _base_cfg()
        del cfg["payers"]["Medicare"]["denials"]["idr"]
        sb = ScenarioBuilder(cfg).adjust_idr("Medicare", -0.02)
        self.assertEqual(sb.description, "No changes")


class AdjustFwrTests(unittest.TestCase):

    def test_adjusts_fwr_mean_by_delta(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_fwr(
            "Medicare", -0.02).build()
        self.assertAlmostEqual(
            cfg["payers"]["Medicare"]["denials"]["fwr"]["mean"],
            0.03, places=4,
        )

    def test_fwr_lower_bound_001(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_fwr(
            "Medicare", -0.99).build()
        self.assertEqual(
            cfg["payers"]["Medicare"]["denials"]["fwr"]["mean"], 0.01)

    def test_fwr_upper_bound_95(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_fwr(
            "Medicare", 0.99).build()
        # 0.05 + 0.99 clamps to 0.95
        self.assertEqual(
            cfg["payers"]["Medicare"]["denials"]["fwr"]["mean"], 0.95)


class AdjustUprTests(unittest.TestCase):

    def test_adjusts_upr_mean_by_delta(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_upr(
            "Medicare", -0.02).build()
        self.assertAlmostEqual(
            cfg["payers"]["Medicare"]["underpayments"]["upr"]["mean"],
            0.03, places=4,
        )

    def test_upr_lower_bound_0001(self):
        # UPR has a finer lower bound (0.001) than IDR.
        cfg = ScenarioBuilder(_base_cfg()).adjust_upr(
            "Medicare", -0.99).build()
        self.assertEqual(
            cfg["payers"]["Medicare"]["underpayments"]["upr"]["mean"],
            0.001,
        )

    def test_upr_upper_bound_50(self):
        cfg = ScenarioBuilder(_base_cfg()).adjust_upr(
            "Medicare", 0.99).build()
        self.assertEqual(
            cfg["payers"]["Medicare"]["underpayments"]["upr"]["mean"],
            0.50,
        )

    def test_payer_without_underpayments_silently_skipped(self):
        # Commercial has no underpayments key.
        sb = ScenarioBuilder(_base_cfg()).adjust_upr("Commercial", -0.02)
        self.assertEqual(sb.description, "No changes")


class SetRevenueTests(unittest.TestCase):

    def test_sets_annual_revenue(self):
        cfg = ScenarioBuilder(_base_cfg()).set_revenue(750_000_000).build()
        self.assertEqual(cfg["hospital"]["annual_revenue"], 750_000_000.0)

    def test_creates_hospital_key_if_missing(self):
        cfg = _base_cfg()
        del cfg["hospital"]
        out = ScenarioBuilder(cfg).set_revenue(400_000_000).build()
        self.assertEqual(out["hospital"]["annual_revenue"], 400_000_000.0)


class SetFteTests(unittest.TestCase):

    def test_sets_fte_in_capacity(self):
        cfg = ScenarioBuilder(_base_cfg()).set_fte(20).build()
        self.assertEqual(
            cfg["operations"]["denial_capacity"]["fte"], 20.0)

    def test_creates_operations_key_if_missing(self):
        cfg = _base_cfg()
        del cfg["operations"]
        out = ScenarioBuilder(cfg).set_fte(25).build()
        self.assertEqual(
            out["operations"]["denial_capacity"]["fte"], 25.0)


class DescriptionTests(unittest.TestCase):

    def test_empty_description_when_no_changes(self):
        sb = ScenarioBuilder(_base_cfg())
        self.assertEqual(sb.description, "No changes")

    def test_description_records_each_adjustment(self):
        sb = (ScenarioBuilder(_base_cfg())
              .adjust_idr("Medicare", -0.02)
              .adjust_fwr("Medicare", -0.01))
        desc = sb.description
        self.assertIn("IDR(Medicare)", desc)
        self.assertIn("FWR(Medicare)", desc)

    def test_description_uses_semicolon_separator(self):
        sb = (ScenarioBuilder(_base_cfg())
              .set_revenue(600_000_000)
              .set_fte(15))
        self.assertIn(";", sb.description)


# ---------------------------------------------------------------------------
# apply_scenario_dict — flat dict input (CLI JSON path)
# ---------------------------------------------------------------------------


class ApplyScenarioDictTests(unittest.TestCase):

    def test_empty_dict_returns_unchanged_copy(self):
        base = _base_cfg()
        out = apply_scenario_dict(base, {})
        # Equal but distinct objects.
        self.assertEqual(out, base)
        self.assertIsNot(out, base)

    def test_does_not_mutate_input(self):
        base = _base_cfg()
        original = deepcopy(base)
        _ = apply_scenario_dict(base, {
            "idr_delta_by_payer": {"Medicare": -0.05}})
        self.assertEqual(base, original)

    def test_idr_delta_applies_per_payer(self):
        out = apply_scenario_dict(_base_cfg(), {
            "idr_delta_by_payer": {"Medicare": -0.05},
        })
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"],
            0.05, places=4,
        )

    def test_idr_delta_clamps_to_bounds(self):
        out = apply_scenario_dict(_base_cfg(), {
            "idr_delta_by_payer": {"Medicare": -0.50},
        })
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.01)

    def test_idr_delta_unknown_payer_skipped(self):
        # No crash on unrecognized payer key.
        out = apply_scenario_dict(_base_cfg(), {
            "idr_delta_by_payer": {"Aetna": -0.05},
        })
        self.assertEqual(out, _base_cfg())

    def test_fte_change_applies(self):
        out = apply_scenario_dict(_base_cfg(), {"fte_change": 3})
        self.assertEqual(
            out["operations"]["denial_capacity"]["fte"], 15.0)

    def test_fte_change_floors_at_1(self):
        # 12 - 20 = -8 → floor at 1
        out = apply_scenario_dict(_base_cfg(), {"fte_change": -20})
        self.assertEqual(
            out["operations"]["denial_capacity"]["fte"], 1.0)

    def test_fte_change_creates_operations_section(self):
        cfg = _base_cfg()
        del cfg["operations"]
        out = apply_scenario_dict(cfg, {"fte_change": 5})
        # Default fte=12 + 5 = 17
        self.assertEqual(
            out["operations"]["denial_capacity"]["fte"], 17.0)

    def test_annual_revenue_applies(self):
        out = apply_scenario_dict(_base_cfg(), {
            "annual_revenue": 800_000_000})
        self.assertEqual(out["hospital"]["annual_revenue"], 800_000_000.0)

    def test_multiple_adjustments_compose(self):
        out = apply_scenario_dict(_base_cfg(), {
            "idr_delta_by_payer": {
                "Medicare": -0.02, "Commercial": -0.03,
            },
            "fte_change": 5,
            "annual_revenue": 750_000_000,
        })
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"],
            0.08, places=4,
        )
        self.assertAlmostEqual(
            out["payers"]["Commercial"]["denials"]["idr"]["mean"],
            0.11, places=4,
        )
        self.assertEqual(
            out["operations"]["denial_capacity"]["fte"], 17.0)
        self.assertEqual(out["hospital"]["annual_revenue"], 750_000_000.0)


if __name__ == "__main__":
    unittest.main()
