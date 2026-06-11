"""The denial-driver page leads with the computed recovery opportunity.

The page used to open with a 4-up KPI grid; the headline (recoverable
EBITDA from moving the denial rate to target) was buried as KPI #3 and
in the "What This Means" card. This pins that a ck_value_anchor band
now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.denial_page import render_denial_page


class DenialLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        analysis = {
            "summary": {
                "total_annual_impact": 4_500_000,
                "current_denial_rate": 14.0,
                "target_denial_rate": 9.0,
            },
            "drivers": [
                {"driver": "Eligibility", "contribution_pct": 30,
                 "annual_impact": 1.5e6, "severity": "high"},
            ],
            "recommendations": [],
        }
        return render_denial_page("d1", "Test Deal", analysis)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("DENIAL RECOVERY", html)
        self.assertIn("recoverable EBITDA", html)

    def test_anchor_leads_before_root_causes(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Denial Root Causes"),
        )


if __name__ == "__main__":
    unittest.main()


class DriverParetoChartTests(unittest.TestCase):
    """Wave-8 visual: Pareto SVG of root causes by annual impact."""

    def _analysis(self):
        return {
            "summary": {
                "total_annual_impact": 4_500_000,
                "current_denial_rate": 14.0,
                "target_denial_rate": 9.0,
            },
            "drivers": [
                {"driver": "Eligibility", "contribution_pct": 30,
                 "annual_impact": 1.5e6, "severity": "high"},
                {"driver": "Prior authorization", "contribution_pct": 25,
                 "annual_impact": 2.0e6, "severity": "medium"},
                {"driver": "Duplicate claim", "contribution_pct": 10,
                 "annual_impact": 0.5e6, "severity": "low"},
            ],
            "recommendations": [],
        }

    def test_pareto_renders_with_severity_tones(self):
        from rcm_mc.ui.denial_page import _driver_pareto_svg
        svg = _driver_pareto_svg(self._analysis()["drivers"])
        self.assertIn("<svg", svg)
        self.assertIn("ck-driver-pareto", svg)
        self.assertIn("#b5321e", svg)   # high severity tone
        self.assertIn("#b8732a", svg)   # medium
        self.assertIn("#7a8699", svg)   # low
        self.assertIn("cum 100%", svg)  # last bar closes the running share

    def test_pareto_sorted_largest_first(self):
        from rcm_mc.ui.denial_page import _driver_pareto_svg
        svg = _driver_pareto_svg(self._analysis()["drivers"])
        # Prior auth ($2.0M) must appear before Eligibility ($1.5M).
        self.assertLess(svg.index("Prior authorization"),
                        svg.index("Eligibility"))

    def test_pareto_in_page_before_table(self):
        html = render_denial_page("d1", "Test Deal", self._analysis())
        self.assertIn("ck-driver-pareto", html)
        self.assertLess(html.index("ck-driver-pareto"),
                        html.index('<table class="cad-table"'))

    def test_empty_drivers_render_nothing(self):
        from rcm_mc.ui.denial_page import _driver_pareto_svg
        self.assertEqual(_driver_pareto_svg([]), "")
        self.assertEqual(
            _driver_pareto_svg([{"driver": "X", "annual_impact": 0}]), "")

    def test_page_survives_empty_analysis(self):
        html = render_denial_page("d1", "Test Deal", {
            "summary": {}, "drivers": [], "recommendations": [],
        })
        self.assertNotIn("ck-driver-pareto", html)
