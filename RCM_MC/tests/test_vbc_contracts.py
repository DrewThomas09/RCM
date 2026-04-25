"""Tests for the VBC-ContractValuator."""
from __future__ import annotations

import unittest


def _baseline_cohort():
    from rcm_mc.vbc import Cohort
    return Cohort(
        cohort_id="MA_TX",
        size=2000, avg_age=72,
        pct_female=0.55, pct_dual_eligible=0.20,
        hcc_distribution={
            "HCC_DM_NO_COMP": 0.30,
            "HCC_CHF": 0.18,
            "HCC_COPD": 0.22,
        },
        annual_pmpm_cost=1080.0,
        quality_score=0.85,
        expected_attrition_rate=0.10,
    )


class TestPrograms(unittest.TestCase):
    def test_all_programs_registered(self):
        from rcm_mc.vbc_contracts import list_programs
        programs = list_programs()
        ids = {p.program_id for p in programs}
        # Must include the seven core programs
        for required in (
            "mssp_basic_a", "mssp_enhanced_e",
            "aco_reach_global", "aco_reach_professional",
            "ma_delegated_global", "commercial_dce",
            "medicaid_mco_partial",
        ):
            self.assertIn(required, ids)

    def test_mssp_a_no_downside(self):
        """Track A is upside-only — downside_share must be 0."""
        from rcm_mc.vbc_contracts import PROGRAMS
        a = PROGRAMS["mssp_basic_a"]
        self.assertEqual(a.contract_template.downside_share, 0.0)


class TestStochasticSamplers(unittest.TestCase):
    def test_patient_mix_within_bounds(self):
        import numpy as np
        from rcm_mc.vbc_contracts import sample_patient_mix
        rng = np.random.default_rng(0)
        out = sample_patient_mix(
            {"HCC_DM_NO_COMP": 0.30, "HCC_CHF": 0.20}, rng,
            sigma=0.10,
        )
        for v in out.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_attribution_drift_non_negative(self):
        import numpy as np
        from rcm_mc.vbc_contracts import sample_attribution_drift
        rng = np.random.default_rng(0)
        new = sample_attribution_drift(2000, rng, sigma=0.10)
        self.assertGreaterEqual(new, 0)

    def test_coding_intensity_in_published_range(self):
        import numpy as np
        from rcm_mc.vbc_contracts import sample_coding_intensity
        rng = np.random.default_rng(0)
        ci = sample_coding_intensity(0.941, rng)
        # CMS published factor sits in [0.85, 1.0]
        self.assertGreaterEqual(ci, 0.85)
        self.assertLessEqual(ci, 1.0)


class TestMonteCarlo(unittest.TestCase):
    def test_distribution_has_required_quantiles(self):
        from rcm_mc.vbc_contracts import (
            run_monte_carlo_npv, StochasticInputs,
        )
        from rcm_mc.vbc import ContractTerms
        cohort = _baseline_cohort()
        contract = ContractTerms(
            contract_type="TCC", benchmark_pmpm=1180.0,
        )
        result = run_monte_carlo_npv(
            cohort, contract,
            inputs=StochasticInputs(n_simulations=80, seed=1),
        )
        for k in ("mean_npv_mm", "p5_mm", "p25_mm",
                  "p50_mm", "p75_mm", "p95_mm",
                  "prob_loss", "n_simulations"):
            self.assertIn(k, result)
        # Quantile ordering invariant
        self.assertLessEqual(result["p5_mm"], result["p25_mm"])
        self.assertLessEqual(result["p25_mm"], result["p50_mm"])
        self.assertLessEqual(result["p50_mm"], result["p75_mm"])
        self.assertLessEqual(result["p75_mm"], result["p95_mm"])


class TestBayesianUpdate(unittest.TestCase):
    def test_no_obs_returns_prior(self):
        from rcm_mc.vbc_contracts import bayesian_update_pmpm, PriorBelief
        prior = PriorBelief(mean_pmpm=1100.0, stddev_pmpm=80.0)
        m, sd = bayesian_update_pmpm(prior, [])
        self.assertEqual(m, 1100.0)
        self.assertEqual(sd, 80.0)

    def test_obs_pulls_posterior_toward_data(self):
        from rcm_mc.vbc_contracts import bayesian_update_pmpm, PriorBelief
        prior = PriorBelief(mean_pmpm=1100.0, stddev_pmpm=80.0)
        # 3 observations averaging $1300
        m, sd = bayesian_update_pmpm(
            prior, [1280, 1310, 1310], obs_stddev=80.0,
        )
        # Posterior should sit between prior and observed mean
        self.assertGreater(m, 1100.0)
        self.assertLess(m, 1300.0)
        # SD shrinks with data
        self.assertLess(sd, prior.stddev_pmpm)


class TestValuateContract(unittest.TestCase):
    def test_returns_distribution(self):
        from rcm_mc.vbc_contracts import (
            valuate_contract, StochasticInputs,
        )
        cohort = _baseline_cohort()
        result = valuate_contract(
            cohort, "aco_reach_professional",
            inputs=StochasticInputs(n_simulations=50, seed=2),
        )
        self.assertEqual(result.program_id, "aco_reach_professional")
        self.assertIn("mean_npv_mm", result.distribution)


class TestTrackChoice(unittest.TestCase):
    def test_optimizer_returns_recommendation(self):
        from rcm_mc.vbc_contracts import (
            choose_optimal_track, StochasticInputs,
        )
        cohort = _baseline_cohort()
        result = choose_optimal_track(
            cohort,
            program_ids=[
                "mssp_basic_a", "mssp_basic_d",
                "aco_reach_professional",
            ],
            inputs=StochasticInputs(n_simulations=50, seed=3),
        )
        self.assertIsNotNone(result["recommended"])
        self.assertEqual(len(result["results"]), 3)
        # Results sorted descending by risk-adjusted score
        scores = [r.risk_adjusted_score for r in result["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
