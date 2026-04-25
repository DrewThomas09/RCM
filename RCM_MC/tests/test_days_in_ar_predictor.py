"""Tests for days-in-AR predictor + leave-one-cohort-out CV."""
from __future__ import annotations

import unittest

import numpy as np


def _synth_hospitals(n: int = 200, seed: int = 7):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        beds = float(rng.integers(20, 800))
        mc = float(rng.uniform(0.20, 0.65))
        md = float(rng.uniform(0.05, 0.40))
        sp = float(rng.uniform(0.02, 0.15))
        ma = float(rng.uniform(0.20, 0.70))
        margin = float(rng.normal(0.04, 0.06))
        gross_per_disch = float(rng.uniform(40_000, 110_000))
        rural = 1.0 if beds < 50 else 0.0
        # Latent days-in-AR driven by payer mix + case mix +
        # MA-medicaid interaction + rural penalty + occupancy
        occ = float(rng.uniform(0.40, 0.90))
        true_dso = (
            42.0
            + 12.0 * md          # Medicaid pays slow
            + 25.0 * sp          # Self-pay slowest
            + 8.0 * mc
            - 0.000_05 * (beds * 1000)  # scale
            + 8.0 * ma * md       # prior-auth interaction
            + 6.0 * rural         # rural penalty
            - 12.0 * margin       # better-margin = better RCM
            + 0.000_2 * gross_per_disch  # CMI proxy
            + rng.normal(0, 3.0)
        )
        true_dso = max(20.0, min(110.0, true_dso))
        rows.append({
            "beds": beds,
            "discharges": beds * 4,
            "medicare_day_pct": mc,
            "medicaid_day_pct": md,
            "self_pay_pct": sp,
            "ma_penetration": ma,
            "rural": rural,
            "gross_patient_revenue":
                beds * 4 * gross_per_disch,
            "net_patient_revenue":
                beds * 4 * gross_per_disch * 0.30,
            "operating_expenses":
                beds * 4 * gross_per_disch * 0.30
                * (1 - margin),
            "total_patient_days": beds * 365 * occ,
            "bed_days_available": beds * 365,
            "days_in_ar": true_dso,
        })
    return rows


class TestDaysARPredictor(unittest.TestCase):
    def test_train_predicts_with_skill(self):
        from rcm_mc.ml.days_in_ar_predictor import (
            DAYS_AR_FEATURES,
            train_days_in_ar_predictor,
        )
        rows = _synth_hospitals(n=200)
        p = train_days_in_ar_predictor(rows)
        self.assertEqual(p.feature_names, DAYS_AR_FEATURES)
        self.assertEqual(p.target_metric, "days_in_ar")
        # CV R² should be meaningfully positive on this signal
        self.assertGreater(p.cv_r2_mean, 0.40)
        # MAE should be in days, not insane
        self.assertLess(p.cv_mae, 15.0)
        self.assertEqual(p.sanity_range, (15.0, 120.0))

    def test_predict_returns_realistic_dso(self):
        from rcm_mc.ml.days_in_ar_predictor import (
            train_days_in_ar_predictor,
            predict_days_in_ar,
        )
        rows = _synth_hospitals(n=200)
        p = train_days_in_ar_predictor(rows)
        yhat, (lo, hi), expl = predict_days_in_ar(p, {
            "beds": 250, "medicare_day_pct": 0.45,
            "medicaid_day_pct": 0.20,
        })
        # National avg ~40-55 days
        self.assertGreater(yhat, 25)
        self.assertLess(yhat, 90)
        self.assertLessEqual(lo, yhat)
        self.assertLessEqual(yhat, hi)
        self.assertGreater(len(expl), 0)

    def test_payer_mix_changes_drive_prediction(self):
        """High-Medicaid + high-self-pay should predict longer
        days-in-AR than commercial-heavy mix."""
        from rcm_mc.ml.days_in_ar_predictor import (
            train_days_in_ar_predictor,
            predict_days_in_ar,
        )
        rows = _synth_hospitals(n=400, seed=11)
        p = train_days_in_ar_predictor(rows)
        # Bad mix: high Medicaid + self-pay
        bad_yhat, _, _ = predict_days_in_ar(p, {
            "beds": 200,
            "medicare_day_pct": 0.30,
            "medicaid_day_pct": 0.40,
            "self_pay_pct": 0.15,
        })
        # Good mix: commercial-heavy
        good_yhat, _, _ = predict_days_in_ar(p, {
            "beds": 200,
            "medicare_day_pct": 0.30,
            "medicaid_day_pct": 0.05,
            "self_pay_pct": 0.02,
        })
        self.assertGreater(bad_yhat, good_yhat)


class TestCohortCV(unittest.TestCase):
    def test_leave_one_cohort_out_runs(self):
        from rcm_mc.ml.days_in_ar_predictor import (
            cross_validate_days_in_ar_by_cohort,
        )
        rows = _synth_hospitals(n=300)
        result = cross_validate_days_in_ar_by_cohort(rows)
        # Should have all 4 bed-size buckets present in synth
        self.assertIn("critical_access",
                      result.cohort_labels)
        self.assertIn("small", result.cohort_labels)
        self.assertIn("mid", result.cohort_labels)
        self.assertIn("large", result.cohort_labels)
        # Each cohort should have an R² and MAE
        for label in ("critical_access", "small",
                      "mid", "large"):
            self.assertIn(label, result.per_cohort_r2)
            self.assertIn(label, result.per_cohort_mae)
            self.assertIn(label, result.per_cohort_n)
        # Overall transfer R² should be positive
        self.assertGreater(result.overall_transfer_r2, 0.20)
        # Worst cohort identified
        self.assertIn(result.worst_cohort,
                      result.cohort_labels)

    def test_explicit_cohort_field(self):
        from rcm_mc.ml.days_in_ar_predictor import (
            cross_validate_days_in_ar_by_cohort,
        )
        rows = _synth_hospitals(n=200, seed=9)
        # Tag hospitals with arbitrary region cohort
        for i, r in enumerate(rows):
            r["region"] = ("south" if i % 2 == 0
                           else "northeast")
        result = cross_validate_days_in_ar_by_cohort(
            rows, cohort_field="region")
        self.assertEqual(
            sorted(result.cohort_labels),
            ["northeast", "south"])

    def test_single_cohort_rejected(self):
        from rcm_mc.ml.trained_rcm_predictor import (
            cross_validate_across_cohorts,
        )
        X = np.random.normal(0, 1, size=(50, 3))
        y = np.random.normal(0, 1, size=50)
        cohort = ["only"] * 50
        with self.assertRaises(ValueError):
            cross_validate_across_cohorts(
                X, y, cohort,
                feature_names=["a", "b", "c"])

    def test_tiny_cohort_yields_nan(self):
        """Cohort with <5 training rows when held out should
        gracefully return NaN, not crash."""
        from rcm_mc.ml.trained_rcm_predictor import (
            cross_validate_across_cohorts,
        )
        rng = np.random.default_rng(13)
        X = rng.normal(0, 1, size=(20, 3))
        y = rng.normal(0, 1, size=20)
        # All but 2 rows in cohort A → leaving out A leaves
        # only 2 training rows → NaN for A
        cohort = ["A"] * 18 + ["B"] * 2
        result = cross_validate_across_cohorts(
            X, y, cohort, feature_names=["a", "b", "c"])
        # Both cohorts present, but A's R² is NaN
        self.assertIn("A", result.per_cohort_r2)
        self.assertIn("B", result.per_cohort_r2)
        self.assertTrue(
            np.isnan(result.per_cohort_r2["A"]))


if __name__ == "__main__":
    unittest.main()
