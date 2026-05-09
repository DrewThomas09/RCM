"""tests for ``run_live_link`` (P79)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import _WORKBENCH_TAB_TO_MODULE, run_live_link


class CanonicalMappings(unittest.TestCase):

    EXPECTED = {
        "rcm-profile":   "/diligence/benchmarks",
        "ebitda-bridge": "/diligence/bridge-audit",
        "monte-carlo":   "/diligence/deal-mc",
        "risk":          "/diligence/risk-workbench",
    }

    def test_each_known_tab_links_to_module(self) -> None:
        for tab, expected_target in self.EXPECTED.items():
            with self.subTest(tab=tab):
                html = run_live_link(tab, "aurora")
                self.assertIn(
                    f'href="{expected_target}?deal_id=aurora"',
                    html,
                )

    def test_overview_has_no_live_link(self) -> None:
        # Overview is a synthesis surface — no module to "run live".
        self.assertEqual(run_live_link("overview", "aurora"), "")


class GracefulInput(unittest.TestCase):

    def test_unknown_tab_returns_empty(self) -> None:
        self.assertEqual(run_live_link("unknown-tab", "aurora"), "")

    def test_no_deal_returns_empty(self) -> None:
        self.assertEqual(run_live_link("rcm-profile", ""), "")


class RegistryShape(unittest.TestCase):

    def test_registry_has_at_least_workbench_core_tabs(self) -> None:
        for tab in ("rcm-profile", "ebitda-bridge", "monte-carlo",
                    "risk", "health"):
            with self.subTest(tab=tab):
                self.assertIn(tab, _WORKBENCH_TAB_TO_MODULE)


if __name__ == "__main__":
    unittest.main()
