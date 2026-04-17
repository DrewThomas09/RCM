"""Tests for the RCM → EBITDA bridge.

The research calibration band is the contract:

    Denial rate  12 → 5       $8-15M   on $400M NPR
    A/R days     55 → 38      $5-10M
    Clean claim  85 → 96      $1-3M
    Net coll.    92 → 97      $10-15M
    Cost coll.    5 → 3       $4-8M
    CDI / CMI   +0.05          $3-8M

If any of these bands are violated by the bridge's math on a realistic
hospital profile, the bridge is wrong — partners will push back on the
numbers in IC. These tests lock that contract in place so a refactor
can't silently drift the calibration.
"""
from __future__ import annotations

import math
import unittest
from typing import Dict

from rcm_mc.pe.rcm_ebitda_bridge import (
    FinancialProfile,
    RCMEBITDABridge,
    TargetRecommendation,
    TornadoResult,
    profile_from_packet,
)
from rcm_mc.analysis.completeness import RCM_METRIC_REGISTRY
from rcm_mc.analysis.packet import (
    EBITDABridgeResult,
    HospitalProfile,
    MetricImpact,
    SectionStatus,
)


def _research_profile(net_revenue: float = 400_000_000) -> FinancialProfile:
    """Standard profile for research-band calibration tests."""
    return FinancialProfile(
        gross_revenue=net_revenue * 2.5,     # typical gross-to-net ratio
        net_revenue=net_revenue,
        current_ebitda=net_revenue * 0.08,   # 8% margin
        cost_of_capital_pct=0.08,
        total_claims_volume=300_000,
        cost_per_reworked_claim=30.0,
        fte_cost_follow_up=55_000.0,
        claims_per_follow_up_fte=10_000,
        payer_mix={"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    )


# ── Research calibration ────────────────────────────────────────────

class TestResearchCalibration(unittest.TestCase):
    """Every lever, on the $400M NPR reference hospital, should produce
    an EBITDA impact inside the research band."""

    def setUp(self):
        self.bridge = RCMEBITDABridge(_research_profile())

    def test_denial_rate_12_to_5_lands_in_8_to_15M(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 12.0}, {"denial_rate": 5.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "denial_rate")
        self.assertGreaterEqual(imp.ebitda_impact, 8_000_000)
        self.assertLessEqual(imp.ebitda_impact, 15_000_000)

    def test_days_in_ar_55_to_38_lands_in_5_to_10M(self):
        r = self.bridge.compute_bridge(
            {"days_in_ar": 55.0}, {"days_in_ar": 38.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "days_in_ar")
        self.assertGreaterEqual(imp.ebitda_impact, 5_000_000)
        self.assertLessEqual(imp.ebitda_impact, 10_000_000)
        # Working capital released: 17 × $400M/365 ≈ $18.6M one-time.
        self.assertGreater(imp.working_capital_impact, 18_000_000)
        self.assertLess(imp.working_capital_impact, 20_000_000)

    def test_clean_claim_85_to_96_lands_in_1_to_3M(self):
        r = self.bridge.compute_bridge(
            {"clean_claim_rate": 85.0}, {"clean_claim_rate": 96.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "clean_claim_rate")
        self.assertGreaterEqual(imp.ebitda_impact, 900_000)   # low-end tolerance
        self.assertLessEqual(imp.ebitda_impact, 3_000_000)

    def test_net_collection_92_to_97_lands_in_10_to_15M(self):
        r = self.bridge.compute_bridge(
            {"net_collection_rate": 92.0}, {"net_collection_rate": 97.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "net_collection_rate")
        self.assertGreaterEqual(imp.ebitda_impact, 10_000_000)
        self.assertLessEqual(imp.ebitda_impact, 15_000_000)

    def test_cost_to_collect_5_to_3_lands_in_4_to_8M(self):
        r = self.bridge.compute_bridge(
            {"cost_to_collect": 5.0}, {"cost_to_collect": 3.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "cost_to_collect")
        self.assertGreaterEqual(imp.ebitda_impact, 4_000_000)
        self.assertLessEqual(imp.ebitda_impact, 8_000_000)

    def test_cmi_up_by_point_zero_five_lands_in_3_to_8M(self):
        r = self.bridge.compute_bridge(
            {"case_mix_index": 1.60}, {"case_mix_index": 1.65},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "case_mix_index")
        self.assertGreaterEqual(imp.ebitda_impact, 3_000_000)
        self.assertLessEqual(imp.ebitda_impact, 8_000_000)


# ── Bridge aggregate ────────────────────────────────────────────────

class TestComputeBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = RCMEBITDABridge(_research_profile())

    def test_zero_change_produces_zero_impact(self):
        r = self.bridge.compute_bridge({}, {})
        self.assertEqual(r.total_ebitda_impact, 0.0)
        self.assertEqual(r.target_ebitda, r.current_ebitda)
        self.assertEqual(r.per_metric_impacts, [])

    def test_same_current_and_target_is_skipped(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 5.0}, {"denial_rate": 5.0},
        )
        self.assertEqual(r.per_metric_impacts, [])
        self.assertEqual(r.total_ebitda_impact, 0.0)

    def test_waterfall_reconciles_with_total(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 10.0, "days_in_ar": 55.0},
            {"denial_rate": 7.0, "days_in_ar": 45.0},
        )
        # first entry = current, last = target, middle = per-lever impacts
        self.assertEqual(r.waterfall_data[0][0], "Current EBITDA")
        self.assertEqual(r.waterfall_data[-1][0], "Target EBITDA")
        inner_sum = sum(v for _, v in r.waterfall_data[1:-1])
        self.assertAlmostEqual(inner_sum, r.total_ebitda_impact, places=3)
        self.assertAlmostEqual(
            r.current_ebitda + r.total_ebitda_impact, r.target_ebitda,
            places=3,
        )

    def test_margin_improvement_bps_positive_when_ebitda_grows(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
        )
        self.assertGreater(r.margin_improvement_bps, 0)

    def test_ev_impact_at_multiple_scales_linearly(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
        )
        self.assertIn("10x", r.ev_impact_at_multiple)
        self.assertIn("12x", r.ev_impact_at_multiple)
        self.assertIn("15x", r.ev_impact_at_multiple)
        ratio = r.ev_impact_at_multiple["15x"] / r.ev_impact_at_multiple["10x"]
        self.assertAlmostEqual(ratio, 1.5, places=3)

    def test_monotonicity_improving_metrics_never_reduces_ebitda(self):
        """Every lever in its improvement direction must produce
        ebitda_impact >= 0.
        """
        improvements = {
            "denial_rate":                (10.0, 5.0),   # reduce
            "days_in_ar":                 (55.0, 40.0),  # reduce
            "net_collection_rate":        (92.0, 97.0),  # increase
            "clean_claim_rate":           (85.0, 96.0),  # increase
            "cost_to_collect":            (4.0, 2.5),    # reduce
            "first_pass_resolution_rate": (80.0, 92.0),  # increase
            "case_mix_index":             (1.60, 1.70),  # increase
        }
        for metric, (cur, tgt) in improvements.items():
            r = self.bridge.compute_bridge({metric: cur}, {metric: tgt})
            imp = next(m for m in r.per_metric_impacts if m.metric_key == metric)
            self.assertGreaterEqual(imp.ebitda_impact, 0.0,
                                    f"{metric} improvement went negative")

    def test_degradation_produces_negative_impact(self):
        """Moving denial_rate UP (bad) should give negative ebitda_impact."""
        r = self.bridge.compute_bridge(
            {"denial_rate": 5.0}, {"denial_rate": 10.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "denial_rate")
        self.assertLess(imp.ebitda_impact, 0.0)

    def test_bridge_with_zero_revenue_is_incomplete(self):
        fp = _research_profile()
        fp.net_revenue = 0.0
        bridge = RCMEBITDABridge(fp)
        r = bridge.compute_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
        )
        self.assertEqual(r.status, SectionStatus.INCOMPLETE)
        self.assertIn("net_revenue", r.reason)

    def test_nan_inputs_do_not_leak_into_result(self):
        """Partners paste spreadsheet cells that sometimes contain
        ``#N/A`` or blank strings. The bridge must coerce/skip those
        instead of producing NaN dollars downstream.
        """
        r = self.bridge.compute_bridge(
            {"denial_rate": float("nan")},
            {"denial_rate": 5.0},
        )
        for imp in r.per_metric_impacts:
            self.assertFalse(math.isnan(imp.ebitda_impact))
            self.assertFalse(math.isinf(imp.ebitda_impact))
        self.assertFalse(math.isnan(r.total_ebitda_impact))

    def test_extreme_inputs_do_not_produce_inf(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 100.0, "days_in_ar": 365.0},
            {"denial_rate": 0.0, "days_in_ar": 0.0},
        )
        self.assertTrue(math.isfinite(r.total_ebitda_impact))
        for imp in r.per_metric_impacts:
            self.assertTrue(math.isfinite(imp.ebitda_impact))
            self.assertTrue(math.isfinite(imp.working_capital_impact))

    def test_upstream_metrics_populated(self):
        """Provenance: each lever lists the inputs that drove it."""
        r = self.bridge.compute_bridge(
            {"denial_rate": 10.0}, {"denial_rate": 5.0},
        )
        imp = next(m for m in r.per_metric_impacts if m.metric_key == "denial_rate")
        self.assertIn("denial_rate", imp.upstream_metrics)
        self.assertIn("net_revenue", imp.upstream_metrics)

    def test_multiple_levers_combine_additively(self):
        r = self.bridge.compute_bridge(
            {"denial_rate": 10.0, "days_in_ar": 55.0, "cost_to_collect": 4.0},
            {"denial_rate": 5.0, "days_in_ar": 40.0, "cost_to_collect": 3.0},
        )
        self.assertEqual(len(r.per_metric_impacts), 3)
        expected = sum(m.ebitda_impact for m in r.per_metric_impacts)
        self.assertAlmostEqual(r.total_ebitda_impact, expected, places=3)


# ── Sensitivity tornado ─────────────────────────────────────────────

class TestTornado(unittest.TestCase):
    def setUp(self):
        self.bridge = RCMEBITDABridge(_research_profile())

    def test_tornado_returns_rows_sorted_by_magnitude(self):
        tor = self.bridge.compute_sensitivity_tornado(
            {"denial_rate": 10.0, "days_in_ar": 55.0,
             "net_collection_rate": 92.0, "clean_claim_rate": 85.0,
             "cost_to_collect": 4.0, "first_pass_resolution_rate": 80.0,
             "case_mix_index": 1.60},
            improvement_scenarios=[0.01, 0.05, 0.10, 0.20],
        )
        self.assertIsInstance(tor, TornadoResult)
        self.assertEqual(len(tor.rows), 7)
        # Sorted descending by max_abs_impact
        impacts = [r.max_abs_impact for r in tor.rows]
        self.assertEqual(impacts, sorted(impacts, reverse=True))

    def test_tornado_scenarios_are_monotone_in_absolute_value(self):
        """For each lever, bigger relative improvement should produce a
        larger absolute EBITDA impact (monotonicity sanity)."""
        tor = self.bridge.compute_sensitivity_tornado(
            {"denial_rate": 10.0},
            improvement_scenarios=[0.01, 0.05, 0.10, 0.20],
        )
        row = tor.rows[0]
        vals = [row.scenarios["1pct"], row.scenarios["5pct"],
                row.scenarios["10pct"], row.scenarios["20pct"]]
        abs_vals = [abs(v) for v in vals]
        self.assertEqual(abs_vals, sorted(abs_vals))

    def test_tornado_skips_zero_current(self):
        tor = self.bridge.compute_sensitivity_tornado(
            {"denial_rate": 0.0, "days_in_ar": 55.0},
        )
        metrics = {r.metric for r in tor.rows}
        self.assertNotIn("denial_rate", metrics)
        self.assertIn("days_in_ar", metrics)


# ── Target recommendations ──────────────────────────────────────────

class TestSuggestTargets(unittest.TestCase):
    def setUp(self):
        self.bridge = RCMEBITDABridge(_research_profile())

    def test_three_tiers_return(self):
        current = {
            "denial_rate": 12.0, "days_in_ar": 55.0,
            "net_collection_rate": 92.0, "clean_claim_rate": 85.0,
            "cost_to_collect": 5.0, "first_pass_resolution_rate": 80.0,
            "case_mix_index": 1.55,
        }
        rec = self.bridge.suggest_targets(current, None, RCM_METRIC_REGISTRY)
        self.assertIsInstance(rec, TargetRecommendation)
        self.assertEqual(rec.conservative.tier, "conservative")
        self.assertEqual(rec.moderate.tier, "moderate")
        self.assertEqual(rec.aggressive.tier, "aggressive")

    def test_aggressive_impact_exceeds_conservative(self):
        current = {
            "denial_rate": 12.0, "days_in_ar": 55.0,
            "net_collection_rate": 90.0, "clean_claim_rate": 80.0,
            "cost_to_collect": 5.5, "first_pass_resolution_rate": 72.0,
        }
        rec = self.bridge.suggest_targets(current, None, RCM_METRIC_REGISTRY)
        self.assertGreaterEqual(rec.aggressive.total_ebitda_impact,
                                rec.moderate.total_ebitda_impact)
        self.assertGreaterEqual(rec.moderate.total_ebitda_impact,
                                rec.conservative.total_ebitda_impact)

    def test_achievability_decreases_with_aggression(self):
        current = {
            "denial_rate": 12.0, "days_in_ar": 60.0,
            "net_collection_rate": 88.0, "clean_claim_rate": 82.0,
        }
        rec = self.bridge.suggest_targets(current, None, RCM_METRIC_REGISTRY)
        self.assertGreaterEqual(rec.conservative.achievability_score,
                                rec.moderate.achievability_score)
        self.assertGreaterEqual(rec.moderate.achievability_score,
                                rec.aggressive.achievability_score)

    def test_months_are_positive(self):
        current = {"denial_rate": 12.0, "days_in_ar": 60.0}
        rec = self.bridge.suggest_targets(current, None, RCM_METRIC_REGISTRY)
        self.assertGreaterEqual(rec.moderate.estimated_months_to_achieve, 3)

    def test_skip_metric_already_better_than_target(self):
        """If the hospital is already at P25 on denial_rate (low is
        better), no conservative target should be set for it."""
        current = {"denial_rate": 2.0}       # below P25 (3.0)
        rec = self.bridge.suggest_targets(current, None, RCM_METRIC_REGISTRY)
        self.assertNotIn("denial_rate", rec.conservative.targets)


# ── pe_math integration ────────────────────────────────────────────

class TestPEMathIntegration(unittest.TestCase):
    def test_returns_from_rcm_bridge_flows_through(self):
        from rcm_mc.pe.pe_math import returns_from_rcm_bridge
        bridge = RCMEBITDABridge(_research_profile())
        r = bridge.compute_bridge(
            {"denial_rate": 10.0, "days_in_ar": 55.0, "cost_to_collect": 4.0},
            {"denial_rate": 5.0, "days_in_ar": 40.0, "cost_to_collect": 2.5},
        )
        self.assertGreater(r.total_ebitda_impact, 0)
        out = returns_from_rcm_bridge(
            r, entry_multiple=10.0, exit_multiple=11.0,
            hold_years=5.0, organic_growth_pct=0.03,
        )
        self.assertIn("bridge", out)
        self.assertIn("returns", out)
        self.assertGreater(out["returns"].moic, 1.0)
        self.assertGreater(out["entry_ev"], 0)
        self.assertGreater(out["exit_ev"], out["entry_ev"])

    def test_returns_raises_on_zero_current_ebitda(self):
        from rcm_mc.pe.pe_math import returns_from_rcm_bridge
        r = EBITDABridgeResult(current_ebitda=0.0)
        with self.assertRaises(ValueError):
            returns_from_rcm_bridge(
                r, entry_multiple=10.0, exit_multiple=10.0, hold_years=5.0,
            )


# ── Profile helper ──────────────────────────────────────────────────

class TestProfileFromPacket(unittest.TestCase):
    def test_profile_from_packet_pulls_observed(self):
        from rcm_mc.analysis.packet import HospitalProfile, ObservedMetric
        hp = HospitalProfile(bed_count=400, payer_mix={"medicare": 0.4, "commercial": 0.6})
        observed = {
            "gross_revenue": ObservedMetric(value=1_000_000_000),
            "net_revenue": ObservedMetric(value=400_000_000),
            "current_ebitda": ObservedMetric(value=30_000_000),
        }
        fp = profile_from_packet(hp, observed, total_claims_volume=300_000)
        self.assertEqual(fp.gross_revenue, 1_000_000_000)
        self.assertEqual(fp.net_revenue, 400_000_000)
        self.assertEqual(fp.current_ebitda, 30_000_000)
        self.assertEqual(fp.total_claims_volume, 300_000)
        self.assertEqual(fp.payer_mix, {"medicare": 0.4, "commercial": 0.6})


if __name__ == "__main__":
    unittest.main()
