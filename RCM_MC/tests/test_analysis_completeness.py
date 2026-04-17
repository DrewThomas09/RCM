"""Tests for the completeness assessment layer.

Covers the registry structure, coverage / grade math, and each of the
six quality-flag detection rules.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta

from rcm_mc.analysis.completeness import (
    METRIC_CATEGORIES,
    RCM_METRIC_REGISTRY,
    assess_completeness,
    hfma_map_key_metrics,
    metric_display_name,
    metric_keys,
)
from rcm_mc.analysis.packet import (
    ConflictField,
    HospitalProfile,
    MissingField,
    ObservedMetric,
    QualityFlag,
    RiskSeverity,
    SectionStatus,
    StaleField,
    CompletenessAssessment,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.portfolio.store import PortfolioStore


# ── Registry tests ────────────────────────────────────────────────────

class TestRegistry(unittest.TestCase):
    def test_registry_has_expected_size(self):
        # Spec: 35-40 metrics total.
        self.assertGreaterEqual(len(RCM_METRIC_REGISTRY), 35)
        self.assertLessEqual(len(RCM_METRIC_REGISTRY), 45)

    def test_every_entry_has_required_fields(self):
        required = {
            "display_name", "category", "unit", "hfma_map_key",
            "required_for_bridge", "ebitda_sensitivity_rank",
            "valid_range", "stale_after_days",
        }
        for key, meta in RCM_METRIC_REGISTRY.items():
            missing = required - set(meta.keys())
            self.assertFalse(missing, f"{key} missing keys: {missing}")

    def test_categories_all_valid(self):
        for key, meta in RCM_METRIC_REGISTRY.items():
            self.assertIn(meta["category"], METRIC_CATEGORIES,
                          f"{key} has unknown category {meta['category']!r}")

    def test_hfma_map_keys_count(self):
        # ~29 HFMA MAP Keys in the spec. Accept a band since our
        # registry compresses a few redundant entries.
        hfma = hfma_map_key_metrics()
        self.assertGreaterEqual(len(hfma), 18)
        self.assertLessEqual(len(hfma), 32)

    def test_sensitivity_ranks_unique(self):
        ranks = [m["ebitda_sensitivity_rank"] for m in RCM_METRIC_REGISTRY.values()]
        self.assertEqual(len(ranks), len(set(ranks)),
                         "Duplicate EBITDA sensitivity ranks — ranks must be unique")

    def test_metric_keys_sorted_by_sensitivity(self):
        keys = metric_keys()
        ranks = [RCM_METRIC_REGISTRY[k]["ebitda_sensitivity_rank"] for k in keys]
        self.assertEqual(ranks, sorted(ranks))

    def test_valid_range_wellformed(self):
        for key, meta in RCM_METRIC_REGISTRY.items():
            lo, hi = meta["valid_range"]
            self.assertLess(lo, hi, f"{key}: valid_range not strictly increasing")

    def test_display_name_helper(self):
        self.assertIn("Denial", metric_display_name("denial_rate"))
        self.assertEqual(metric_display_name("nonexistent"), "nonexistent")

    def test_breakdown_parents_point_at_real_metrics(self):
        for key, meta in RCM_METRIC_REGISTRY.items():
            parent = meta.get("breakdown_of")
            if parent:
                self.assertIn(parent, RCM_METRIC_REGISTRY,
                              f"{key}.breakdown_of={parent!r} is not a registered metric")

    def test_financial_metrics_exist(self):
        for k in ("gross_revenue", "net_revenue", "current_ebitda",
                  "ebitda_margin", "total_operating_expenses"):
            self.assertIn(k, RCM_METRIC_REGISTRY)


# ── Core assessment tests ─────────────────────────────────────────────

def _profile(payer_mix=None):
    return HospitalProfile(
        bed_count=400, region="midwest", state="IL",
        payer_mix=payer_mix or {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    )


def _om(value, source="USER_INPUT", as_of=None):
    return ObservedMetric(
        value=float(value), source=source,
        as_of_date=as_of or date(2026, 3, 31),
    )


def _fully_observed() -> dict:
    """Return an observed dict hitting every registry key with a
    reasonable within-range value (roughly P50).
    """
    out = {}
    for key, meta in RCM_METRIC_REGISTRY.items():
        p50 = meta.get("benchmark_p50")
        if p50 is not None:
            val = p50
        else:
            # Financial metrics with no benchmark — pick a plausible mid.
            lo, hi = meta["valid_range"]
            val = max(lo, min(hi, 100_000_000.0)) if meta["unit"] == "dollars" else (lo + hi) / 2
        out[key] = _om(val)
    return out


class TestCoverageAndGrade(unittest.TestCase):
    def test_empty_observed_gives_d_grade(self):
        r = assess_completeness({}, _profile(), as_of=date(2026, 4, 15))
        self.assertEqual(r.grade, "D")
        self.assertEqual(r.observed_count, 0)
        self.assertEqual(r.total_metrics, len(RCM_METRIC_REGISTRY))
        self.assertAlmostEqual(r.coverage_pct, 0.0)
        self.assertEqual(r.status, SectionStatus.INCOMPLETE)

    def test_full_observed_gives_a_grade(self):
        r = assess_completeness(_fully_observed(), _profile(),
                                as_of=date(2026, 4, 15))
        self.assertEqual(r.grade, "A")
        self.assertAlmostEqual(r.coverage_pct, 1.0)
        self.assertEqual(r.observed_count, len(RCM_METRIC_REGISTRY))
        self.assertEqual(r.missing_fields, [])

    def test_sparse_5_metrics_gives_d_grade(self):
        observed = {
            "denial_rate": _om(5.0),
            "days_in_ar": _om(45.0),
            "net_collection_rate": _om(96.5),
            "clean_claim_rate": _om(92.0),
            "cost_to_collect": _om(2.8),
        }
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertEqual(r.observed_count, 5)
        self.assertEqual(r.grade, "D")

    def test_grade_c_boundary(self):
        # 50% coverage → grade C
        keys = metric_keys()
        n = len(keys)
        half = n // 2
        observed = {k: _om(RCM_METRIC_REGISTRY[k].get("benchmark_p50") or 1.0)
                    for k in keys[:half]}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertIn(r.grade, ("C", "D"))  # just under 0.5 ok too
        self.assertGreaterEqual(r.coverage_pct, 0.45)
        self.assertLessEqual(r.coverage_pct, 0.55)

    def test_grade_b_at_80_pct_coverage(self):
        keys = metric_keys()
        # 80% coverage → above the B threshold, below A (89% ceiling).
        n_target = int(round(len(keys) * 0.80))
        observed = {k: _om(RCM_METRIC_REGISTRY[k].get("benchmark_p50") or 1.0)
                    for k in keys[:n_target]}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertEqual(r.grade, "B")

    def test_grade_a_requires_no_critical_flags(self):
        """A fully observed hospital with an OUT_OF_RANGE value should
        be downgraded from A — structural errors dominate coverage."""
        observed = _fully_observed()
        observed["denial_rate"] = _om(200.0)  # > valid_range upper bound
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertNotEqual(r.grade, "A")

    def test_missing_fields_structured(self):
        observed = {"denial_rate": _om(5.0)}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertTrue(all(isinstance(m, MissingField) for m in r.missing_fields))
        # The missing list should NOT contain the observed metric.
        metric_keys_in_missing = {m.metric_key for m in r.missing_fields}
        self.assertNotIn("denial_rate", metric_keys_in_missing)

    def test_missing_ranked_by_sensitivity_order(self):
        """Top-ranked (rank=1) metrics surface first when missing."""
        observed = {}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        # denial_rate has rank 1 per the registry; should be first.
        self.assertEqual(r.missing_ranked_by_sensitivity[0], "denial_rate")
        self.assertEqual(r.missing_fields[0].ebitda_sensitivity_rank, 1)


# ── Quality-flag tests ────────────────────────────────────────────────

class TestQualityFlags(unittest.TestCase):
    def test_out_of_range_flag(self):
        observed = {"denial_rate": _om(150.0)}  # > 100%
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("OUT_OF_RANGE", types)
        flag = next(q for q in r.quality_flags if q.flag_type == "OUT_OF_RANGE")
        self.assertEqual(flag.severity, RiskSeverity.HIGH)
        self.assertEqual(flag.metric_key, "denial_rate")

    def test_stale_flag(self):
        old = date(2026, 4, 15) - timedelta(days=200)
        observed = {"days_in_ar": _om(45.0, as_of=old)}  # stale_after=30
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        stale_keys = {s.metric_key for s in r.stale_fields}
        self.assertIn("days_in_ar", stale_keys)
        flag_types = {q.flag_type for q in r.quality_flags}
        self.assertIn("STALE", flag_types)

    def test_missing_breakdown_flag(self):
        observed = {"denial_rate": _om(5.0)}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("MISSING_BREAKDOWN", types)
        flag = next(q for q in r.quality_flags if q.flag_type == "MISSING_BREAKDOWN")
        self.assertEqual(flag.metric_key, "denial_rate")

    def test_missing_breakdown_not_flagged_if_any_child_present(self):
        observed = {
            "denial_rate": _om(5.0),
            "denial_rate_commercial": _om(7.5),
        }
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        missing_breakdown = [q for q in r.quality_flags
                             if q.flag_type == "MISSING_BREAKDOWN"]
        self.assertEqual(len(missing_breakdown), 0)

    def test_benchmark_outlier_flag(self):
        observed = {"days_in_ar": _om(200.0)}  # well above P90
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("BENCHMARK_OUTLIER", types)

    def test_benchmark_outlier_not_flagged_on_out_of_range(self):
        """If value is OUT_OF_RANGE we skip the outlier check — the
        range violation is the real story."""
        observed = {"days_in_ar": _om(1000.0)}  # > 365 valid_range max
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags if q.metric_key == "days_in_ar"}
        self.assertIn("OUT_OF_RANGE", types)
        self.assertNotIn("BENCHMARK_OUTLIER", types)

    def test_suspicious_change_flag(self):
        historical = {
            "denial_rate": [
                (date(2026, 1, 31), 5.0),
                (date(2026, 2, 28), 9.0),  # +80% MoM
            ],
        }
        observed = {"denial_rate": _om(9.0)}
        r = assess_completeness(
            observed, _profile(), as_of=date(2026, 4, 15),
            historical_values=historical,
        )
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("SUSPICIOUS_CHANGE", types)

    def test_suspicious_change_below_threshold(self):
        historical = {
            "denial_rate": [
                (date(2026, 1, 31), 5.0),
                (date(2026, 2, 28), 5.5),  # +10%
            ],
        }
        observed = {"denial_rate": _om(5.5)}
        r = assess_completeness(
            observed, _profile(), as_of=date(2026, 4, 15),
            historical_values=historical,
        )
        types = {q.flag_type for q in r.quality_flags}
        self.assertNotIn("SUSPICIOUS_CHANGE", types)

    def test_payer_mix_incomplete_on_bad_sum(self):
        bad_profile = HospitalProfile(
            bed_count=300,
            payer_mix={"medicare": 0.40, "commercial": 0.30},  # sums to 70%
        )
        r = assess_completeness({}, bad_profile, as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("PAYER_MIX_INCOMPLETE", types)
        flag = next(q for q in r.quality_flags if q.flag_type == "PAYER_MIX_INCOMPLETE")
        self.assertEqual(flag.severity, RiskSeverity.HIGH)

    def test_payer_mix_pct_metrics_trigger_same_check(self):
        observed = {
            "payer_mix_commercial_pct": _om(30.0),
            "payer_mix_medicare_pct": _om(30.0),
            "payer_mix_medicaid_pct": _om(10.0),  # sums to 70% only
            "payer_mix_selfpay_pct": _om(0.0),
        }
        # Don't pass a profile.payer_mix — force the pct-metric path.
        profile = HospitalProfile(bed_count=300)
        r = assess_completeness(observed, profile, as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertIn("PAYER_MIX_INCOMPLETE", types)

    def test_valid_payer_mix_does_not_flag(self):
        good = HospitalProfile(
            bed_count=300,
            payer_mix={"medicare": 0.40, "commercial": 0.45,
                       "medicaid": 0.10, "self_pay": 0.05},
        )
        r = assess_completeness({}, good, as_of=date(2026, 4, 15))
        types = {q.flag_type for q in r.quality_flags}
        self.assertNotIn("PAYER_MIX_INCOMPLETE", types)

    def test_conflicting_sources(self):
        observed = {"denial_rate": _om(5.5, source="USER_INPUT")}
        conflicts = {
            "denial_rate": [
                ("HCRIS", 6.2, "2025-12-31"),
                ("USER_INPUT", 5.5, "2026-01-31"),
            ],
        }
        r = assess_completeness(
            observed, _profile(), as_of=date(2026, 4, 15),
            conflict_sources=conflicts,
        )
        self.assertEqual(len(r.conflicting_fields), 1)
        self.assertEqual(r.conflicting_fields[0].metric_key, "denial_rate")
        self.assertEqual(r.conflicting_fields[0].chosen_source, "USER_INPUT")

    def test_stale_severity_higher_for_bridge_inputs(self):
        old = date(2026, 4, 15) - timedelta(days=400)
        observed = {
            "days_in_ar": _om(45.0, as_of=old),   # required_for_bridge=True
            "autopost_rate": _om(85.0, as_of=old), # required_for_bridge=False
        }
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        stale_flags = {q.metric_key: q for q in r.quality_flags
                       if q.flag_type == "STALE"}
        # critical metric → MEDIUM severity; non-critical → LOW
        self.assertEqual(stale_flags["days_in_ar"].severity, RiskSeverity.MEDIUM)
        self.assertEqual(stale_flags["autopost_rate"].severity, RiskSeverity.LOW)

    def test_unknown_metric_key_ignored(self):
        """Keys not in the registry shouldn't crash or contribute to
        coverage — they're just out of scope."""
        observed = {"an_unknown_metric": _om(1.0),
                    "denial_rate": _om(5.0)}
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        self.assertEqual(r.observed_count, 1)


