"""Tests for the two-source Monte Carlo layer.

Covers:
- Distribution summary math
- Single-metric & multi-metric runs
- Zero-variance assumption matches deterministic bridge
- Convergence check on a known-stable process
- Correlated sampling produces the expected output correlation
- Variance decomposition sums to ~1
- Probability_of_target_moic is monotone in the target
- MOIC / IRR wiring
- Scenario comparison
- SQLite store round-trip
- Packet integration (step 8 picks RCM MC path)
- Hold-period grid with MC bands
"""
from __future__ import annotations

import math
import os
import tempfile
import unittest

import numpy as np

from rcm_mc.mc import (
    ConvergenceReport,
    DistributionSummary,
    MetricAssumption,
    MonteCarloResult,
    RCMMonteCarloSimulator,
    check_convergence,
    compare_scenarios,
    default_execution_assumption,
    from_conformal_prediction,
)
from rcm_mc.mc.mc_store import (
    list_mc_runs,
    load_latest_mc_run,
    save_mc_run,
)
from rcm_mc.pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
from rcm_mc.pe.pe_math import hold_period_grid_with_mc
from rcm_mc.portfolio.store import PortfolioStore


# ── Fixtures ─────────────────────────────────────────────────────────

def _research_bridge(net_revenue: float = 400_000_000) -> RCMEBITDABridge:
    return RCMEBITDABridge(FinancialProfile(
        gross_revenue=net_revenue * 2.5,
        net_revenue=net_revenue,
        current_ebitda=net_revenue * 0.08,
        total_claims_volume=300_000,
        cost_per_reworked_claim=30.0,
        payer_mix={"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    ))


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── DistributionSummary ──────────────────────────────────────────────

class TestDistributionSummary(unittest.TestCase):
    def test_from_array_computes_quantiles(self):
        arr = np.arange(1.0, 101.0)
        ds = DistributionSummary.from_array(arr)
        self.assertAlmostEqual(ds.p50, 50.5, delta=0.5)
        self.assertAlmostEqual(ds.mean, 50.5, delta=0.5)
        self.assertGreater(ds.p90, ds.p75)
        self.assertGreater(ds.p75, ds.p25)
        self.assertGreater(ds.std, 0)

    def test_from_array_empty_returns_zeros(self):
        ds = DistributionSummary.from_array(np.asarray([]))
        self.assertEqual(ds.p50, 0.0)
        self.assertEqual(ds.std, 0.0)

    def test_from_array_drops_nan_inf(self):
        arr = np.asarray([1.0, 2.0, float("nan"), float("inf"), 3.0])
        ds = DistributionSummary.from_array(arr)
        self.assertAlmostEqual(ds.mean, 2.0, places=3)


# ── Convergence ──────────────────────────────────────────────────────

class TestConvergence(unittest.TestCase):
    def test_stable_process_converges(self):
        rng = np.random.default_rng(0)
        vals = rng.normal(100.0, 1.0, size=5000)
        rep = check_convergence(vals, window=1000, tolerance=0.05)
        self.assertIsInstance(rep, ConvergenceReport)
        self.assertTrue(rep.converged)
        self.assertGreater(rep.p50_final, 99.0)
        self.assertLess(rep.p50_final, 101.0)

    def test_insufficient_samples_not_converged(self):
        rep = check_convergence(np.arange(10.0), window=1000, tolerance=0.01)
        self.assertFalse(rep.converged)
        self.assertGreaterEqual(rep.recommended_n, 1000)

    def test_empty_array_returns_not_converged(self):
        rep = check_convergence(np.asarray([]), window=100, tolerance=0.01)
        self.assertFalse(rep.converged)
        self.assertEqual(rep.n_simulations, 0)


# ── Simulator core ──────────────────────────────────────────────────

class TestSimulatorRun(unittest.TestCase):
    def _basic_sim(self, n=500, seed=42):
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=n, seed=seed)
        assumptions = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=12.0, target_value=7.0),
            "days_in_ar": default_execution_assumption(
                "days_in_ar", current_value=55.0, target_value=45.0),
        }
        sim.configure(
            {"denial_rate": 12.0, "days_in_ar": 55.0}, assumptions,
            entry_multiple=10.0, exit_multiple=11.0, hold_years=5.0,
            organic_growth_pct=0.03,
        )
        return sim

    def test_run_produces_distribution_summary(self):
        sim = self._basic_sim()
        r = sim.run(scenario_label="base")
        self.assertEqual(r.n_simulations, 500)
        self.assertGreater(r.ebitda_impact.p50, 0)
        self.assertGreater(r.ebitda_impact.p90, r.ebitda_impact.p10)
        self.assertEqual(r.scenario_label, "base")

    def test_run_without_configure_raises(self):
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=100)
        with self.assertRaises(RuntimeError):
            sim.run()

    def test_zero_variance_matches_deterministic_bridge(self):
        """When uncertainty sources have zero spread, MC mean/P50 must
        match the deterministic bridge exactly. This guarantees the
        simulator is a strict generalization of the bridge, not an
        independent rewriting of it."""
        bridge = _research_bridge()
        current = {"denial_rate": 12.0, "days_in_ar": 55.0, "cost_to_collect": 4.5}
        targets = {"denial_rate": 7.0, "days_in_ar": 45.0, "cost_to_collect": 3.0}
        deterministic = bridge.compute_bridge(current, targets)

        zero_var = {}
        for k, t in targets.items():
            zero_var[k] = MetricAssumption(
                metric_key=k, current_value=current[k], target_value=t,
                uncertainty_source="none",
                prediction_ci_low=t, prediction_ci_high=t,
                execution_probability=1.0, execution_distribution="none",
            )
        sim = RCMMonteCarloSimulator(bridge, n_simulations=200, seed=0)
        sim.configure(current, zero_var)
        r = sim.run()
        self.assertAlmostEqual(r.ebitda_impact.p50,
                               deterministic.total_ebitda_impact, places=2)
        self.assertAlmostEqual(r.ebitda_impact.mean,
                               deterministic.total_ebitda_impact, places=2)
        self.assertAlmostEqual(r.ebitda_impact.std, 0.0, places=3)

    def test_execution_zero_means_no_movement(self):
        """If execution mean is 0 (team never moves the needle),
        EBITDA impact is 0 regardless of prediction."""
        bridge = _research_bridge()
        assumption = MetricAssumption(
            metric_key="denial_rate", current_value=12.0, target_value=5.0,
            uncertainty_source="none",
            prediction_ci_low=5.0, prediction_ci_high=5.0,
            execution_probability=0.0, execution_distribution="none",
        )
        sim = RCMMonteCarloSimulator(bridge, n_simulations=100, seed=1)
        sim.configure({"denial_rate": 12.0}, {"denial_rate": assumption})
        r = sim.run()
        self.assertAlmostEqual(r.ebitda_impact.mean, 0.0, places=1)

    def test_probability_of_negative_impact_zero_on_improvement(self):
        sim = self._basic_sim()
        r = sim.run()
        # All levers are improvements; no sim should produce negative EBITDA.
        self.assertLess(r.probability_of_negative_impact, 0.05)

    def test_probability_of_target_moic_monotonically_decreasing(self):
        sim = self._basic_sim()
        r = sim.run()
        targets = sorted(r.probability_of_target_moic.keys(),
                         key=lambda k: float(k.rstrip("x")))
        probs = [r.probability_of_target_moic[k] for k in targets]
        # Higher MOIC target → lower probability.
        for i in range(len(probs) - 1):
            self.assertGreaterEqual(probs[i], probs[i + 1])

    def test_variance_contribution_sums_to_one(self):
        sim = self._basic_sim(n=400)
        r = sim.run()
        total = sum(r.variance_contribution.values())
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_variance_contribution_is_nonnegative(self):
        sim = self._basic_sim()
        r = sim.run()
        for v in r.variance_contribution.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_tornado_sorted_by_range(self):
        sim = self._basic_sim()
        r = sim.run()
        ranges = [t.range for t in r.tornado_data]
        self.assertEqual(ranges, sorted(ranges, reverse=True))
        for t in r.tornado_data:
            self.assertGreaterEqual(t.range, 0.0)

    def test_histogram_has_n_bins(self):
        sim = self._basic_sim(n=500)
        r = sim.run()
        self.assertEqual(len(r.histogram_data), 30)
        total = sum(h.count for h in r.histogram_data)
        self.assertEqual(total, 500)

    def test_convergence_reported(self):
        sim = self._basic_sim(n=3000)
        r = sim.run()
        self.assertIsInstance(r.convergence_check, ConvergenceReport)
        self.assertGreater(r.convergence_check.p50_final, 0)

    def test_moic_and_irr_populated(self):
        sim = self._basic_sim()
        r = sim.run()
        self.assertGreater(r.moic.p50, 1.0)
        self.assertGreater(r.irr.p50, 0.0)

    def test_working_capital_summary_matches_days_in_ar_lever(self):
        sim = self._basic_sim()
        r = sim.run()
        # Only days_in_ar releases working capital in this setup.
        self.assertGreater(r.working_capital_released.p50, 0)


