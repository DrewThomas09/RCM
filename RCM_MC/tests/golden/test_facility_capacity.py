"""Golden test for NEW-21 Facility / capacity model.

Hand-computed (30 chairs, 312 days, 4 turns/day, 70% utilization, $520/visit):
    theoretical capacity = 30 * 312 * 4 = 37,440
    utilized capacity    = 37,440 * 0.70 = 26,208
    revenue              = 26,208 * 520 = 13,628,160

Erlang-C (lambda=2, mu=1, c=3 servers): offered load a=2, rho=2/3.
    sum_{k=0..2} a^k/k! = 1 + 2 + 2 = 5
    last term = a^3 / (3! * (1-rho)) = 8 / (6 * 1/3) = 4
    P(wait) = 4 / (5 + 4) = 4/9 = 0.4444...
"""
import unittest

from rcm_mc.cdd.facility_capacity import erlang_c_wait_probability, facility_capacity

TOL = 1e-6


class TestFacilityCapacity(unittest.TestCase):
    def test_capacity_to_revenue_hand_computed(self):
        ex = facility_capacity(
            units=30,
            periods=312,
            turns_per_period=4,
            utilization=0.70,
            revenue_per_volume=520.0,
            units_label="chairs",
            source="Golden fixture",
            vintage="2026",
        )
        m = ex.meta
        self.assertAlmostEqual(m["theoretical_capacity"], 37_440.0, delta=TOL)
        self.assertAlmostEqual(m["utilized_capacity"], 26_208.0, delta=TOL)
        self.assertAlmostEqual(m["revenue"], 13_628_160.0, delta=1e-3)
        self.assertEqual(m["binding_constraint"], "physical")
        self.assertTrue(ex.reconciled)

    def test_demand_binding_caps_volume(self):
        ex = facility_capacity(
            units=30,
            periods=312,
            turns_per_period=4,
            utilization=0.70,
            revenue_per_volume=520.0,
            demand_volume=20_000.0,
        )
        self.assertEqual(ex.meta["binding_constraint"], "demand")
        self.assertAlmostEqual(ex.meta["effective_volume"], 20_000.0, delta=TOL)
        self.assertIn("binding_demand", ex.flag_codes())

    def test_staffing_binding_caps_volume(self):
        ex = facility_capacity(
            units=30,
            periods=312,
            turns_per_period=4,
            utilization=0.70,
            revenue_per_volume=520.0,
            staffing_capacity_volume=15_000.0,
            demand_volume=40_000.0,
        )
        self.assertEqual(ex.meta["binding_constraint"], "staffing")
        self.assertAlmostEqual(ex.meta["effective_volume"], 15_000.0, delta=TOL)

    def test_high_utilization_flag(self):
        ex = facility_capacity(
            units=10,
            periods=300,
            turns_per_period=3,
            utilization=0.95,
            revenue_per_volume=100.0,
        )
        self.assertIn("high_utilization", ex.flag_codes())

    def test_erlang_c_hand_computed(self):
        self.assertAlmostEqual(
            erlang_c_wait_probability(2.0, 1.0, 3), 4.0 / 9.0, delta=TOL
        )

    def test_erlang_c_unstable_raises(self):
        with self.assertRaises(ValueError):
            erlang_c_wait_probability(3.0, 1.0, 3)

    def test_utilization_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            facility_capacity(
                units=1, periods=1, turns_per_period=1,
                utilization=1.5, revenue_per_volume=1.0,
            )


if __name__ == "__main__":
    unittest.main()
