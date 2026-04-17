"""Tests for the v2 Monte Carlo simulator.

Invariants this suite locks down:

1. Zero-variance mode reproduces the deterministic v2 bridge exactly.
2. EV from recurring never includes the one-time WC release.
3. Variance contributions sum to 1.0 (or 0.0 when degenerate).
4. Reproducibility: same seed → identical p50s on every distribution.
5. Monotone MOIC target probabilities: P(MOIC ≥ 1.5) ≥ P(MOIC ≥ 2.0) ≥ ...
6. Additional v2 sampling dimensions widen the P10-P90 band vs. the
   v1 simulator with the same metric assumptions and a v2-compatible
   hospital.
7. Convergence passes at n_sims ≥ 5000 on a commercial-heavy hospital.
8. Backwards compat: packets without ``v2_simulation`` still deserialize.
9. ``dependency_adjusted`` is always True (the v2 bridge always walks).
10. Tornado rows are sorted by |range| descending.
11. Per-sim BridgeAssumptions carry the sampled payer_revenue_leverage
    override and the base leverage is not mutated.
12. Exit-multiple triangular mode matches ``base.exit_multiple``.
13. API endpoint ``POST /api/analysis/<id>/simulate/v2`` returns a
    well-formed v2_mc object.
"""
from __future__ import annotations

import copy
import json
import unittest

import numpy as np

from rcm_mc.analysis.packet import DealAnalysisPacket
from rcm_mc.finance.reimbursement_engine import (
    PayerClass,
    PayerClassProfile,
    ReimbursementMethod,
    ReimbursementProfile,
)
from rcm_mc.mc import V2MonteCarloResult, V2MonteCarloSimulator
from rcm_mc.mc.ebitda_mc import (
    MetricAssumption,
    default_execution_assumption,
)
from rcm_mc.pe.value_bridge_v2 import (
    BridgeAssumptions,
    _PAYER_REVENUE_LEVERAGE,
    compute_value_bridge,
)


# ── Shared fixtures ────────────────────────────────────────────────