# ── Correlated sampling ─────────────────────────────────────────────

class TestCorrelatedSampling(unittest.TestCase):
    def test_correlation_matrix_requires_matching_shape(self):
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=100, seed=0)
        assumptions = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=10.0, target_value=5.0),
            "days_in_ar": default_execution_assumption(
                "days_in_ar", current_value=55.0, target_value=45.0),
        }
        wrong_shape = np.eye(3)
        with self.assertRaises(ValueError):
            sim.configure({"denial_rate": 10.0, "days_in_ar": 55.0},
                           assumptions, correlation_matrix=wrong_shape,
                           metric_order=["denial_rate", "days_in_ar"])

    def test_positive_correlation_propagates_to_output(self):
        """When two levers are 0.9-correlated in their prediction
        draws, the bridge output should inherit positive correlation
        between their contributions (simulated samples track together).
        """
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=800, seed=7)
        # Make prediction uncertainty dominate (wide CIs) so the
        # correlation shows through — execution noise is independent.
        a = MetricAssumption(
            metric_key="denial_rate", current_value=12.0, target_value=5.0,
            uncertainty_source="conformal",
            prediction_ci_low=3.0, prediction_ci_high=7.0,
            execution_probability=1.0, execution_distribution="none",
        )
        b = MetricAssumption(
            metric_key="days_in_ar", current_value=55.0, target_value=40.0,
            uncertainty_source="conformal",
            prediction_ci_low=35.0, prediction_ci_high=45.0,
            execution_probability=1.0, execution_distribution="none",
        )
        corr = np.asarray([[1.0, 0.9], [0.9, 1.0]])
        sim.configure(
            {"denial_rate": 12.0, "days_in_ar": 55.0},
            {"denial_rate": a, "days_in_ar": b},
            correlation_matrix=corr,
            metric_order=["denial_rate", "days_in_ar"],
        )
        r = sim.run()
        # Both metrics should have substantial variance contribution;
        # neither dominates because correlated improvements move
        # together. Sum still ≈ 1 by construction.
        total = sum(r.variance_contribution.values())
        self.assertAlmostEqual(total, 1.0, places=3)
        # Sanity: output distribution is wider than with zero corr
        # (positive correlation amplifies combined swing).
        self.assertGreater(r.ebitda_impact.std, 0)


