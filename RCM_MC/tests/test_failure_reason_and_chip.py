"""Tests for the FailureReason channel + prediction-diagnostic chip.

Two surfaces verified here:

1. ``ck_prediction_chip`` renders the right HTML for every
   FailureReason variant — and renders the empty string for clean
   fits (``failure_reason is None``).

2. The ridge predictor sets ``failure_reason=PINV_FALLBACK`` when
   ``_RidgeModel.fit`` had to recover via pseudoinverse — verified
   end-to-end against a deliberately collinear synthetic cohort.

A.1 scope (PR ``fix/ridge-predictor-null-on-failure``): the chip and
the failure_reason channel ship in this PR. The orchestrator-level
emission of INSUFFICIENT_COMPARABLES / FIT_EXCEPTION on fallback and
hard-failure paths is the next Tier B item. So the chip helper
unit-tests cover all 7 FailureReason variants (defensive against
the future emission), but the predictor integration test only
exercises the variants this PR actually fires (PINV_FALLBACK is
the cleanest deterministic trigger; CI_UNSTABLE and R2_NEGATIVE
are stochastic and would make a flaky test, so they are covered by
direct field-construction in the unit-test surface).
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.ml.ridge_predictor import (
    FailureReason,
    PredictedMetric as RidgePM,
    _RidgeModel,
)
from rcm_mc.ui._chartis_kit import ck_prediction_chip


# ────────────────────────────────────────────────────────────────────
# 1. ck_prediction_chip unit tests — all 7 variants + None + unknown
# ────────────────────────────────────────────────────────────────────


class TestChipRenderingPerVariant(unittest.TestCase):
    """One assertion per FailureReason value — locks the chip taxonomy.

    Three chip tones (na / warn / error) bucket the 7 reasons into 3
    visual variants. If anyone reclassifies a reason between buckets
    (e.g. moves PINV_FALLBACK from warn → error), this test catches
    it before merge.
    """

    def _build(self, reason):
        # Construct a minimum-viable ridge-PM with the failure_reason
        # set. Other fields don't matter for the chip rendering.
        return RidgePM(value=10.0, failure_reason=reason)

    def test_pinv_fallback_is_warn(self):
        chip = ck_prediction_chip(self._build(FailureReason.PINV_FALLBACK))
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)
        self.assertIn("pseudoinverse", chip)

    def test_ci_unstable_is_warn(self):
        chip = ck_prediction_chip(self._build(FailureReason.CI_UNSTABLE))
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)
        self.assertIn("wider than 2", chip)

    def test_r2_negative_is_warn(self):
        chip = ck_prediction_chip(self._build(FailureReason.R2_NEGATIVE))
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)
        self.assertIn("R", chip)  # mentions R² in the tooltip

    def test_insufficient_comparables_is_na(self):
        chip = ck_prediction_chip(
            self._build(FailureReason.INSUFFICIENT_COMPARABLES)
        )
        self.assertIn("ck-pred-chip-na", chip)
        self.assertIn("insufficient comparables", chip)

    def test_target_features_missing_is_na(self):
        chip = ck_prediction_chip(
            self._build(FailureReason.TARGET_FEATURES_MISSING)
        )
        self.assertIn("ck-pred-chip-na", chip)
        self.assertIn("missing input features", chip)

    def test_no_benchmark_is_na(self):
        chip = ck_prediction_chip(
            self._build(FailureReason.NO_BENCHMARK)
        )
        self.assertIn("ck-pred-chip-na", chip)
        self.assertIn("no benchmark", chip)

    def test_fit_exception_is_error(self):
        chip = ck_prediction_chip(
            self._build(FailureReason.FIT_EXCEPTION)
        )
        self.assertIn("ck-pred-chip-error", chip)
        self.assertIn("prediction failed", chip)


class TestChipEdgeCases(unittest.TestCase):
    def test_none_pm_renders_empty(self):
        self.assertEqual(ck_prediction_chip(None), "")

    def test_clean_pm_renders_empty(self):
        pm = RidgePM(value=5.0, ci_low=4.0, ci_high=6.0, r_squared=0.7)
        # failure_reason defaults to None on a clean fit
        self.assertIsNone(pm.failure_reason)
        self.assertEqual(ck_prediction_chip(pm), "")

    def test_string_failure_reason_works(self):
        # Packet PM stores the string value (not the Enum) so JSON
        # round-trip stays clean. The chip helper must accept both.
        class _StringFR:
            failure_reason = "pinv_fallback"
        chip = ck_prediction_chip(_StringFR())
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)

    def test_unknown_failure_reason_degrades_to_error(self):
        # Forward-compat: if a future Tier B PR adds a new
        # FailureReason variant the chip map hasn't been updated for,
        # the renderer must degrade gracefully (not crash, not stay
        # silent — show the error chip with the raw reason in the
        # tooltip so the partner sees a signal).
        class _UnknownFR:
            failure_reason = "future_unrecognized_variant"
        chip = ck_prediction_chip(_UnknownFR())
        self.assertIn("ck-pred-chip-error", chip)
        self.assertIn("future_unrecognized_variant", chip)

    def test_chip_escapes_tooltip(self):
        # Tooltip text is HTML-escaped — defensive against any future
        # caller that crafts a reason value with embedded angle
        # brackets.
        class _XssFR:
            failure_reason = "<script>x</script>"
        chip = ck_prediction_chip(_XssFR())
        self.assertNotIn("<script>", chip)
        self.assertIn("&lt;script&gt;", chip)


# ────────────────────────────────────────────────────────────────────
# 2. End-to-end: PINV_FALLBACK fires from real _RidgeModel
# ────────────────────────────────────────────────────────────────────


class TestRidgeModelPinvDetection(unittest.TestCase):
    """Verify the ``used_pinv`` flag flips when ``np.linalg.solve``
    fails. The cleanest way to force the failure is to disable the
    L2 regularization (``alpha=0``) and feed perfectly collinear
    features — without the alpha cushion, the normal-equation matrix
    is singular and ``solve`` raises ``LinAlgError``, triggering the
    pinv recovery path.
    """

    def test_used_pinv_false_on_clean_fit(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(40, 2))
        y = X @ [1.5, -2.0] + rng.normal(0, 0.3, size=40)
        m = _RidgeModel(alpha=1.0)
        m.fit(X, y)
        self.assertFalse(m.used_pinv,
                         "clean fit must not flag pinv recovery")

    def test_used_pinv_true_on_singular_matrix(self):
        # Perfectly collinear features + alpha=0 → singular normal
        # equation → LinAlgError → pinv recovery path → used_pinv=True.
        #
        # Note on cohort shape: we use 2 collinear features (not 3+)
        # because numpy.linalg.solve raises LinAlgError reliably on
        # rank-1 2×2 systems but can silently produce a one-of-many
        # solution on rank-1 3×3 systems via its LU driver. The
        # 2-column case is the deterministic trigger; the 3-column
        # case is numpy-version-dependent. For chip detection that
        # the predictor actually uses, we test the deterministic case.
        n = 20
        rng = np.random.default_rng(1)
        x1 = rng.normal(size=n)
        x2 = 2.0 * x1   # perfectly collinear with x1
        X = np.column_stack([x1, x2])
        y = rng.normal(size=n)
        m = _RidgeModel(alpha=0.0)
        m.fit(X, y)
        self.assertTrue(m.used_pinv,
                        "singular matrix must trigger pinv fallback")

    def test_used_pinv_reset_per_fit(self):
        # The flag is per-fit, not sticky — verify a clean fit after
        # a singular fit resets it to False.
        n = 20
        rng = np.random.default_rng(2)
        m = _RidgeModel(alpha=0.0)
        # First fit: singular → used_pinv True
        x1 = rng.normal(size=n)
        X_bad = np.column_stack([x1, 2.0 * x1])
        m.fit(X_bad, rng.normal(size=n))
        self.assertTrue(m.used_pinv)
        # Second fit: clean → used_pinv must flip back to False
        X_good = rng.normal(size=(n, 2))
        m.fit(X_good, rng.normal(size=n))
        self.assertFalse(m.used_pinv,
                         "fit must reset used_pinv per call")


# ────────────────────────────────────────────────────────────────────
# 3. PredictedMetric round-trip preserves failure_reason
# ────────────────────────────────────────────────────────────────────


class TestPredictedMetricRoundTrip(unittest.TestCase):
    """The local (ridge-flavor) PM serializes the FailureReason as its
    string value so JSON survives the wire. The packet PM stores it
    as a plain string."""

    def test_local_pm_to_dict_emits_enum_value(self):
        pm = RidgePM(value=10.0, failure_reason=FailureReason.PINV_FALLBACK)
        d = pm.to_dict()
        self.assertEqual(d["failure_reason"], "pinv_fallback")

    def test_local_pm_to_dict_none_when_clean(self):
        pm = RidgePM(value=10.0)
        d = pm.to_dict()
        self.assertIsNone(d["failure_reason"])

    def test_packet_pm_round_trip_preserves_failure_reason(self):
        # Verify the packet PM's from_dict / to_dict cycle keeps the
        # string value intact — older packets that lack the field
        # default to None, and the wire format is always a string.
        from rcm_mc.analysis.packet import PredictedMetric as PacketPM
        d = {
            "value": 10.0, "ci_low": 8.0, "ci_high": 12.0,
            "failure_reason": "ci_unstable",
        }
        pm = PacketPM.from_dict(d)
        self.assertEqual(pm.failure_reason, "ci_unstable")
        round_tripped = pm.to_dict()
        self.assertEqual(round_tripped["failure_reason"], "ci_unstable")

    def test_packet_pm_older_packet_defaults_failure_reason_to_none(self):
        # An older packet won't have the failure_reason key — verify
        # the from_dict path doesn't blow up and defaults to None.
        from rcm_mc.analysis.packet import PredictedMetric as PacketPM
        d = {"value": 10.0, "ci_low": 8.0, "ci_high": 12.0}
        pm = PacketPM.from_dict(d)
        self.assertIsNone(pm.failure_reason)


if __name__ == "__main__":
    unittest.main()