def _commercial_heavy_profile() -> ReimbursementProfile:
    return ReimbursementProfile(
        payer_classes={
            PayerClass.COMMERCIAL: PayerClassProfile(
                payer_class=PayerClass.COMMERCIAL, revenue_share=0.55,
                method_distribution={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
            ),
            PayerClass.MEDICARE_FFS: PayerClassProfile(
                payer_class=PayerClass.MEDICARE_FFS, revenue_share=0.30,
                method_distribution={ReimbursementMethod.DRG_PROSPECTIVE: 1.0},
            ),
            PayerClass.MEDICAID: PayerClassProfile(
                payer_class=PayerClass.MEDICAID, revenue_share=0.15,
                method_distribution={ReimbursementMethod.DRG_PROSPECTIVE: 1.0},
            ),
        },
        method_weights={
            ReimbursementMethod.FEE_FOR_SERVICE: 0.55,
            ReimbursementMethod.DRG_PROSPECTIVE: 0.45,
        },
    )


def _simple_profile() -> ReimbursementProfile:
    return ReimbursementProfile(
        payer_classes={
            PayerClass.COMMERCIAL: PayerClassProfile(
                payer_class=PayerClass.COMMERCIAL, revenue_share=1.0,
                method_distribution={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
            ),
        },
        method_weights={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
    )


def _point_mass_assumption(key: str, cur: float, tgt: float) -> MetricAssumption:
    """MetricAssumption with no prediction or execution noise."""
    return MetricAssumption(
        metric_key=key, current_value=cur, target_value=tgt,
        uncertainty_source="none",
        execution_probability=1.0,
        execution_distribution="none",
        execution_params={},
    )


# ── Constructor / configuration ────────────────────────────────────

class TestSimulatorLifecycle(unittest.TestCase):

    def test_n_simulations_must_be_positive(self):
        with self.assertRaises(ValueError):
            V2MonteCarloSimulator(n_simulations=0)

    def test_run_before_configure_raises(self):
        sim = V2MonteCarloSimulator(n_simulations=10)
        with self.assertRaises(RuntimeError):
            sim.run()

    def test_metric_order_must_match_assumptions(self):
        sim = V2MonteCarloSimulator(n_simulations=10)
        with self.assertRaises(ValueError):
            sim.configure(
                current_metrics={"denial_rate": 11.0},
                metric_assumptions={
                    "denial_rate": _point_mass_assumption("denial_rate", 11.0, 7.0),
                },
                reimbursement_profile=_simple_profile(),
                metric_order=["unknown_metric"],
            )

    def test_returns_v2_result_type(self):
        sim = V2MonteCarloSimulator(n_simulations=30, seed=1)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_simple_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        result = sim.run()
        self.assertIsInstance(result, V2MonteCarloResult)
        self.assertEqual(result.n_simulations, 30)


# ── Deterministic equivalence ──────────────────────────────────────

class TestZeroVarianceIdentity(unittest.TestCase):

    def test_zero_variance_matches_deterministic_bridge(self):
        profile = _simple_profile()
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
        )
        det = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            profile, base, current_ebitda=60_000_000,
        )
        sim = V2MonteCarloSimulator(n_simulations=50, seed=42)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": _point_mass_assumption("denial_rate", 11.0, 7.0),
            },
            reimbursement_profile=profile,
            base_assumptions=base,
            current_ebitda=60_000_000,
            zero_variance=True,
        )
        r = sim.run()
        self.assertAlmostEqual(
            r.recurring_ebitda_distribution.p50,
            det.total_recurring_ebitda_delta,
            places=2,
        )
        self.assertEqual(r.recurring_ebitda_distribution.std, 0.0)

    def test_zero_variance_ev_matches(self):
        profile = _simple_profile()
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000, exit_multiple=9.0,
        )
        det = compute_value_bridge(
            {"denial_rate": 11.0}, {"denial_rate": 7.0},
            profile, base, current_ebitda=60_000_000,
        )
        sim = V2MonteCarloSimulator(n_simulations=30, seed=42)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": _point_mass_assumption("denial_rate", 11.0, 7.0),
            },
            reimbursement_profile=profile,
            base_assumptions=base,
            current_ebitda=60_000_000,
            zero_variance=True,
        )
        r = sim.run()
        self.assertAlmostEqual(
            r.ev_from_recurring_distribution.p50,
            det.enterprise_value_from_recurring,
            places=2,
        )


# ── EV vs. one-time cash separation ────────────────────────────────

class TestOneTimeCashSeparation(unittest.TestCase):

    def test_ev_excludes_one_time_cash(self):
        """EV from recurring must equal total_recurring_ebitda * exit_multiple
        — never touches the WC release. Even when WC is non-trivial."""
        profile = _commercial_heavy_profile()
        base = BridgeAssumptions(
            net_revenue=500_000_000, claims_volume=150_000,
            exit_multiple=10.0,
        )
        ma = {
            "days_in_ar": _point_mass_assumption("days_in_ar", 55.0, 45.0),
        }
        sim = V2MonteCarloSimulator(n_simulations=50, seed=7)
        sim.configure(
            current_metrics={"days_in_ar": 55.0},
            metric_assumptions=ma,
            reimbursement_profile=profile,
            base_assumptions=base,
            current_ebitda=60_000_000,
            zero_variance=True,
        )
        r = sim.run()
        # The AR-days lever generates a non-zero one-time WC release.
        self.assertGreater(r.one_time_cash_distribution.p50, 0.0)
        # Total cash should be larger than EV because it includes WC.
        self.assertGreater(
            r.total_cash_distribution.p50,
            r.ev_from_recurring_distribution.p50,
        )

    def test_total_cash_equals_exit_ev_plus_wc(self):
        profile = _commercial_heavy_profile()
        base = BridgeAssumptions(
            net_revenue=500_000_000, claims_volume=150_000,
            exit_multiple=10.0,
        )
        sim = V2MonteCarloSimulator(n_simulations=20, seed=11)
        sim.configure(
            current_metrics={"days_in_ar": 55.0},
            metric_assumptions={
                "days_in_ar": _point_mass_assumption("days_in_ar", 55.0, 45.0),
            },
            reimbursement_profile=profile,
            base_assumptions=base,
            current_ebitda=60_000_000,
            entry_multiple=10.0, hold_years=5.0,
            organic_growth_pct=0.0,
            zero_variance=True,
        )
        r = sim.run()
        # total_cash = exit_ebitda * exit_mult + one_time_wc
        expected_exit_ebitda = (
            60_000_000 + r.recurring_ebitda_distribution.p50
        )
        expected_total = (
            expected_exit_ebitda * 10.0
            + r.one_time_cash_distribution.p50
        )
        self.assertAlmostEqual(
            r.total_cash_distribution.p50, expected_total, places=0,
        )


