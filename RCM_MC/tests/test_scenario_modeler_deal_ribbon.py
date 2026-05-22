"""The per-deal scenario modeler carries the deal-context ribbon.

The /scenarios/<ccn> modeler is the ribbon's "SCN" slot but used a
bespoke cad-btn cross-links bar. It now leads with the standard
_model_nav pill ribbon (consistent with every other per-deal surface);
the partial bespoke bar is removed since the ribbon covers those links
and more.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=40):
    rng = np.random.RandomState(7)
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


class ScenarioModelerDealRibbonTests(unittest.TestCase):
    def _html(self) -> str:
        from rcm_mc.ui.scenario_modeler_page import render_scenario_modeler
        return render_scenario_modeler("000001", _sample_hcris(), "")

    def test_carries_model_ribbon(self):
        html = self._html()
        self.assertIn("ck-model-pill", html)
        self.assertIn("/models/returns/000001", html)
        self.assertIn("/ebitda-bridge/000001", html)

    def test_bespoke_crosslinks_panel_removed(self):
        html = self._html()
        self.assertNotIn("Cross-links", html)


if __name__ == "__main__":
    unittest.main()
