"""Expected-vs-actual layer (measure model + profile benchmark).

Locks the honesty contract: in-sample fit with R²/n exposed, composite
sub-ratings excluded from predictors, no imputation, descriptive-not-causal
and not-a-forecast caveats, and sensible real coefficients.
"""
from __future__ import annotations

import itertools
import unittest

from rcm_mc.data.cross_sector import SECTOR_BY_ID, SECTORS
from rcm_mc.data.sector_expected_value import (
    _MIN_FIT_N, _fit_measure_model, expected_vs_actual,
)

_SECTORS = tuple(s.id for s in SECTORS)


class MeasureModelTests(unittest.TestCase):
    def test_every_sector_fits_a_model(self):
        for sid in _SECTORS:
            fit = _fit_measure_model(sid)
            with self.subTest(sid=sid):
                self.assertIsNotNone(fit)
                model, _ = fit
                self.assertGreaterEqual(model.n_fit, _MIN_FIT_N)
                self.assertGreaterEqual(model.r2, 0.0)
                self.assertLessEqual(model.r2, 1.0)
                self.assertTrue(model.predictors)

    def test_composite_target_excludes_subrating_predictors(self):
        # SNF overall_rating is a composite; its sub-ratings must NOT be
        # predictors (that would be mechanically tautological).
        model, _ = _fit_measure_model("nursing-homes")
        self.assertTrue(model.composite_target)
        keys = {c.key for c in model.predictors}
        for sub in ("health_inspection_rating", "staffing_rating", "qm_rating"):
            self.assertNotIn(sub, keys)
        # R² stays modest precisely because it isn't tautological.
        self.assertLess(model.r2, 0.95)

    def test_coefficients_have_sensible_signs(self):
        # SNF: more nurse turnover and more fine dollars should not push the
        # rating UP; staffing hours should not push it DOWN.
        model, _ = _fit_measure_model("nursing-homes")
        coef = {c.key: c.std_coef for c in model.predictors}
        self.assertLess(coef["total_nurse_turnover_pct"], 0)
        self.assertLess(coef["total_fines_usd"], 0)
        self.assertGreater(coef["total_nurse_hprd"], 0)

    def test_predictors_sorted_by_abs_strength(self):
        model, _ = _fit_measure_model("dialysis")
        mags = [abs(c.std_coef) for c in model.predictors]
        self.assertEqual(mags, sorted(mags, reverse=True))


class ExpectedVsActualTests(unittest.TestCase):
    def _first_scored(self, sid):
        spec = SECTOR_BY_ID[sid]
        for ccn in itertools.islice(spec.providers_loader(), 500):
            e = expected_vs_actual(sid, ccn)
            if e and e.model_residual.expected is not None \
                    and e.profile.expected is not None:
                return e
        return None

    def test_residual_is_actual_minus_expected(self):
        for sid in _SECTORS:
            e = self._first_scored(sid)
            with self.subTest(sid=sid):
                self.assertIsNotNone(e, f"no scored provider for {sid}")
                mr = e.model_residual
                self.assertAlmostEqual(mr.residual, mr.actual - mr.expected, places=2)
                pb = e.profile
                self.assertAlmostEqual(pb.residual, pb.actual - pb.expected, places=2)

    def test_no_imputation_when_predictor_missing(self):
        # A provider missing a model predictor must get expected=None, not a
        # guessed value. Construct by finding one with a None in the headline
        # or predictors path: any provider whose model_residual is n/a.
        spec = SECTOR_BY_ID["inpatient-rehab"]
        found_na = False
        for ccn in spec.providers_loader():
            e = expected_vs_actual("inpatient-rehab", ccn)
            if e.model_residual.flag == "n/a":
                self.assertIsNone(e.model_residual.expected)
                found_na = True
                break
        self.assertTrue(found_na)

    def test_caveats_are_descriptive_not_forecast(self):
        e = self._first_scored("nursing-homes")
        blob = " ".join(e.caveats).lower()
        self.assertIn("not causation", blob)
        self.assertIn("not a forecast", blob)
        self.assertIn("not a verdict", blob)

    def test_unknown_sector_and_ccn(self):
        self.assertIsNone(expected_vs_actual("not-a-sector", "x"))
        self.assertIsNone(expected_vs_actual("nursing-homes", "ZZZZZZ"))

    def test_profile_cohort_label_has_state_and_ownership(self):
        e = self._first_scored("dialysis")
        self.assertTrue(e.profile.cohort_label)
        self.assertIn(e.state, e.profile.cohort_label)


if __name__ == "__main__":
    unittest.main()
