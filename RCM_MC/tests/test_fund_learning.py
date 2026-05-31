"""Tests for the fund-level learning engine.

`rcm_mc/ml/fund_learning.py` aggregates value-creation actual-vs-plan
across all closed deals to detect systematic bias by lever ("we
overestimate denial improvement by 18%") and apply those corrections
to future predictions. It's the compounding moat — every closed deal
improves the next underwrite. Both public functions had no test
coverage before this file:

- compute_fund_accuracy(db_path) — aggregates from SQLite
- get_adjusted_bridge(db_path, bridge) — applies the bias to a new
  bridge before it's shown to the partner
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from rcm_mc.ml.fund_learning import (
    FundAccuracy,
    LeverBias,
    compute_fund_accuracy,
    get_adjusted_bridge,
)


def _build_db(plans=None, actuals=None) -> str:
    """Create a temp SQLite with the two tables the module reads.

    Returns the path; caller is responsible for cleanup (or rely on
    OS tempdir GC at process exit since these are tiny)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = tmp.name
    tmp.close()
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE value_creation_plans ("
        "  deal_id TEXT, hospital_name TEXT, plan_json TEXT,"
        "  total_planned_uplift REAL)"
    )
    con.execute(
        "CREATE TABLE value_creation_actuals ("
        "  deal_id TEXT, lever TEXT, actual_impact REAL,"
        "  planned_impact REAL, quarter TEXT)"
    )
    if plans:
        con.executemany(
            "INSERT INTO value_creation_plans VALUES (?, ?, ?, ?)",
            plans,
        )
    if actuals:
        con.executemany(
            "INSERT INTO value_creation_actuals VALUES (?, ?, ?, ?, ?)",
            actuals,
        )
    con.commit()
    con.close()
    return path