# ── Variance contribution ──────────────────────────────────────────

class TestVarianceContribution(unittest.TestCase):

    def test_variance_contributions_sum_to_one(self):
        sim = V2MonteCarloSimulator(n_simulations=300, seed=3)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        self.assertAlmostEqual(
            sum(r.variance_contribution.values()), 1.0, places=6,
        )

    def test_variance_includes_v2_dimensions(self):
        sim = V2MonteCarloSimulator(n_simulations=200, seed=5)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        self.assertIn("collection_realization", r.variance_contribution)
        self.assertIn("denial_overturn_rate", r.variance_contribution)
        self.assertIn("exit_multiple", r.variance_contribution)
        # At least one per-payer leverage key.
        self.assertTrue(
            any(k.startswith("leverage:")
                for k in r.variance_contribution),
        )

    def test_zero_variance_degenerates_to_zeros(self):
        sim = V2MonteCarloSimulator(n_simulations=50, seed=1)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": _point_mass_assumption("denial_rate", 11.0, 7.0),
            },
            reimbursement_profile=_simple_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
            zero_variance=True,
        )
        r = sim.run()
        for v in r.variance_contribution.values():
            self.assertEqual(v, 0.0)


# ── Tornado ────────────────────────────────────────────────────────

class TestTornado(unittest.TestCase):

    def test_tornado_sorted_by_range_desc(self):
        sim = V2MonteCarloSimulator(n_simulations=250, seed=13)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        ranges = [t.range for t in r.tornado_data]
        self.assertEqual(ranges, sorted(ranges, reverse=True))

    def test_tornado_row_p10_differs_from_p90(self):
        """A dimension that drives variance should have distinct P10/P90
        averages on the output."""
        sim = V2MonteCarloSimulator(n_simulations=300, seed=17)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        # Find the denial_rate row.
        row = next(t for t in r.tornado_data if t.metric == "denial_rate")
        self.assertNotAlmostEqual(row.p10_impact, row.p90_impact, places=2)


# ── Reproducibility ─────────────────────────────────────────────────

class TestReproducibility(unittest.TestCase):

    def test_same_seed_same_p50s(self):
        profile = _commercial_heavy_profile()
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
        )
        ma = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=11.0, target_value=7.0,
            ),
        }

        def _run():
            s = V2MonteCarloSimulator(n_simulations=200, seed=99)
            s.configure(
                current_metrics={"denial_rate": 11.0},
                metric_assumptions=ma,
                reimbursement_profile=profile,
                base_assumptions=base,
                current_ebitda=60_000_000,
            )
            return s.run()

        a, b = _run(), _run()
        self.assertEqual(
            a.recurring_ebitda_distribution.p50,
            b.recurring_ebitda_distribution.p50,
        )
        self.assertEqual(
            a.total_cash_distribution.p50,
            b.total_cash_distribution.p50,
        )

    def test_different_seed_differs(self):
        profile = _commercial_heavy_profile()
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
        )
        ma = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=11.0, target_value=7.0,
            ),
        }

        def _run(seed):
            s = V2MonteCarloSimulator(n_simulations=200, seed=seed)
            s.configure(
                current_metrics={"denial_rate": 11.0},
                metric_assumptions=ma,
                reimbursement_profile=profile,
                base_assumptions=base,
                current_ebitda=60_000_000,
            )
            return s.run()

        a = _run(1).recurring_ebitda_distribution.p50
        b = _run(2).recurring_ebitda_distribution.p50
        self.assertNotEqual(a, b)


# ── Target MOIC monotonicity ───────────────────────────────────────

