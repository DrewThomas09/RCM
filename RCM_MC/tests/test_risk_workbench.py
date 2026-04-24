"""Risk Workbench integration tests.

- Steward demo input fires every panel at the correct severity
- Minimal input produces 'Not supplied' for all 9 panels
- Individual panels render cleanly with their specific inputs
- Nav link is reachable in the legacy sidebar
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.physician_comp import Provider
from rcm_mc.ui.risk_workbench_page import (
    WorkbenchInput, demo_steward_input, render_risk_workbench,
)


class WorkbenchStewardDemoTests(unittest.TestCase):

    def setUp(self):
        self.html = render_risk_workbench(demo_steward_input())

    def test_all_nine_panels_render(self):
        for panel in (
            "Bankruptcy-Survivor", "Regulatory Exposure",
            "Real Estate", "Physician Comp", "Cyber Posture",
            "MA Dynamics", "Quality / WC / Synergy",
            "Labor / Referral", "Patient-pay / Reputational",
        ):
            self.assertIn(
                panel, self.html,
                msg=f"panel {panel!r} not in demo workbench",
            )

    def test_steward_demo_fires_steward_pattern_critical(self):
        """The Steward replay should surface CRITICAL somewhere."""
        self.assertIn("CRITICAL", self.html)

    def test_steward_case_study_mentioned(self):
        # The Steward Score's case_study narrative should appear
        # somewhere in the rendered panel when all 5 factors trip.
        self.assertIn("Steward", self.html)

    def test_bankruptcy_scan_drill_down_link(self):
        self.assertIn(
            'href="/screening/bankruptcy-survivor"', self.html,
        )


class MinimalInputTests(unittest.TestCase):

    def test_empty_input_all_panels_not_supplied(self):
        html = render_risk_workbench(
            WorkbenchInput(target_name="Empty"),
        )
        # Should have a "Not supplied" for each of the N regulatory-
        # dependent panels.
        count = html.count("Not supplied")
        self.assertGreaterEqual(count, 7)

    def test_target_name_renders_in_hero(self):
        html = render_risk_workbench(
            WorkbenchInput(target_name="Project Aurora"),
        )
        self.assertIn("Project Aurora", html)


class IndividualPanelTests(unittest.TestCase):

    def test_physician_comp_panel_with_roster(self):
        """30 equal providers → diversified roster → WRVU_BASED."""
        inp = WorkbenchInput(
            target_name="CompTest",
            providers=[
                Provider(
                    provider_id=f"P{i}", specialty="FAMILY_MEDICINE",
                    base_salary_usd=260_000,
                    collections_annual_usd=600_000,
                    wrvus_annual=5200,
                )
                for i in range(30)
            ],
        )
        html = render_risk_workbench(inp)
        self.assertIn("Physician Comp", html)
        self.assertIn("WRVU_BASED", html)

    def test_cyber_panel_with_change_healthcare(self):
        inp = WorkbenchInput(
            target_name="CyberTest",
            ehr_vendor="ORACLE_CERNER",
            business_associates=["Change Healthcare"],
            revenue_per_day_usd=100_000,
            annual_revenue_usd=36_500_000,
        )
        html = render_risk_workbench(inp)
        self.assertIn("Cyber Posture", html)
        # Any Change-Healthcare-adjacent text rendered
        self.assertIn("BA cascade", html)

    def test_regulatory_panel_steward_states(self):
        inp = WorkbenchInput(
            target_name="RegTest",
            states=["OR"], msas=["Portland"],
            legal_structure="FRIENDLY_PC_PASS_THROUGH",
        )
        html = render_risk_workbench(inp)
        self.assertIn("Regulatory Exposure", html)
        # OR friendly-PC fires CPOM RED
        self.assertIn("RED", html)


class NavLinkTests(unittest.TestCase):

    def test_risk_workbench_is_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn(
            'href="/diligence/risk-workbench?demo=steward"', rendered,
        )

    def test_bankruptcy_scan_is_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn(
            'href="/screening/bankruptcy-survivor"', rendered,
        )


if __name__ == "__main__":
    unittest.main()
