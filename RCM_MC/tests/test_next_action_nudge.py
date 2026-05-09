"""tests for ``next_action_nudge`` (P88)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import _NEXT_ACTION_NUDGES, next_action_nudge


class RegistryShape(unittest.TestCase):

    def test_each_entry_has_headline_and_href(self) -> None:
        for key, spec in _NEXT_ACTION_NUDGES.items():
            with self.subTest(key=key):
                self.assertIn("headline", spec)
                self.assertIn("href", spec)


class NudgeRendering(unittest.TestCase):

    def test_ingest_routes_to_benchmarks(self) -> None:
        html = next_action_nudge(completed_module="ingest")
        self.assertIn("Benchmarks", html)
        self.assertIn('href="/diligence/benchmarks"', html)

    def test_bridge_audit_routes_to_comparable_outcomes(self) -> None:
        html = next_action_nudge(completed_module="bridge_audit")
        self.assertIn("/diligence/comparable-outcomes", html)

    def test_deal_id_appended(self) -> None:
        html = next_action_nudge(
            completed_module="ingest", deal_id="aurora",
        )
        self.assertIn("?deal_id=aurora", html)

    def test_unknown_module_returns_empty(self) -> None:
        self.assertEqual(
            next_action_nudge(completed_module="nonsense"),
            "",
        )

    def test_uses_eyebrow_label(self) -> None:
        html = next_action_nudge(completed_module="ingest")
        self.assertIn("Next:", html)


if __name__ == "__main__":
    unittest.main()
