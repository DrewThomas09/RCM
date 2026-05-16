"""A.10 PR A — chip propagation foundation tests.

Covers the architectural seam that A.10 fixes: ``failure_reason``
on a ``PredictedMetric`` was being silently dropped when
``_merge_rcm_profile`` converted to ``ProfileMetric``. Every
downstream UI consumer reads ``ProfileMetric``, so without the
propagation the diagnostic signal A.1 added never reached any
partner-facing surface.

This PR ships the foundation (data carrier + conversion + aggregator
helper). PR B rolls out the chip render across the 7+ Type A
surfaces. These tests pin the foundation only — surface integration
tests land with PR B.

Three concern blocks:

1. ``ProfileMetric.failure_reason`` round-trips through ``to_dict``
   / ``from_dict`` and defaults to ``None`` on packets predating
   A.10 (back-compat).

2. ``_merge_rcm_profile`` propagates ``pm.failure_reason`` from
   the PREDICTED branch into the resulting ``ProfileMetric``. The
   OBSERVED and AUTO_POPULATED branches have no PM source so they
   keep ``failure_reason=None`` (verified — propagation is scoped
   precisely to the one branch that has a predictor input).

3. ``ck_aggregate`` composes the worst-tier failure across multiple
   inputs, returns an ``AggregatedFailure`` shaped to feed back into
   ``ck_prediction_chip`` directly, and surfaces per-source
   contribution detail for tooltip enhancement.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.packet import (
    ComparableHospital,
    MetricSource,
    ObservedMetric,
    PredictedMetric,
    ProfileMetric,
)
from rcm_mc.analysis.packet_builder import _merge_rcm_profile
from rcm_mc.ml.ridge_predictor import FailureReason
from rcm_mc.ui._chartis_kit import (
    AggregatedFailure,
    ck_aggregate,
    ck_prediction_chip,
)


# ────────────────────────────────────────────────────────────────────
# 1. ProfileMetric.failure_reason round-trip + back-compat
# ────────────────────────────────────────────────────────────────────


class TestProfileMetricFailureReasonField(unittest.TestCase):
    def test_default_is_none(self):
        pm = ProfileMetric(value=10.0)
        self.assertIsNone(pm.failure_reason)

    def test_to_dict_emits_field(self):
        pm = ProfileMetric(value=10.0, failure_reason="ci_unstable")
        d = pm.to_dict()
        self.assertIn("failure_reason", d)
        self.assertEqual(d["failure_reason"], "ci_unstable")

    def test_to_dict_none_serializes_none(self):
        pm = ProfileMetric(value=10.0)
        d = pm.to_dict()
        self.assertIn("failure_reason", d)
        self.assertIsNone(d["failure_reason"])

    def test_from_dict_preserves_failure_reason(self):
        d = {"value": 10.0, "source": "PREDICTED", "failure_reason": "pinv_fallback"}
        pm = ProfileMetric.from_dict(d)
        self.assertEqual(pm.failure_reason, "pinv_fallback")

    def test_from_dict_back_compat_pre_a10_packet(self):
        # Packets serialized before A.10 don't have the key. The
        # defensive read must default to None, not raise KeyError.
        d = {"value": 10.0, "source": "OBSERVED"}
        pm = ProfileMetric.from_dict(d)
        self.assertIsNone(pm.failure_reason)

    def test_round_trip_preserves_failure_reason(self):
        original = ProfileMetric(
            value=12.5, source=MetricSource.PREDICTED,
            ci_low=10.0, ci_high=15.0,
            failure_reason="r2_negative",
        )
        round_tripped = ProfileMetric.from_dict(original.to_dict())
        self.assertEqual(round_tripped.failure_reason, "r2_negative")


# ────────────────────────────────────────────────────────────────────
# 2. _merge_rcm_profile propagates failure_reason from predicted PM
# ────────────────────────────────────────────────────────────────────


class TestMergeRcmProfilePropagation(unittest.TestCase):
    """The architectural seam under test. The PREDICTED branch must
    carry failure_reason forward into ProfileMetric; the OBSERVED
    and AUTO_POPULATED branches have no PM source and stay None."""

    def test_predicted_branch_propagates_failure_reason(self):
        # A predicted PM with an unstable-fit diagnostic must arrive
        # in the ProfileMetric carrying the same failure_reason
        # string. This is the one-line fix that makes the whole
        # propagation chain work.
        pred_pm = PredictedMetric(
            value=10.0, ci_low=5.0, ci_high=15.0,
            method="ridge_regression", r_squared=0.6,
            n_comparables_used=20,
            failure_reason="ci_unstable",
        )
        merged = _merge_rcm_profile(
            observed={}, predicted={"denial_rate": pred_pm}, peers=[],
        )
        self.assertIn("denial_rate", merged)
        self.assertEqual(merged["denial_rate"].failure_reason, "ci_unstable")
        self.assertEqual(merged["denial_rate"].source, MetricSource.PREDICTED)

    def test_predicted_clean_pm_yields_none_failure_reason(self):
        # When the prediction is clean (no failure_reason set), the
        # propagation must not invent one.
        pred_pm = PredictedMetric(
            value=10.0, ci_low=8.0, ci_high=12.0,
            method="ridge_regression", r_squared=0.8,
            n_comparables_used=30,
        )
        merged = _merge_rcm_profile(
            observed={}, predicted={"denial_rate": pred_pm}, peers=[],
        )
        self.assertIsNone(merged["denial_rate"].failure_reason)

    def test_observed_branch_keeps_failure_reason_none(self):
        # OBSERVED metrics have no upstream predictor, so failure_reason
        # must stay None — propagation is scoped exactly to PREDICTED.
        obs = {"denial_rate": ObservedMetric(value=11.0, source="USER_INPUT")}
        merged = _merge_rcm_profile(
            observed=obs, predicted={}, peers=[],
        )
        self.assertIsNone(merged["denial_rate"].failure_reason)
        self.assertEqual(merged["denial_rate"].source, MetricSource.OBSERVED)

    def test_auto_populated_branch_keeps_failure_reason_none(self):
        # AUTO_POPULATED values come from public data sources (HCRIS
        # etc.), not a predictor — same logic as OBSERVED.
        merged = _merge_rcm_profile(
            observed={}, predicted={},
            peers=[],
            auto_populated={"denial_rate": 8.5},
        )
        self.assertIsNone(merged["denial_rate"].failure_reason)
        self.assertEqual(merged["denial_rate"].source, MetricSource.AUTO_POPULATED)

    def test_observed_wins_over_predicted_when_both_present(self):
        # Existing precedence rule (observed beats predicted) must be
        # preserved — the failure_reason from the predicted PM is
        # NOT propagated when an observed value overrode it.
        obs = {"denial_rate": ObservedMetric(value=11.0, source="USER_INPUT")}
        pred_pm = PredictedMetric(
            value=10.0, ci_low=5.0, ci_high=15.0,
            failure_reason="pinv_fallback",
        )
        merged = _merge_rcm_profile(
            observed=obs, predicted={"denial_rate": pred_pm}, peers=[],
        )
        self.assertEqual(merged["denial_rate"].source, MetricSource.OBSERVED)
        self.assertIsNone(merged["denial_rate"].failure_reason)


# ────────────────────────────────────────────────────────────────────
# 3. AggregatedFailure + ck_aggregate severity composition
# ────────────────────────────────────────────────────────────────────


class TestAggregatedFailureDefaults(unittest.TestCase):
    def test_defaults_to_clean_state(self):
        af = AggregatedFailure()
        self.assertIsNone(af.failure_reason)
        self.assertEqual(af.tier, 0)
        self.assertEqual(af.contributing_sources, [])

    def test_chip_helper_renders_nothing_on_clean_aggregate(self):
        af = AggregatedFailure()
        self.assertEqual(ck_prediction_chip(af), "")


class TestAggregatorSeverity(unittest.TestCase):
    """Severity ordering is the load-bearing design call in A.10.
    These tests pin the tier mapping so a future change can't
    silently demote a chip variant."""

    def _pm(self, reason):
        # packet.PredictedMetric requires ci_low/ci_high as positional.
        return PredictedMetric(
            value=10.0, ci_low=8.0, ci_high=12.0, failure_reason=reason,
        )

    def test_tier3_wins_over_tier2(self):
        # FIT_EXCEPTION (3) beats CI_UNSTABLE (2)
        result = ck_aggregate(self._pm("ci_unstable"), self._pm("fit_exception"))
        self.assertEqual(result.tier, 3)
        self.assertEqual(result.failure_reason, "fit_exception")

    def test_tier2_wins_over_tier1(self):
        # PINV_FALLBACK (2) beats INSUFFICIENT_COMPARABLES (1)
        result = ck_aggregate(
            self._pm("insufficient_comparables"),
            self._pm("pinv_fallback"),
        )
        self.assertEqual(result.tier, 2)
        self.assertEqual(result.failure_reason, "pinv_fallback")

    def test_tier1_wins_over_clean(self):
        result = ck_aggregate(self._pm("no_benchmark"), self._pm(None))
        self.assertEqual(result.tier, 1)
        self.assertEqual(result.failure_reason, "no_benchmark")

    def test_all_clean_yields_tier_zero(self):
        result = ck_aggregate(self._pm(None), self._pm(None))
        self.assertEqual(result.tier, 0)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(result.contributing_sources, [])

    def test_none_sources_skipped(self):
        # None inputs (no PM provided) contribute nothing — common
        # case when a KPI's input is conditionally populated.
        result = ck_aggregate(None, self._pm("ci_unstable"), None)
        self.assertEqual(result.tier, 2)
        self.assertEqual(result.failure_reason, "ci_unstable")
        self.assertEqual(len(result.contributing_sources), 1)

    def test_all_none_sources(self):
        result = ck_aggregate(None, None, None)
        self.assertEqual(result.tier, 0)
        self.assertIsNone(result.failure_reason)

    def test_unknown_reason_defensively_treated_as_tier3(self):
        # A typo or future enum variant the tier map doesn't know
        # about must default to tier 3 (loudest) — don't silently
        # swallow as tier 0.
        result = ck_aggregate(self._pm("future_unrecognized_variant"))
        self.assertEqual(result.tier, 3)
        self.assertEqual(result.failure_reason, "future_unrecognized_variant")


class TestAggregatorMixedTypes(unittest.TestCase):
    """The aggregator must accept inputs from any PM-shaped source:
    ridge-flavor PM (Enum-valued), packet PM (string-valued),
    ProfileMetric (string-valued), or AggregatedFailure (nested)."""

    def test_ridge_pm_enum_failure_reason(self):
        from rcm_mc.ml.ridge_predictor import (
            PredictedMetric as RidgePM,
        )
        rpm = RidgePM(value=10.0, failure_reason=FailureReason.PINV_FALLBACK)
        result = ck_aggregate(rpm)
        self.assertEqual(result.failure_reason, "pinv_fallback")
        self.assertEqual(result.tier, 2)

    def test_packet_pm_string_failure_reason(self):
        ppm = PredictedMetric(
            value=10.0, ci_low=8.0, ci_high=12.0, failure_reason="ci_unstable",
        )
        result = ck_aggregate(ppm)
        self.assertEqual(result.failure_reason, "ci_unstable")

    def test_profile_metric_string_failure_reason(self):
        # ProfileMetric just got the field in A.10 PR A
        prof = ProfileMetric(value=10.0, failure_reason="r2_negative")
        result = ck_aggregate(prof)
        self.assertEqual(result.failure_reason, "r2_negative")

    def test_mixed_pm_types_in_one_aggregate(self):
        from rcm_mc.ml.ridge_predictor import (
            PredictedMetric as RidgePM,
        )
        rpm = RidgePM(value=1.0, failure_reason=FailureReason.CI_UNSTABLE)
        ppm = PredictedMetric(
            value=2.0, ci_low=1.5, ci_high=2.5, failure_reason="fit_exception",
        )
        prof = ProfileMetric(value=3.0)  # clean
        result = ck_aggregate(rpm, ppm, prof)
        self.assertEqual(result.failure_reason, "fit_exception")
        self.assertEqual(result.tier, 3)


class TestAggregatorContributingSources(unittest.TestCase):
    """Tooltip enhancement depends on the contributing_sources list
    being correctly populated with per-source labels."""

    def _pm(self, reason):
        # packet.PredictedMetric requires ci_low/ci_high as positional.
        return PredictedMetric(
            value=10.0, ci_low=8.0, ci_high=12.0, failure_reason=reason,
        )

    def test_labels_appear_in_contributing_sources(self):
        result = ck_aggregate(
            self._pm("ci_unstable"),
            self._pm("pinv_fallback"),
            labels=["denial_rate", "payer_mix"],
        )
        self.assertIn("denial_rate (ci_unstable)", result.contributing_sources)
        self.assertIn("payer_mix (pinv_fallback)", result.contributing_sources)

    def test_no_labels_falls_back_to_indexed_names(self):
        result = ck_aggregate(self._pm("ci_unstable"), self._pm("pinv_fallback"))
        self.assertIn("source[0] (ci_unstable)", result.contributing_sources)
        self.assertIn("source[1] (pinv_fallback)", result.contributing_sources)

    def test_clean_sources_dont_appear_in_contributing(self):
        # Only non-clean inputs contribute. Clean and None inputs
        # are skipped from the list.
        result = ck_aggregate(
            self._pm(None),
            self._pm("ci_unstable"),
            None,
            labels=["clean_metric", "unstable_metric", "missing_metric"],
        )
        self.assertEqual(len(result.contributing_sources), 1)
        self.assertIn("unstable_metric (ci_unstable)", result.contributing_sources)

    def test_chip_tooltip_enhanced_with_contributing_sources(self):
        # When the aggregate has contributing sources, the chip's
        # tooltip must include them — this is the partner-facing
        # diagnostic improvement the AggregatedFailure shape exists for.
        result = ck_aggregate(
            self._pm("ci_unstable"),
            self._pm("pinv_fallback"),
            labels=["denial_rate", "payer_mix"],
        )
        chip = ck_prediction_chip(result)
        # The label string (chip face) is the tier-2 amber chip
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertIn("fit unstable", chip)
        # The tooltip carries the source detail
        self.assertIn("denial_rate (ci_unstable)", chip)
        self.assertIn("payer_mix (pinv_fallback)", chip)

    def test_chip_tooltip_unchanged_for_single_pm_input(self):
        # Backward-compat: single-PM call (the A.1 path) renders the
        # default tooltip with no Sources suffix.
        single = self._pm("ci_unstable")
        chip = ck_prediction_chip(single)
        self.assertIn("ck-pred-chip-warn", chip)
        self.assertNotIn("Sources:", chip)


if __name__ == "__main__":
    unittest.main()
