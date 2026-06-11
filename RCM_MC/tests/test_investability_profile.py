"""Wave-10 visual: exit-readiness dimension profile.

The investability page's exit-readiness panel listed 12 dimensions in
a table; the weakest dimensions — the ones dragging the verdict — had
no visual ranking. Pins the fixed-axis profile SVG: weakest-first
order, status tones, composite guide line, and empty states.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.chartis.investability_page import (
    _FINDING_STATUS_COLORS,
    _readiness_profile_svg,
)


def _finding(dim, score, status, weight=None):
    return SimpleNamespace(
        dimension=dim, score=score, status=status, weight=weight,
        commentary="",
    )


def _report(findings, score=60):
    return SimpleNamespace(findings=findings, score=score)


class ReadinessProfileTests(unittest.TestCase):
    def test_renders_weakest_first_with_status_tones(self):
        svg = _readiness_profile_svg(_report([
            _finding("Audited financials", 90, "ready", 0.10),
            _finding("Data room", 20, "not_ready", 0.05),
            _finding("QoE", 55, "concern", 0.10),
        ]))
        self.assertIn("<svg", svg)
        self.assertIn("ck-exit-profile", svg)
        # Weakest (Data room, 20) leads; strongest last.
        self.assertLess(svg.index("Data room"), svg.index("QoE"))
        self.assertLess(svg.index("QoE"), svg.index("Audited financials"))
        self.assertIn(_FINDING_STATUS_COLORS["not_ready"], svg)
        self.assertIn(_FINDING_STATUS_COLORS["concern"], svg)
        self.assertIn(_FINDING_STATUS_COLORS["ready"], svg)

    def test_composite_guide_and_weight_labels(self):
        svg = _readiness_profile_svg(_report(
            [_finding("Legal", 40, "gap", 0.08)], score=60,
        ))
        self.assertIn("stroke-dasharray", svg)   # composite guide
        self.assertIn("w 8%", svg)               # weight label

    def test_unscored_findings_omitted(self):
        svg = _readiness_profile_svg(_report([
            _finding("KPI reporting", None, "unknown"),
            _finding("Legal", 40, "gap"),
        ]))
        self.assertNotIn("KPI reporting", svg)
        self.assertIn("Legal", svg)

    def test_empty_states_render_nothing(self):
        self.assertEqual(_readiness_profile_svg(None), "")
        self.assertEqual(_readiness_profile_svg(_report([])), "")
        self.assertEqual(
            _readiness_profile_svg(_report(
                [_finding("Legal", None, "unknown")]
            )),
            "",
        )


if __name__ == "__main__":
    unittest.main()
