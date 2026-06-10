"""Workbench EBITDA-Opportunity hero must not fabricate a green $0.

When the bridge couldn't run (no levers contributed / section not OK) the
hero showed "$0" in positive green — reading as "no opportunity" when the
truth is "not computed". It now gates on the bridge's own status + evidence
and renders an honest dash with the bridge's reason.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket, EBITDABridgeResult, SectionStatus,
)


def _shell_packet(bridge) -> DealAnalysisPacket:
    p = DealAnalysisPacket(deal_id="t1", deal_name="Test Deal")
    p.ebitda_bridge = bridge
    return p


class HonestHeroTests(unittest.TestCase):
    def _render(self, packet):
        from rcm_mc.ui.analysis_workbench import render_workbench
        return render_workbench(packet)

    def test_skipped_bridge_renders_dash_with_reason(self):
        b = EBITDABridgeResult(status=SectionStatus.SKIPPED,
                               reason="no revenue baseline")
        h = self._render(_shell_packet(b))
        self.assertIn("not computed: no revenue baseline", h)
        self.assertNotIn('class="hero-number pos">$0<', h)

    def test_ok_bridge_with_no_impacts_still_dashes(self):
        # status OK but zero levers contributed → nothing was computed FROM.
        b = EBITDABridgeResult(status=SectionStatus.OK,
                               total_ebitda_impact=0.0)
        h = self._render(_shell_packet(b))
        self.assertIn("not computed", h)


if __name__ == "__main__":
    unittest.main()
