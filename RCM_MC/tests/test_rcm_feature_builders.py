"""Tests for the per-predictor feature-builder functions.

`rcm_mc/ml/collection_rate_predictor.py:build_collection_features`
and `rcm_mc/ml/days_in_ar_predictor.py:build_days_ar_features` are
the canonical adapters from a raw hospital dict to the trained-Ridge
feature vector. Both have:

- multi-step fallback chains (`gross_patient_revenue` →
  `gross_charges` → `beds × 4 × 50_000`)
- per-feature defaults when the hospital dict is missing the key
- derived features (occupancy, case_mix_proxy, log-transforms,
  interaction terms)
- range-clamping (margin to [-0.5, 0.5])

Neither builder had direct test coverage despite being exercised by
every prediction path. The cohort-bucket classifier
`_bed_size_bucket` was likewise untested. This file pins all three.
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from rcm_mc.ml.collection_rate_predictor import (
    COLLECTION_RATE_FEATURES,
    build_collection_features,
)
from rcm_mc.ml.days_in_ar_predictor import (
    DAYS_AR_FEATURES,
    _bed_size_bucket,
    build_days_ar_features,
)


class BuildCollectionFeaturesTests(unittest.TestCase):
    """Contract for ``build_collection_features``."""

    def test_returns_dict_with_full_feature_set(self):
        out = build_collection_features({"beds": 200})
        # Every feature listed in COLLECTION_RATE_FEATURES must be in
        # the output — the trained-Ridge predictor's _features_to_matrix
        # iterates the canonical list, missing keys would crash.
        for f in COLLECTION_RATE_FEATURES:
            self.assertIn(f, out, f"missing canonical feature {f!r}")

    def test_empty_hospital_uses_defaults(self):
        # No keys at all → every default fires; no crash, no NaN.
        out = build_collection_features({})
        self.assertTrue(all(isinstance(v, float) for v in out.values()))
        # Documented defaults from the source:
        self.assertEqual(out["medicare_day_pct"], 0.40)
        self.assertEqual(out["medicaid_day_pct"], 0.15)
        self.assertEqual(out["self_pay_pct"], 0.05)
        self.assertEqual(out["denial_rate_input"], 0.10)
        self.assertEqual(out["days_in_ar_input"], 45.0)
        self.assertEqual(out["hcahps_score"], 0.72)
        self.assertEqual(out["ma_penetration"], 0.40)
        self.assertEqual(out["rural_flag"], 0.0)
        # state_rcm_factor defaults to 0 when state map missing.
        self.assertEqual(out["state_rcm_factor"], 0.0)

    def test_beds_log_is_log_of_beds(self):
        out = build_collection_features({"beds": 100})
        self.assertAlmostEqual(out["beds_log"], math.log(100), places=4)

    def test_beds_zero_uses_default_of_100(self):
        # SUBTLE: the source uses `float(hospital.get("beds") or 100)`
        # — `0 or 100` evaluates to 100 (Python falsy-default trap).
        # So a hospital with beds=0 gets the 100-bed default, NOT a
        # log(1)=0 clamp. The np.log(max(1.0, beds)) clamp only fires
        # for an explicit None default-skip (which `or 100` already
        # prevented). Document the actual behavior so a future
        # refactor doesn't accidentally fix it without checking.
        out = build_collection_features({"beds": 0})
        self.assertAlmostEqual(out["beds_log"], math.log(100),
                                places=4)

    def test_operating_margin_computed_from_rev_minus_opex(self):
        # rev = 100M, opex = 90M → margin = 0.10
        out = build_collection_features({
            "beds": 200,
            "net_patient_revenue": 100_000_000,
            "operating_expenses": 90_000_000,
        })
        self.assertAlmostEqual(out["operating_margin"], 0.10)

    def test_operating_margin_clamped_above(self):
        # Implausibly high margin → clamped at +0.5
        out = build_collection_features({
            "net_patient_revenue": 100_000_000,
            "operating_expenses": -100_000_000,  # opex<0 → 'margin'=2.0
        })
        self.assertEqual(out["operating_margin"], 0.5)

    def test_operating_margin_clamped_below(self):
        # Implausibly negative margin → clamped at -0.5
        out = build_collection_features({
            "net_patient_revenue": 100_000_000,
            "operating_expenses": 200_000_000,  # 'margin' = -1.0
        })
        self.assertEqual(out["operating_margin"], -0.5)

    def test_operating_margin_zero_when_revenue_under_floor(self):
        # rev < 1e5 → guard returns 0 (avoids garbage on shell
        # hospitals with placeholder revenue).
        out = build_collection_features({
            "net_patient_revenue": 50_000,
            "operating_expenses": 200_000,
        })
        self.assertEqual(out["operating_margin"], 0.0)

    def test_occupancy_rate_from_days_over_bda(self):
        out = build_collection_features({
            "beds": 100,
            "total_patient_days": 25_000,
            "bed_days_available": 36_500,  # 100×365
        })
        # 25000/36500 ≈ 0.685
        self.assertAlmostEqual(out["occupancy_rate"], 25_000 / 36_500,
                                places=4)

    def test_occupancy_rate_when_bda_zero_uses_defaulted_chain(self):
        # bed_days_available=0 → falsy → fallback to beds*365.
        # But beds=0 also goes through `or 100` → beds=100 →
        # bda=36_500, days=20_000 → occupancy ≈ 0.548 (NOT the 0.5
        # safety default — that only fires when bda is STILL zero
        # after the fallback chain).
        out = build_collection_features({
            "beds": 0, "bed_days_available": 0,
        })
        # 20000/36500 ≈ 0.5479
        self.assertAlmostEqual(out["occupancy_rate"], 20_000 / 36_500,
                                places=4)

    def test_occupancy_rate_explicit_safety_default(self):
        # The 0.5 safety default fires when bda is STILL 0 after the
        # fallback chain. Easiest way: explicit override.
        # (Can't actually trigger via the public API without monkey-
        # patching, since 'beds or 100' floors beds. Document that
        # the 0.5 default is dead-code on the public path.)
        # Skip the test: covered by the test above showing the actual
        # behavior.
        pass

    def test_case_mix_proxy_is_charges_over_discharges_scaled(self):
        # gross=100M / 1000 discharges = 100,000 per discharge
        # → case_mix_proxy = 100000/100000 = 1.0
        out = build_collection_features({
            "gross_patient_revenue": 100_000_000,
            "discharges": 1000,
        })
        self.assertAlmostEqual(out["case_mix_proxy"], 1.0)

    def test_state_rcm_factor_uses_provided_map(self):
        out = build_collection_features(
            {"state": "ca"},
            state_rcm_factors={"CA": 0.25, "TX": -0.10},
        )
        self.assertEqual(out["state_rcm_factor"], 0.25)

    def test_state_rcm_factor_zero_for_unknown_state(self):
        out = build_collection_features(
            {"state": "ZZ"},
            state_rcm_factors={"CA": 0.25},
        )
        self.assertEqual(out["state_rcm_factor"], 0.0)

    def test_upstream_rcm_signals_passed_through(self):
        # If denial_rate and days_in_ar are present (typical in
        # training data), they become upstream features. In prediction
        # they'd be the OTHER predictors' outputs.
        out = build_collection_features({
            "denial_rate": 0.085,
            "days_in_ar": 38.2,
        })
        self.assertAlmostEqual(out["denial_rate_input"], 0.085)
        self.assertAlmostEqual(out["days_in_ar_input"], 38.2)

    def test_gross_charges_fallback(self):
        # gross_patient_revenue missing → falls back to gross_charges
        out = build_collection_features({
            "beds": 100,
            "gross_charges": 50_000_000,
            "discharges": 500,
        })
        # case_mix_proxy = 50M / 500 / 100K = 1.0
        self.assertAlmostEqual(out["case_mix_proxy"], 1.0)


class BuildDaysArFeaturesTests(unittest.TestCase):
    """Contract for ``build_days_ar_features``."""

    def test_returns_dict_with_full_feature_set(self):
        out = build_days_ar_features({"beds": 200})
        for f in DAYS_AR_FEATURES:
            self.assertIn(f, out, f"missing canonical feature {f!r}")

    def test_empty_hospital_uses_defaults(self):
        out = build_days_ar_features({})
        self.assertTrue(all(isinstance(v, float) for v in out.values()))
        self.assertEqual(out["medicare_day_pct"], 0.40)
        self.assertEqual(out["medicaid_day_pct"], 0.15)
        self.assertEqual(out["self_pay_pct"], 0.05)
        self.assertEqual(out["ma_penetration"], 0.40)
        self.assertEqual(out["rural_flag"], 0.0)
        self.assertEqual(out["state_rcm_factor"], 0.0)

    def test_includes_log_transforms(self):
        out = build_days_ar_features({
            "beds": 100,
            "discharges": 5000,
        })
        self.assertAlmostEqual(out["beds_log"], math.log(100), places=4)
        self.assertAlmostEqual(out["discharges_log"], math.log(5000),
                                places=4)

    def test_log_transforms_use_fallback_defaults(self):
        # Same falsy-default trap as collection_features:
        # beds=0 → fallback to 100; discharges=0 → fallback to
        # beds*4 = 400. So log values reflect the defaults, not 0.
        out = build_days_ar_features({"beds": 0, "discharges": 0})
        self.assertAlmostEqual(out["beds_log"], math.log(100), places=4)
        self.assertAlmostEqual(out["discharges_log"], math.log(400),
                                places=4)

    def test_total_discharges_fallback(self):
        # 'total_discharges' key works in place of 'discharges'.
        out = build_days_ar_features({
            "beds": 100,
            "total_discharges": 4_000,
        })
        self.assertAlmostEqual(out["discharges_log"], math.log(4_000),
                                places=4)

    def test_ma_x_medicaid_interaction(self):
        # The interaction term captures prior-auth burden on dual-
        # eligibles: ma_penetration × medicaid_day_pct.
        out = build_days_ar_features({
            "ma_penetration": 0.5,
            "medicaid_day_pct": 0.30,
        })
        self.assertAlmostEqual(out["ma_x_medicaid"], 0.15, places=6)

    def test_operating_margin_clamped(self):
        out = build_days_ar_features({
            "net_patient_revenue": 100_000_000,
            "operating_expenses": -100_000_000,
        })
        self.assertEqual(out["operating_margin"], 0.5)
        out = build_days_ar_features({
            "net_patient_revenue": 100_000_000,
            "operating_expenses": 200_000_000,
        })
        self.assertEqual(out["operating_margin"], -0.5)

    def test_occupancy_when_bda_zero_uses_defaulted_chain(self):
        # Same as collection_features: beds=0 falls back to 100,
        # bda falls back to beds*365=36500, days falls back to
        # beds*200=20000 → occupancy ≈ 0.548.
        out = build_days_ar_features({
            "beds": 0, "bed_days_available": 0,
        })
        self.assertAlmostEqual(out["occupancy_rate"], 20_000 / 36_500,
                                places=4)

    def test_state_factor_case_insensitive(self):
        # 'ca' uppercased to 'CA' before lookup.
        out = build_days_ar_features(
            {"state": "ca"},
            state_rcm_factors={"CA": 0.15},
        )
        self.assertEqual(out["state_rcm_factor"], 0.15)

    def test_does_not_carry_upstream_rcm_signals(self):
        # Days-AR predictor sees payer mix + volume + geography +
        # case mix — but NOT denial_rate or net_collection_rate
        # (would be circular at training).
        self.assertNotIn("denial_rate_input", DAYS_AR_FEATURES)
        self.assertNotIn("net_collection_rate_input", DAYS_AR_FEATURES)


class BedSizeBucketTests(unittest.TestCase):
    """Contract for the cohort classifier ``_bed_size_bucket``."""

    def test_critical_access_under_50(self):
        for b in (1, 10, 25, 49):
            self.assertEqual(_bed_size_bucket(b), "critical_access")

    def test_small_50_to_149(self):
        for b in (50, 75, 100, 149):
            self.assertEqual(_bed_size_bucket(b), "small")

    def test_mid_150_to_399(self):
        for b in (150, 200, 300, 399):
            self.assertEqual(_bed_size_bucket(b), "mid")

    def test_large_400_plus(self):
        for b in (400, 500, 1000, 5000):
            self.assertEqual(_bed_size_bucket(b), "large")

    def test_zero_or_negative_safe(self):
        self.assertEqual(_bed_size_bucket(0), "critical_access")
        self.assertEqual(_bed_size_bucket(-10), "critical_access")

    def test_none_safe(self):
        # `_bed_size_bucket(None)` → float(None or 0) = 0.0 →
        # critical_access band. Defensive against missing data.
        self.assertEqual(_bed_size_bucket(None), "critical_access")

    def test_boundary_50_is_small_not_critical(self):
        # The bands use strict-less-than: <50 → critical,
        # 50–149 → small. Lock the exact boundary.
        self.assertEqual(_bed_size_bucket(49.999), "critical_access")
        self.assertEqual(_bed_size_bucket(50), "small")

    def test_boundary_150_is_mid_not_small(self):
        self.assertEqual(_bed_size_bucket(149.999), "small")
        self.assertEqual(_bed_size_bucket(150), "mid")

    def test_boundary_400_is_large_not_mid(self):
        self.assertEqual(_bed_size_bucket(399.999), "mid")
        self.assertEqual(_bed_size_bucket(400), "large")

    def test_float_input_handled(self):
        # Real hospital data has float bed counts (avg over period).
        self.assertEqual(_bed_size_bucket(225.5), "mid")


if __name__ == "__main__":
    unittest.main()
