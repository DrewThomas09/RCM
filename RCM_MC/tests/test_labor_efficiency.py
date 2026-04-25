"""Tests for labor efficiency model + EBITDA optimization."""
from __future__ import annotations

import unittest


def _profile(ccn, beds, aob, discharges, fte, labor_cost,
             npr, *, bucket=None):
    from rcm_mc.ml.labor_efficiency import HospitalLaborProfile
    return HospitalLaborProfile(
        ccn=ccn, fiscal_year=2023,
        beds=beds, adjusted_occupied_beds=aob,
        adjusted_discharges=discharges,
        total_fte=fte, total_labor_cost=labor_cost,
        net_patient_revenue=npr,
        bed_size_bucket=bucket,
    )


def _peer_set(n=10, fte_per_aob=5.5, salary=95_000):
    """n peer hospitals at the given staffing intensity ± noise."""
    out = []
    for i in range(n):
        beds = 250
        aob = 200
        # FTE = ratio × AOB, with small variation
        fte = fte_per_aob * aob * (0.93 + 0.015 * i)
        labor = fte * salary
        npr = labor / 0.52
        discharges = aob * 60
        out.append(_profile(
            f"PEER{i:03d}", beds, aob, discharges,
            fte, labor, npr, bucket="mid"))
    return out


class TestProfileMetrics(unittest.TestCase):
    def test_fte_per_aob(self):
        p = _profile("X", 250, 200, 12000,
                     1100, 100_000_000, 200_000_000)
        self.assertAlmostEqual(p.fte_per_aob, 5.5)

    def test_labor_cost_per_discharge(self):
        p = _profile("X", 250, 200, 10_000,
                     1000, 80_000_000, 200_000_000)
        self.assertAlmostEqual(
            p.labor_cost_per_adj_discharge, 8000.0)

    def test_labor_pct_of_npsr(self):
        p = _profile("X", 250, 200, 12000,
                     1000, 100_000_000, 200_000_000)
        self.assertAlmostEqual(p.labor_pct_of_npsr, 0.50)

    def test_salary_per_fte(self):
        p = _profile("X", 250, 200, 12000,
                     1000, 95_000_000, 200_000_000)
        self.assertAlmostEqual(p.salary_per_fte, 95_000)

    def test_zero_aob_returns_none(self):
        p = _profile("X", 250, 0, 12000,
                     1000, 95_000_000, 200_000_000)
        self.assertIsNone(p.fte_per_aob)


class TestPeerBenchmarks(unittest.TestCase):
    def test_basic_percentiles(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        bench = compute_peer_benchmarks(
            peers, target_bucket="mid")
        # Should have populated p25/p50/p75 from the peer set
        self.assertGreater(bench.fte_per_aob["p50"], 5.0)
        self.assertLess(bench.fte_per_aob["p50"], 6.0)
        self.assertEqual(bench.n_peers, 10)
        self.assertIn("mid", bench.cohort_label)

    def test_falls_back_to_industry(self):
        """Sparse cohort → fallback to industry medians."""
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
            INDUSTRY_FALLBACK,
        )
        peers = _peer_set(n=2)
        bench = compute_peer_benchmarks(
            peers, target_bucket="critical_access")
        self.assertEqual(
            bench.fte_per_aob,
            INDUSTRY_FALLBACK["fte_per_aob"])
        self.assertIn("fallback", bench.cohort_label)

    def test_filters_by_bucket(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
        )
        peers = _peer_set(n=10)
        # All peers tagged 'mid'; ask for 'large' → fallback
        bench = compute_peer_benchmarks(
            peers, target_bucket="large")
        self.assertIn("fallback", bench.cohort_label)


