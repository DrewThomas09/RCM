"""The IC memo carries a no-print deal-context ribbon.

The interactive memo view now leads with the standard _model_nav pill
ribbon so a reviewer can jump to any sibling analysis on the deal.
The ribbon is wrapped no-print, so the exported/printed memo stays a
clean document (and the print-preview view omits it).
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=40):
    rng = np.random.RandomState(2)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"H{i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX"], n),
        "county": rng.choice(["A", "B"], n),
        "beds": rng.choice([150, 300], n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 2e9, n),
        "operating_expenses": rng.uniform(4e7, 1.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 5e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class IcMemoDealRibbonTests(unittest.TestCase):
    def test_interactive_view_carries_ribbon(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        html = render_ic_memo("000001", _sample_hcris())
        self.assertIn("ck-model-pill", html)
        self.assertIn("/models/returns/000001", html)

    def test_print_preview_omits_ribbon(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        html = render_ic_memo("000001", _sample_hcris(), print_preview=True)
        self.assertNotIn("ck-model-pill", html)


if __name__ == "__main__":
    unittest.main()