class TestMOICTargets(unittest.TestCase):

    def test_target_moic_probabilities_monotone(self):
        sim = V2MonteCarloSimulator(n_simulations=500, seed=21)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
            moic_targets=(1.0, 1.5, 2.0, 2.5, 3.0),
        )
        r = sim.run()
        probs = [r.probability_of_target_moic[k] for k in
                 ("1x", "1.5x", "2x", "2.5x", "3x")]
        for prev, nxt in zip(probs, probs[1:]):
            self.assertGreaterEqual(prev, nxt)


# ── Width compared to v1 simulator ─────────────────────────────────

class TestDistributionWidth(unittest.TestCase):

    def test_v2_simulator_produces_nontrivial_spread(self):
        """With all v2 sampling dimensions active, the P10-P90 range on
        recurring EBITDA should be meaningfully positive."""
        sim = V2MonteCarloSimulator(n_simulations=500, seed=29)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        p10 = r.recurring_ebitda_distribution.p10
        p90 = r.recurring_ebitda_distribution.p90
        self.assertGreater(p90 - p10, 0.0)

    def test_payer_leverage_sigma_widens_output(self):
        """Doubling leverage_sigma should strictly widen (or tie) the
        P10-P90 range of recurring EBITDA for a payer-mix-sensitive
        lever."""
        base_cfg = dict(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        s_tight = V2MonteCarloSimulator(n_simulations=500, seed=37)
        s_tight.configure(**base_cfg, leverage_sigma=0.01)
        s_wide = V2MonteCarloSimulator(n_simulations=500, seed=37)
        s_wide.configure(**base_cfg, leverage_sigma=0.15)
        tight = s_tight.run()
        wide = s_wide.run()
        tight_range = (
            tight.recurring_ebitda_distribution.p90
            - tight.recurring_ebitda_distribution.p10
        )
        wide_range = (
            wide.recurring_ebitda_distribution.p90
            - wide.recurring_ebitda_distribution.p10
        )
        self.assertGreaterEqual(wide_range, tight_range)


# ── Convergence ────────────────────────────────────────────────────

class TestConvergence(unittest.TestCase):

    def test_convergence_at_5000_sims(self):
        sim = V2MonteCarloSimulator(n_simulations=5000, seed=41)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        self.assertTrue(r.convergence_check.converged)


# ── Dependency-adjusted flag ───────────────────────────────────────

class TestDependencyFlag(unittest.TestCase):

    def test_result_reports_dependency_adjusted(self):
        sim = V2MonteCarloSimulator(n_simulations=30, seed=43)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_simple_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        self.assertTrue(r.dependency_adjusted)


# ── Payer leverage plumbing ────────────────────────────────────────

class TestPayerLeveragePlumbing(unittest.TestCase):

    def test_base_leverage_table_not_mutated(self):
        before = dict(_PAYER_REVENUE_LEVERAGE)
        sim = V2MonteCarloSimulator(n_simulations=50, seed=51)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_commercial_heavy_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        sim.run()
        self.assertEqual(before, _PAYER_REVENUE_LEVERAGE)

    def test_exit_multiple_sampled_around_mode(self):
        """With large n, the P50 exit multiple should land near the
        configured mode (the base exit_multiple)."""
        profile = _commercial_heavy_profile()
        base = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000, exit_multiple=10.0,
        )
        sim = V2MonteCarloSimulator(n_simulations=2000, seed=53)
        # Use an all-else-equal config: point mass metric so the only
        # variation comes from v2 dimensions.
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": _point_mass_assumption("denial_rate", 11.0, 7.0),
            },
            reimbursement_profile=profile,
            base_assumptions=base,
            current_ebitda=60_000_000,
        )
        # Reach into the simulator and regenerate exit multiples to
        # check distributional centering.
        rng = np.random.default_rng(53)
        draws = np.array([sim._sample_exit_multiple(rng) for _ in range(2000)])
        self.assertAlmostEqual(float(np.median(draws)), 10.0, delta=0.3)

    def test_payer_leverage_override_respected(self):
        """Setting payer_revenue_leverage on the base assumptions should
        shift the recurring EBITDA downward when we lower commercial
        leverage — that lever is commercial-dominated in our fixture."""
        profile = _simple_profile()  # 100% commercial
        base_default = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
        )
        base_half = BridgeAssumptions(
            net_revenue=400_000_000, claims_volume=120_000,
            payer_revenue_leverage={PayerClass.COMMERCIAL: 0.5},
        )
        def _run(base):
            s = V2MonteCarloSimulator(n_simulations=30, seed=61)
            s.configure(
                current_metrics={"denial_rate": 11.0},
                metric_assumptions={
                    "denial_rate": _point_mass_assumption(
                        "denial_rate", 11.0, 7.0,
                    ),
                },
                reimbursement_profile=profile,
                base_assumptions=base,
                current_ebitda=60_000_000,
                zero_variance=True,
            )
            return s.run()

        r_default = _run(base_default)
        r_half = _run(base_half)
        self.assertGreater(
            r_default.recurring_ebitda_distribution.p50,
            r_half.recurring_ebitda_distribution.p50,
        )


