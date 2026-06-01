"""Tests for the pure helpers + dataclasses in ``rcm_mc/analysis/playbook.py``.

``build_playbook`` orchestrates against a SQLite ``store`` (DB-bound
integration), but the pure helpers underneath drive the editorial
contract that lands in the partner brief:

  * ``DealOutcome`` / ``PlaybookEntry`` dataclasses (JSON round-trip)
  * ``_classify_pattern`` — ~10-archetype hospital classification
    that decides which historical deals match the target
  * ``_achievement_pct`` / ``_is_success`` — the "did the lever
    deliver?" math underneath every success-rate cell
  * ``_infer_failure_factors`` — heuristic root-cause tagging on the
    misses

These ladder into 'hospitals that look like yours improved denial
rates 70% of the time, typically using X and Y' partner language.
Module had no direct unit tests for these helpers — locking them
before any tweak silently changes the brief.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.playbook import (
    DealOutcome,
    PlaybookEntry,
    SUCCESS_THRESHOLD,
    _achievement_pct,
    _classify_pattern,
    _infer_failure_factors,
    _is_success,
)


# ---------------------------------------------------------------------------
# DealOutcome (dataclass + JSON round-trip)
# ---------------------------------------------------------------------------


class DealOutcomeTests(unittest.TestCase):

    def test_to_dict_and_from_dict_roundtrip(self):
        d = DealOutcome(
            deal_id="D-1",
            initial_value=10.0, target_value=20.0, achieved_value=18.0,
            months_elapsed=14, success=True,
            initiatives_used=["robotic_appeals", "payer_audit"],
        )
        out = d.to_dict()
        # to_dict returns asdict-style mapping
        self.assertEqual(out["deal_id"], "D-1")
        self.assertEqual(out["initial_value"], 10.0)
        self.assertEqual(out["months_elapsed"], 14)
        self.assertEqual(out["success"], True)
        self.assertEqual(out["initiatives_used"],
                         ["robotic_appeals", "payer_audit"])
        # Round trip back via from_dict
        d2 = DealOutcome.from_dict(out)
        self.assertEqual(d.deal_id, d2.deal_id)
        self.assertEqual(d.initial_value, d2.initial_value)
        self.assertEqual(d.target_value, d2.target_value)
        self.assertEqual(d.achieved_value, d2.achieved_value)
        self.assertEqual(d.months_elapsed, d2.months_elapsed)
        self.assertEqual(d.success, d2.success)
        self.assertEqual(d.initiatives_used, d2.initiatives_used)

    def test_from_dict_handles_missing_fields(self):
        # Partial dict → from_dict fills defaults via 'or 0' guards.
        d = DealOutcome.from_dict({"deal_id": "D-2"})
        self.assertEqual(d.deal_id, "D-2")
        self.assertEqual(d.initial_value, 0.0)
        self.assertEqual(d.target_value, 0.0)
        self.assertEqual(d.achieved_value, 0.0)
        self.assertEqual(d.months_elapsed, 0)
        self.assertFalse(d.success)

    def test_from_dict_coerces_types(self):
        # String numbers → coerced to float/int
        d = DealOutcome.from_dict({
            "deal_id": "D-3",
            "initial_value": "10.5",
            "target_value": "20.5",
            "achieved_value": "15.0",
            "months_elapsed": "12",
        })
        self.assertEqual(d.initial_value, 10.5)
        self.assertEqual(d.months_elapsed, 12)

    def test_default_initiatives_isolated(self):
        # Dataclass mutable-default trap — independent instances.
        a = DealOutcome("A", 0, 0, 0, 0, False)
        b = DealOutcome("B", 0, 0, 0, 0, False)
        a.initiatives_used.append("x")
        self.assertEqual(b.initiatives_used, [])


# ---------------------------------------------------------------------------
# PlaybookEntry (dataclass + to_dict)
# ---------------------------------------------------------------------------


class PlaybookEntryTests(unittest.TestCase):

    def test_to_dict_serializes_nested_outcomes(self):
        outcomes = [
            DealOutcome("A", 0, 10, 9, 12, True),
            DealOutcome("B", 0, 10, 5, 12, False),
        ]
        entry = PlaybookEntry(
            lever="denial_rate",
            pattern="commercial_heavy_denial",
            matching_deals=outcomes,
            success_rate=0.5,
            avg_achievement_pct=0.7,
            common_initiatives=["robotic_appeals"],
            failure_factors=["insufficient_ramp_time"],
            recommendation="Recommend X, Y.",
        )
        out = entry.to_dict()
        self.assertEqual(out["lever"], "denial_rate")
        self.assertEqual(out["pattern"], "commercial_heavy_denial")
        # matching_deals is serialized via to_dict() on each child.
        self.assertEqual(len(out["matching_deals"]), 2)
        self.assertEqual(out["matching_deals"][0]["deal_id"], "A")
        self.assertEqual(out["success_rate"], 0.5)
        self.assertEqual(out["common_initiatives"], ["robotic_appeals"])

    def test_defaults(self):
        # Required fields only — defaults must be safe.
        entry = PlaybookEntry(lever="X", pattern="general")
        self.assertEqual(entry.matching_deals, [])
        self.assertEqual(entry.success_rate, 0.0)
        self.assertEqual(entry.avg_achievement_pct, 0.0)
        self.assertEqual(entry.common_initiatives, [])
        self.assertEqual(entry.failure_factors, [])
        self.assertEqual(entry.recommendation, "")


# ---------------------------------------------------------------------------
# _classify_pattern
# ---------------------------------------------------------------------------


class ClassifyPatternTests(unittest.TestCase):
    """Order-matters classification — first match wins. Lock each
    archetype's trigger so any reorder is caught."""

    def test_commercial_heavy_denial(self):
        out = _classify_pattern("denial_rate", {
            "commercial_pct": 55, "denial_rate": 12,
        })
        self.assertEqual(out, "commercial_heavy_denial")

    def test_medicare_heavy_ar(self):
        out = _classify_pattern("ar_days", {
            "medicare_pct": 60, "ar_days": 65,
        })
        self.assertEqual(out, "medicare_heavy_ar")

    def test_rural_access_coding_under_200_beds(self):
        # beds < 200 (and > 0) → rural_access_coding, regardless of
        # other fields (after commercial/medicare gates fail).
        out = _classify_pattern("x", {"beds": 150})
        self.assertEqual(out, "rural_access_coding")

    def test_system_acquisition_when_affiliated(self):
        out = _classify_pattern("x", {"system_affiliated": True})
        self.assertEqual(out, "system_acquisition")

    def test_high_medicaid_write_off(self):
        out = _classify_pattern("x", {
            "medicaid_pct": 45, "denial_rate": 9,
        })
        self.assertEqual(out, "high_medicaid_write_off")

    def test_large_academic_complex(self):
        out = _classify_pattern("x", {
            "is_academic": True, "beds": 600,
        })
        self.assertEqual(out, "large_academic_complex")

    def test_outpatient_dominant(self):
        out = _classify_pattern("x", {"outpatient_pct": 70})
        self.assertEqual(out, "outpatient_dominant")

    def test_post_merger_integration(self):
        out = _classify_pattern("x", {"post_merger": True})
        self.assertEqual(out, "post_merger_integration")

    def test_falls_back_to_general(self):
        # Empty profile → general
        out = _classify_pattern("x", {})
        self.assertEqual(out, "general")

    def test_first_match_wins_commercial_over_medicare(self):
        # Both criteria true → commercial_heavy_denial fires (first rule).
        out = _classify_pattern("x", {
            "commercial_pct": 55, "denial_rate": 12,
            "medicare_pct": 60, "ar_days": 65,
        })
        self.assertEqual(out, "commercial_heavy_denial")

    def test_first_match_wins_rural_over_academic(self):
        # beds=150 < 200 → rural_access_coding wins even though
        # is_academic=True (which would otherwise → large_academic).
        out = _classify_pattern("x", {
            "beds": 150, "is_academic": True,
        })
        self.assertEqual(out, "rural_access_coding")

    def test_none_values_safely_coerced_via_or(self):
        # commercial_pct=None → coerced to 0 via 'or 0' guard
        out = _classify_pattern("x", {
            "commercial_pct": None, "denial_rate": None,
        })
        self.assertEqual(out, "general")


