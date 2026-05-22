"""The predictive screener leads with the screen's aggregate opportunity.

The page used to open with a 5-up KPI strip; the headline (total
estimated EBITDA uplift across the matched universe) was buried as
KPI #2. This pins that a ck_value_anchor band now surfaces it at the
top, ahead of the results table.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=60):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY"], n),
        "county": rng.choice(["A", "B"], n),
        "beds": rng.choice([25, 100, 300, 500], n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 3e9, n),
        "operating_expenses": rng.uniform(4e7, 2.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 8e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class PredictiveScreenerLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        return render_predictive_screener(_sample_hcris(), "")

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("SCREEN OPPORTUNITY", html)
        self.assertIn("total est. uplift", html)

    def test_anchor_leads_before_results(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Screening Results"),
        )


if __name__ == "__main__":
    unittest.main()