class ComputeFundAccuracyTests(unittest.TestCase):
    """Contract for ``compute_fund_accuracy``."""

    def test_missing_db_returns_none(self):
        # Path doesn't exist → sqlite3.connect would create it (and
        # the SELECT on missing tables would except). The function
        # returns None when EITHER the connect or the plans SELECT
        # fails — verify via a path the SELECT can't satisfy.
        with tempfile.TemporaryDirectory() as tmp:
            # Create empty DB (no tables) — connect succeeds, plans
            # SELECT raises, function returns None.
            path = Path(tmp) / "empty.db"
            con = sqlite3.connect(str(path))
            con.close()
            self.assertIsNone(compute_fund_accuracy(str(path)))

    def test_no_plans_returns_none(self):
        # Tables exist but plans table is empty → return None
        # (nothing to aggregate; sentinel for the UI to render
        # "no closed deals yet").
        path = _build_db(plans=[], actuals=[])
        self.assertIsNone(compute_fund_accuracy(path))

    def test_plans_no_actuals_returns_stub(self):
        # Plans exist but no actuals recorded → returns a stub with
        # n_closed_deals = N, total_realized = 0, narrative
        # explaining why.
        plans = [
            ("d1", "Hosp A", "{}", 5_000_000),
            ("d2", "Hosp B", "{}", 3_000_000),
        ]
        path = _build_db(plans=plans, actuals=[])
        fa = compute_fund_accuracy(path)
        self.assertIsNotNone(fa)
        self.assertEqual(fa.n_closed_deals, 2)
        self.assertEqual(fa.total_planned, 8_000_000)
        self.assertEqual(fa.total_realized, 0)
        self.assertEqual(fa.lever_biases, [])
        self.assertIn("No quarterly actuals recorded yet", fa.narrative)

    def test_perfect_realization(self):
        # Single deal, single lever, actual exactly == planned →
        # fund realization = 100% and the lever is 'accurate'.
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "denial_reduction", 1_000_000, 1_000_000, "2024Q1"),
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.fund_realization_pct, 1.0)
        self.assertEqual(len(fa.lever_biases), 1)
        self.assertEqual(fa.lever_biases[0].lever, "denial_reduction")
        self.assertEqual(fa.lever_biases[0].realization_pct, 1.0)
        self.assertEqual(fa.lever_biases[0].bias_direction, "accurate")
        # adjustment_factor = 1.0 (no correction needed)
        self.assertEqual(fa.adjustment_factors["denial_reduction"], 1.0)

    def test_overestimation_classified(self):
        # Realization < 0.8 → 'overestimates'
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "denial_reduction", 500_000, 1_000_000, "2024Q1"),
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.lever_biases[0].realization_pct, 0.5)
        self.assertEqual(fa.lever_biases[0].bias_direction, "overestimates")
        # adjustment_factor clamped to >=0.3
        self.assertGreaterEqual(fa.adjustment_factors["denial_reduction"], 0.3)
        self.assertEqual(fa.adjustment_factors["denial_reduction"], 0.5)

    def test_underestimation_classified(self):
        # Realization > 1.0 → 'underestimates'
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "denial_reduction", 1_500_000, 1_000_000, "2024Q1"),
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.lever_biases[0].realization_pct, 1.5)
        self.assertEqual(fa.lever_biases[0].bias_direction, "underestimates")
        # adjustment_factor clamped to <=1.5
        self.assertLessEqual(fa.adjustment_factors["denial_reduction"], 1.5)

    def test_adjustment_factor_clamped_at_15(self):
        # Realization of 3.0 → adjustment should be CAPPED at 1.5
        # so we never go more than 1.5x the planned uplift.
        plans = [("d1", "Hosp A", "{}", 100_000)]
        actuals = [("d1", "denial", 300_000, 100_000, "Q1")]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.adjustment_factors["denial"], 1.5)

    def test_adjustment_factor_floor_at_03(self):
        # Realization of 0.1 → adjustment FLOORED at 0.3 (we still
        # give a deal SOME credit for the lever, never 0).
        plans = [("d1", "Hosp A", "{}", 100_000)]
        actuals = [("d1", "denial", 10_000, 100_000, "Q1")]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.adjustment_factors["denial"], 0.3)

    def test_multi_lever_aggregation(self):
        # Multiple levers across multiple deals — verify each
        # lever's realization is computed independently and the
        # fund-level percentage is total_actual / total_planned.
        plans = [
            ("d1", "Hosp A", "{}", 2_000_000),
            ("d2", "Hosp B", "{}", 1_000_000),
        ]
        actuals = [
            ("d1", "denial",     400_000, 500_000, "Q1"),  # 0.8
            ("d1", "ar_days",    600_000, 500_000, "Q1"),  # 1.2
            ("d2", "denial",     250_000, 500_000, "Q1"),  # 0.5
            ("d2", "ar_days",    500_000, 500_000, "Q1"),  # 1.0
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.n_closed_deals, 2)
        # Fund: total_actual = 1,750,000, total_planned = 2,000,000
        self.assertEqual(fa.total_planned, 2_000_000)
        self.assertEqual(fa.total_realized, 1_750_000)
        self.assertAlmostEqual(fa.fund_realization_pct, 0.875)
        # Per-lever realizations
        by_lever = {b.lever: b.realization_pct for b in fa.lever_biases}
        # denial: 650K / 1M = 0.65
        self.assertAlmostEqual(by_lever["denial"], 0.65)
        # ar_days: 1.1M / 1M = 1.1
        self.assertAlmostEqual(by_lever["ar_days"], 1.1)

    def test_zero_planned_safe(self):
        # Lever with planned=0 must not divide-by-zero (defaults to
        # realization=0 + adjustment=1.0).
        plans = [("d1", "Hosp A", "{}", 0)]
        actuals = [("d1", "denial", 0, 0, "Q1")]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertEqual(fa.lever_biases[0].realization_pct, 0)
        self.assertEqual(fa.adjustment_factors["denial"], 1.0)
        # fund_realization_pct is also safe (no divide-by-zero)
        self.assertEqual(fa.fund_realization_pct, 0)

    def test_narrative_carries_realization_and_bias(self):
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "denial",  400_000, 1_000_000, "Q1"),  # over-estimate
            ("d1", "ar_days", 500_000, 250_000, "Q1"),    # under-estimate
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        self.assertIn("realization", fa.narrative.lower())
        # Both biases should be mentioned
        self.assertIn("overestimates", fa.narrative.lower())
        self.assertIn("underestimates", fa.narrative.lower())

    def test_biases_sorted_by_distance_from_one(self):
        # Sort key is |1 - realization_pct| DESC — biggest deviation
        # from accurate (1.0) shows first.
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "near_target",  100_000, 100_000, "Q1"),  # 1.0
            ("d1", "way_off",      10_000, 100_000, "Q1"),   # 0.1
            ("d1", "slightly_off", 90_000, 100_000, "Q1"),   # 0.9
        ]
        path = _build_db(plans, actuals)
        fa = compute_fund_accuracy(path)
        distances = [abs(1 - b.realization_pct) for b in fa.lever_biases]
        self.assertEqual(distances, sorted(distances, reverse=True))


