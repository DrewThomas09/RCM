"""Regression: the focused /app initiative tracker reads the columns the
variance report actually emits.

The report emits cumulative_actual / cumulative_plan (dollars) keyed by
initiative_id. The tracker used to read actual_cumulative_M /
plan_cumulative_M / initiative_name, which don't exist — so every row
showed $0 actual, 0% variance, and a blank name. This pins the fix.
"""
from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd


class InitiativeTrackerColumnsTests(unittest.TestCase):
    def test_reads_real_columns_and_resolves_name(self):
        from rcm_mc.ui.chartis import _app_initiative_tracker as it
        df = pd.DataFrame({
            "deal_id": ["d1", "d1"],
            "initiative_id": ["denial_workflow_automation", "coding_cdi"],
            "quarters_active": [3, 2],
            "cumulative_actual": [2_400_000.0, 900_000.0],
            "cumulative_plan": [3_000_000.0, 1_000_000.0],
            "variance_pct": [-0.20, -0.10],
            "severity": ["watch", "ok"],
        })
        with mock.patch(
            "rcm_mc.rcm.initiative_tracking.initiative_variance_report",
            return_value=df,
        ):
            rows = it._fetch_initiative_rows(object(), "d1")
        self.assertEqual(len(rows), 2)
        # Actuals are non-zero now (read from cumulative_actual).
        self.assertTrue(all(r["actual"] > 0 for r in rows))
        # Variance computed from the right columns: 2.4M of 3.0M = -20%.
        worst = rows[0]  # sorted by |variance| desc
        self.assertAlmostEqual(worst["actual"], 2_400_000.0)
        self.assertAlmostEqual(worst["variance"], -20.0, places=1)
        # Names resolved (not blank): titleized id at worst.
        self.assertTrue(all(r["name"] for r in rows))

    def test_empty_report_returns_empty(self):
        from rcm_mc.ui.chartis import _app_initiative_tracker as it
        with mock.patch(
            "rcm_mc.rcm.initiative_tracking.initiative_variance_report",
            return_value=pd.DataFrame(),
        ):
            self.assertEqual(it._fetch_initiative_rows(object(), "d1"), [])


class MorningBriefStageOrderTests(unittest.TestCase):
    def test_stage_order_matches_canonical_deal_stages(self):
        from rcm_mc.ui.chartis._app_morning_brief import _STAGE_ORDER
        # The funnel must include the canonical stages that were being
        # silently dropped before (sourced, spa).
        self.assertIn("sourced", _STAGE_ORDER)
        self.assertIn("spa", _STAGE_ORDER)
        self.assertNotIn("sourcing", _STAGE_ORDER)  # the stale label
        self.assertNotIn("diligence", _STAGE_ORDER)


if __name__ == "__main__":
    unittest.main()