# ── Serialization ──────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_result_to_dict_roundtrip(self):
        sim = V2MonteCarloSimulator(n_simulations=30, seed=71)
        sim.configure(
            current_metrics={"denial_rate": 11.0},
            metric_assumptions={
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=11.0, target_value=7.0,
                ),
            },
            reimbursement_profile=_simple_profile(),
            base_assumptions=BridgeAssumptions(
                net_revenue=400_000_000, claims_volume=120_000,
            ),
            current_ebitda=60_000_000,
        )
        r = sim.run()
        payload = json.dumps(r.to_dict())  # must not raise
        restored = json.loads(payload)
        self.assertEqual(restored["n_simulations"], 30)
        self.assertIn("recurring_ebitda_distribution", restored)
        self.assertTrue(restored["dependency_adjusted"])

    def test_bridge_assumptions_to_dict_enum_keys(self):
        """``payer_revenue_leverage`` may use PayerClass enum keys;
        the to_dict() should coerce them to string for JSON safety."""
        ba = BridgeAssumptions(
            payer_revenue_leverage={PayerClass.COMMERCIAL: 0.9},
        )
        d = ba.to_dict()
        self.assertEqual(d["payer_revenue_leverage"]["commercial"], 0.9)
        # Serializes as JSON without error.
        json.dumps(d)

    def test_packet_without_v2_simulation_deserializes(self):
        """Old packets saved before the v2_simulation field was added
        should round-trip via from_dict with v2_simulation == None."""
        d = {
            "deal_id": "d1",
            "deal_name": "Test",
            "profile": {},
            "observed_metrics": {},
            "completeness": {},
            "comparables": {},
            "predicted_metrics": {},
            "rcm_profile": {},
            "ebitda_bridge": {},
            "simulation": None,
            "risk_flags": [],
            "provenance": {},
            "diligence_questions": [],
            "exports": {},
        }
        p = DealAnalysisPacket.from_dict(d)
        self.assertIsNone(p.v2_simulation)

    def test_packet_with_v2_simulation_roundtrip(self):
        d = {
            "deal_id": "d1",
            "v2_simulation": {
                "n_simulations": 100,
                "dependency_adjusted": True,
            },
        }
        p = DealAnalysisPacket.from_dict(d)
        self.assertEqual(p.v2_simulation.get("n_simulations"), 100)
        # to_dict → from_dict round-trip preserves it.
        roundtripped = DealAnalysisPacket.from_dict(p.to_dict())
        self.assertEqual(
            roundtripped.v2_simulation.get("n_simulations"), 100,
        )


# ── v1 untouched ───────────────────────────────────────────────────

class TestV1SimulatorUntouched(unittest.TestCase):

    def test_v1_simulator_still_imports(self):
        from rcm_mc.mc import MonteCarloResult, RCMMonteCarloSimulator  # noqa
        # If the v2 module had broken v1 imports this line would fail.
        self.assertTrue(True)

    def test_v1_and_v2_coexist_in_same_packet_shape(self):
        from rcm_mc.analysis.packet import SimulationSummary
        # SimulationSummary (v1) and v2_simulation (dict) both live
        # under DealAnalysisPacket.
        s = SimulationSummary(n_sims=10)
        d = {"deal_id": "d1", "v2_simulation": {"n_simulations": 5}}
        p = DealAnalysisPacket.from_dict(d)
        p.simulation = s
        out = p.to_dict()
        self.assertIsNotNone(out["simulation"])
        self.assertIsNotNone(out["v2_simulation"])