# ---------------------------------------------------------------------------
# _achievement_pct + _is_success
# ---------------------------------------------------------------------------


class AchievementPctTests(unittest.TestCase):

    def test_full_achievement(self):
        # achieved == target → 100%
        self.assertEqual(_achievement_pct(10, 20, 20), 1.0)

    def test_no_progress(self):
        # achieved == initial → 0%
        self.assertEqual(_achievement_pct(10, 20, 10), 0.0)

    def test_half_progress(self):
        # 10 → 20 target, achieved 15 → 50%
        self.assertEqual(_achievement_pct(10, 20, 15), 0.5)

    def test_overachievement_not_capped(self):
        # achieved beats target → > 100% (uncapped per docstring)
        self.assertEqual(_achievement_pct(10, 20, 25), 1.5)

    def test_negative_progress_clamps_to_zero(self):
        # achieved worse than initial → clamped to 0 (no negative %)
        self.assertEqual(_achievement_pct(10, 20, 5), 0.0)

    def test_zero_span_returns_zero(self):
        # target == initial → no intended improvement → 0%
        self.assertEqual(_achievement_pct(10, 10, 12), 0.0)

    def test_negative_target_direction(self):
        # Target reduction (e.g. AR days going DOWN): initial=60, target=40
        # achieved=50 → halfway → 50%
        self.assertEqual(_achievement_pct(60, 40, 50), 0.5)


