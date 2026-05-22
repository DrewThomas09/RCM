"""The per-deal competitive-intel page carries the deal-context ribbon.

The page used to end with a bespoke 6-button cad-btn bar — an
inconsistent, partial set of links. It now leads with the same
_model_nav pill ribbon the model pages use, so every sibling analysis
on the deal is one click away in consistent editorial styling.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=40):
    rng = np.random.RandomState(1)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"H{i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX"], n),
        "beds": rng.choice([100, 300], n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 2e9, n),
        "operating_expenses": rng.uniform(4e7, 1.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 5e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class CompetitiveIntelDealRibbonTests(unittest.TestCase):
    def _html(self) -> str:
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        return render_competitive_intel("000001", _sample_hcris())

    def test_carries_model_ribbon(self):
        html = self._html()
        self.assertIn("ck-model-pill", html)
        self.assertIn("Comp Intel", html)

    def test_ribbon_leads_the_body(self):
        html = self._html()
        # Ribbon renders ahead of the body explainer prose + KPIs.
        self.assertLess(
            html.index("ck-model-pill"),
            html.index("Per-metric percentile ranks"),
        )

    def test_links_to_sibling_analyses(self):
        html = self._html()
        for href in ("/ebitda-bridge/000001", "/models/returns/000001",
                     "/ic-memo/000001"):
            self.assertIn(href, html)


if __name__ == "__main__":
    unittest.main()
