"""Pin for the Launched-vs-Realized value-creation panel (PR 8).

Definitions implemented by _value_creation_panel:
  * Launched  = Σ cumulative underwritten plan of initiatives in
    execution (≥1 quarter of actuals), portfolio-level.
  * Realized  = Σ cumulative actual EBITDA impact recorded to date
    (run-rate, not TTM, not re-attributed).
  * Capture   = realized / launched.

When no actuals exist the panel shows an honest empty state — never a
fabricated number.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui import portfolio_monitor_page as pmp


class ValueCreationPanelTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self._tmp.name, "p.db"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_state_when_no_actuals(self):
        panel = pmp._value_creation_panel(self.store)
        self.assertIn("Value Creation", panel)
        self.assertIn("No initiative actuals recorded yet", panel)

    def _patched(self, df):
        return mock.patch(
            "rcm_mc.rcm.initiative_rollup.initiative_portfolio_rollup",
            return_value=df,
        )

    def test_launched_realized_and_capture_math(self):
        # 3 initiatives: plan Σ = 10.0M, actual Σ = 7.0M → 70% capture.
        df = pd.DataFrame({
            "initiative_id": ["a", "b", "c"],
            "cumulative_plan": [5.0e6, 3.0e6, 2.0e6],
            "cumulative_actual": [4.0e6, 2.0e6, 1.0e6],
        })
        with self._patched(df):
            panel = pmp._value_creation_panel(self.store)
        self.assertIn("70%", panel)               # capture rate
        self.assertIn("3 initiatives", panel)
        self.assertIn("Launched", panel)
        self.assertIn("Realized", panel)

    def test_states_definitions_for_defensibility(self):
        df = pd.DataFrame({
            "initiative_id": ["a", "b"],
            "cumulative_plan": [5.0e6, 5.0e6],
            "cumulative_actual": [4.0e6, 4.0e6],
        })
        with self._patched(df):
            panel = pmp._value_creation_panel(self.store)
        # The panel must state how launched/realized are measured.
        self.assertIn("≥1 quarter of actuals", panel)
        self.assertIn("not TTM", panel)

    def test_nan_plan_or_actual_ignored(self):
        df = pd.DataFrame({
            "initiative_id": ["a", "b"],
            "cumulative_plan": [10.0e6, float("nan")],
            "cumulative_actual": [5.0e6, float("nan")],
        })
        with self._patched(df):
            panel = pmp._value_creation_panel(self.store)
        # Only the finite row contributes: 5M of 10M = 50%.
        self.assertIn("50%", panel)


if __name__ == "__main__":
    unittest.main()
