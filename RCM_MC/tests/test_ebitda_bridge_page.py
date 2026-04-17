"""Tests for the EBITDA Bridge page — PE returns math visualization."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=50):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY"], n),
        "beds": rng.randint(50, 500, n).astype(float),
        "net_patient_revenue": rng.uniform(5e7, 3e9, n),
        "operating_expenses": rng.uniform(4e7, 2.8e9, n),
        "gross_patient_revenue": rng.uniform(1e8, 8e9, n),
        "medicare_day_pct": rng.uniform(0.2, 0.6, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.25, n),
        "total_patient_days": rng.randint(5000, 80000, n).astype(float),
        "bed_days_available": rng.randint(10000, 150000, n).astype(float),
    })


class TestEBITDABridgeComputation(unittest.TestCase):

    def test_compute_bridge(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(
            net_revenue=400e6, current_ebitda=50e6, medicare_pct=0.40)
        self.assertGreater(result["total_ebitda_impact"], 0)
        self.assertEqual(len(result["levers"]), 6)
        self.assertAlmostEqual(
            result["new_ebitda"],
            result["current_ebitda"] + result["total_ebitda_impact"],
            delta=1,
        )

    def test_bridge_in_research_band(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(
            net_revenue=400e6, current_ebitda=50e6, medicare_pct=0.40)
        total = result["total_ebitda_impact"]
        self.assertGreater(total, 5e6)
        self.assertLess(total, 60e6)

    def test_lever_timing(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(
            net_revenue=400e6, current_ebitda=50e6)
        for lev in result["levers"]:
            self.assertGreater(len(lev["timing"]), 5)
            last = lev["timing"][-1]
            self.assertEqual(last["pct"], 1.0)

    def test_margin_improvement(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(
            net_revenue=400e6, current_ebitda=50e6)
        self.assertGreater(result["margin_improvement_bps"], 0)

    def test_wc_released(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        result = _compute_bridge(
            net_revenue=400e6, current_ebitda=50e6)
        self.assertGreater(result["total_wc_released"], 0)


class TestReturnsGrid(unittest.TestCase):

    def test_grid_dimensions(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_returns_grid
        grid = _compute_returns_grid(
            current_ebitda=50e6, ebitda_uplift=10e6,
            entry_multiples=[8, 10, 12], exit_multiples=[9, 11])
        self.assertEqual(len(grid), 6)

    def test_moic_positive(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_returns_grid
        grid = _compute_returns_grid(
            current_ebitda=50e6, ebitda_uplift=10e6,
            entry_multiples=[10], exit_multiples=[11])
        self.assertGreater(grid[0]["moic"], 0)

    def test_higher_exit_better_moic(self):
        from rcm_mc.ui.ebitda_bridge_page import _compute_returns_grid
        grid = _compute_returns_grid(
            current_ebitda=50e6, ebitda_uplift=10e6,
            entry_multiples=[10], exit_multiples=[10, 12])
        moic_10 = next(g for g in grid if g["exit_multiple"] == 10)["moic"]
        moic_12 = next(g for g in grid if g["exit_multiple"] == 12)["moic"]
        self.assertGreater(moic_12, moic_10)


class TestEBITDABridgePage(unittest.TestCase):

    def test_renders(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris()
        html = render_ebitda_bridge("000001", df)
        self.assertIn("SeekingChartis", html)
        self.assertIn("EBITDA Bridge", html)
        self.assertIn("Lever Detail", html)
        self.assertIn("Timing Curve", html)
        self.assertIn("Returns Sensitivity", html)
        self.assertIn("Covenant", html)

    def test_not_found(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris(10)
        html = render_ebitda_bridge("999999", df)
        self.assertIn("not found", html)

    def test_has_waterfall_bars(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris()
        html = render_ebitda_bridge("000001", df)
        self.assertIn("Denial Rate", html)
        self.assertIn("A/R Days", html)

    def test_has_irr_moic_values(self):
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = _sample_hcris()
        html = render_ebitda_bridge("000001", df)
        self.assertIn("%", html)
        self.assertIn("x", html)


if __name__ == "__main__":
    unittest.main()