class GetAdjustedBridgeTests(unittest.TestCase):
    """Contract for ``get_adjusted_bridge``."""

    def test_no_accuracy_returns_bridge_unchanged(self):
        # If compute_fund_accuracy returns None (no plans yet), the
        # bridge is returned unmodified — no '_fund_adjusted' flag.
        with tempfile.TemporaryDirectory() as tmp:
            empty_path = Path(tmp) / "empty.db"
            con = sqlite3.connect(str(empty_path))
            con.close()  # Missing tables → compute returns None
            bridge = {"levers": [{"name": "denial",
                                  "ebitda_impact": 1_000_000,
                                  "revenue_impact": 2_000_000,
                                  "cost_impact": -100_000}]}
            out = get_adjusted_bridge(str(empty_path), bridge)
            self.assertEqual(out, bridge)
            self.assertNotIn("_fund_adjusted", out)

    def test_adjustment_factor_one_passes_through(self):
        # If the lever's adjustment_factor == 1.0, the lever is left
        # alone (no _adjustment_factor or _original_impact added).
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [("d1", "denial",
                    900_000, 1_000_000, "Q1")]  # 0.9 → 'accurate'
        path = _build_db(plans, actuals)
        bridge = {"levers": [{"name": "denial",
                              "ebitda_impact": 500_000,
                              "revenue_impact": 1_000_000,
                              "cost_impact": -50_000}]}
        out = get_adjusted_bridge(path, bridge)
        # accuracy = 0.9 → adjustment_factor = 0.9 ≠ 1.0
        adj_lever = out["levers"][0]
        self.assertIn("_adjustment_factor", adj_lever)
        # ebitda_impact = 500K × 0.9 = 450K
        self.assertEqual(adj_lever["ebitda_impact"], 450_000)
        self.assertEqual(adj_lever["_original_impact"], 500_000)

    def test_bridge_total_recomputed(self):
        # Sum of adjusted lever impacts must equal total_ebitda_impact.
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [
            ("d1", "denial",  500_000, 1_000_000, "Q1"),  # 0.5
            ("d1", "ar_days", 800_000, 1_000_000, "Q1"),  # 0.8
        ]
        path = _build_db(plans, actuals)
        bridge = {"levers": [
            {"name": "denial",  "ebitda_impact": 1_000_000,
             "revenue_impact": 2_000_000, "cost_impact": -100_000},
            {"name": "ar_days", "ebitda_impact": 500_000,
             "revenue_impact": 1_000_000, "cost_impact": -50_000},
        ]}
        out = get_adjusted_bridge(path, bridge)
        # denial: 1M × 0.5 = 500K
        # ar_days: 500K × 0.8 = 400K
        # total = 900K
        self.assertEqual(out["total_ebitda_impact"], 900_000)
        # Verify per-lever values match
        by_name = {l["name"]: l for l in out["levers"]}
        self.assertEqual(by_name["denial"]["ebitda_impact"], 500_000)
        self.assertEqual(by_name["ar_days"]["ebitda_impact"], 400_000)

    def test_unknown_lever_passes_through(self):
        # A lever with a name NOT in the fund's adjustment_factors
        # uses factor=1.0 (no change).
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [("d1", "denial", 500_000, 1_000_000, "Q1")]
        path = _build_db(plans, actuals)
        bridge = {"levers": [
            {"name": "denial", "ebitda_impact": 1_000_000,
             "revenue_impact": 0, "cost_impact": 0},
            {"name": "new_lever_never_modeled",
             "ebitda_impact": 200_000,
             "revenue_impact": 0, "cost_impact": 0},
        ]}
        out = get_adjusted_bridge(path, bridge)
        by_name = {l["name"]: l for l in out["levers"]}
        # denial gets scaled down
        self.assertEqual(by_name["denial"]["ebitda_impact"], 500_000)
        # new_lever_never_modeled unchanged (no _adjustment_factor flag)
        self.assertEqual(
            by_name["new_lever_never_modeled"]["ebitda_impact"],
            200_000)
        self.assertNotIn(
            "_adjustment_factor",
            by_name["new_lever_never_modeled"])

    def test_marks_bridge_as_fund_adjusted(self):
        plans = [("d1", "Hosp A", "{}", 1_000_000)]
        actuals = [("d1", "denial", 500_000, 1_000_000, "Q1")]
        path = _build_db(plans, actuals)
        bridge = {"levers": [{"name": "denial",
                              "ebitda_impact": 1_000_000,
                              "revenue_impact": 0,
                              "cost_impact": 0}]}
        out = get_adjusted_bridge(path, bridge)
        self.assertTrue(out["_fund_adjusted"])
        self.assertIn("_fund_realization", out)
        self.assertAlmostEqual(out["_fund_realization"], 0.5)


class DataclassDefaults(unittest.TestCase):
    """Sanity defaults on the dataclasses — keep partner-facing
    fields explicit so nothing accidentally renders as None."""

    def test_lever_bias_fields_exist(self):
        b = LeverBias(
            lever="denial", planned_total=1.0, actual_total=0.5,
            realization_pct=0.5, bias_direction="overestimates",
            n_deals=1, adjustment_factor=0.5,
        )
        self.assertEqual(b.lever, "denial")
        self.assertEqual(b.bias_direction, "overestimates")

    def test_fund_accuracy_fields_exist(self):
        fa = FundAccuracy(
            n_closed_deals=0, total_planned=0, total_realized=0,
            fund_realization_pct=0, lever_biases=[],
            accuracy_trend=[], narrative="",
            adjustment_factors={},
        )
        self.assertEqual(fa.n_closed_deals, 0)


if __name__ == "__main__":
    unittest.main()