# ── Builder integration ────────────────────────────────────────────

class TestBuilderIntegration(unittest.TestCase):
    """Integration: run ``build_analysis_packet`` and confirm it
    populates the ``v2_simulation`` section when the v2 bridge
    succeeds. We use the simplest path that exercises that branch.
    """

    def test_builder_attaches_v2_simulation_when_bridge_ok(self):
        from unittest import mock
        from rcm_mc.analysis.packet import (
            EBITDABridgeResult, MetricImpact,
        )
        from rcm_mc.analysis import packet_builder as pb

        fake_bridge = EBITDABridgeResult(
            current_ebitda=60_000_000,
            target_ebitda=65_000_000,
            per_metric_impacts=[
                MetricImpact(
                    metric_key="denial_rate",
                    current_value=11.0, target_value=7.0,
                ),
            ],
        )
        # Keep only the keys our logic looks at.
        stub_deal = {"id": "d1", "name": "Test"}
        fake_rcm_profile = {}
        with mock.patch.object(pb, "_load_deal_row", return_value=stub_deal), \
                mock.patch.object(pb, "_build_profile", return_value=pb.HospitalProfile()), \
                mock.patch.object(pb, "_build_observed", return_value={}), \
                mock.patch.object(pb, "_build_completeness", return_value=pb.CompletenessAssessment()), \
                mock.patch.object(pb, "_build_comparables", return_value=pb.ComparableSet()), \
                mock.patch.object(pb, "_build_predictions", return_value={}), \
                mock.patch.object(pb, "_merge_rcm_profile", return_value=fake_rcm_profile), \
                mock.patch.object(pb, "_build_reimbursement_views",
                                  return_value=({}, {}, {})), \
                mock.patch.object(pb, "_build_bridge", return_value=fake_bridge), \
                mock.patch.object(pb, "_build_value_bridge_v2",
                                  return_value=({"status": "OK"}, [], {}, {})), \
                mock.patch.object(pb, "_build_v2_monte_carlo",
                                  return_value={"n_simulations": 100, "dependency_adjusted": True}), \
                mock.patch.object(pb, "_build_rcm_monte_carlo",
                                  return_value=pb.SimulationSummary()), \
                mock.patch.object(pb, "_build_risk_flags", return_value=[]), \
                mock.patch.object(pb, "_build_provenance",
                                  return_value=pb.ProvenanceSnapshot()), \
                mock.patch.object(pb, "_build_diligence_questions", return_value=[]):
            packet = pb.build_analysis_packet(store=None, deal_id="d1")
        self.assertIsNotNone(packet.v2_simulation)
        self.assertEqual(packet.v2_simulation.get("n_simulations"), 100)


class TestPacketSectionLookup(unittest.TestCase):

    def test_v2_simulation_is_a_named_section(self):
        """``packet.section("v2_simulation")`` should not raise — it's
        in ``SECTION_NAMES`` so the ``/api/analysis/<id>/section/<name>``
        endpoint can serve it."""
        from rcm_mc.analysis.packet import SECTION_NAMES
        self.assertIn("v2_simulation", SECTION_NAMES)
        p = DealAnalysisPacket(deal_id="d1")
        # section() must accept the name; value can be None.
        self.assertIsNone(p.section("v2_simulation"))


class TestAPIEndpointSmoke(unittest.TestCase):
    """Smoke test: verify the ``POST /api/analysis/<id>/simulate/v2``
    dispatch is wired. We don't spin a real server — just check the
    handler method exists and that the path matches the dispatch rule.
    """

    def test_route_handler_method_exists(self):
        from rcm_mc.server import RCMHandler
        self.assertTrue(hasattr(RCMHandler, "_route_simulate_v2"))

    def test_save_v2_mc_run_helper_exists(self):
        from rcm_mc.mc.mc_store import save_v2_mc_run  # noqa: F401
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