# ── Serialization / dataclass tests ────────────────────────────────────

class TestAssessmentSerialization(unittest.TestCase):
    def test_roundtrip_preserves_structured_fields(self):
        observed = {
            "denial_rate": _om(16.0),  # above warn
            "days_in_ar": _om(200.0),  # out of range
        }
        r = assess_completeness(observed, _profile(), as_of=date(2026, 4, 15))
        d = r.to_dict()
        r2 = CompletenessAssessment.from_dict(d)
        self.assertEqual(r.grade, r2.grade)
        self.assertEqual(r.total_metrics, r2.total_metrics)
        self.assertEqual(r.observed_count, r2.observed_count)
        self.assertEqual(len(r.quality_flags), len(r2.quality_flags))
        self.assertEqual(r.missing_ranked_by_sensitivity,
                         r2.missing_ranked_by_sensitivity)

    def test_legacy_string_missing_fields_coerce(self):
        """An older packet saved with list[str] missing_fields should
        still deserialize — the post_init coerces strings to
        MissingField(metric_key=...)."""
        legacy = CompletenessAssessment(
            coverage_pct=0.5, missing_fields=["days_in_ar", "clean_claim_rate"],
        )
        self.assertEqual(len(legacy.missing_fields), 2)
        self.assertIsInstance(legacy.missing_fields[0], MissingField)
        self.assertEqual(legacy.missing_fields[0].metric_key, "days_in_ar")


