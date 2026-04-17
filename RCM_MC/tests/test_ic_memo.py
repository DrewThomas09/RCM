"""Tests for the IC Memo Generator."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=200):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL", "IL"], n),
        "county": rng.choice(["County A", "County B"], n),
        "beds": rng.randint(50, 500, n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 3e9, n),
        "operating_expenses": rng.uniform(4e7, 2.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 8e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class TestBuildMemoData(unittest.TestCase):

    def test_builds_data(self):
        from rcm_mc.ui.ic_memo_page import _build_memo_data
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        data = _build_memo_data("000001", df)
        self.assertIsNotNone(data)
        self.assertIn("bridge", data)
        self.assertIn("base_grid", data)
        self.assertGreater(data["revenue"], 0)
        self.assertGreater(len(data["bridge"]["levers"]), 0)

    def test_nonexistent_returns_none(self):
        from rcm_mc.ui.ic_memo_page import _build_memo_data
        df = _sample_hcris(10)
        self.assertIsNone(_build_memo_data("999999", df))


class TestICMemoPage(unittest.TestCase):

    def test_renders_all_sections(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        html = render_ic_memo("000001", df)
        self.assertIn("Investment Committee", html)
        self.assertIn("Target Overview", html)
        self.assertIn("Market Context", html)
        self.assertIn("Comparable Hospitals", html)
        self.assertIn("Improvement Opportunities", html)
        self.assertIn("EBITDA Bridge", html)
        self.assertIn("Returns Analysis", html)
        self.assertIn("Key Risks", html)
        self.assertIn("Data Sources", html)

    def test_has_real_numbers(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        html = render_ic_memo("000001", df)
        self.assertIn("$", html)
        self.assertIn("%", html)
        self.assertIn("MOIC", html)
        self.assertIn("IRR", html)

    def test_has_print_css(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        html = render_ic_memo("000001", df)
        self.assertIn("@media print", html)

    def test_not_found(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        df = _sample_hcris(10)
        html = render_ic_memo("999999", df)
        self.assertIn("not found", html)

    def test_risk_section_populated(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        html = render_ic_memo("000001", df)
        self.assertIn("Mitigant", html)

    def test_comp_table_populated(self):
        from rcm_mc.ui.ic_memo_page import render_ic_memo
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris())
        html = render_ic_memo("000001", df)
        self.assertIn("(Target)", html)


if __name__ == "__main__":
    unittest.main()
