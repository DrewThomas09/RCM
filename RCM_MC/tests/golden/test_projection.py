"""Golden test for NEW-24 Forward-projection engines.

Cohort-component (3 bands; survival [0.9, 0.8, 0.5]; fertility [0, 0.5, 0]):
    pop          = [100, 80, 60]
    births       = 100*0 + 80*0.5 + 60*0 = 40
    next[0]      = 40
    next[1]      = 100*0.9 = 90
    next[2]      = 80*0.8 + 60*0.5 = 64 + 30 = 94
    -> [40, 90, 94]

Fisher-Pry: feeding exact logistic points (a=-2, b=1) must recover a and b, and
fisher_pry_share(-2, 1, 0) = 1/(1+exp(2)) = 0.119202922...
"""
import math
import unittest

from rcm_mc.cdd.projection import (
    cohort_component_projection,
    cohort_component_step,
    fisher_pry_projection,
    fisher_pry_share,
    fit_fisher_pry,
    project_demand,
)

TOL = 1e-9


class TestProjection(unittest.TestCase):
    def test_cohort_step_hand_computed(self):
        nxt = cohort_component_step(
            [100.0, 80.0, 60.0],
            survival=[0.9, 0.8, 0.5],
            fertility=[0.0, 0.5, 0.0],
        )
        self.assertAlmostEqual(nxt[0], 40.0, delta=TOL)
        self.assertAlmostEqual(nxt[1], 90.0, delta=TOL)
        self.assertAlmostEqual(nxt[2], 94.0, delta=TOL)

    def test_cohort_projection_returns_each_year(self):
        proj = cohort_component_projection(
            [100.0, 80.0, 60.0],
            survival=[0.9, 0.8, 0.5],
            fertility=[0.0, 0.5, 0.0],
            years=2,
        )
        self.assertEqual(len(proj), 3)  # year 0 + 2 projected
        self.assertEqual(proj[0], [100.0, 80.0, 60.0])
        self.assertAlmostEqual(proj[1][2], 94.0, delta=TOL)

    def test_migration_applied(self):
        nxt = cohort_component_step(
            [100.0, 80.0, 60.0],
            survival=[0.9, 0.8, 0.5],
            fertility=[0.0, 0.5, 0.0],
            net_migration=[10.0, -5.0, 0.0],
        )
        self.assertAlmostEqual(nxt[0], 50.0, delta=TOL)
        self.assertAlmostEqual(nxt[1], 85.0, delta=TOL)

    def test_project_demand_applies_rates(self):
        pops = [[100.0, 80.0], [110.0, 90.0]]
        # band rates per capita: 0.1 and 0.2
        demand = project_demand(pops, [0.1, 0.2])
        self.assertAlmostEqual(demand[0], 100 * 0.1 + 80 * 0.2, delta=TOL)
        self.assertAlmostEqual(demand[1], 110 * 0.1 + 90 * 0.2, delta=TOL)

    def test_fisher_pry_share_value(self):
        self.assertAlmostEqual(
            fisher_pry_share(-2.0, 1.0, 0.0), 1.0 / (1.0 + math.exp(2.0)), delta=TOL
        )

    def test_fit_recovers_parameters(self):
        a_true, b_true = -2.0, 1.0
        times = [0, 1, 2, 3, 4]
        shares = [fisher_pry_share(a_true, b_true, t) for t in times]
        a, b = fit_fisher_pry(times, shares)
        self.assertAlmostEqual(a, a_true, delta=1e-6)
        self.assertAlmostEqual(b, b_true, delta=1e-6)

    def test_projection_exhibit_reconciles(self):
        ex = fisher_pry_projection(
            times=[0, 1, 2, 3, 4],
            shares=[0.20, 0.28, 0.38, 0.49, 0.60],
            future_times=[5, 6, 7],
            source="Golden fixture",
            vintage="2026",
        )
        self.assertTrue(ex.reconciled)
        self.assertGreater(ex.meta["b"], 0.0)  # share is rising
        # Projected share keeps climbing past the last observed point.
        self.assertGreater(ex.meta["projected"][-1][1], 0.60)

    def test_fit_needs_two_points(self):
        with self.assertRaises(ValueError):
            fit_fisher_pry([0], [0.5])


if __name__ == "__main__":
    unittest.main()