class IsSuccessTests(unittest.TestCase):

    def test_at_threshold_is_success(self):
        # Exactly SUCCESS_THRESHOLD (0.80) → success
        # 0 → 10 target, achieved 8.0 → 80% achievement → True
        self.assertTrue(_is_success(0, 10, 8.0))

    def test_just_below_threshold_is_failure(self):
        # 79% achievement → False
        self.assertFalse(_is_success(0, 10, 7.9))

    def test_above_threshold_is_success(self):
        self.assertTrue(_is_success(0, 10, 9.5))

    def test_zero_span_is_failure(self):
        # No intended improvement → 0% achievement → False
        self.assertFalse(_is_success(10, 10, 12))

    def test_threshold_constant_is_80pct(self):
        # If we ever change the constant the partner brief shifts —
        # lock it.
        self.assertEqual(SUCCESS_THRESHOLD, 0.80)


# ---------------------------------------------------------------------------
# _infer_failure_factors
# ---------------------------------------------------------------------------


class InferFailureFactorsTests(unittest.TestCase):

    def test_empty_outcomes_returns_empty(self):
        self.assertEqual(_infer_failure_factors([]), [])

    def test_only_successes_returns_empty(self):
        out = [DealOutcome("A", 0, 10, 9, 24, True)]
        self.assertEqual(_infer_failure_factors(out), [])

    def test_short_ramp_flagged(self):
        # All failures have months_elapsed < 12 → insufficient_ramp_time
        failures = [
            DealOutcome("A", 0, 10, 3, 6, False),
            DealOutcome("B", 0, 10, 3, 9, False),
        ]
        out = _infer_failure_factors(failures)
        self.assertIn("insufficient_ramp_time", out)

    def test_long_ramp_not_flagged(self):
        # avg_months >= 12 → no flag
        failures = [
            DealOutcome("A", 0, 10, 3, 12, False),
            DealOutcome("B", 0, 10, 3, 18, False),
        ]
        out = _infer_failure_factors(failures)
        self.assertNotIn("insufficient_ramp_time", out)

    def test_no_documented_initiatives_flagged(self):
        # More than half have empty initiatives_used
        failures = [
            DealOutcome("A", 0, 10, 3, 18, False, []),
            DealOutcome("B", 0, 10, 3, 18, False, []),
            DealOutcome("C", 0, 10, 3, 18, False, ["x"]),
        ]
        out = _infer_failure_factors(failures)
        self.assertIn("no_documented_initiatives", out)

    def test_metric_regressed_flagged(self):
        # achieved went in wrong direction relative to target
        # target=20 from initial=10 → direction up. achieved=5 → went DOWN.
        failures = [DealOutcome("A", 10, 20, 5, 18, False, ["x"])]
        out = _infer_failure_factors(failures)
        self.assertIn("metric_regressed", out)

    def test_zero_span_does_not_flag_regression(self):
        # target == initial → span = 0 → no regression possible.
        failures = [DealOutcome("A", 10, 10, 5, 18, False, ["x"])]
        out = _infer_failure_factors(failures)
        self.assertNotIn("metric_regressed", out)

    def test_correct_direction_does_not_flag_regression(self):
        # Both initial→target up AND achieved>initial → not regression
        failures = [DealOutcome("A", 10, 20, 12, 18, False, ["x"])]
        out = _infer_failure_factors(failures)
        self.assertNotIn("metric_regressed", out)

    def test_multiple_factors_can_fire(self):
        failures = [
            DealOutcome("A", 10, 20, 5, 6, False, []),    # all 3 trigger
            DealOutcome("B", 10, 20, 6, 6, False, []),
        ]
        out = _infer_failure_factors(failures)
        # all three flags possible
        self.assertIn("insufficient_ramp_time", out)
        self.assertIn("no_documented_initiatives", out)
        self.assertIn("metric_regressed", out)

    def test_success_filtered_out_of_failure_factors(self):
        # Successes ignored.
        outcomes = [
            DealOutcome("A", 0, 10, 9, 6, True, []),     # success
            DealOutcome("B", 0, 10, 3, 6, False, []),    # failure
        ]
        out = _infer_failure_factors(outcomes)
        # Only B's months_elapsed=6 should count, so insufficient_ramp_time fires.
        self.assertIn("insufficient_ramp_time", out)


if __name__ == "__main__":
    unittest.main()
