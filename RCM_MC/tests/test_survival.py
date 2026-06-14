"""Tests for the survival-analysis module (KM / log-rank / Cox)."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.survival import (
    cox_ph,
    kaplan_meier,
    logrank_test,
)


class KaplanMeierTests(unittest.TestCase):

    def test_no_censoring_simple_curve(self):
        # 4 subjects, events at 1,2,3,4. S drops by 1/n each step.
        km = kaplan_meier([1, 2, 3, 4], [1, 1, 1, 1])
        self.assertEqual(km.n_subjects, 4)
        self.assertEqual(km.n_events_total, 4)
        # After first event: 1 - 1/4 = 0.75
        self.assertAlmostEqual(km.survival[0], 0.75)
        self.assertAlmostEqual(km.survival[-1], 0.0)

    def test_survival_is_monotone_nonincreasing(self):
        rng = np.random.default_rng(0)
        t = rng.exponential(10, 60)
        e = (rng.random(60) < 0.7).astype(int)
        km = kaplan_meier(t, e)
        for a, b in zip(km.survival, km.survival[1:]):
            self.assertGreaterEqual(a + 1e-9, b)

    def test_censoring_keeps_subject_at_risk(self):
        # Censored obs at t=2 should still count in the risk set at t<=2.
        km = kaplan_meier([1, 2, 3], [1, 0, 1])
        # At t=1: at risk 3, 1 event → S=2/3
        self.assertAlmostEqual(km.survival[0], 2 / 3)

    def test_median_survival(self):
        km = kaplan_meier([1, 2, 3, 4, 5, 6], [1, 1, 1, 1, 1, 1])
        # S drops 5/6,4/6,3/6=0.5 at t=3 → median 3
        self.assertEqual(km.median_survival, 3.0)

    def test_ci_within_unit_interval(self):
        km = kaplan_meier([1, 2, 3, 4, 5], [1, 1, 1, 1, 0])
        for lo, hi, s in zip(km.ci_low, km.ci_high, km.survival):
            self.assertGreaterEqual(s + 1e-9, lo)
            self.assertLessEqual(s - 1e-9, hi)
            self.assertGreaterEqual(lo, 0.0)
            self.assertLessEqual(hi, 1.0)

    def test_survival_at_step_function(self):
        km = kaplan_meier([2, 4, 6], [1, 1, 1])
        self.assertEqual(km.survival_at(0), 1.0)       # before any event
        self.assertAlmostEqual(km.survival_at(2), km.survival[0])
        self.assertAlmostEqual(km.survival_at(5), km.survival[1])

    def test_empty(self):
        km = kaplan_meier([], [])
        self.assertEqual(km.n_subjects, 0)
        self.assertIsNone(km.median_survival)

    def test_to_dict(self):
        d = kaplan_meier([1, 2], [1, 1]).to_dict()
        self.assertEqual(d["citation_key"], "SV1")


class LogRankTests(unittest.TestCase):

    def test_identical_groups_not_significant(self):
        # Two interleaved identical groups → high p.
        t = [1, 1, 2, 2, 3, 3, 4, 4]
        e = [1, 1, 1, 1, 1, 1, 1, 1]
        g = [0, 1, 0, 1, 0, 1, 0, 1]
        r = logrank_test(t, e, g)
        self.assertGreater(r.p_value, 0.2)

    def test_separated_groups_significant(self):
        # Group 1 fails early, group 0 fails late → low p.
        rng = np.random.default_rng(1)
        t0 = rng.normal(30, 3, 40)
        t1 = rng.normal(10, 3, 40)
        t = np.concatenate([t0, t1])
        e = np.ones(80, dtype=int)
        g = np.concatenate([np.zeros(40), np.ones(40)]).astype(int)
        r = logrank_test(t, e, g)
        self.assertLess(r.p_value, 0.001)
        self.assertGreater(r.observed_group1, r.expected_group1)

    def test_chi_square_nonnegative(self):
        r = logrank_test([1, 2, 3, 4], [1, 1, 1, 1], [0, 0, 1, 1])
        self.assertGreaterEqual(r.chi_square, 0.0)


class CoxTests(unittest.TestCase):

    def _make_cox_data(self, beta=1.0, n=300, seed=0):
        """Exponential survival with hazard exp(beta*x); admin censoring."""
        rng = np.random.default_rng(seed)
        x = rng.normal(0, 1, n)
        base_rate = 0.1
        scale = 1.0 / (base_rate * np.exp(beta * x))
        t_event = rng.exponential(scale)
        c = rng.uniform(0, 30, n)            # censoring time
        t = np.minimum(t_event, c)
        e = (t_event <= c).astype(int)
        return t, e, x

    def test_recovers_positive_coefficient(self):
        t, e, x = self._make_cox_data(beta=1.0, n=400, seed=2)
        res = cox_ph(t, e, x.reshape(-1, 1), names=["acuity"])
        self.assertTrue(res.converged)
        cov = res.covariates[0]
        self.assertAlmostEqual(cov.coef, 1.0, delta=0.3)
        self.assertGreater(cov.hazard_ratio, 1.0)
        self.assertLess(cov.p_value, 0.01)

    def test_recovers_negative_coefficient(self):
        t, e, x = self._make_cox_data(beta=-0.8, n=400, seed=3)
        res = cox_ph(t, e, x.reshape(-1, 1), names=["protective"])
        cov = res.covariates[0]
        self.assertLess(cov.hazard_ratio, 1.0)

    def test_concordance_above_half_for_signal(self):
        t, e, x = self._make_cox_data(beta=1.5, n=400, seed=4)
        res = cox_ph(t, e, x.reshape(-1, 1))
        self.assertGreater(res.concordance, 0.6)

    def test_null_covariate_ci_includes_one(self):
        rng = np.random.default_rng(5)
        n = 300
        t = rng.exponential(10, n)
        e = (rng.random(n) < 0.7).astype(int)
        x = rng.normal(0, 1, n)             # unrelated to t
        res = cox_ph(t, e, x.reshape(-1, 1))
        cov = res.covariates[0]
        self.assertLess(cov.ci_low_hr, 1.0)
        self.assertGreater(cov.ci_high_hr, 1.0)

    def test_multivariable(self):
        rng = np.random.default_rng(6)
        n = 400
        x1 = rng.normal(0, 1, n)
        x2 = rng.normal(0, 1, n)
        scale = 1.0 / (0.1 * np.exp(1.0 * x1 - 0.5 * x2))
        t_event = rng.exponential(scale)
        c = rng.uniform(0, 30, n)
        t = np.minimum(t_event, c)
        e = (t_event <= c).astype(int)
        res = cox_ph(t, e, np.column_stack([x1, x2]), names=["a", "b"])
        self.assertEqual(len(res.covariates), 2)
        self.assertGreater(res.covariates[0].hazard_ratio, 1.0)
        self.assertLess(res.covariates[1].hazard_ratio, 1.0)

    def test_headline_and_dict(self):
        t, e, x = self._make_cox_data(beta=1.0, n=200, seed=7)
        res = cox_ph(t, e, x.reshape(-1, 1), names=["acuity"])
        self.assertIn("acuity", res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "SV1")


class CoxTiesTests(unittest.TestCase):

    def test_efron_equals_breslow_without_ties(self):
        # Distinct event times → the two corrections must agree.
        t = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        e = [1, 1, 1, 1, 1, 1, 1, 1]
        x = [[v] for v in (0.5, -0.3, 1.2, -1.0, 0.1, 0.8, -0.6, 0.2)]
        b = cox_ph(t, e, x, ties="breslow")
        ef = cox_ph(t, e, x, ties="efron")
        self.assertAlmostEqual(b.covariates[0].coef, ef.covariates[0].coef,
                               places=6)

    def test_efron_runs_with_heavy_ties_and_recovers_sign(self):
        rng = np.random.default_rng(9)
        n = 400
        x = rng.normal(0, 1, n)
        scale = 1.0 / (0.1 * np.exp(1.0 * x))
        t_event = rng.exponential(scale)
        # Coarsen to integer times → many ties.
        t = np.ceil(np.minimum(t_event, rng.uniform(0, 30, n)))
        e = (t_event <= rng.uniform(0, 30, n)).astype(int)
        res = cox_ph(t, e, x.reshape(-1, 1), ties="efron")
        self.assertGreater(res.tie_fraction, 0.3)   # genuinely tied
        self.assertGreater(res.covariates[0].hazard_ratio, 1.0)

    def test_invalid_ties_raises(self):
        with self.assertRaises(ValueError):
            cox_ph([1, 2], [1, 1], [[0.0], [1.0]], ties="nope")


if __name__ == "__main__":
    unittest.main()
