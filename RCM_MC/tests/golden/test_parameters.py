"""Golden test for NEW-18 Defensible parameter library.

Hand-checked invariants:

- Every parameter carries a non-empty source, vintage, and a valid
  defensibility flag.
- Named values match their cited sources: statin PDC>=80% = 0.610, the V28
  constrained diabetes-with-PVD coefficient = 0.166, Bass p/q = 0.03/0.38,
  the hospital inpatient commercial multiplier = 2.54.
- The conversion factor mirrors the fee-schedule backbone (single source of
  truth, no drift).
- Distribution sampling honors its support: a beta-on-[0,1] stays in [0,1];
  a PERT stays within [low, high]; the central value sits inside the sampled
  range.
- The exhibit reconciles its per-flag counts to the registry total and flags
  every illustrative parameter.
"""
import unittest

import numpy as np

from rcm_mc.cdd import parameters as P
from rcm_mc.data_public.fee_schedule_2026 import FEE_SCHEDULE_BACKBONE_2026

TOL = 1e-9


class TestParameters(unittest.TestCase):
    def test_named_values_match_sources(self):
        self.assertAlmostEqual(P.value("statin_pdc80"), 0.610, delta=TOL)
        self.assertAlmostEqual(
            P.value("v28_diabetes_pvd_constrained_coef"), 0.166, delta=TOL
        )
        self.assertAlmostEqual(P.value("bass_p"), 0.03, delta=TOL)
        self.assertAlmostEqual(P.value("bass_q"), 0.38, delta=TOL)
        self.assertAlmostEqual(
            P.value("comm_mult_hospital_inpatient"), 2.54, delta=TOL
        )
        self.assertAlmostEqual(P.value("mlr_floor"), 0.85, delta=TOL)

    def test_conversion_factor_is_single_source_of_truth(self):
        # No drift: the library imports the CF rather than re-typing it.
        self.assertAlmostEqual(
            P.value("pfs_conversion_factor"),
            float(FEE_SCHEDULE_BACKBONE_2026["pfs_cf_nonqp"].value),
            delta=TOL,
        )

    def test_every_parameter_is_sourced_and_flagged(self):
        for p in P.all_parameters():
            self.assertTrue(p.source, f"{p.key} missing source")
            self.assertTrue(p.vintage, f"{p.key} missing vintage")
            self.assertIn(p.defensibility, (P.WELL_ESTABLISHED, P.ILLUSTRATIVE))
            self.assertTrue(p.unit, f"{p.key} missing unit")

    def test_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            P.get_parameter("does_not_exist")

    def test_beta_sampling_stays_in_unit_interval(self):
        rng = np.random.default_rng(7)
        draws = P.get_parameter("statin_pdc80").sample(rng, 5000)
        self.assertEqual(draws.shape, (5000,))
        self.assertGreaterEqual(draws.min(), 0.0)
        self.assertLessEqual(draws.max(), 1.0)
        # The central value sits inside the sampled spread.
        self.assertLess(draws.min(), 0.610)
        self.assertGreater(draws.max(), 0.610)

    def test_pert_sampling_respects_bounds(self):
        rng = np.random.default_rng(11)
        spec = P.DistSpec("pert", low=1.62, mode=2.54, high=3.46)
        draws = spec.sample(rng, 5000)
        self.assertGreaterEqual(draws.min(), 1.62 - TOL)
        self.assertLessEqual(draws.max(), 3.46 + TOL)
        # PERT weights the mode 4x: the sample mean lands near the mode.
        self.assertAlmostEqual(float(draws.mean()), 2.54, delta=0.1)

    def test_deterministic_parameter_repeats_value(self):
        rng = np.random.default_rng(1)
        draws = P.get_parameter("pfs_conversion_factor").sample(rng, 100)
        self.assertTrue(np.allclose(draws, P.value("pfs_conversion_factor")))

    def test_defensibility_summary_sums_to_total(self):
        s = P.defensibility_summary()
        self.assertEqual(
            s[P.WELL_ESTABLISHED] + s[P.ILLUSTRATIVE], len(P.all_parameters())
        )

    def test_illustrative_params_are_flagged_in_exhibit(self):
        ex = P.build_exhibit()
        self.assertTrue(ex.reconciled, "per-flag counts must tie to the total")
        # The stale FY2013 utilization anchor and the borrowed Bass p/q must flag.
        codes = ex.flag_codes()
        self.assertIn("illustrative_tka_discharges_per_1000_medicare", codes)
        self.assertIn("illustrative_bass_p", codes)

    def test_partner_view_hides_full_register(self):
        ex = P.build_exhibit()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        internal = {s["name"] for s in ex.render(internal_mode=True)["series"]}
        self.assertNotIn("Parameter register", partner)
        self.assertIn("Parameter register", internal)


if __name__ == "__main__":
    unittest.main()