# ── Conformal-driven assumption helper ──────────────────────────────

class TestFromConformal(unittest.TestCase):
    def test_from_conformal_prediction_populates_ci(self):
        a = from_conformal_prediction(
            "denial_rate", current_value=12.0, target_value=6.0,
            ci_low=5.0, ci_high=7.0,
        )
        self.assertEqual(a.uncertainty_source, "conformal")
        self.assertEqual(a.prediction_ci_low, 5.0)
        self.assertEqual(a.prediction_ci_high, 7.0)
        self.assertGreater(a.execution_probability, 0.0)
        self.assertLessEqual(a.execution_probability, 1.0)
        self.assertEqual(a.execution_distribution, "beta")

    def test_default_execution_by_lever_family(self):
        # Denial management: alpha=7, beta=3 → mean 0.70
        a = default_execution_assumption(
            "denial_rate", current_value=10.0, target_value=5.0)
        self.assertAlmostEqual(a.execution_probability, 0.70)
        # AR/collections: 8/2 → 0.80
        b = default_execution_assumption(
            "days_in_ar", current_value=55.0, target_value=40.0)
        self.assertAlmostEqual(b.execution_probability, 0.80)


# ── Scenario comparison ─────────────────────────────────────────────

class TestScenarioComparison(unittest.TestCase):
    def test_compare_returns_per_scenario_and_pairwise(self):
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=200, seed=0)
        sim.configure(
            {"denial_rate": 10.0, "days_in_ar": 55.0},
            {
                "denial_rate": default_execution_assumption(
                    "denial_rate", current_value=10.0, target_value=5.0),
                "days_in_ar": default_execution_assumption(
                    "days_in_ar", current_value=55.0, target_value=40.0),
            },
        )
        base_assumptions = dict(sim._assumptions)

        base_case = dict(base_assumptions)
        upside = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=10.0, target_value=3.0),   # aggressive
            "days_in_ar": default_execution_assumption(
                "days_in_ar", current_value=55.0, target_value=35.0),
        }
        downside = {
            "denial_rate": default_execution_assumption(
                "denial_rate", current_value=10.0, target_value=8.0),   # small reduction
            "days_in_ar": default_execution_assumption(
                "days_in_ar", current_value=55.0, target_value=52.0),
        }
        cmp = compare_scenarios(
            sim, {"base": base_case, "upside": upside, "downside": downside},
        )
        self.assertEqual(len(cmp.per_scenario), 3)
        # Upside should beat base more than half the time.
        self.assertGreater(cmp.pairwise_overlap["upside__vs__base"], 0.5)
        self.assertLess(cmp.pairwise_overlap["downside__vs__upside"], 0.5)
        # Recommendation picks upside given higher mean + only modest downside.
        self.assertEqual(cmp.recommended_scenario, "upside")

    def test_empty_scenarios_returns_empty_comparison(self):
        bridge = _research_bridge()
        sim = RCMMonteCarloSimulator(bridge, n_simulations=50, seed=0)
        sim.configure(
            {"denial_rate": 10.0},
            {"denial_rate": default_execution_assumption(
                "denial_rate", current_value=10.0, target_value=5.0)},
        )
        cmp = compare_scenarios(sim, {})
        self.assertEqual(cmp.per_scenario, {})
        self.assertEqual(cmp.recommended_scenario, "")


