"""The hospital-history page carries the deal-context ribbon.

render_hospital_history (/hospital/<ccn>/history) used a bespoke
cad-btn cross-links bar. It now leads with the standard _model_nav
pill ribbon; the panel is trimmed to just the state-market link the
ribbon doesn't carry. History isn't a ribbon slot, so no pill is
highlighted.
"""
from __future__ import annotations

import unittest

import pandas as pd


class HospitalHistoryDealRibbonTests(unittest.TestCase):
    def _html(self) -> str:
        from rcm_mc.ui.hospital_history import render_hospital_history
        trend = pd.DataFrame({
            "year": [2019, 2020, 2021, 2022],
            "net_patient_revenue": [1.4e8, 1.45e8, 1.5e8, 1.55e8],
            "operating_margin": [0.04, 0.03, 0.05, 0.06],
            "beds": [200, 200, 200, 200],
        })
        return render_hospital_history("010001", "Test Hosp", trend, state="GA")

    def test_carries_model_ribbon_and_sibling_links(self):
        html = self._html()
        self.assertIn("ck-model-pill", html)
        self.assertIn("/ebitda-bridge/010001", html)
        self.assertIn("/models/returns/010001", html)

    def test_state_market_link_retained(self):
        html = self._html()
        self.assertIn("Market context", html)
        self.assertIn("/market-data/state/GA", html)


if __name__ == "__main__":
    unittest.main()
