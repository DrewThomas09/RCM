"""Golden test for NEW-22 Installed-base / adoption model.

Hand-computed discrete Bass (M=1000, p=0.03, q=0.38):
    n(1) = 0.03*1000 + 0.38*(0/1000)*1000 = 30        ; N(1) = 30
    n(2) = 0.03*970 + 0.38*(30/1000)*970
         = 29.1 + 0.38*0.03*970 = 29.1 + 11.058 = 40.158 ; N(2) = 70.158

ACV build (seats 10, price 100 -> ACV 1,000; NRR 1.1):
    ARR(1) = 0*1.1 + 30*1000          = 30,000
    ARR(2) = 30,000*1.1 + 40.158*1000 = 33,000 + 40,158 = 73,158

NRR: (1,000,000 + 200,000 - 50,000 - 100,000) / 1,000,000 = 1.05
"""
import math
import unittest

from rcm_mc.cdd.adoption_bass import (
    adoption_model,
    bass_adoption,
    bass_peak_period,
    nrr,
)

TOL = 1e-6


class TestAdoptionBass(unittest.TestCase):
    def test_bass_first_periods_hand_computed(self):
        d = bass_adoption(1000.0, 0.03, 0.38, 5)
        self.assertAlmostEqual(d["incremental"][0], 30.0, delta=TOL)
        self.assertAlmostEqual(d["cumulative"][0], 30.0, delta=TOL)
        self.assertAlmostEqual(d["incremental"][1], 40.158, delta=1e-3)
        self.assertAlmostEqual(d["cumulative"][1], 70.158, delta=1e-3)

    def test_bass_monotone_and_bounded(self):
        d = bass_adoption(1000.0, 0.03, 0.38, 60)
        cum = d["cumulative"]
        self.assertTrue(all(cum[i] <= cum[i + 1] + TOL for i in range(len(cum) - 1)))
        self.assertLessEqual(cum[-1], 1000.0 + TOL)
        # Over a long horizon the diffusion nearly saturates the potential.
        self.assertGreater(cum[-1], 990.0)

    def test_bass_peak_period(self):
        # t* = ln(q/p)/(p+q) = ln(0.38/0.03)/0.41
        self.assertAlmostEqual(
            bass_peak_period(0.03, 0.38), math.log(0.38 / 0.03) / 0.41, delta=TOL
        )

    def test_nrr(self):
        self.assertAlmostEqual(
            nrr(1_000_000.0, 200_000.0, 50_000.0, 100_000.0), 1.05, delta=TOL
        )

    def test_arr_trajectory_hand_computed(self):
        ex = adoption_model(
            addressable_units=1000,
            icp_qualification_rate=1.0,
            p=0.03,
            q=0.38,
            periods=5,
            seats_per_customer=10,
            price_per_seat=100.0,
            net_revenue_retention=1.10,
            source="Golden fixture",
            vintage="2026",
        )
        path = ex.meta["arr_path"]
        self.assertAlmostEqual(path[0], 30_000.0, delta=1e-3)
        self.assertAlmostEqual(path[1], 73_158.0, delta=1.0)
        self.assertAlmostEqual(ex.meta["acv"], 1000.0, delta=TOL)
        self.assertEqual(ex.meta["market_potential"], 1000.0)
        self.assertTrue(ex.reconciled)

    def test_borrowed_params_flag_present(self):
        ex = adoption_model(
            addressable_units=1000,
            icp_qualification_rate=0.5,
            p=0.03,
            q=0.38,
            periods=10,
            seats_per_customer=5,
            price_per_seat=200.0,
        )
        self.assertIn("borrowed_diffusion_params", ex.flag_codes())

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bass_adoption(0.0, 0.03, 0.38, 5)
        with self.assertRaises(ValueError):
            adoption_model(
                addressable_units=1000, icp_qualification_rate=1.5,
                p=0.03, q=0.38, periods=5,
                seats_per_customer=1, price_per_seat=1.0,
            )


if __name__ == "__main__":
    unittest.main()
