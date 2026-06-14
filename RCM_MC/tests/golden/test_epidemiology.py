"""Golden test for NEW-19 Epidemiology patient-flow funnel.

Hand-computed mechanics:

- persistence_to_hazard(0.5) = -ln(0.5)/12 = 0.0577623...
- exponential survival S(tau)=exp(-lambda*tau): S(0)=1, monotone decreasing.
- mean_persistence_months for a constant hazard converges to the geometric sum
  1/(1-exp(-lambda)).
- simulate_cohorts of a single 100-patient cohort decays as 100*S(t).
- A constant initiation stream reaches a steady state of init*D-bar.

Funnel (population 1,000,000; prevalence 0.10; diagnosis 0.80; treatment 0.50):
    prevalent pool = 100,000
    diagnosed      = 80,000
    treated pool   = 40,000
    annual revenue = 40,000 * 12 * $10 = $4,800,000
The steady-state cohort build must reconcile to the 40,000 treated pool.
"""
import math
import unittest

from rcm_mc.cdd.epidemiology import (
    exponential_survival,
    line_of_therapy_occupancy,
    mean_persistence_months,
    patient_flow_funnel,
    persistence_to_hazard,
    simulate_cohorts,
    weibull_survival,
)

TOL = 1e-9


class TestEpidemiology(unittest.TestCase):
    def test_persistence_to_hazard(self):
        self.assertAlmostEqual(
            persistence_to_hazard(0.5), -math.log(0.5) / 12.0, delta=TOL
        )
        # The worked example in the spec: 78.28% -> ~0.0204/month.
        self.assertAlmostEqual(persistence_to_hazard(0.7828), 0.0204, delta=1e-4)
        with self.assertRaises(ValueError):
            persistence_to_hazard(0.0)

    def test_exponential_survival_shape(self):
        s = exponential_survival(0.05)
        self.assertAlmostEqual(s(0), 1.0, delta=TOL)
        self.assertAlmostEqual(s(10), math.exp(-0.5), delta=TOL)
        self.assertLess(s(20), s(10))

    def test_weibull_beta_one_equals_exponential(self):
        lam = 0.05
        w = weibull_survival(1.0 / lam, 1.0)
        e = exponential_survival(lam)
        for tau in (0, 1, 5, 25):
            self.assertAlmostEqual(w(tau), e(tau), delta=TOL)

    def test_mean_persistence_matches_geometric_sum(self):
        lam = 0.05
        d_bar = mean_persistence_months(exponential_survival(lam))
        self.assertAlmostEqual(d_bar, 1.0 / (1.0 - math.exp(-lam)), delta=1e-6)

    def test_single_cohort_decays_as_survival(self):
        s = exponential_survival(0.1)
        n = simulate_cohorts([100.0, 0.0, 0.0], s)
        self.assertAlmostEqual(n[0], 100.0, delta=TOL)
        self.assertAlmostEqual(n[1], 100.0 * s(1), delta=TOL)
        self.assertAlmostEqual(n[2], 100.0 * s(2), delta=TOL)

    def test_constant_initiation_reaches_steady_state(self):
        s = exponential_survival(0.1)
        d_bar = mean_persistence_months(s)
        n = simulate_cohorts([50.0] * 400, s)
        # The tail converges to init * D-bar.
        self.assertAlmostEqual(n[-1], 50.0 * d_bar, delta=50.0 * d_bar * 1e-3)

    def test_funnel_hand_computed(self):
        ex = patient_flow_funnel(
            population=1_000_000,
            prevalence_rate=0.10,
            diagnosis_rate=0.80,
            treatment_rate=0.50,
            price_per_patient_month=10.0,
            persistence_12=0.5,
            source="Golden fixture",
            vintage="2026",
        )
        m = ex.meta
        self.assertAlmostEqual(m["prevalent_pool"], 100_000.0, delta=TOL)
        self.assertAlmostEqual(m["diagnosed"], 80_000.0, delta=TOL)
        self.assertAlmostEqual(m["treated_pool"], 40_000.0, delta=TOL)
        self.assertAlmostEqual(m["annual_revenue"], 4_800_000.0, delta=TOL)
        self.assertTrue(
            ex.reconciled,
            msg="steady-state cohort build must reconcile to the treated pool",
        )

    def test_thin_funnel_flags(self):
        ex = patient_flow_funnel(
            population=1_000_000,
            prevalence_rate=0.10,
            diagnosis_rate=0.10,  # 0.10 * 0.50 = 0.05 conversion, below 10%
            treatment_rate=0.50,
            price_per_patient_month=10.0,
            persistence_12=0.5,
        )
        self.assertIn("thin_funnel", ex.flag_codes())

    def test_line_of_therapy_occupancy_conserves_flow(self):
        # Two lines, no progression, pure discontinuation at 10%/mo on line 1.
        # Steady state line-1 occupancy = init / discontinue = 100 / 0.1 = 1000.
        occ = line_of_therapy_occupancy(
            [{"progress": 0.0, "discontinue": 0.1}, {"progress": 0.0, "discontinue": 0.1}],
            line1_initiations_per_month=100.0,
            horizon_months=500,
        )
        self.assertAlmostEqual(occ[0], 1000.0, delta=1.0)
        # Line 2 never fills because progression is zero.
        self.assertAlmostEqual(occ[1], 0.0, delta=TOL)

    def test_requires_a_persistence_input(self):
        with self.assertRaises(ValueError):
            patient_flow_funnel(
                population=1000,
                prevalence_rate=0.1,
                diagnosis_rate=0.5,
                treatment_rate=0.5,
                price_per_patient_month=1.0,
            )


if __name__ == "__main__":
    unittest.main()