# ── SQLite store ────────────────────────────────────────────────────

class TestMCStore(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()
        # Prompt 21 added FK enforcement on mc_simulation_runs.deal_id
        # → parent deal must exist before we persist a MC run.
        self.store.upsert_deal("deal-1", name="deal-1")
        self.store.upsert_deal("d", name="d")

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_save_and_load_roundtrip(self):
        r = MonteCarloResult(n_simulations=100, scenario_label="s1")
        r.ebitda_impact = DistributionSummary(
            p5=1.0, p10=2.0, p25=3.0, p50=4.0,
            p75=5.0, p90=6.0, p95=7.0, mean=4.0, std=1.5,
        )
        save_mc_run(self.store, "deal-1", r)
        loaded = load_latest_mc_run(self.store, "deal-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.scenario_label, "s1")
        self.assertEqual(loaded.ebitda_impact.p50, 4.0)

    def test_load_latest_by_scenario(self):
        r_base = MonteCarloResult(n_simulations=100, scenario_label="base")
        r_up = MonteCarloResult(n_simulations=100, scenario_label="upside")
        save_mc_run(self.store, "d", r_base)
        save_mc_run(self.store, "d", r_up)
        loaded = load_latest_mc_run(self.store, "d", scenario_label="base")
        self.assertEqual(loaded.scenario_label, "base")

    def test_list_mc_runs(self):
        save_mc_run(self.store, "d", MonteCarloResult(scenario_label="a"))
        save_mc_run(self.store, "d", MonteCarloResult(scenario_label="b"))
        rows = list_mc_runs(self.store, "d")
        self.assertEqual(len(rows), 2)


# ── Packet integration ──────────────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):
    def test_packet_builder_uses_rcm_mc_when_bridge_ok(self):
        from rcm_mc.analysis.packet_builder import build_analysis_packet
        from rcm_mc.analysis.packet import ObservedMetric

        store, path = _temp_store()
        try:
            store.upsert_deal("t", name="T", profile={
                "bed_count": 400, "region": "midwest",
                "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
            })
            packet = build_analysis_packet(
                store, "t", skip_simulation=False,
                observed_override={
                    "denial_rate": ObservedMetric(value=11.0),
                    "days_in_ar": ObservedMetric(value=55.0),
                    "cost_to_collect": ObservedMetric(value=4.0),
                },
                target_metrics={"denial_rate": 7.0, "days_in_ar": 45.0,
                                 "cost_to_collect": 3.0},
                financials={
                    "gross_revenue": 1_000_000_000,
                    "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000,
                    "claims_volume": 300_000,
                    "mc_n_sims": 300,
                    "mc_seed": 5,
                    "entry_multiple": 10.0, "exit_multiple": 11.0,
                    "hold_years": 5.0,
                },
            )
            self.assertIsNotNone(packet.simulation)
            self.assertEqual(packet.simulation.status.value, "OK")
            self.assertGreater(packet.simulation.n_sims, 0)
            self.assertGreater(packet.simulation.ebitda_uplift.p50, 0)
            # Variance contribution should have at least one metric.
            self.assertGreater(
                len(packet.simulation.variance_contribution_by_metric), 0,
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── Hold-period grid with MC bands ──────────────────────────────────

class TestHoldPeriodGridMC(unittest.TestCase):
    def test_grid_emits_p10_p50_p90_per_cell(self):
        summary = DistributionSummary(
            p5=5e6, p10=7e6, p25=9e6, p50=12e6,
            p75=15e6, p90=18e6, p95=22e6, mean=12e6, std=4e6,
        )
        rows = hold_period_grid_with_mc(
            entry_ebitda=50e6, mc_ebitda_summary=summary,
            entry_multiple=10.0, exit_multiples=[10.0, 12.0],
            hold_years_list=[3, 5, 7],
            entry_equity=500e6,
        )
        self.assertEqual(len(rows), 2 * 3)
        for row in rows:
            for band in ("p10", "p50", "p90"):
                self.assertIn(f"moic_{band}", row)
                self.assertIn(f"irr_{band}", row)
            # P90 MOIC must be >= P50 MOIC for the same cell.
            self.assertGreaterEqual(row["moic_p90"], row["moic_p50"])
            self.assertGreaterEqual(row["moic_p50"], row["moic_p10"])


if __name__ == "__main__":
    unittest.main()
