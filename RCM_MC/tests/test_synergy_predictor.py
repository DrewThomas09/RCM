"""Tests for the PortfolioSynergyPredictor (SDID + diffusion +
alpha attribution).

Distinct from the earlier ``test_portfolio_synergy.py`` (which
covers a separate Brick-60 module). This file tests the new
``rcm_mc.portfolio_synergy`` package.
"""
from __future__ import annotations

import unittest

import numpy as np


# ── SDID ────────────────────────────────────────────────────────

class TestSDID(unittest.TestCase):
    def test_no_treatment_effect_zero_estimate(self):
        from rcm_mc.portfolio_synergy import sdid_estimate
        n_units, n_periods = 5, 12
        rng = np.random.default_rng(0)
        baseline = np.linspace(100, 130, n_periods)
        Y = np.array([
            baseline + rng.normal(0, 1, n_periods)
            for _ in range(n_units)
        ])
        result = sdid_estimate(
            Y, treated_unit=0, treated_period=6)
        # Effect should be near zero
        self.assertLess(abs(result.treatment_effect), 5.0)

    def test_positive_treatment_effect_recovered(self):
        from rcm_mc.portfolio_synergy import sdid_estimate
        n_units, n_periods = 5, 12
        rng = np.random.default_rng(1)
        baseline = np.linspace(100, 130, n_periods)
        Y = np.array([
            baseline + rng.normal(0, 0.5, n_periods)
            for _ in range(n_units)
        ])
        Y[0, 6:] += 20.0
        result = sdid_estimate(
            Y, treated_unit=0, treated_period=6)
        self.assertGreater(result.treatment_effect, 10.0)
        self.assertLess(result.treatment_effect, 30.0)
        self.assertGreater(
            result.pre_treatment_match_quality, 0.80)


# ── Diffusion ───────────────────────────────────────────────────

class TestDiffusion(unittest.TestCase):
    def test_logistic_fit_recovers_curve(self):
        from rcm_mc.portfolio_synergy import fit_diffusion_curve
        months = list(range(0, 30, 2))
        L_true, k_true, t0_true = 0.80, 0.30, 12.0
        adoption = [
            L_true / (1.0 + np.exp(-k_true * (m - t0_true)))
            for m in months
        ]
        curve = fit_diffusion_curve(
            months, adoption, n_iterations=500)
        self.assertLess(curve.rmse, 0.05)
        self.assertAlmostEqual(curve.L, 0.80, delta=0.15)

    def test_synergy_timing_predictions(self):
        from rcm_mc.portfolio_synergy import (
            fit_diffusion_curve, predict_synergy_timing,
        )
        months = list(range(0, 36, 3))
        adoption = [
            0.75 / (1.0 + np.exp(-0.25 * (m - 14.0)))
            for m in months
        ]
        curve = fit_diffusion_curve(months, adoption,
                                    n_iterations=500)
        timing = predict_synergy_timing(
            curve, target_ebitda_lift_pct=0.10)
        self.assertLess(timing.months_to_50pct_adoption,
                        timing.months_to_80pct_adoption)
        self.assertGreater(timing.expected_ebitda_lift_at_36mo,
                           timing.expected_ebitda_lift_at_18mo)


# ── Alpha attribution ─────────────────────────────────────────

class TestAlphaAttribution(unittest.TestCase):
    def test_alpha_isolates_intervention_lift(self):
        from rcm_mc.portfolio_synergy import (
            operational_alpha_attribution,
        )
        n_units, n_periods = 5, 12
        rng = np.random.default_rng(2)
        baseline = np.linspace(100, 110, n_periods)
        Y = np.array([
            baseline + rng.normal(0, 0.5, n_periods)
            for _ in range(n_units)
        ])
        Y[0, 6:] += 15.0
        attr = operational_alpha_attribution(
            "TestCo", Y,
            treated_unit=0, treated_period=6,
            realized_ebitda_growth_pct=0.25,
        )
        # Beta near +10% (control growth)
        self.assertAlmostEqual(
            attr.market_beta_pct, 0.10, delta=0.05)
        # Alpha ≈ 15% (realized - beta)
        self.assertAlmostEqual(
            attr.operational_alpha_pct, 0.15, delta=0.05)
        self.assertGreater(attr.sdid_match_quality, 0.50)


if __name__ == "__main__":
    unittest.main()
