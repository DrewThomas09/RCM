"""tests for ``diligence_complete_banner`` (P69)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import diligence_complete_banner


def _all_pass(**overrides) -> dict:
    base = dict(
        p0_coverage=1.0,
        health_score=92,
        n_critical=0,
        bridge_variance=0.06,
    )
    base.update(overrides)
    return base


class FullPassRendersBanner(unittest.TestCase):

    def test_renders(self) -> None:
        html = diligence_complete_banner(**_all_pass())
        self.assertIn("Diligence is complete enough", html)
        self.assertIn("Schedule IC", html)
        self.assertIn("diligence-complete-banner", html)


class AnyMissCollapsesBanner(unittest.TestCase):

    def test_low_p0_coverage(self) -> None:
        html = diligence_complete_banner(**_all_pass(p0_coverage=0.85))
        self.assertEqual(html, "")

    def test_low_health_score(self) -> None:
        html = diligence_complete_banner(**_all_pass(health_score=85))
        self.assertEqual(html, "")

    def test_critical_panel(self) -> None:
        html = diligence_complete_banner(**_all_pass(n_critical=1))
        self.assertEqual(html, "")

    def test_high_bridge_variance(self) -> None:
        html = diligence_complete_banner(**_all_pass(bridge_variance=0.12))
        self.assertEqual(html, "")


class BoundaryConditions(unittest.TestCase):

    def test_p0_exactly_one_passes(self) -> None:
        html = diligence_complete_banner(**_all_pass(p0_coverage=1.0))
        self.assertNotEqual(html, "")

    def test_health_exactly_90_passes(self) -> None:
        html = diligence_complete_banner(**_all_pass(health_score=90))
        self.assertNotEqual(html, "")

    def test_variance_just_under_10_pct(self) -> None:
        html = diligence_complete_banner(**_all_pass(bridge_variance=0.0999))
        self.assertNotEqual(html, "")

    def test_variance_at_10_pct_does_not_pass(self) -> None:
        html = diligence_complete_banner(**_all_pass(bridge_variance=0.10))
        self.assertEqual(html, "")


class GracefulInput(unittest.TestCase):

    def test_non_numeric_inputs_return_empty(self) -> None:
        html = diligence_complete_banner(
            p0_coverage="not a number",
            health_score=92, n_critical=0, bridge_variance=0.06,
        )
        self.assertEqual(html, "")


if __name__ == "__main__":
    unittest.main()
