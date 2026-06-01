"""Tests for the standalone capacity/backlog modeling module.

`rcm_mc/infra/capacity.py` isolates capacity logic from the main
simulator so alternative capacity models (unlimited, outsourced,
queue) can be wired in cleanly. The 4 untested public functions:

  - compute_queue_metrics — monthly-queue buildup simulator
  - compute_backlog_x — normalized over-capacity ratio with cap
  - compute_capacity — unified entry-point covering all 4 modes
    (unlimited / outsourced / annual_backlog / queue)
  - assign_bucket_wait_days — per-bucket wait-day allocation when
    high-dollar-first priority is in effect

Pure math/logic — no I/O, no DB, no simulator coupling. Bugs
here directly change the denial-team capacity assumptions the
simulator uses, which materially shifts EBITDA drag.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.infra.capacity import (
    assign_bucket_wait_days,
    compute_backlog_x,
    compute_capacity,
    compute_queue_metrics,
)


class ComputeQueueMetricsTests(unittest.TestCase):
    """Contract for ``compute_queue_metrics``."""

    def test_capacity_covers_demand_zero_wait(self):
        # demand ≤ capacity → no backlog, no wait.
        out = compute_queue_metrics(
            demand_touches_annual=10_000,
            capacity_touches_annual=15_000,
        )
        self.assertAlmostEqual(out["queue_wait_days_avg"], 0.0)
        self.assertAlmostEqual(out["backlog_months_avg"], 0.0)
        self.assertAlmostEqual(out["backlog_months_max"], 0.0)

    def test_capacity_below_demand_builds_backlog(self):
        # demand >> capacity → backlog grows; queue wait > 0.
        out = compute_queue_metrics(
            demand_touches_annual=30_000,
            capacity_touches_annual=10_000,
        )
        self.assertGreater(out["queue_wait_days_avg"], 0)
        self.assertGreater(out["backlog_months_avg"], 0)
        # Max ≥ avg (backlog peaks at the end of the year).
        self.assertGreaterEqual(out["backlog_months_max"],
                                 out["backlog_months_avg"])

    def test_zero_capacity_returns_zeros(self):
        # Defensive: divide-by-zero → return safe zeros.
        out = compute_queue_metrics(
            demand_touches_annual=100,
            capacity_touches_annual=0,
        )
        self.assertEqual(out["queue_wait_days_avg"], 0)
        self.assertEqual(out["backlog_months_avg"], 0)
        self.assertEqual(out["backlog_months_max"], 0)

    def test_negative_capacity_returns_zeros(self):
        out = compute_queue_metrics(
            demand_touches_annual=100,
            capacity_touches_annual=-50,
        )
        self.assertEqual(out["queue_wait_days_avg"], 0)

    def test_months_floored_at_one(self):
        # months=0 → coerced to 1.
        out = compute_queue_metrics(
            demand_touches_annual=10_000,
            capacity_touches_annual=5_000,
            months=0,
        )
        self.assertTrue(math.isfinite(out["queue_wait_days_avg"]))

    def test_days_per_month_floored_at_one(self):
        out = compute_queue_metrics(
            demand_touches_annual=10_000,
            capacity_touches_annual=5_000,
            days_per_month=0,
        )
        self.assertTrue(math.isfinite(out["queue_wait_days_avg"]))

    def test_wait_days_proportional_to_days_per_month(self):
        # Doubling days_per_month doubles the wait-days output
        # (it's a unit conversion at the end).
        a = compute_queue_metrics(
            demand_touches_annual=30_000,
            capacity_touches_annual=10_000,
            days_per_month=30,
        )
        b = compute_queue_metrics(
            demand_touches_annual=30_000,
            capacity_touches_annual=10_000,
            days_per_month=60,
        )
        self.assertAlmostEqual(
            b["queue_wait_days_avg"] / a["queue_wait_days_avg"],
            2.0, places=5)


class ComputeBacklogXTests(unittest.TestCase):
    """``compute_backlog_x`` — normalized over-capacity ratio
    (touches / capacity - 1), clamped to [0, max_x]."""

    def test_zero_when_below_capacity(self):
        # demand ≤ capacity → x = 0
        self.assertEqual(compute_backlog_x(50, 100), 0)
        self.assertEqual(compute_backlog_x(100, 100), 0)

    def test_positive_when_above_capacity(self):
        # demand = 200, capacity = 100 → x = (2 - 1) = 1.0
        self.assertAlmostEqual(compute_backlog_x(200, 100), 1.0)

    def test_capped_at_max_x(self):
        # 5x capacity → x would be 4.0; capped at default max_x=3.0
        self.assertEqual(compute_backlog_x(500, 100), 3.0)
        # Custom max_x respected
        self.assertEqual(compute_backlog_x(500, 100, max_x=1.5), 1.5)

    def test_zero_capacity_returns_zero(self):
        self.assertEqual(compute_backlog_x(100, 0), 0)
        self.assertEqual(compute_backlog_x(100, -5), 0)

    def test_non_finite_capacity_returns_zero(self):
        # NaN / inf capacity → 0 (defensive against config bugs).
        self.assertEqual(compute_backlog_x(100, float("nan")), 0)
        self.assertEqual(compute_backlog_x(100, float("inf")), 0)


class ComputeCapacityTests(unittest.TestCase):
    """``compute_capacity`` is the unified entry point covering
    all 4 modes (unlimited / outsourced / annual_backlog / queue)."""

    @staticmethod
    def _cfg(**overrides):
        base = {
            "operations": {
                "denial_capacity": {
                    "enabled": True,
                    "mode": "annual_backlog",
                    "fte": 10.0,
                    "denials_per_fte_per_day": 12.0,
                    "backlog": {"max_over_capacity_x": 3.0},
                    "queue": {"enabled": True, "months": 12,
                              "days_per_month": 30.0},
                },
            },
            "analysis": {"working_days": 250},
        }
        for k, v in overrides.items():
            base["operations"]["denial_capacity"][k] = v
        return base

    def test_disabled_capacity_returns_infinite_touches(self):
        cfg = self._cfg(enabled=False)
        out = compute_capacity(cfg, total_denial_touches=10_000,
                                total_denial_cases=1_000)
        self.assertEqual(out["capacity_touches"], float("inf"))
        self.assertEqual(out["mode"], "annual_backlog")

    def test_unlimited_mode_returns_infinite_touches(self):
        cfg = self._cfg(mode="unlimited")
        out = compute_capacity(cfg, 10_000, 1_000)
        self.assertEqual(out["capacity_touches"], float("inf"))

    def test_outsourced_mode_costs_per_case(self):
        cfg = self._cfg(mode="outsourced", cost_per_case=50.0)
        out = compute_capacity(cfg, 10_000, 500)
        self.assertEqual(out["outsourced_cost"], 25_000.0)
        self.assertEqual(out["capacity_touches"], float("inf"))

    def test_annual_backlog_capacity_from_fte(self):
        # capacity_touches = fte × per_fte_per_day × working_days
        cfg = self._cfg(mode="annual_backlog", fte=10,
                         denials_per_fte_per_day=12)
        out = compute_capacity(cfg, total_denial_touches=10_000,
                                total_denial_cases=1_000)
        # 10 × 12 × 250 = 30_000
        self.assertEqual(out["capacity_touches"], 30_000)

    def test_annual_backlog_computes_backlog_x(self):
        # Demand 60K > capacity 30K → x = 1.0
        cfg = self._cfg()
        out = compute_capacity(cfg, total_denial_touches=60_000,
                                total_denial_cases=1_000)
        self.assertAlmostEqual(out["backlog_x"], 1.0)

    def test_queue_mode_computes_queue_metrics(self):
        cfg = self._cfg(mode="queue")
        out = compute_capacity(cfg, total_denial_touches=60_000,
                                total_denial_cases=1_000)
        # Above-capacity in queue mode → wait days > 0
        self.assertGreater(out["queue_wait_days"], 0)
        self.assertGreater(out["backlog_months_avg"], 0)

    def test_queue_mode_disabled_subkey_keeps_wait_zero(self):
        cfg = self._cfg(mode="queue")
        cfg["operations"]["denial_capacity"]["queue"]["enabled"] = False
        out = compute_capacity(cfg, total_denial_touches=60_000,
                                total_denial_cases=1_000)
        # Queue disabled → backlog_x still computed but no queue
        # wait-days emitted.
        self.assertEqual(out["queue_wait_days"], 0)

    def test_zero_fte_returns_zero_capacity(self):
        cfg = self._cfg(fte=0)
        out = compute_capacity(cfg, 100, 10)
        self.assertEqual(out["capacity_touches"], 0)

    def test_returns_documented_schema_keys(self):
        cfg = self._cfg()
        out = compute_capacity(cfg, 100, 10)
        for k in ("mode", "capacity_touches", "backlog_x",
                  "queue_wait_days", "backlog_months_avg",
                  "backlog_months_max", "outsourced_cost"):
            self.assertIn(k, out, f"missing key {k!r}")


class AssignBucketWaitDaysTests(unittest.TestCase):
    """``assign_bucket_wait_days`` allocates per-bucket wait days
    when high-dollar-first priority is in effect."""

    def test_empty_buckets_does_nothing(self):
        buckets = []
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=10,
                                priority="high_dollar_first")
        self.assertEqual(buckets, [])

    def test_fifo_assigns_uniform_wait(self):
        # FIFO priority → every bucket gets the same wait_days.
        buckets = [
            {"mean_amount": 100, "denial_cases": 10},
            {"mean_amount": 1000, "denial_cases": 10},
            {"mean_amount": 10_000, "denial_cases": 10},
        ]
        assign_bucket_wait_days(buckets, queue_wait_days_base=20,
                                 priority="fifo")
        for b in buckets:
            self.assertEqual(b["queue_wait_days"], 20)

    def test_zero_base_wait_assigns_zero_everywhere(self):
        buckets = [
            {"mean_amount": 100, "denial_cases": 10},
            {"mean_amount": 1000, "denial_cases": 5},
        ]
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=0,
                                priority="high_dollar_first")
        for b in buckets:
            self.assertEqual(b["queue_wait_days"], 0)

    def test_single_bucket_gets_base(self):
        # 1-bucket lists short-circuit to uniform base regardless
        # of priority.
        buckets = [{"mean_amount": 100, "denial_cases": 10}]
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=15,
                                priority="high_dollar_first")
        self.assertEqual(buckets[0]["queue_wait_days"], 15)

    def test_high_dollar_first_short_waits_for_big_buckets(self):
        # high_dollar_first priority → bigger mean_amount → shorter
        # wait_days (work the big claims first).
        buckets = [
            {"mean_amount": 100,    "denial_cases": 10},  # small
            {"mean_amount": 10_000, "denial_cases": 10},  # big
        ]
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=20,
                                priority="high_dollar_first")
        # The big bucket (mean=10K) should have shorter wait than
        # the small one (mean=100).
        self.assertLess(buckets[1]["queue_wait_days"],
                         buckets[0]["queue_wait_days"])

    def test_dollar_weighted_average_preserves_base(self):
        # The factor renormalization ensures the dollar-weighted
        # average wait_days ≈ queue_wait_days_base (so total work
        # is conserved when re-prioritizing).
        buckets = [
            {"mean_amount": 100, "denial_cases": 70},
            {"mean_amount": 1000, "denial_cases": 25},
            {"mean_amount": 10_000, "denial_cases": 5},
        ]
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=20,
                                priority="high_dollar_first")
        # Weighted avg = Σ (cases × wait) / Σ cases  ≈ 20
        total_cases = sum(b["denial_cases"] for b in buckets)
        weighted_avg = sum(
            b["denial_cases"] * b["queue_wait_days"] for b in buckets
        ) / total_cases
        self.assertAlmostEqual(weighted_avg, 20, delta=2.0)

    def test_falls_back_to_uniform_weights_when_no_case_data(self):
        # All denial_cases=0 → fallback to ones → still produces
        # valid (positive) wait_days for every bucket.
        buckets = [
            {"mean_amount": 100, "denial_cases": 0},
            {"mean_amount": 10_000, "denial_cases": 0},
        ]
        assign_bucket_wait_days(buckets,
                                queue_wait_days_base=20,
                                priority="high_dollar_first")
        for b in buckets:
            self.assertGreater(b["queue_wait_days"], 0)


if __name__ == "__main__":
    unittest.main()