# ── Integration with packet_builder ────────────────────────────────────

class TestPacketBuilderIntegration(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = PortfolioStore(self.db_path)
        self.store.upsert_deal(
            "test-deal", name="Test Health",
            profile={
                "bed_count": 400,
                "region": "midwest",
                "payer_mix": {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
            },
        )

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_builder_produces_graded_completeness(self):
        observed = {
            "denial_rate": ObservedMetric(value=5.0),
            "days_in_ar": ObservedMetric(value=45.0),
            "clean_claim_rate": ObservedMetric(value=92.0),
        }
        packet = build_analysis_packet(
            self.store, "test-deal", skip_simulation=True,
            observed_override=observed,
        )
        self.assertIn(packet.completeness.grade, ("A", "B", "C", "D"))
        self.assertEqual(packet.completeness.observed_count, 3)
        self.assertGreater(packet.completeness.total_metrics, 30)

    def test_builder_preserves_quality_flags_across_json_roundtrip(self):
        observed = {"denial_rate": ObservedMetric(value=150.0)}  # bad value
        packet = build_analysis_packet(
            self.store, "test-deal", skip_simulation=True,
            observed_override=observed,
        )
        payload = packet.to_json()
        from rcm_mc.analysis.packet import DealAnalysisPacket
        restored = DealAnalysisPacket.from_json(payload)
        types_before = {q.flag_type for q in packet.completeness.quality_flags}
        types_after = {q.flag_type for q in restored.completeness.quality_flags}
        self.assertEqual(types_before, types_after)
        self.assertIn("OUT_OF_RANGE", types_after)


if __name__ == "__main__":
    unittest.main()
