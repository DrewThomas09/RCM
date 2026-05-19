"""Tests for the per-hospital regression drivers section.

The per-hospital stats page (/portfolio/regression/hospital/<ccn>)
fits a quick OLS for each of several key targets and shows the
hospital's predicted vs. actual residual. The drivers section
explains WHY the prediction came out where it did — top 3 features
by absolute z-scored contribution, with sign and share of the
(pred - mean) gap.

Without these the partner reads "Op Margin: actual 5.2%, predicted
3.1%" and has no idea which features pushed the prediction down.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ui.hospital_stats_page import render_hospital_stats


def _synthetic_hcris(n: int = 100, target_ccn: str = "TEST01") -> pd.DataFrame:
    """Minimal HCRIS-shaped frame with one known hospital so the page
    can render in tests and the drivers section has signal to compute."""
    rng = np.random.default_rng(42)
    rows = []
    for i in range(n):
        rows.append({
            "ccn": f"H{i:04d}" if i > 0 else target_ccn,
            "name": (
                f"TARGET HOSPITAL" if i == 0 else f"Hospital {i}"
            ),
            "state": "MA",
            "county": "Suffolk",
            "beds": float(rng.integers(20, 500)),
            "bed_days_available": float(rng.integers(7000, 180000)),
            "total_patient_days": float(rng.integers(5000, 150000)),
            "medicare_days": float(rng.integers(1000, 60000)),
            "medicaid_days": float(rng.integers(500, 30000)),
            "medicare_day_pct": float(rng.uniform(20, 70)),
            "medicaid_day_pct": float(rng.uniform(5, 35)),
            "net_patient_revenue": float(rng.uniform(1e7, 1e9)),
            "operating_expenses": float(rng.uniform(1e7, 9e8)),
            "gross_patient_revenue": float(rng.uniform(2e7, 2e9)),
            "contractual_allowances": float(rng.uniform(1e7, 9e8)),
            "net_income": float(rng.uniform(-1e7, 1e8)),
        })
    return pd.DataFrame(rows)


class DriversSectionTests(unittest.TestCase):
    def test_drivers_section_renders_for_present_hospital(self):
        df = _synthetic_hcris(120)
        html = render_hospital_stats("TEST01", df)
        self.assertIn("Driving Each Prediction", html)
        # Drivers list class present
        self.assertIn("rg-drivers", html)
        # At least one driver entry rendered (arrow + % share)
        self.assertTrue(
            "▲" in html or "▼" in html,
            "drivers should render at least one ▲/▼ arrow",
        )
        self.assertIn("of gap", html)

    def test_drivers_section_absent_when_hospital_missing(self):
        df = _synthetic_hcris(50)
        html = render_hospital_stats("DOES_NOT_EXIST", df)
        # Missing-hospital page is the "not found" fallback; no
        # drivers section at all.
        self.assertNotIn("rg-drivers", html)
        self.assertNotIn("Driving Each Prediction", html)

    def test_per_target_header_includes_corpus_gap(self):
        # Each target's drivers list is preceded by a small header
        # showing the gap-vs-mean. Verify the "vs corpus mean" phrase
        # renders for at least one target.
        df = _synthetic_hcris(120)
        html = render_hospital_stats("TEST01", df)
        self.assertIn("vs corpus mean", html)


if __name__ == "__main__":
    unittest.main()
