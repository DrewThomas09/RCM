"""The EBITDA bridge carries the standard deal-context ribbon.

The bridge used to rely on a bespoke "Cross-links" panel for generic
deal navigation. It now leads with the standard _model_nav pill ribbon
(consistent with every other per-deal surface), and the bottom panel
is trimmed to just the bridge-specific actions (Freeze as Value Plan,
Download Excel, Value Tracker, Fund Learning) that the ribbon doesn't
carry.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=40):
    rng = np.random.RandomState(5)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"H{i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX"], n),
        "beds": rng.choice([150, 300], n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 2e9, n),
        "operating_expenses": rng.uniform(4e7, 1.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 5e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class EbitdaBridgeDealRibbonTests(unittest.TestCase):
    def _html(self) -> str:
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        return render_ebitda_bridge("000001", _sample_hcris())

    def test_carries_model_ribbon(self):
        html = self._html()
        self.assertIn("ck-model-pill", html)
        self.assertIn("/models/returns/000001", html)

    def test_panel_trimmed_to_bridge_actions(self):
        html = self._html()
        self.assertIn("Bridge actions", html)
        self.assertIn("Freeze as Value Plan", html)
        # generic nav links no longer duplicated in the panel
        panel = html.split("Bridge actions")[1][:500]
        self.assertNotIn("Deal Screener", panel)
        self.assertNotIn("DCF", panel)


if __name__ == "__main__":
    unittest.main()
