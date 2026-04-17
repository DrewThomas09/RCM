"""Tests for competitive intelligence page."""
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
        "beds": rng.randint(30, 500, n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 3e9, n),
        "operating_expenses": rng.uniform(4e7, 2.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 8e9, n),
        "medicare_day_pct": rng.uniform(0.15, 0.65, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(3000, 80000, n).astype(float),
        "bed_days_available": rng.randint(8000, 150000, n).astype(float),
    })


class TestCompetitiveIntel(unittest.TestCase):

    def test_renders_all_sections(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertIn("Percentile Rankings", html)
        self.assertIn("Value Creation Gaps", html)
        self.assertIn("Size-Matched Peers", html)
        self.assertIn("SeekingChartis", html)

    def test_multiple_peer_groups(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertIn("National", html)
        self.assertIn("Size-Matched", html)

    def test_not_found(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris(10)
        html = render_competitive_intel("999999", df)
        self.assertIn("not found", html)

    def test_gap_analysis_has_values(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertIn("P75 Target", html)
        self.assertIn("Gap", html)

    def test_peer_table_has_target_row(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertIn("(Target)", html)

    def test_direction_indicators(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertIn("higher", html)
        self.assertIn("lower", html)

    def test_percentile_bars(self):
        from rcm_mc.ui.competitive_intel_page import render_competitive_intel
        df = _sample_hcris()
        html = render_competitive_intel("000001", df)
        self.assertRegex(html, r"P\d+")


class TestPeerStats(unittest.TestCase):

    def test_compute_stats(self):
        from rcm_mc.ui.competitive_intel_page import _compute_peer_stats
        vals = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        stats = _compute_peer_stats(55, vals, "count", "higher")
        self.assertGreater(stats["pctile"], 40)
        self.assertLess(stats["pctile"], 60)
        self.assertGreater(stats["gap_to_p75"], 0)

    def test_empty_series(self):
        from rcm_mc.ui.competitive_intel_page import _compute_peer_stats
        stats = _compute_peer_stats(50, pd.Series(dtype=float), "count", "higher")
        self.assertEqual(stats["pctile"], 50)


if __name__ == "__main__":
    unittest.main()