class TestLaborEfficiency(unittest.TestCase):
    def test_overstaffed_hospital(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_labor_efficiency,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        # Target: 7.5 FTE/AOB (well above peer p75)
        target = _profile(
            "TARGET", 250, 200, 12000,
            1500, 142_500_000, 274_000_000,
            bucket="mid")
        result = compute_labor_efficiency(
            target, peers)
        self.assertEqual(
            result.overall_staffing_label,
            "over_staffed")
        # FTE/AOB metric should be flagged
        fte_var = next(v for v in result.variances
                       if v.metric == "fte_per_aob")
        self.assertEqual(fte_var.direction, "over_staffed")
        self.assertGreater(fte_var.gap_to_p50, 0)

    def test_understaffed_hospital(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_labor_efficiency,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        # Target: 3.8 FTE/AOB (well below peer p25)
        target = _profile(
            "TARGET", 250, 200, 12000,
            760, 72_200_000, 138_000_000,
            bucket="mid")
        result = compute_labor_efficiency(target, peers)
        self.assertEqual(
            result.overall_staffing_label,
            "under_staffed")
        # Burnout-risk note should fire
        self.assertTrue(any(
            "burnout" in n or "vacancy" in n
            for n in result.notes))

    def test_in_line_hospital(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_labor_efficiency,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        # Target: matches peer median
        target = _profile(
            "TARGET", 250, 200, 12000,
            1100, 104_500_000, 201_000_000,
            bucket="mid")
        result = compute_labor_efficiency(target, peers)
        self.assertEqual(
            result.overall_staffing_label, "in_line")

    def test_metric_percentiles(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_labor_efficiency,
        )
        peers = _peer_set(n=10)
        target = _profile(
            "TARGET", 250, 200, 12000,
            1100, 104_500_000, 201_000_000,
            bucket="mid")
        result = compute_labor_efficiency(target, peers)
        for v in result.variances:
            self.assertGreaterEqual(v.percentile, 0)
            self.assertLessEqual(v.percentile, 100)


class TestOptimizationModel(unittest.TestCase):
    def test_overstaffed_produces_savings(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
            model_labor_optimization_impact,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5,
                          salary=95_000)
        bench = compute_peer_benchmarks(
            peers, target_bucket="mid")
        # 7.5 FTE/AOB → 1500 FTE; target is 5.5 → 1100; 400 over
        target = _profile(
            "TARGET", 250, 200, 12000,
            1500, 142_500_000, 274_000_000,
            bucket="mid")
        scenarios = model_labor_optimization_impact(
            target, bench)
        self.assertIn("realistic", scenarios)
        # Realistic = 400 FTE × 0.4 realism ≈ 160 FTE × $95K
        # = ~$15M (peer p50 has small variation, so exact value
        # depends on percentile interpolation)
        realistic = scenarios["realistic"]
        self.assertGreater(realistic.fte_reduction, 150)
        self.assertLess(realistic.fte_reduction, 175)
        self.assertGreater(
            realistic.annual_labor_savings, 14_000_000)
        self.assertLess(
            realistic.annual_labor_savings, 17_000_000)
        # Optimistic > Realistic > Conservative
        self.assertGreater(
            scenarios["optimistic"].annual_labor_savings,
            scenarios["realistic"].annual_labor_savings)
        self.assertGreater(
            scenarios["realistic"].annual_labor_savings,
            scenarios["conservative"].annual_labor_savings)

    def test_already_lean_no_savings(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
            model_labor_optimization_impact,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        bench = compute_peer_benchmarks(
            peers, target_bucket="mid")
        # 4.0 FTE/AOB — already below median
        lean = _profile(
            "TARGET", 250, 200, 12000,
            800, 76_000_000, 146_000_000,
            bucket="mid")
        scenarios = model_labor_optimization_impact(
            lean, bench)
        # Refuses to model 'savings' from cutting deeper
        self.assertEqual(scenarios, {})

    def test_realism_factor_override(self):
        from rcm_mc.ml.labor_efficiency import (
            compute_peer_benchmarks,
            model_labor_optimization_impact,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5,
                          salary=95_000)
        bench = compute_peer_benchmarks(
            peers, target_bucket="mid")
        target = _profile(
            "TARGET", 250, 200, 12000,
            1500, 142_500_000, 274_000_000,
            bucket="mid")
        # Aggressive realism (0.8) → 2× the savings of default
        baseline = model_labor_optimization_impact(
            target, bench, realism_factor=0.40)
        aggressive = model_labor_optimization_impact(
            target, bench, realism_factor=0.80)
        self.assertGreater(
            aggressive["realistic"].annual_labor_savings,
            baseline["realistic"].annual_labor_savings)


class TestComposer(unittest.TestCase):
    def test_overstaffed_attaches_optimization(self):
        from rcm_mc.ml.labor_efficiency import (
            analyze_labor_efficiency,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        target = _profile(
            "TARGET", 250, 200, 12000,
            1500, 142_500_000, 274_000_000,
            bucket="mid")
        result = analyze_labor_efficiency(target, peers)
        self.assertEqual(
            result.overall_staffing_label,
            "over_staffed")
        self.assertIn("realistic", result.optimization)
        # Note mentions the EBITDA impact
        self.assertTrue(any(
            "annual EBITDA uplift" in n
            for n in result.notes))

    def test_in_line_no_optimization(self):
        from rcm_mc.ml.labor_efficiency import (
            analyze_labor_efficiency,
        )
        peers = _peer_set(n=10, fte_per_aob=5.5)
        target = _profile(
            "TARGET", 250, 200, 12000,
            1100, 104_500_000, 201_000_000,
            bucket="mid")
        result = analyze_labor_efficiency(target, peers)
        # In-line hospitals don't get optimization
        self.assertEqual(result.optimization, {})


if __name__ == "__main__":
    unittest.main()
