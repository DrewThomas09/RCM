"""Tests for the post-close value-tracking engine.

`rcm_mc/pe/value_tracker.py` is the feedback loop that makes every
closed deal improve the next underwrite. The 3 untested public
entry points:

  - record_quarterly_lever — book one (deal, quarter, lever)
    actual, compute realization vs the frozen-bridge plan
  - get_tracking_summary — aggregate per-lever realization +
    classify on_track / lagging / off_track + emit narrative
  - feed_prediction_ledger — push every realized value into the
    prediction ledger so the model improves

freeze_bridge_as_plan + get_plan are tested via integration paths;
the 3 above had no direct coverage. Uses temp sqlite for fixtures
(same pattern as test_fund_learning).
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from rcm_mc.pe.value_tracker import (
    ValueTrackingSummary,
    feed_prediction_ledger,
    freeze_bridge_as_plan,
    get_plan,
    get_tracking_summary,
    record_quarterly_lever,
)


def _con() -> sqlite3.Connection:
    """In-memory sqlite for fast test fixtures."""
    return sqlite3.connect(":memory:")


def _basic_bridge():
    """A 3-lever bridge plan, total uplift = $4M."""
    return {
        "total_ebitda_impact": 4_000_000,
        "levers": [
            {"name": "denial_reduction", "metric": "denial_rate",
             "ebitda_impact": 2_000_000, "ramp_months": 12},
            {"name": "dso_compression",  "metric": "days_in_ar",
             "ebitda_impact": 1_500_000, "ramp_months": 18},
            {"name": "underpay_recovery", "metric": "underpay_severity",
             "ebitda_impact": 500_000, "ramp_months": 6},
        ],
    }


class RecordQuarterlyLeverTests(unittest.TestCase):
    """Contract for ``record_quarterly_lever``."""

    def test_inserts_actual_with_realization(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=100_000)
        rows = con.execute(
            "SELECT lever, planned_impact, actual_impact, "
            "realization_pct FROM value_creation_actuals "
            "WHERE deal_id = ?", ("d1",)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        lever, planned, actual, realization = rows[0]
        self.assertEqual(lever, "denial_reduction")
        self.assertEqual(actual, 100_000)
        # planned at Q1 = 2M × (3/12) / 4 = 125_000
        self.assertAlmostEqual(planned, 125_000)
        # realization = 100K / 125K = 0.8
        self.assertAlmostEqual(realization, 0.8)

    def test_planned_scales_with_quarter_progression(self):
        # Q1 → 3 months, Q4 → 12 months. Planned impact at Q1 is
        # 1/4 of full-year (3/12 ramp × 1/4 for quarterly slice).
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "2026Q1",
                                "dso_compression", actual_impact=0)
        record_quarterly_lever(con, "d1", "2026Q4",
                                "dso_compression", actual_impact=0)
        rows = con.execute(
            "SELECT quarter, planned_impact FROM value_creation_actuals "
            "WHERE deal_id = ? ORDER BY quarter", ("d1",)
        ).fetchall()
        q1_planned = rows[0][1]
        q4_planned = rows[1][1]
        # Q4 ramp 12/18 vs Q1 ramp 3/18 → 4× scaling
        self.assertGreater(q4_planned, q1_planned)
        self.assertAlmostEqual(q4_planned / q1_planned, 4.0, delta=0.01)

    def test_zero_planned_safe(self):
        # Lever not in plan → planned=0 → realization=0
        # (no divide-by-zero).
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "2026Q1",
                                "non_existent_lever",
                                actual_impact=50_000)
        rows = con.execute(
            "SELECT planned_impact, realization_pct "
            "FROM value_creation_actuals WHERE deal_id = ?",
            ("d1",)).fetchall()
        self.assertEqual(rows[0][0], 0)
        self.assertEqual(rows[0][1], 0)

    def test_unparseable_quarter_falls_back_to_month_3(self):
        # If the quarter string can't be parsed, default to month 3
        # (one-quarter ramp). Defensive: don't crash.
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "garbage",
                                "denial_reduction", actual_impact=0)
        rows = con.execute(
            "SELECT planned_impact FROM value_creation_actuals "
            "WHERE deal_id = ?", ("d1",)).fetchall()
        # Should match Q1 (3 months) planned value
        self.assertAlmostEqual(rows[0][0], 125_000)

    def test_overwrites_same_lever_in_same_quarter(self):
        # UNIQUE(deal_id, quarter, lever) → INSERT OR REPLACE
        # → second call updates the row.
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=100_000)
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=150_000,
                                notes="updated")
        rows = con.execute(
            "SELECT actual_impact, notes FROM value_creation_actuals "
            "WHERE deal_id = ?", ("d1",)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 150_000)
        self.assertEqual(rows[0][1], "updated")


class GetTrackingSummaryTests(unittest.TestCase):
    """Contract for ``get_tracking_summary``."""

    def test_returns_none_for_unknown_deal(self):
        con = _con()
        self.assertIsNone(get_tracking_summary(con, "no_such_deal"))

    def test_aggregates_across_quarters(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # 3 quarters of denial_reduction actuals
        for q, val in [("2026Q1", 100_000), ("2026Q2", 200_000),
                        ("2026Q3", 250_000)]:
            record_quarterly_lever(con, "d1", q, "denial_reduction",
                                    actual_impact=val)
        s = get_tracking_summary(con, "d1")
        self.assertIsInstance(s, ValueTrackingSummary)
        self.assertEqual(s.total_realized, 550_000)
        self.assertEqual(s.quarters_tracked, 3)

    def test_classifies_on_track_at_85_pct(self):
        # >=85% realization → on_track
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # Planned Q1 = 125K; actual 110K → 88% → on_track
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=110_000)
        s = get_tracking_summary(con, "d1")
        self.assertEqual(s.on_track_count, 1)
        self.assertEqual(s.lagging_count, 0)
        self.assertEqual(s.off_track_count, 0)
        self.assertIn("On track", s.ramp_assessment)

    def test_classifies_lagging_at_60_to_85(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # 70% realization → lagging
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=87_500)  # 70% of 125K
        s = get_tracking_summary(con, "d1")
        self.assertEqual(s.lagging_count, 1)
        self.assertEqual(s.on_track_count, 0)
        self.assertEqual(s.off_track_count, 0)
        self.assertIn("Lagging", s.ramp_assessment)

    def test_classifies_off_track_below_60(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # 40% realization → off_track
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=50_000)  # 40% of 125K
        s = get_tracking_summary(con, "d1")
        self.assertEqual(s.off_track_count, 1)
        self.assertEqual(s.lagging_count, 0)
        self.assertEqual(s.on_track_count, 0)
        self.assertIn("Off track", s.ramp_assessment)

    def test_levers_sorted_by_absolute_actual_desc(self):
        # The levers list is sorted by |actual| desc — biggest
        # dollar contributor first (UI shows the most-impactful lever
        # at top).
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        record_quarterly_lever(con, "d1", "2026Q1",
                                "underpay_recovery",
                                actual_impact=10_000)
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=100_000)
        record_quarterly_lever(con, "d1", "2026Q1",
                                "dso_compression",
                                actual_impact=50_000)
        s = get_tracking_summary(con, "d1")
        actuals = [l["actual"] for l in s.levers]
        self.assertEqual(
            actuals, sorted(actuals, key=abs, reverse=True),
        )

    def test_realization_pct_overall(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # Total planned at Q1 (over all 3 levers):
        # 2M × 3/12 / 4 = 125K + 1.5M × 3/18 / 4 = 62.5K +
        # 0.5M × 3/6 / 4 = 62.5K = 250K
        # Actuals sum = 0 + 0 + 0 = 0 → 0%
        # Easier: only record one lever fully.
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=125_000)  # 100% of 125K
        s = get_tracking_summary(con, "d1")
        self.assertAlmostEqual(s.realization_pct, 1.0, places=3)


class FeedPredictionLedgerTests(unittest.TestCase):
    """Contract for ``feed_prediction_ledger``."""

    def test_returns_zero_for_unknown_deal(self):
        con = _con()
        self.assertEqual(feed_prediction_ledger(con, "no_such"), 0)

    def test_feeds_one_record_per_lever_with_planned_gt_zero(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # Record actuals on 2 of 3 levers
        record_quarterly_lever(con, "d1", "2026Q1",
                                "denial_reduction",
                                actual_impact=100_000)
        record_quarterly_lever(con, "d1", "2026Q1",
                                "dso_compression",
                                actual_impact=50_000)
        n_fed = feed_prediction_ledger(con, "d1")
        # 2 levers with planned > 0 → 2 records fed back
        self.assertEqual(n_fed, 2)

    def test_skips_levers_with_zero_planned(self):
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        # Record an actual for a lever NOT in the plan → planned=0
        # → skipped in feed_prediction_ledger.
        record_quarterly_lever(con, "d1", "2026Q1",
                                "non_existent",
                                actual_impact=50_000)
        n_fed = feed_prediction_ledger(con, "d1")
        # The orphan lever has planned=0 → skipped.
        self.assertEqual(n_fed, 0)

    def test_no_actuals_returns_zero(self):
        # Plan exists but no actuals recorded yet → tracking summary
        # has levers=[] → 0 records fed.
        con = _con()
        freeze_bridge_as_plan(con, "d1", "12345", "Hosp A",
                               _basic_bridge())
        self.assertEqual(feed_prediction_ledger(con, "d1"), 0)


if __name__ == "__main__":
    unittest.main()
