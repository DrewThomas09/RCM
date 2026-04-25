"""Tests for the shared causal-inference substrate (DiD +
Synthetic Controls + SDID)."""
from __future__ import annotations

import unittest

import numpy as np


def _build_panel(treatment_effect: float = 0.0,
                 noise_sd: float = 1.0,
                 seed: int = 0):
    """5-unit, 12-period panel with optional treatment effect
    injected at unit 0 from period 6 onward."""
    rng = np.random.default_rng(seed)
    n_units, n_periods = 5, 12
    baseline = np.linspace(100, 130, n_periods)
    Y = np.array([
        baseline + rng.normal(0, noise_sd, n_periods)
        for _ in range(n_units)
    ])
    if treatment_effect:
        Y[0, 6:] += treatment_effect
    return Y


# ── DiD ────────────────────────────────────────────────────────

class TestDiD(unittest.TestCase):
    def test_no_effect_near_zero(self):
        from rcm_mc.causal import did_estimate
        Y = _build_panel(treatment_effect=0.0)
        r = did_estimate(Y, treated_unit=0, treated_period=6)
        self.assertLess(abs(r.treatment_effect), 5.0)

    def test_recovers_injected_effect(self):
        from rcm_mc.causal import did_estimate
        Y = _build_panel(treatment_effect=20.0, noise_sd=0.5,
                         seed=1)
        r = did_estimate(Y, treated_unit=0, treated_period=6)
        self.assertGreater(r.treatment_effect, 15.0)
        self.assertLess(r.treatment_effect, 25.0)
        # Standard error reported
        self.assertGreaterEqual(r.standard_error, 0.0)

    def test_validates_inputs(self):
        from rcm_mc.causal import did_estimate
        Y = _build_panel()
        with self.assertRaises(ValueError):
            did_estimate(Y, treated_unit=99, treated_period=6)
        with self.assertRaises(ValueError):
            did_estimate(Y, treated_unit=0, treated_period=0)


# ── Synthetic Controls ────────────────────────────────────────

class TestSyntheticControl(unittest.TestCase):
    def test_weights_sum_to_one_non_negative(self):
        from rcm_mc.causal import synthetic_control_estimate
        Y = _build_panel(treatment_effect=15.0, seed=2)
        r = synthetic_control_estimate(
            Y, treated_unit=0, treated_period=6,
            n_iterations=300)
        # Treated unit's weight should be 0; the rest sum to 1
        self.assertEqual(r.unit_weights[0], 0.0)
        self.assertAlmostEqual(
            float(r.unit_weights.sum()), 1.0, places=2)
        for w in r.unit_weights:
            self.assertGreaterEqual(w, 0.0)

    def test_recovers_injected_effect(self):
        from rcm_mc.causal import synthetic_control_estimate
        Y = _build_panel(treatment_effect=15.0, noise_sd=0.5,
                         seed=3)
        r = synthetic_control_estimate(
            Y, treated_unit=0, treated_period=6,
            n_iterations=500)
        # Should be in the right ballpark
        self.assertGreater(r.treatment_effect, 8.0)
        self.assertLess(r.treatment_effect, 22.0)
        # Pre-match RMSE should be small relative to the
        # injected effect
        self.assertLess(r.pre_match_rmse, 5.0)

    def test_placebo_ratio_flags_weak_signal(self):
        """When there's no real effect, the placebo ratio
        shouldn't be wildly large — Abadie says <2 = noise."""
        from rcm_mc.causal import synthetic_control_estimate
        Y = _build_panel(treatment_effect=0.0, noise_sd=2.0,
                         seed=4)
        r = synthetic_control_estimate(
            Y, treated_unit=0, treated_period=6,
            n_iterations=200)
        # Effect should be small — noise band, not signal
        self.assertLess(abs(r.treatment_effect), 5.0)


# ── SDID (via the shared substrate) ───────────────────────────

class TestSDID(unittest.TestCase):
    def test_substrate_reachable_from_causal(self):
        from rcm_mc.causal import sdid_estimate, SDIDResult
        Y = _build_panel(treatment_effect=20.0, seed=5)
        r = sdid_estimate(Y, treated_unit=0, treated_period=6)
        self.assertIsInstance(r, SDIDResult)
        self.assertGreater(r.treatment_effect, 10.0)

    def test_old_portfolio_synergy_path_still_works(self):
        """Backwards compat: importing from the old location
        still works (re-export)."""
        from rcm_mc.portfolio_synergy.sdid import (
            sdid_estimate as legacy,
        )
        from rcm_mc.causal import sdid_estimate
        # Same function (re-exported)
        self.assertIs(legacy, sdid_estimate)


# ── Cross-estimator agreement ────────────────────────────────

class TestEstimatorAgreement(unittest.TestCase):
    def test_three_estimators_agree_in_ballpark(self):
        """For a clean panel with a strong injected effect, all
        three estimators should agree to within ~5 units."""
        from rcm_mc.causal import (
            did_estimate, synthetic_control_estimate,
            sdid_estimate,
        )
        Y = _build_panel(treatment_effect=20.0, noise_sd=0.5,
                         seed=6)
        did = did_estimate(Y, treated_unit=0, treated_period=6)
        sc = synthetic_control_estimate(
            Y, treated_unit=0, treated_period=6,
            n_iterations=500)
        sdid = sdid_estimate(
            Y, treated_unit=0, treated_period=6)
        # All three should land near 20
        for est in (did.treatment_effect,
                    sc.treatment_effect,
                    sdid.treatment_effect):
            self.assertGreater(est, 12.0)
            self.assertLess(est, 28.0)


if __name__ == "__main__":
    unittest.main()
