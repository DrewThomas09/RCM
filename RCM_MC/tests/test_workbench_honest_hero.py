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


class RealizationHoldoutTests(unittest.TestCase):
    """The bridge-realization accuracy shown to partners must be measured on
    rows the model never trained on (was in-sample), and the UI must name
    the engine specifically (logistic regression), never generically."""

    def test_accuracy_is_holdout_and_reproducible(self):
        import pandas as pd
        from rcm_mc.ml.realization_predictor import train_realization_model
        import numpy as np
        rng = np.random.RandomState(3)
        n = 400
        df = pd.DataFrame({
            "ccn": [f"{i:06d}" for i in range(n)],
            "state": ["TX"] * (n // 2) + ["CA"] * (n - n // 2),
            "operating_margin": rng.normal(0.03, 0.05, n),
            "occupancy_rate": rng.uniform(0.3, 0.9, n),
            "revenue_per_bed": rng.uniform(5e5, 3e6, n),
            "beds": rng.uniform(50, 800, n),
            "commercial_pct": rng.uniform(0.1, 0.6, n),
            "net_to_gross_ratio": rng.uniform(0.15, 0.45, n),
            "payer_diversity": rng.uniform(0.2, 0.65, n),
            "log_beds": rng.uniform(3.5, 6.5, n),
        })
        b1 = train_realization_model(df)
        b2 = train_realization_model(df)
        # n_training is the TRAIN split (80%), not the full frame
        self.assertEqual(b1[4], int(n - max(1, int(n * 0.20))))
        # seeded split → identical accuracy across calls (reproducible claim)
        self.assertEqual(b1[3], b2[3])

    def test_bridge_page_names_the_engine(self):
        import pathlib
        src = pathlib.Path("rcm_mc/ui/ebitda_bridge_page.py").read_text()
        self.assertIn("Logistic regression", src)
        self.assertIn("Holdout accuracy", src)
        self.assertNotIn("ML model predicts", src)
