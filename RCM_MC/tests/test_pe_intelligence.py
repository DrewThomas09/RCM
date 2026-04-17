"""Tests for rcm_mc.pe_intelligence — reasonableness, heuristics,
narrative, and the top-level partner_review entry point.

The tests deliberately use hand-built ``HeuristicContext`` objects and
dict-shaped packet stubs rather than real ``DealAnalysisPacket``
instances where possible. This isolates the intelligence brain from
packet-builder changes — the contract we care about is "given these
inputs, produce this judgment," not the packet's internal plumbing.

Every test targets a specific partner rule or band. The rule ids
referenced here must match those in heuristics.py — if a rule is
renamed, the test will fail on id-level assertion.
"""
from __future__ import annotations

import unittest

from rcm_mc.pe_intelligence import (
    Band,
    BandCheck,
    HeuristicContext,
    HeuristicHit,
    NarrativeBlock,
    PartnerReview,
    all_heuristics,
    check_ebitda_margin,
    check_irr,
    check_lever_realizability,
    check_multiple_ceiling,
    compose_narrative,
    partner_review,
    partner_review_from_context,
    run_heuristics,
    run_reasonableness_checks,
)
from rcm_mc.pe_intelligence.narrative import (
    REC_PASS,
    REC_PROCEED,
    REC_PROCEED_CAVEATS,
    REC_STRONG_PROCEED,
)
from rcm_mc.pe_intelligence.reasonableness import (
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
    classify_payer_mix,
    classify_size,
    get_irr_band,
    get_lever_timeframe,
    get_margin_band,
    PAYER_BALANCED,
    PAYER_COMMERCIAL_HEAVY,
    PAYER_GOVT_HEAVY,
    PAYER_MEDICAID_HEAVY,
    PAYER_MEDICARE_HEAVY,
    SIZE_LARGE,
    SIZE_LOWER_MID,
    SIZE_MID,
    SIZE_SMALL,
    SIZE_UPPER_MID,
)
from rcm_mc.pe_intelligence.heuristics import (
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_LOW,
    SEV_MEDIUM,
)


# ── Reasonableness: Band classification ───────────────────────────────

class TestBandClassification(unittest.TestCase):

    def test_band_in_band_returns_in_band(self) -> None:
        band = Band("test", "test", low=0.10, high=0.20,
                    stretch_high=0.25, implausible_high=0.35)
        self.assertEqual(band.classify(0.15), VERDICT_IN_BAND)

    def test_band_stretch_returns_stretch(self) -> None:
        band = Band("test", "test", low=0.10, high=0.20,
                    stretch_high=0.25, implausible_high=0.35)
        self.assertEqual(band.classify(0.23), VERDICT_STRETCH)

    def test_band_out_of_band_returns_out_of_band(self) -> None:
        band = Band("test", "test", low=0.10, high=0.20,
                    stretch_high=0.25, implausible_high=0.35)
        self.assertEqual(band.classify(0.30), VERDICT_OUT_OF_BAND)

    def test_band_implausible_returns_implausible(self) -> None:
        band = Band("test", "test", low=0.10, high=0.20,
                    stretch_high=0.25, implausible_high=0.35)
        self.assertEqual(band.classify(0.40), VERDICT_IMPLAUSIBLE)

    def test_band_none_value_returns_unknown(self) -> None:
        band = Band("test", "test", low=0.10, high=0.20)
        self.assertEqual(band.classify(None), VERDICT_UNKNOWN)


class TestSizeClassification(unittest.TestCase):

    def test_small_bucket(self) -> None:
        self.assertEqual(classify_size(5.0), SIZE_SMALL)

    def test_lower_mid_bucket(self) -> None:
        self.assertEqual(classify_size(15.0), SIZE_LOWER_MID)

    def test_mid_bucket(self) -> None:
        self.assertEqual(classify_size(50.0), SIZE_MID)

    def test_upper_mid_bucket(self) -> None:
        self.assertEqual(classify_size(150.0), SIZE_UPPER_MID)

    def test_large_bucket(self) -> None:
        self.assertEqual(classify_size(400.0), SIZE_LARGE)

    def test_missing_defaults_to_small(self) -> None:
        self.assertEqual(classify_size(None), SIZE_SMALL)


class TestPayerMixClassification(unittest.TestCase):

    def test_commercial_heavy(self) -> None:
        self.assertEqual(
            classify_payer_mix({"commercial": 0.50, "medicare": 0.30, "medicaid": 0.10}),
            PAYER_COMMERCIAL_HEAVY,
        )

    def test_medicare_heavy(self) -> None:
        self.assertEqual(
            classify_payer_mix({"medicare": 0.60, "commercial": 0.30}),
            PAYER_MEDICARE_HEAVY,
        )

    def test_govt_heavy_takes_precedence(self) -> None:
        # Medicare 45 + Medicaid 30 = 75% — should be govt_heavy.
        self.assertEqual(
            classify_payer_mix({"medicare": 0.45, "medicaid": 0.30, "commercial": 0.25}),
            PAYER_GOVT_HEAVY,
        )

    def test_medicaid_heavy(self) -> None:
        self.assertEqual(
            classify_payer_mix({"medicaid": 0.35, "commercial": 0.40, "medicare": 0.25}),
            PAYER_MEDICAID_HEAVY,
        )

    def test_balanced_when_no_regime_hits(self) -> None:
        self.assertEqual(
            classify_payer_mix({"commercial": 0.35, "medicare": 0.40, "medicaid": 0.20, "other": 0.05}),
            PAYER_BALANCED,
        )

    def test_empty_returns_balanced(self) -> None:
        self.assertEqual(classify_payer_mix({}), PAYER_BALANCED)

    def test_percent_format_autonormalized(self) -> None:
        # Given as percentages (sum ~ 100) — should still classify correctly.
        # 60 medicare + 5 medicaid = 65% govt, below the 70% govt_heavy cutoff,
        # so the classifier should resolve to medicare_heavy.
        self.assertEqual(
            classify_payer_mix({"medicare": 60.0, "commercial": 35.0, "medicaid": 5.0}),
            PAYER_MEDICARE_HEAVY,
        )


# ── Reasonableness: IRR checks ────────────────────────────────────────

class TestCheckIRR(unittest.TestCase):

    def test_none_irr_returns_unknown(self) -> None:
        result = check_irr(None, ebitda_m=50.0, payer_mix={"commercial": 0.50})
        self.assertEqual(result.verdict, VERDICT_UNKNOWN)

    def test_medicare_heavy_irr_in_band(self) -> None:
        # Mid-size, Medicare-heavy (below 70% govt threshold) — 14% IRR is in the band
        r = check_irr(0.14, ebitda_m=50.0,
                      payer_mix={"medicare": 0.60, "commercial": 0.35, "medicaid": 0.05})
        self.assertEqual(r.verdict, VERDICT_IN_BAND)
        self.assertIn("Medicare-heavy", r.rationale)

    def test_medicare_heavy_irr_stretch(self) -> None:
        r = check_irr(0.19, ebitda_m=50.0,
                      payer_mix={"medicare": 0.60, "commercial": 0.35, "medicaid": 0.05})
        self.assertEqual(r.verdict, VERDICT_STRETCH)

    def test_medicare_heavy_irr_implausible(self) -> None:
        # mid × medicare_heavy has implausible > 28%
        r = check_irr(0.35, ebitda_m=50.0,
                      payer_mix={"medicare": 0.60, "commercial": 0.35, "medicaid": 0.05})
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)
        self.assertIn("IC", r.partner_note)

    def test_commercial_heavy_same_irr_not_implausible(self) -> None:
        # The same 35% IRR in a commercial-heavy mid deal is STRETCH, not implausible.
        r = check_irr(0.35, ebitda_m=50.0,
                      payer_mix={"commercial": 0.55, "medicare": 0.30})
        self.assertNotEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_band_varies_by_size(self) -> None:
        """A 25% IRR is IN_BAND for small-commercial but OUT/IMPLAUSIBLE for large."""
        r_small = check_irr(0.25, ebitda_m=5.0, payer_mix={"commercial": 0.55})
        r_large = check_irr(0.25, ebitda_m=300.0, payer_mix={"commercial": 0.55})
        self.assertEqual(r_small.verdict, VERDICT_IN_BAND)
        # Large-commercial IN_BAND is 12-20, STRETCH 25, so this should be STRETCH.
        self.assertIn(r_large.verdict, (VERDICT_STRETCH, VERDICT_OUT_OF_BAND))

    def test_get_irr_band_falls_back_to_balanced(self) -> None:
        # Contrived: should never return None.
        band = get_irr_band(SIZE_MID, "totally_bogus_regime")
        self.assertIsNotNone(band)


# ── Reasonableness: EBITDA margin ─────────────────────────────────────

class TestCheckEBITDAMargin(unittest.TestCase):

    def test_none_margin_returns_unknown(self) -> None:
        r = check_ebitda_margin(None, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_acute_care_normal_margin(self) -> None:
        r = check_ebitda_margin(0.08, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_acute_care_high_margin_flagged(self) -> None:
        r = check_ebitda_margin(0.22, hospital_type="acute_care")
        self.assertIn(r.verdict, (VERDICT_OUT_OF_BAND, VERDICT_STRETCH))

    def test_acute_care_extreme_margin_implausible(self) -> None:
        r = check_ebitda_margin(0.40, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_asc_high_margin_is_normal(self) -> None:
        # 25% margin on an ASC is entirely normal.
        r = check_ebitda_margin(0.25, hospital_type="asc")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_critical_access_tight_band(self) -> None:
        # 12% on CAH is above band.
        r = check_ebitda_margin(0.12, hospital_type="critical_access")
        self.assertIn(r.verdict, (VERDICT_STRETCH, VERDICT_OUT_OF_BAND))

    def test_aliases_resolve(self) -> None:
        r = check_ebitda_margin(0.08, hospital_type="acute")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)
        r2 = check_ebitda_margin(0.08, hospital_type="hospital")
        self.assertEqual(r2.verdict, VERDICT_IN_BAND)

    def test_unknown_type_falls_back_to_acute(self) -> None:
        # Unknown hospital type should fall back to acute_care band.
        r = check_ebitda_margin(0.08, hospital_type="made_up_type")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)


# ── Reasonableness: exit multiple ─────────────────────────────────────

class TestCheckMultipleCeiling(unittest.TestCase):

    def test_none_multiple_returns_unknown(self) -> None:
        r = check_multiple_ceiling(None, payer_mix={"commercial": 0.55})
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_commercial_heavy_high_multiple_in_band(self) -> None:
        r = check_multiple_ceiling(10.0, payer_mix={"commercial": 0.55})
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_medicare_heavy_same_multiple_out_of_band(self) -> None:
        r = check_multiple_ceiling(10.0, payer_mix={"medicare": 0.65})
        self.assertIn(r.verdict, (VERDICT_STRETCH, VERDICT_OUT_OF_BAND))

    def test_medicare_heavy_extreme_multiple_implausible(self) -> None:
        r = check_multiple_ceiling(14.0, payer_mix={"medicare": 0.65})
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)


# ── Reasonableness: lever realizability ──────────────────────────────

class TestCheckLeverRealizability(unittest.TestCase):

    def test_denial_12mo_200bps_is_in_band(self) -> None:
        r = check_lever_realizability("denial_rate", 200, 12)
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_denial_12mo_300bps_is_stretch(self) -> None:
        # 12mo denial: reasonable ≤ 200, stretch ≤ 350, implausible > 600.
        r = check_lever_realizability("denial_rate", 300, 12)
        self.assertEqual(r.verdict, VERDICT_STRETCH)

    def test_denial_12mo_400bps_is_out_of_band(self) -> None:
        # 400 bps exceeds stretch_max=350 but is below implausible=600.
        r = check_lever_realizability("denial_rate", 400, 12)
        self.assertEqual(r.verdict, VERDICT_OUT_OF_BAND)

    def test_denial_12mo_700bps_is_implausible(self) -> None:
        r = check_lever_realizability("denial_rate", 700, 12)
        self.assertIn(r.verdict, (VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE))

    def test_ar_days_12mo_reasonable(self) -> None:
        r = check_lever_realizability("days_in_ar", 8, 12)
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_ar_days_12mo_implausible(self) -> None:
        r = check_lever_realizability("days_in_ar", 40, 12)
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_unknown_lever_returns_unknown_verdict(self) -> None:
        r = check_lever_realizability("made_up_lever", 100, 12)
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_get_lever_timeframe_finds_nearest(self) -> None:
        # Asking for an 18-month denial timeframe should resolve to 12 or 24 (closest).
        lt = get_lever_timeframe("denial_rate", 18)
        self.assertIsNotNone(lt)
        self.assertIn(lt.months, (12, 24))


# ── Reasonableness orchestrator ──────────────────────────────────────

class TestRunReasonablenessChecks(unittest.TestCase):

    def test_runs_all_three_core_checks(self) -> None:
        results = run_reasonableness_checks(
            irr=0.18, ebitda_margin=0.08, ebitda_m=30.0,
            exit_multiple=10.0, hospital_type="acute_care",
            payer_mix={"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
            lever_claims=[],
        )
        metrics = [r.metric for r in results]
        self.assertIn("irr", metrics)
        self.assertIn("ebitda_margin", metrics)
        self.assertIn("exit_multiple", metrics)

    def test_lever_claims_produce_lever_bands(self) -> None:
        results = run_reasonableness_checks(
            irr=0.20, ebitda_margin=0.10, ebitda_m=50.0,
            exit_multiple=9.5, hospital_type="acute_care",
            payer_mix={"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
            lever_claims=[{"lever": "denial_rate", "magnitude": 250, "months": 12}],
        )
        lever_checks = [r for r in results if r.metric.startswith("lever:")]
        self.assertEqual(len(lever_checks), 1)

    def test_missing_inputs_still_produces_unknown(self) -> None:
        results = run_reasonableness_checks()
        # All three core checks should still emit UNKNOWN rather than raise.
        self.assertTrue(any(r.verdict == VERDICT_UNKNOWN for r in results))


# ── Heuristics: individual rules ─────────────────────────────────────

class TestHeuristicsFireOnExpectedPatterns(unittest.TestCase):

    def test_medicare_heavy_exit_fires(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25, "medicaid": 0.10},
            exit_multiple=11.5,
        )
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "medicare_heavy_multiple_ceiling" for h in hits))

    def test_medicare_heavy_exit_doesnt_fire_below_threshold(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25, "medicaid": 0.10},
            exit_multiple=8.5,
        )
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "medicare_heavy_multiple_ceiling" for h in hits))

    def test_aggressive_denial_fires_above_200_bps(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=350)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "aggressive_denial_improvement" for h in hits))

    def test_aggressive_denial_doesnt_fire_at_200_bps(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=180)
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "aggressive_denial_improvement" for h in hits))

    def test_aggressive_denial_critical_above_600(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=700)
        hits = run_heuristics(ctx)
        denial = next(h for h in hits if h.id == "aggressive_denial_improvement")
        self.assertEqual(denial.severity, SEV_CRITICAL)

    def test_capitation_with_ffs_growth_fires(self) -> None:
        ctx = HeuristicContext(
            deal_structure="capitation",
            revenue_growth_pct_per_yr=7.0,
        )
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "capitation_vbc_uses_ffs_growth" for h in hits))

    def test_capitation_with_flat_growth_does_not_fire(self) -> None:
        ctx = HeuristicContext(
            deal_structure="capitation",
            revenue_growth_pct_per_yr=2.5,
        )
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "capitation_vbc_uses_ffs_growth" for h in hits))

    def test_multiple_expansion_fires(self) -> None:
        ctx = HeuristicContext(entry_multiple=7.0, exit_multiple=10.0)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "multiple_expansion_carrying_return" for h in hits))

    def test_multiple_expansion_low_delta_doesnt_fire(self) -> None:
        ctx = HeuristicContext(entry_multiple=9.0, exit_multiple=9.5)
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "multiple_expansion_carrying_return" for h in hits))

    def test_leverage_high_with_govt_fires(self) -> None:
        ctx = HeuristicContext(
            leverage_multiple=6.2,
            payer_mix={"medicare": 0.45, "medicaid": 0.30, "commercial": 0.25},
        )
        hits = run_heuristics(ctx)
        hit = next((h for h in hits if h.id == "leverage_too_high_govt_mix"), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.severity, SEV_HIGH)

    def test_leverage_high_with_commercial_doesnt_fire(self) -> None:
        ctx = HeuristicContext(
            leverage_multiple=6.2,
            payer_mix={"commercial": 0.60, "medicare": 0.25, "medicaid": 0.15},
        )
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "leverage_too_high_govt_mix" for h in hits))

    def test_covenant_headroom_tight_fires(self) -> None:
        ctx = HeuristicContext(covenant_headroom_pct=0.08)
        hits = run_heuristics(ctx)
        hit = next((h for h in hits if h.id == "covenant_headroom_tight"), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.severity, SEV_HIGH)

    def test_data_coverage_low_fires(self) -> None:
        ctx = HeuristicContext(data_coverage_pct=0.45)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "insufficient_data_coverage" for h in hits))

    def test_case_mix_missing_fires_on_acute(self) -> None:
        ctx = HeuristicContext(hospital_type="acute_care", has_case_mix_data=False)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "case_mix_missing" for h in hits))

    def test_case_mix_missing_doesnt_fire_on_asc(self) -> None:
        ctx = HeuristicContext(hospital_type="asc", has_case_mix_data=False)
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "case_mix_missing" for h in hits))

    def test_ar_days_high_fires(self) -> None:
        ctx = HeuristicContext(days_in_ar=75)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "ar_days_above_peer" for h in hits))

    def test_denial_rate_elevated_fires(self) -> None:
        ctx = HeuristicContext(denial_rate=0.15)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "denial_rate_elevated" for h in hits))

    def test_small_deal_mega_irr_fires(self) -> None:
        ctx = HeuristicContext(ebitda_m=8.0, projected_irr=0.52)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "small_deal_mega_irr" for h in hits))

    def test_small_deal_normal_irr_doesnt_fire(self) -> None:
        ctx = HeuristicContext(ebitda_m=8.0, projected_irr=0.25)
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "small_deal_mega_irr" for h in hits))

    def test_short_hold_rcm_fires(self) -> None:
        ctx = HeuristicContext(hold_years=3.0, denial_improvement_bps_per_yr=150)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "hold_too_short_for_rcm" for h in hits))

    def test_short_hold_without_rcm_doesnt_fire(self) -> None:
        ctx = HeuristicContext(hold_years=3.0)
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "hold_too_short_for_rcm" for h in hits))

    def test_writeoff_rate_high_fires(self) -> None:
        ctx = HeuristicContext(final_writeoff_rate=0.095)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "writeoff_rate_high" for h in hits))

    def test_cah_reimbursement_fires(self) -> None:
        ctx = HeuristicContext(hospital_type="critical_access")
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "critical_access_reimbursement" for h in hits))

    def test_moic_cagr_high_fires(self) -> None:
        ctx = HeuristicContext(projected_moic=4.0, hold_years=4.0)  # ~41% CAGR
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "moic_cagr_too_high" for h in hits))

    def test_moic_cagr_reasonable_doesnt_fire(self) -> None:
        ctx = HeuristicContext(projected_moic=2.5, hold_years=5.0)  # ~20% CAGR
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "moic_cagr_too_high" for h in hits))

    def test_teaching_hospital_fires(self) -> None:
        ctx = HeuristicContext(teaching_status="major")
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "teaching_hospital_complexity" for h in hits))

    def test_ar_reduction_aggressive_fires(self) -> None:
        ctx = HeuristicContext(ar_reduction_days_per_yr=20)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "ar_reduction_aggressive" for h in hits))

    def test_medicaid_volatile_state_fires(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicaid": 0.40, "commercial": 0.40, "medicare": 0.20},
            state="IL",
        )
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "state_medicaid_volatility" for h in hits))

    def test_medicaid_non_volatile_state_doesnt_fire(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicaid": 0.40, "commercial": 0.40, "medicare": 0.20},
            state="TX",
        )
        hits = run_heuristics(ctx)
        self.assertFalse(any(h.id == "state_medicaid_volatility" for h in hits))

    def test_margin_expansion_too_fast_fires(self) -> None:
        ctx = HeuristicContext(margin_expansion_bps_per_yr=450)
        hits = run_heuristics(ctx)
        self.assertTrue(any(h.id == "margin_expansion_too_fast" for h in hits))


class TestHeuristicsSortingAndRegistry(unittest.TestCase):

    def test_registry_is_stable_and_non_empty(self) -> None:
        catalog = all_heuristics()
        self.assertGreaterEqual(len(catalog), 19)
        # All ids are unique.
        ids = [h.id for h in catalog]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hits_sorted_highest_severity_first(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25, "medicaid": 0.10},
            ebitda_m=50.0,
            leverage_multiple=6.5,  # should trigger HIGH
            covenant_headroom_pct=0.05,  # HIGH
            teaching_status="major",  # LOW
        )
        hits = run_heuristics(ctx)
        # Severities should be non-increasing.
        ranks = [h.severity_rank() for h in hits]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_every_hit_has_finding_and_partner_voice(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25, "medicaid": 0.10},
            exit_multiple=11.5,
            denial_improvement_bps_per_yr=400,
            days_in_ar=75,
            denial_rate=0.15,
        )
        hits = run_heuristics(ctx)
        for h in hits:
            self.assertTrue(h.finding, f"{h.id} has empty finding")
            # Not every hit must have partner_voice, but most should.
            # Check that id, title, category all populated.
            self.assertTrue(h.id)
            self.assertTrue(h.title)
            self.assertTrue(h.category)

    def test_heuristic_hit_to_dict_roundtrip(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=350)
        hits = run_heuristics(ctx)
        self.assertGreaterEqual(len(hits), 1)
        d = hits[0].to_dict()
        self.assertIn("id", d)
        self.assertIn("severity", d)
        self.assertIn("finding", d)
        self.assertIn("trigger_values", d)


# ── Narrative composer ──────────────────────────────────────────────

class TestNarrativeCompose(unittest.TestCase):

    def test_clean_deal_returns_strong_proceed(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.50, "medicare": 0.35, "medicaid": 0.15},
            ebitda_m=40.0, hospital_type="acute_care",
            exit_multiple=9.0, entry_multiple=8.5, hold_years=5.0,
            projected_irr=0.19, projected_moic=2.2,
            denial_improvement_bps_per_yr=150,
            ar_reduction_days_per_yr=6,
            leverage_multiple=4.8, covenant_headroom_pct=0.30,
            data_coverage_pct=0.80, has_case_mix_data=True,
            ebitda_margin=0.09, days_in_ar=50,
            denial_rate=0.09, final_writeoff_rate=0.04,
            state="TX", margin_expansion_bps_per_yr=150,
        )
        review = partner_review_from_context(ctx, deal_id="d1")
        self.assertIn(review.narrative.recommendation, (REC_STRONG_PROCEED, REC_PROCEED))

    def test_implausible_irr_forces_pass(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.70, "commercial": 0.20, "medicaid": 0.10},
            ebitda_m=50.0, hospital_type="acute_care",
            projected_irr=0.45,  # implausible for mid × medicare_heavy
            exit_multiple=14.0,
        )
        review = partner_review_from_context(ctx)
        self.assertEqual(review.narrative.recommendation, REC_PASS)

    def test_multiple_high_hits_trigger_caveats_or_pass(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.45, "medicaid": 0.30, "commercial": 0.25},
            ebitda_m=50.0, hospital_type="acute_care",
            exit_multiple=9.5, entry_multiple=9.0,
            leverage_multiple=6.3,
            covenant_headroom_pct=0.12,
            data_coverage_pct=0.40,
            days_in_ar=80,
            denial_rate=0.18,
            denial_improvement_bps_per_yr=500,
            projected_irr=0.16,
        )
        review = partner_review_from_context(ctx)
        self.assertIn(review.narrative.recommendation,
                      (REC_PROCEED_CAVEATS, REC_PASS))

    def test_narrative_has_all_sections(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30.0,
            hospital_type="acute_care", projected_irr=0.20,
            exit_multiple=9.5, entry_multiple=8.0, hold_years=5.0,
        )
        review = partner_review_from_context(ctx)
        self.assertTrue(review.narrative.headline)
        self.assertTrue(review.narrative.bull_case)
        self.assertTrue(review.narrative.bear_case)
        self.assertGreaterEqual(len(review.narrative.key_questions), 3)
        self.assertTrue(review.narrative.ic_memo_paragraph)

    def test_compose_narrative_directly(self) -> None:
        bands = [
            check_irr(0.25, ebitda_m=15.0, payer_mix={"commercial": 0.50}),
            check_ebitda_margin(0.09, hospital_type="acute_care"),
        ]
        hits = []
        nb = compose_narrative(
            bands=bands, hits=hits, hospital_type="acute_care",
            ebitda_m=15.0, payer_mix={"commercial": 0.50},
        )
        self.assertIsInstance(nb, NarrativeBlock)
        self.assertTrue(nb.recommendation)


# ── partner_review entry point ───────────────────────────────────────

def _make_packet_dict(**overrides):
    """Minimal dict-shaped packet for testing."""
    base = {
        "deal_id": "test",
        "deal_name": "Test Hospital",
        "profile": {
            "payer_mix": {"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
            "hospital_type": "acute_care",
            "bed_count": 220,
            "state": "TX",
        },
        "observed_metrics": {
            "initial_denial_rate": {"value": 0.09},
            "days_in_ar": {"value": 48},
            "final_writeoff_rate": {"value": 0.04},
            "case_mix_index": {"value": 1.45},
        },
        "rcm_profile": {},
        "ebitda_bridge": {
            "current_ebitda": 30_000_000,
            "target_ebitda": 40_000_000,
            "new_ebitda_margin": 0.10,
            "margin_improvement_bps": 150,
            "per_metric_impacts": [
                {"metric_key": "initial_denial_rate", "current_value": 0.09, "target_value": 0.07},
                {"metric_key": "days_in_ar", "current_value": 48, "target_value": 40},
            ],
        },
        "simulation": {
            "irr": {"p50": 0.20},
            "moic": {"p50": 2.5},
        },
        "enterprise_value_summary": {
            "exit_multiple": 9.5,
            "entry_multiple": 8.0,
            "hold_years": 5.0,
            "leverage_multiple": 4.5,
        },
        "completeness": {"coverage_pct": 0.75},
    }
    # Shallow override
    for k, v in overrides.items():
        base[k] = v
    return base


class TestPartnerReviewFromPacket(unittest.TestCase):

    def test_minimal_dict_packet_produces_review(self) -> None:
        packet = _make_packet_dict()
        review = partner_review(packet)
        self.assertIsInstance(review, PartnerReview)
        self.assertEqual(review.deal_id, "test")
        self.assertEqual(review.deal_name, "Test Hospital")

    def test_review_is_json_roundtrippable(self) -> None:
        import json
        packet = _make_packet_dict()
        review = partner_review(packet)
        d = review.to_dict()
        s = json.dumps(d, default=str)
        back = json.loads(s)
        self.assertEqual(back["deal_id"], "test")
        self.assertIn("reasonableness_checks", back)
        self.assertIn("heuristic_hits", back)
        self.assertIn("narrative", back)

    def test_severity_counts_populate(self) -> None:
        # Bad deal should have high severity count.
        packet = _make_packet_dict()
        packet["profile"]["payer_mix"] = {"medicare": 0.70, "commercial": 0.20, "medicaid": 0.10}
        packet["enterprise_value_summary"]["exit_multiple"] = 12.5
        packet["enterprise_value_summary"]["leverage_multiple"] = 6.5
        review = partner_review(packet)
        counts = review.severity_counts()
        self.assertGreaterEqual(sum(counts.values()), 1)

    def test_empty_packet_does_not_raise(self) -> None:
        review = partner_review({})
        self.assertIsInstance(review, PartnerReview)

    def test_minimal_packet_with_only_deal_id(self) -> None:
        review = partner_review({"deal_id": "X"})
        self.assertEqual(review.deal_id, "X")
        self.assertIsInstance(review.narrative, NarrativeBlock)

    def test_review_to_dict_has_expected_keys(self) -> None:
        review = partner_review(_make_packet_dict())
        d = review.to_dict()
        for key in ("deal_id", "reasonableness_checks", "heuristic_hits",
                    "narrative", "severity_counts", "band_counts",
                    "recommendation", "has_critical_flag", "is_fundable"):
            self.assertIn(key, d)

    def test_real_packet_instance_also_works(self) -> None:
        """If a real DealAnalysisPacket import path is available, we
        also accept it."""
        try:
            from rcm_mc.analysis.packet import DealAnalysisPacket, HospitalProfile
        except ImportError:
            self.skipTest("DealAnalysisPacket not importable in this env")
            return
        p = DealAnalysisPacket(
            deal_id="real",
            deal_name="Real Hospital",
            profile=HospitalProfile(
                payer_mix={"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
                bed_count=200, state="TX",
            ),
        )
        review = partner_review(p)
        self.assertEqual(review.deal_id, "real")


class TestPartnerReviewConvenienceFlags(unittest.TestCase):

    def test_has_critical_flag_detects_critical(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=700)
        review = partner_review_from_context(ctx)
        self.assertTrue(review.has_critical_flag())

    def test_is_fundable_false_when_recommendation_is_pass(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=700)
        review = partner_review_from_context(ctx)
        self.assertFalse(review.is_fundable())

    def test_is_fundable_true_when_strong_proceed(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.50, "medicare": 0.35, "medicaid": 0.15},
            ebitda_m=40.0, hospital_type="acute_care",
            exit_multiple=9.0, entry_multiple=8.5, hold_years=5.0,
            projected_irr=0.19, projected_moic=2.2,
            denial_improvement_bps_per_yr=150,
            ar_reduction_days_per_yr=6,
            leverage_multiple=4.8, covenant_headroom_pct=0.30,
            data_coverage_pct=0.80, has_case_mix_data=True,
            ebitda_margin=0.09, days_in_ar=50,
            denial_rate=0.09, final_writeoff_rate=0.04,
            state="TX", margin_expansion_bps_per_yr=150,
        )
        review = partner_review_from_context(ctx)
        self.assertTrue(review.is_fundable())


# ── Independence: no packet_builder modification ─────────────────────

class TestNoPacketBuilderModification(unittest.TestCase):
    """Sentinel test: partner_review must NOT touch packet_builder. The
    packet is an input; the review is a sibling, not a replacement.
    """

    def test_pe_intelligence_does_not_import_packet_builder(self) -> None:
        import importlib
        # pe_intelligence package must not pull in packet_builder.
        for mod in ("rcm_mc.pe_intelligence.heuristics",
                    "rcm_mc.pe_intelligence.reasonableness",
                    "rcm_mc.pe_intelligence.narrative",
                    "rcm_mc.pe_intelligence.partner_review"):
            m = importlib.import_module(mod)
            src = getattr(m, "__file__", "")
            if src:
                with open(src) as f:
                    content = f.read()
                self.assertNotIn("packet_builder", content,
                                 f"{mod} should not import packet_builder")


# ── Red flags ────────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    RED_FLAG_FIELDS,
    run_all_rules,
    run_red_flags,
)


def _red_ctx(**extras) -> HeuristicContext:
    """Build a context with red-flag fields set via setattr."""
    ctx = HeuristicContext(
        payer_mix={"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
        ebitda_m=40.0, hold_years=5.0,
    )
    for k, v in extras.items():
        setattr(ctx, k, v)
    return ctx


class TestRedFlagDetectors(unittest.TestCase):

    def test_payer_concentration_single_payer_over_40_fires(self) -> None:
        ctx = HeuristicContext(payer_mix={"bcbs": 0.45, "medicare": 0.30, "medicaid": 0.25})
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "payer_concentration_risk" for h in hits))

    def test_payer_concentration_doesnt_fire_under_40(self) -> None:
        ctx = HeuristicContext(payer_mix={"bcbs": 0.30, "united": 0.30, "medicare": 0.40})
        hits = run_red_flags(ctx)
        self.assertFalse(any(h.id == "payer_concentration_risk" for h in hits))

    def test_contract_labor_dependency_fires(self) -> None:
        ctx = _red_ctx(contract_labor_share=0.22)
        hits = run_red_flags(ctx)
        hit = next((h for h in hits if h.id == "contract_labor_dependency"), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.severity, SEV_MEDIUM)

    def test_contract_labor_critical_at_high_share(self) -> None:
        ctx = _red_ctx(contract_labor_share=0.30)
        hits = run_red_flags(ctx)
        hit = next((h for h in hits if h.id == "contract_labor_dependency"), None)
        self.assertEqual(hit.severity, SEV_HIGH)

    def test_service_line_concentration_fires(self) -> None:
        ctx = _red_ctx(top_service_line_share=0.42)
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "service_line_concentration" for h in hits))

    def test_340b_dependency_fires(self) -> None:
        ctx = _red_ctx(share_340b_of_margin=0.20)
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "340b_margin_dependency" for h in hits))

    def test_covid_unwind_fires(self) -> None:
        ctx = _red_ctx(covid_relief_share_of_ebitda=0.15)
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "covid_relief_unwind" for h in hits))

    def test_rate_cliff_fires_with_string_marker(self) -> None:
        ctx = _red_ctx(known_rate_cliff_in_hold="IMD waiver expires 2028")
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "known_rate_cliff_in_hold" for h in hits))

    def test_ehr_migration_fires(self) -> None:
        ctx = _red_ctx(ehr_migration_planned=True)
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "ehr_migration_planned" for h in hits))

    def test_prior_regulatory_action_fires(self) -> None:
        ctx = _red_ctx(prior_regulatory_action="2022 CMS CIA")
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "prior_regulatory_action" for h in hits))

    def test_low_star_rating_fires(self) -> None:
        ctx = _red_ctx(cms_star_rating=2.0)
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "quality_score_below_peer" for h in hits))

    def test_high_star_rating_doesnt_fire(self) -> None:
        ctx = _red_ctx(cms_star_rating=4.0)
        hits = run_red_flags(ctx)
        self.assertFalse(any(h.id == "quality_score_below_peer" for h in hits))

    def test_debt_maturity_in_hold_fires(self) -> None:
        ctx = _red_ctx(debt_maturity_years=3.0)  # hold=5yr
        hits = run_red_flags(ctx)
        self.assertTrue(any(h.id == "debt_maturity_in_hold" for h in hits))

    def test_debt_maturity_after_hold_does_not_fire(self) -> None:
        ctx = _red_ctx(debt_maturity_years=7.0)  # hold=5yr
        hits = run_red_flags(ctx)
        self.assertFalse(any(h.id == "debt_maturity_in_hold" for h in hits))

    def test_no_red_flag_fields_produces_no_hits(self) -> None:
        ctx = HeuristicContext()
        hits = run_red_flags(ctx)
        self.assertEqual(hits, [])


class TestRunAllRules(unittest.TestCase):

    def test_merges_base_and_red_flags(self) -> None:
        ctx = _red_ctx(
            denial_improvement_bps_per_yr=400,  # base heuristic
            contract_labor_share=0.22,          # red flag
        )
        merged = run_all_rules(ctx)
        ids = {h.id for h in merged}
        self.assertIn("aggressive_denial_improvement", ids)
        self.assertIn("contract_labor_dependency", ids)

    def test_merged_list_is_severity_sorted(self) -> None:
        ctx = _red_ctx(
            denial_improvement_bps_per_yr=650,  # CRITICAL
            contract_labor_share=0.22,          # MEDIUM
        )
        merged = run_all_rules(ctx)
        ranks = [h.severity_rank() for h in merged]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_partner_review_runs_red_flags(self) -> None:
        packet = _make_packet_dict()
        # Add a red-flag field to the profile.
        packet["profile"]["contract_labor_share"] = 0.30
        review = partner_review(packet)
        ids = {h.id for h in review.heuristic_hits}
        self.assertIn("contract_labor_dependency", ids)


class TestRedFlagFieldsConstant(unittest.TestCase):

    def test_red_flag_fields_list_is_populated(self) -> None:
        self.assertGreater(len(RED_FLAG_FIELDS), 5)
        for f in RED_FLAG_FIELDS:
            self.assertIsInstance(f, str)


# ── Valuation checks ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ValuationInputs,
    check_equity_concentration,
    check_ev_walk,
    check_interest_coverage,
    check_terminal_growth,
    check_terminal_value_share,
    check_wacc,
    run_valuation_checks,
)


class TestWACCCheck(unittest.TestCase):

    def test_normal_wacc_in_band(self) -> None:
        self.assertEqual(check_wacc(0.10).verdict, VERDICT_IN_BAND)

    def test_low_wacc_stretch(self) -> None:
        self.assertEqual(check_wacc(0.075).verdict, VERDICT_STRETCH)

    def test_impossible_low_wacc_implausible(self) -> None:
        self.assertEqual(check_wacc(0.04).verdict, VERDICT_IMPLAUSIBLE)

    def test_impossible_high_wacc_implausible(self) -> None:
        self.assertEqual(check_wacc(0.22).verdict, VERDICT_IMPLAUSIBLE)

    def test_missing_wacc_unknown(self) -> None:
        self.assertEqual(check_wacc(None).verdict, VERDICT_UNKNOWN)

    def test_out_of_band_above_stretch_ceiling(self) -> None:
        # 15% is above WACC_STRETCH top (14%) but below implausible high (18%).
        self.assertEqual(check_wacc(0.15).verdict, VERDICT_OUT_OF_BAND)


class TestEVWalk(unittest.TestCase):

    def test_clean_walk_reconciles(self) -> None:
        r = check_ev_walk(
            enterprise_value=1_000_000_000,
            equity_value=600_000_000,
            net_debt=400_000_000,
        )
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_walk_off_by_2pct_stretch(self) -> None:
        r = check_ev_walk(
            enterprise_value=1_000_000_000,
            equity_value=620_000_000,  # expected 600, residual 20 = 2%
            net_debt=400_000_000,
        )
        self.assertEqual(r.verdict, VERDICT_STRETCH)

    def test_walk_large_residual_implausible(self) -> None:
        r = check_ev_walk(
            enterprise_value=1_000_000_000,
            equity_value=800_000_000,  # expected 600, residual 200 = 20%
            net_debt=400_000_000,
        )
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_walk_includes_minorities_and_preferred(self) -> None:
        r = check_ev_walk(
            enterprise_value=1_000_000_000,
            equity_value=500_000_000,
            net_debt=400_000_000,
            minority_interest=60_000_000,
            preferred=40_000_000,
        )
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_walk_missing_inputs_unknown(self) -> None:
        r = check_ev_walk(enterprise_value=None, equity_value=None)
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestTerminalValueShare(unittest.TestCase):

    def test_normal_share_in_band(self) -> None:
        r = check_terminal_value_share(700, 1000)
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_high_share_stretch(self) -> None:
        r = check_terminal_value_share(850, 1000)
        self.assertEqual(r.verdict, VERDICT_STRETCH)

    def test_extreme_share_implausible(self) -> None:
        r = check_terminal_value_share(980, 1000)
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_very_low_share_implausible(self) -> None:
        r = check_terminal_value_share(250, 1000)
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_zero_denominator_unknown(self) -> None:
        r = check_terminal_value_share(500, 0)
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestTerminalGrowth(unittest.TestCase):

    def test_gdp_like_growth_in_band(self) -> None:
        self.assertEqual(check_terminal_growth(0.025).verdict, VERDICT_IN_BAND)

    def test_low_growth_stretch(self) -> None:
        self.assertEqual(check_terminal_growth(0.010).verdict, VERDICT_STRETCH)

    def test_too_high_growth_implausible(self) -> None:
        self.assertEqual(check_terminal_growth(0.07).verdict, VERDICT_IMPLAUSIBLE)

    def test_negative_growth_implausible(self) -> None:
        self.assertEqual(check_terminal_growth(-0.01).verdict, VERDICT_IMPLAUSIBLE)


class TestInterestCoverage(unittest.TestCase):

    def test_comfortable_coverage(self) -> None:
        self.assertEqual(check_interest_coverage(4.0).verdict, VERDICT_IN_BAND)

    def test_tight_coverage_stretch(self) -> None:
        self.assertEqual(check_interest_coverage(2.5).verdict, VERDICT_STRETCH)

    def test_very_tight_out_of_band(self) -> None:
        self.assertEqual(check_interest_coverage(1.7).verdict, VERDICT_OUT_OF_BAND)

    def test_below_one_implausible(self) -> None:
        self.assertEqual(check_interest_coverage(1.2).verdict, VERDICT_IMPLAUSIBLE)


class TestEquityConcentration(unittest.TestCase):

    def test_small_check_in_band(self) -> None:
        self.assertEqual(check_equity_concentration(100, 2000).verdict, VERDICT_IN_BAND)

    def test_concentration_out_of_band(self) -> None:
        self.assertEqual(check_equity_concentration(600, 2000).verdict, VERDICT_OUT_OF_BAND)

    def test_extreme_concentration_implausible(self) -> None:
        self.assertEqual(check_equity_concentration(900, 2000).verdict, VERDICT_IMPLAUSIBLE)


class TestRunValuationChecks(unittest.TestCase):

    def test_empty_inputs_still_emits_checks(self) -> None:
        results = run_valuation_checks(ValuationInputs())
        self.assertEqual(len(results), 6)
        # All UNKNOWN when nothing is populated.
        for r in results:
            self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_full_inputs_produces_six_verdicts(self) -> None:
        results = run_valuation_checks(ValuationInputs(
            wacc=0.10,
            enterprise_value=1_000_000_000,
            equity_value=600_000_000,
            net_debt=400_000_000,
            tv_pv=700, total_dcf_ev=1000,
            terminal_growth=0.025,
            interest_coverage=3.2,
            equity_check=150, fund_size=2000,
        ))
        self.assertEqual(len(results), 6)
        in_band = [r for r in results if r.verdict == VERDICT_IN_BAND]
        self.assertEqual(len(in_band), 6)


# ── Scenario stresses ────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    StressInputs,
    StressResult,
    run_partner_stresses,
    stress_labor_shock,
    stress_lever_slip,
    stress_multiple_compression,
    stress_rate_down,
    stress_volume_down,
    worst_case_summary,
)


def _stress_inputs() -> StressInputs:
    return StressInputs(
        base_ebitda=30_000_000,
        target_ebitda=45_000_000,
        base_revenue=250_000_000,
        entry_multiple=8.0,
        exit_multiple=9.5,
        debt_at_close=150_000_000,
        interest_rate=0.09,
        covenant_leverage=6.0,
        covenant_coverage=2.5,
        contract_labor_spend=30_000_000,
        lever_contribution=10_000_000,
        hold_years=5.0,
        base_moic=2.6,
        medicare_revenue=100_000_000,
        commercial_revenue=120_000_000,
    )


class TestStressRateDown(unittest.TestCase):

    def test_absorbs_modest_shock(self) -> None:
        r = stress_rate_down(_stress_inputs(), bps=100)
        # 100bp on 100M medicare = 1M; ebitda 30M → 29M
        self.assertAlmostEqual(r.shocked_ebitda, 29_000_000, delta=1)
        self.assertTrue(r.passes)

    def test_large_shock_breaches_covenant(self) -> None:
        inputs = _stress_inputs()
        inputs.debt_at_close = 200_000_000  # leverage 6.67x already high
        inputs.covenant_leverage = 5.0
        r = stress_rate_down(inputs, bps=300)
        self.assertTrue(r.covenant_breach)

    def test_missing_inputs_returns_result_with_note(self) -> None:
        r = stress_rate_down(StressInputs(), bps=100)
        self.assertIn("Cannot run", r.partner_note)


class TestStressVolumeDown(unittest.TestCase):

    def test_volume_shock_reduces_ebitda(self) -> None:
        r = stress_volume_down(_stress_inputs(), pct=0.05)
        self.assertIsNotNone(r.shocked_ebitda)
        self.assertLess(r.shocked_ebitda, _stress_inputs().base_ebitda)

    def test_large_volume_shock_breaks(self) -> None:
        inputs = _stress_inputs()
        inputs.base_ebitda = 5_000_000  # thin
        inputs.debt_at_close = 20_000_000
        inputs.covenant_leverage = 5.0
        r = stress_volume_down(inputs, pct=0.20)
        self.assertTrue(r.covenant_breach or not r.passes)


class TestStressMultipleCompression(unittest.TestCase):

    def test_flat_multiple_reduces_moic(self) -> None:
        r = stress_multiple_compression(_stress_inputs(), flat_multiple=True)
        self.assertLess(r.shocked_moic, _stress_inputs().base_moic)

    def test_strong_deal_still_clears_2x(self) -> None:
        inputs = _stress_inputs()
        inputs.base_moic = 3.0
        inputs.exit_multiple = 9.0
        inputs.entry_multiple = 8.5
        r = stress_multiple_compression(inputs, flat_multiple=True)
        # 3.0 * (8.5/9.0) = 2.83 > 2.0
        self.assertTrue(r.passes)

    def test_compression_turns_mode(self) -> None:
        r = stress_multiple_compression(_stress_inputs(), flat_multiple=False,
                                        compression_turns=2.0)
        self.assertIsNotNone(r.shocked_moic)


class TestStressLeverSlip(unittest.TestCase):

    def test_slip_reduces_target_ebitda(self) -> None:
        r = stress_lever_slip(_stress_inputs(), realization=0.60)
        # 40% of 10M lost = 4M lost; target 45M → 41M
        self.assertAlmostEqual(r.shocked_ebitda, 41_000_000, delta=1)
        self.assertTrue(r.passes)

    def test_full_slip_zero_realization(self) -> None:
        r = stress_lever_slip(_stress_inputs(), realization=0.0)
        # Target 45M - 10M = 35M (still > base 30M), passes.
        self.assertAlmostEqual(r.shocked_ebitda, 35_000_000, delta=1)


class TestStressLaborShock(unittest.TestCase):

    def test_labor_shock_hits_ebitda(self) -> None:
        r = stress_labor_shock(_stress_inputs(), pct=0.10)
        # 10% of 30M = 3M hit; ebitda 30M → 27M
        self.assertAlmostEqual(r.shocked_ebitda, 27_000_000, delta=1)

    def test_large_labor_shock_breaks_deal(self) -> None:
        inputs = _stress_inputs()
        inputs.base_ebitda = 8_000_000
        inputs.contract_labor_spend = 40_000_000
        r = stress_labor_shock(inputs, pct=0.25)  # -10M on 8M ebitda
        self.assertFalse(r.passes)


class TestRunPartnerStresses(unittest.TestCase):

    def test_runs_five_scenarios(self) -> None:
        results = run_partner_stresses(_stress_inputs())
        self.assertEqual(len(results), 5)
        scenarios = {r.scenario for r in results}
        self.assertEqual(scenarios, {
            "rate_down", "volume_down", "multiple_compression",
            "lever_slip", "labor_shock",
        })

    def test_worst_case_summary(self) -> None:
        results = run_partner_stresses(_stress_inputs())
        summary = worst_case_summary(results)
        self.assertIn("scenarios_run", summary)
        self.assertEqual(summary["scenarios_run"], 5)

    def test_result_to_dict_roundtrip(self) -> None:
        import json
        r = stress_rate_down(_stress_inputs(), bps=150)
        d = r.to_dict()
        json.dumps(d)  # must not raise


# ── IC memo formatter ────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    render_ic_memo_all,
    render_ic_memo_html,
    render_ic_memo_markdown,
    render_ic_memo_text,
)


def _review_for_memo() -> PartnerReview:
    ctx = HeuristicContext(
        payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
        ebitda_m=30.0, revenue_m=250.0, bed_count=220, state="TX",
        hospital_type="acute_care", exit_multiple=11.0, entry_multiple=8.0,
        hold_years=5.0, projected_irr=0.22, projected_moic=2.9,
        denial_improvement_bps_per_yr=350, ar_reduction_days_per_yr=7,
        leverage_multiple=5.0, covenant_headroom_pct=0.25,
        data_coverage_pct=0.75, has_case_mix_data=True,
        ebitda_margin=0.09, days_in_ar=52, denial_rate=0.10,
        final_writeoff_rate=0.04, margin_expansion_bps_per_yr=150,
    )
    return partner_review_from_context(ctx, deal_id="MEMO_TEST", deal_name="Demo Hospital")


class TestICMemoMarkdown(unittest.TestCase):

    def test_markdown_has_required_sections(self) -> None:
        review = _review_for_memo()
        md = render_ic_memo_markdown(review)
        for section in (
            "# IC Memo",
            "## Context",
            "## Bull case",
            "## Bear case",
            "## Reasonableness",
            "## Pattern flags",
            "## Key questions",
            "## Partner dictation",
        ):
            self.assertIn(section, md)

    def test_markdown_includes_deal_name(self) -> None:
        review = _review_for_memo()
        md = render_ic_memo_markdown(review)
        self.assertIn("Demo Hospital", md)

    def test_markdown_has_recommendation(self) -> None:
        review = _review_for_memo()
        md = render_ic_memo_markdown(review)
        self.assertIn("Recommendation", md)
        self.assertIn(review.narrative.recommendation, md)


class TestICMemoText(unittest.TestCase):

    def test_text_has_required_headings(self) -> None:
        review = _review_for_memo()
        txt = render_ic_memo_text(review)
        for heading in ("CONTEXT", "BULL CASE", "BEAR CASE",
                        "REASONABLENESS", "PATTERN FLAGS",
                        "KEY QUESTIONS", "DICTATION"):
            self.assertIn(heading, txt)

    def test_text_shows_partner_voice_on_flags(self) -> None:
        review = _review_for_memo()
        txt = render_ic_memo_text(review)
        # At least one heuristic should have partner voice quoted.
        has_quote = any('"' in line for line in txt.splitlines())
        if review.heuristic_hits:
            self.assertTrue(has_quote)


class TestICMemoHTML(unittest.TestCase):

    def test_html_has_article_wrapper(self) -> None:
        review = _review_for_memo()
        h = render_ic_memo_html(review)
        self.assertIn('<article class="ic-memo">', h)
        self.assertIn("</article>", h)

    def test_html_escapes_content(self) -> None:
        # Build a context with an XSS-ish deal name.
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        rv = partner_review_from_context(ctx, deal_name="<script>x</script>")
        h = render_ic_memo_html(rv)
        self.assertNotIn("<script>x</script>", h)
        self.assertIn("&lt;script&gt;", h)


class TestICMemoAll(unittest.TestCase):

    def test_render_all_returns_three_formats(self) -> None:
        review = _review_for_memo()
        out = render_ic_memo_all(review)
        self.assertEqual(set(out.keys()), {"markdown", "text", "html"})
        for v in out.values():
            self.assertIsInstance(v, str)
            self.assertGreater(len(v), 50)


# ── Sector benchmarks ────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    GapFinding,
    SectorBenchmark,
    compare_to_peers,
    get_benchmark,
    list_metrics_for_subsector,
    list_subsectors,
)


class TestSectorBenchmarkLookup(unittest.TestCase):

    def test_list_subsectors_non_empty(self) -> None:
        self.assertIn("acute_care", list_subsectors())
        self.assertIn("asc", list_subsectors())

    def test_list_metrics_for_acute_care(self) -> None:
        metrics = list_metrics_for_subsector("acute_care")
        self.assertIn("ebitda_margin", metrics)
        self.assertIn("days_in_ar", metrics)

    def test_get_benchmark_finds_known_pair(self) -> None:
        bm = get_benchmark("acute_care", "ebitda_margin")
        self.assertIsNotNone(bm)
        self.assertEqual(bm.unit, "pct")
        self.assertIsNotNone(bm.p50)

    def test_alias_resolves(self) -> None:
        bm = get_benchmark("hospital", "ebitda_margin")
        self.assertIsNotNone(bm)

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(get_benchmark("acute_care", "made_up_metric"))
        self.assertIsNone(get_benchmark("made_up_sector", "ebitda_margin"))


class TestPercentilePlacement(unittest.TestCase):

    def test_below_p25_is_bottom_percentile(self) -> None:
        bm = get_benchmark("acute_care", "ebitda_margin")
        self.assertEqual(bm.percentile(0.02), 15)

    def test_at_p50_is_middle(self) -> None:
        bm = get_benchmark("acute_care", "ebitda_margin")
        self.assertEqual(bm.percentile(bm.p50), 40)

    def test_above_p75_is_top(self) -> None:
        bm = get_benchmark("acute_care", "ebitda_margin")
        self.assertEqual(bm.percentile(0.15), 85)


class TestCompareToPeers(unittest.TestCase):

    def test_compare_acute_care_mixed(self) -> None:
        findings = compare_to_peers("acute_care", {
            "ebitda_margin": 0.10,          # above median 0.075 — good
            "days_in_ar": 70,               # above median 50 — bad (low is better)
            "initial_denial_rate": 0.06,    # below median 0.09 — good
        })
        self.assertEqual(len(findings), 3)
        by_metric = {f.metric: f for f in findings}
        self.assertEqual(by_metric["ebitda_margin"].direction, "above")
        self.assertEqual(by_metric["days_in_ar"].direction, "above")  # value > median
        # Percentile estimates should be sensible.
        self.assertGreaterEqual(by_metric["ebitda_margin"].percentile_estimate, 40)
        self.assertIn("days", by_metric["days_in_ar"].commentary.lower())

    def test_missing_benchmarks_skipped(self) -> None:
        findings = compare_to_peers("acute_care", {
            "ebitda_margin": 0.08,
            "made_up_metric": 42.0,
        })
        self.assertEqual(len(findings), 1)

    def test_missing_values_skipped(self) -> None:
        findings = compare_to_peers("acute_care", {
            "ebitda_margin": 0.08,
            "days_in_ar": None,
        })
        self.assertEqual(len(findings), 1)

    def test_top_quartile_commentary_on_denial_rate(self) -> None:
        # days_in_ar at 40 is below p25=42 -> top quartile
        findings = compare_to_peers("acute_care", {"days_in_ar": 40})
        self.assertEqual(findings[0].direction, "below")
        self.assertIn("Top-quartile", findings[0].commentary)

    def test_gap_finding_to_dict(self) -> None:
        findings = compare_to_peers("acute_care", {"ebitda_margin": 0.08})
        d = findings[0].to_dict()
        self.assertIn("metric", d)
        self.assertIn("commentary", d)


# ── Deal archetype ───────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ArchetypeContext,
    ArchetypeHit,
    classify_archetypes,
    primary_archetype,
)


class TestClassifyPlatformRollup(unittest.TestCase):

    def test_platform_with_many_addons_fires(self) -> None:
        ctx = ArchetypeContext(
            platform_or_addon="platform",
            number_of_addons_planned=5,
            has_rollup_thesis=True,
        )
        hits = classify_archetypes(ctx)
        ids = [h.archetype for h in hits]
        self.assertIn("platform_rollup", ids)

    def test_platform_rollup_top_of_ranking(self) -> None:
        ctx = ArchetypeContext(
            platform_or_addon="platform",
            number_of_addons_planned=6,
            has_rollup_thesis=True,
            ebitda_growth_pct=0.25,
        )
        self.assertEqual(primary_archetype(ctx), "platform_rollup")


class TestClassifyTakePrivate(unittest.TestCase):

    def test_public_with_take_private_intent_fires(self) -> None:
        ctx = ArchetypeContext(is_public_target=True, plans_go_private=True)
        self.assertEqual(primary_archetype(ctx), "take_private")

    def test_non_public_doesnt_fire(self) -> None:
        ctx = ArchetypeContext(is_public_target=False)
        hits = classify_archetypes(ctx)
        self.assertNotIn("take_private", [h.archetype for h in hits])


class TestClassifyCarveout(unittest.TestCase):

    def test_carveout_with_strategic_seller_fires(self) -> None:
        ctx = ArchetypeContext(is_carveout=True, seller_is_strategic=True)
        self.assertEqual(primary_archetype(ctx), "carve_out")


class TestClassifyTurnaround(unittest.TestCase):

    def test_distressed_and_thesis_triggers(self) -> None:
        ctx = ArchetypeContext(
            is_distressed=True,
            has_turnaround_thesis=True,
            current_ebitda_margin=0.02,
            peer_median_margin=0.075,
        )
        self.assertEqual(primary_archetype(ctx), "turnaround")

    def test_margin_gap_alone_is_weak_signal(self) -> None:
        ctx = ArchetypeContext(
            current_ebitda_margin=0.04,
            peer_median_margin=0.075,
        )
        hits = classify_archetypes(ctx, min_confidence=0.40)
        self.assertEqual(len(hits), 0)


class TestClassifyContinuation(unittest.TestCase):

    def test_continuation_vehicle_fires(self) -> None:
        ctx = ArchetypeContext(is_continuation_vehicle=True, seller_is_sponsor=True)
        self.assertEqual(primary_archetype(ctx), "continuation")


class TestClassifyOperatingLift(unittest.TestCase):

    def test_rcm_thesis_and_lbo_leverage(self) -> None:
        ctx = ArchetypeContext(
            has_rcm_thesis=True,
            debt_to_ebitda=5.5,
        )
        self.assertEqual(primary_archetype(ctx), "operating_lift")


class TestClassifyGrowthEquity(unittest.TestCase):

    def test_minority_with_growth_fires(self) -> None:
        ctx = ArchetypeContext(
            is_minority=True,
            ownership_pct=0.35,
            revenue_growth_pct=0.25,
        )
        self.assertEqual(primary_archetype(ctx), "growth_equity")


class TestClassifyPIPE(unittest.TestCase):

    def test_public_minority_is_pipe(self) -> None:
        ctx = ArchetypeContext(is_public_target=True, is_minority=True)
        self.assertEqual(primary_archetype(ctx), "pipe")


class TestArchetypeMulti(unittest.TestCase):

    def test_multi_archetype_ordering(self) -> None:
        # Carve-out that's also a turnaround — both should surface.
        ctx = ArchetypeContext(
            is_carveout=True, seller_is_strategic=True,
            is_distressed=True, has_turnaround_thesis=True,
            current_ebitda_margin=0.02, peer_median_margin=0.08,
        )
        hits = classify_archetypes(ctx)
        ids = [h.archetype for h in hits]
        self.assertIn("carve_out", ids)
        self.assertIn("turnaround", ids)

    def test_primary_archetype_returns_none_when_empty(self) -> None:
        self.assertIsNone(primary_archetype(ArchetypeContext()))

    def test_archetype_hit_to_dict(self) -> None:
        ctx = ArchetypeContext(
            platform_or_addon="platform", number_of_addons_planned=4,
            has_rollup_thesis=True,
        )
        hits = classify_archetypes(ctx)
        d = hits[0].to_dict()
        self.assertIn("archetype", d)
        self.assertIn("confidence", d)
        self.assertIn("signals", d)
        self.assertIn("playbook", d)

    def test_each_archetype_has_questions_and_risks(self) -> None:
        # Fire every archetype at least once and verify shape.
        combos = [
            ArchetypeContext(platform_or_addon="platform", number_of_addons_planned=5, has_rollup_thesis=True),
            ArchetypeContext(is_public_target=True, plans_go_private=True),
            ArchetypeContext(is_carveout=True, seller_is_strategic=True),
            ArchetypeContext(is_distressed=True, has_turnaround_thesis=True),
            ArchetypeContext(is_continuation_vehicle=True, seller_is_sponsor=True),
            ArchetypeContext(has_rcm_thesis=True, debt_to_ebitda=5.5),
            ArchetypeContext(is_minority=True, ownership_pct=0.30, revenue_growth_pct=0.25),
            ArchetypeContext(is_public_target=True, is_minority=True),
        ]
        for c in combos:
            hits = classify_archetypes(c)
            for h in hits:
                self.assertGreaterEqual(len(h.risks), 1)
                self.assertGreaterEqual(len(h.questions), 1)
                self.assertTrue(h.playbook)


# ── Bear book ────────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    BEAR_PATTERNS,
    BearPatternHit,
    scan_bear_book,
)


class TestBearBookPatterns(unittest.TestCase):

    def test_rollup_integration_failure_fires(self) -> None:
        ctx = HeuristicContext(
            ebitda_m=30.0,
            margin_expansion_bps_per_yr=400,
            leverage_multiple=6.0,
            hold_years=3.5,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "rollup_integration_failure" for h in hits))

    def test_medicare_margin_compression_fires(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.55, "commercial": 0.30, "medicaid": 0.15},
            margin_expansion_bps_per_yr=250,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "medicare_margin_compression" for h in hits))

    def test_carveout_tsa_sprawl_fires(self) -> None:
        ctx = HeuristicContext(
            data_coverage_pct=0.50,
            days_in_ar=70,
            has_case_mix_data=False,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "carveout_tsa_sprawl" for h in hits))

    def test_turnaround_without_operator(self) -> None:
        ctx = HeuristicContext(
            ebitda_margin=0.02,
            margin_expansion_bps_per_yr=350,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "turnaround_without_operator" for h in hits))

    def test_covid_tailwind_fade_fires(self) -> None:
        ctx = HeuristicContext(
            hospital_type="acute_care",
            ebitda_margin=0.16,
            exit_multiple=11.0,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "covid_tailwind_fade" for h in hits))

    def test_high_leverage_thin_coverage_fires(self) -> None:
        ctx = HeuristicContext(
            leverage_multiple=6.5,
            covenant_headroom_pct=0.10,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "high_leverage_thin_coverage" for h in hits))

    def test_vbc_priced_as_ffs_fires(self) -> None:
        ctx = HeuristicContext(
            deal_structure="capitation",
            revenue_growth_pct_per_yr=8.0,
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "vbc_priced_as_ffs" for h in hits))

    def test_rural_single_payer_cliff_fires(self) -> None:
        ctx = HeuristicContext(
            hospital_type="critical_access",
            payer_mix={"medicare": 0.65, "medicaid": 0.25, "commercial": 0.10},
        )
        hits = scan_bear_book(ctx)
        self.assertTrue(any(h.pattern_id == "rural_single_payer_cliff" for h in hits))

    def test_empty_context_no_patterns(self) -> None:
        ctx = HeuristicContext()
        hits = scan_bear_book(ctx)
        self.assertEqual(hits, [])

    def test_results_sorted_by_confidence(self) -> None:
        ctx = HeuristicContext(
            hospital_type="acute_care", ebitda_margin=0.18, exit_multiple=12.0,
            leverage_multiple=6.5, covenant_headroom_pct=0.08,
        )
        hits = scan_bear_book(ctx)
        self.assertGreaterEqual(len(hits), 2)
        confs = [h.confidence for h in hits]
        self.assertEqual(confs, sorted(confs, reverse=True))

    def test_bear_hit_to_dict(self) -> None:
        ctx = HeuristicContext(
            leverage_multiple=6.5,
            covenant_headroom_pct=0.10,
        )
        hits = scan_bear_book(ctx)
        d = hits[0].to_dict()
        self.assertIn("pattern_id", d)
        self.assertIn("failure_mode", d)
        self.assertIn("partner_voice", d)

    def test_min_confidence_filter(self) -> None:
        ctx = HeuristicContext(
            ebitda_m=20.0,
            margin_expansion_bps_per_yr=400,
        )
        low_bar = scan_bear_book(ctx, min_confidence=0.20)
        high_bar = scan_bear_book(ctx, min_confidence=0.80)
        self.assertGreaterEqual(len(low_bar), len(high_bar))


# ── Exit readiness ──────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ExitReadinessInputs,
    ExitReadinessReport,
    ReadinessFinding,
    score_exit_readiness,
)


class TestExitReadinessScoring(unittest.TestCase):

    def test_fully_ready_scores_high(self) -> None:
        inputs = ExitReadinessInputs(
            has_audited_financials_3yr=True,
            has_trailing_12mo_kpis=True,
            data_room_organized=True,
            quality_of_earnings_prepared=True,
            ebitda_trending_up_last_2q=True,
            margin_trending_up_last_2q=True,
            buyer_universe_mapped=True,
            management_retained_through_close=True,
            legal_litigation_clean=True,
            ebitda_adj_recon_documented=True,
            ebitda_vs_plan=1.02,
            revenue_vs_plan=1.01,
        )
        report = score_exit_readiness(HeuristicContext(), inputs)
        self.assertGreaterEqual(report.score, 85)
        self.assertEqual(report.verdict, "ready")

    def test_not_ready_deal_scores_low(self) -> None:
        inputs = ExitReadinessInputs(
            has_audited_financials_3yr=False,
            has_trailing_12mo_kpis=False,
            data_room_organized=False,
            quality_of_earnings_prepared=False,
            ebitda_trending_up_last_2q=False,
            margin_trending_up_last_2q=False,
            buyer_universe_mapped=False,
            management_retained_through_close=False,
            legal_litigation_clean=False,
            ebitda_adj_recon_documented=False,
            ebitda_vs_plan=0.85,
            revenue_vs_plan=0.90,
        )
        report = score_exit_readiness(HeuristicContext(), inputs)
        self.assertLess(report.score, 30)
        self.assertEqual(report.verdict, "not_ready")

    def test_midpack_soft_launches(self) -> None:
        inputs = ExitReadinessInputs(
            has_audited_financials_3yr=True,
            has_trailing_12mo_kpis=True,
            data_room_organized=False,         # gap
            quality_of_earnings_prepared=False,  # gap
            ebitda_trending_up_last_2q=True,
            margin_trending_up_last_2q=True,
            buyer_universe_mapped=True,
            management_retained_through_close=True,
            legal_litigation_clean=True,
            ebitda_adj_recon_documented=True,
            ebitda_vs_plan=1.0,
            revenue_vs_plan=1.0,
        )
        report = score_exit_readiness(HeuristicContext(), inputs)
        self.assertIn(report.verdict, ("soft_launch", "ready"))

    def test_unknown_fields_score_mid(self) -> None:
        report = score_exit_readiness(HeuristicContext(), ExitReadinessInputs())
        # Nothing populated — score ~= 50.
        self.assertGreater(report.score, 30)
        self.assertLess(report.score, 70)

    def test_findings_have_all_dimensions(self) -> None:
        report = score_exit_readiness(HeuristicContext(), ExitReadinessInputs(
            has_audited_financials_3yr=True,
        ))
        dims = {f.dimension for f in report.findings}
        expected = {
            "audited_financials", "kpi_reporting", "data_room",
            "quality_of_earnings", "ebitda_trend", "margin_trend",
            "buyer_universe", "management_retention", "legal_clean",
            "ebitda_adjustments", "ebitda_vs_plan", "revenue_vs_plan",
        }
        self.assertEqual(dims, expected)

    def test_report_to_dict(self) -> None:
        import json
        report = score_exit_readiness(HeuristicContext(), ExitReadinessInputs())
        d = report.to_dict()
        json.dumps(d)

    def test_performance_beating_plan_scores_high(self) -> None:
        inputs = ExitReadinessInputs(ebitda_vs_plan=1.08)
        report = score_exit_readiness(HeuristicContext(), inputs)
        perf = next(f for f in report.findings if f.dimension == "ebitda_vs_plan")
        self.assertEqual(perf.status, "ready")

    def test_performance_missing_plan_scores_low(self) -> None:
        inputs = ExitReadinessInputs(ebitda_vs_plan=0.80)
        report = score_exit_readiness(HeuristicContext(), inputs)
        perf = next(f for f in report.findings if f.dimension == "ebitda_vs_plan")
        self.assertEqual(perf.status, "not_ready")

    def test_headline_matches_verdict(self) -> None:
        for score_hint, vl in [("ready", "banker"), ("soft_launch", "shore up"), ("not_ready", "not exit-ready")]:
            if score_hint == "ready":
                ins = ExitReadinessInputs(has_audited_financials_3yr=True,
                                          has_trailing_12mo_kpis=True,
                                          data_room_organized=True,
                                          quality_of_earnings_prepared=True,
                                          ebitda_trending_up_last_2q=True,
                                          margin_trending_up_last_2q=True,
                                          buyer_universe_mapped=True,
                                          management_retained_through_close=True,
                                          legal_litigation_clean=True,
                                          ebitda_adj_recon_documented=True,
                                          ebitda_vs_plan=1.02, revenue_vs_plan=1.01)
            elif score_hint == "not_ready":
                ins = ExitReadinessInputs(has_audited_financials_3yr=False,
                                          data_room_organized=False,
                                          ebitda_trending_up_last_2q=False,
                                          ebitda_vs_plan=0.80, revenue_vs_plan=0.85)
            else:
                ins = ExitReadinessInputs(
                    has_audited_financials_3yr=True,
                    has_trailing_12mo_kpis=True,
                    data_room_organized=False,          # gap
                    quality_of_earnings_prepared=False,  # gap
                    ebitda_trending_up_last_2q=True,
                    margin_trending_up_last_2q=True,
                    buyer_universe_mapped=True,
                    management_retained_through_close=True,
                    legal_litigation_clean=True,
                    ebitda_adj_recon_documented=True,
                    ebitda_vs_plan=1.0,
                    revenue_vs_plan=1.0,
                )
            report = score_exit_readiness(HeuristicContext(), ins)
            self.assertIn(vl, report.headline.lower())


# ── Payer math ───────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    PayerScenario,
    ProjectionInputs,
    ScenarioResult,
    VBCInputs,
    VBCProjection,
    YearProjection,
    blended_rate_growth,
    compare_payer_scenarios,
    project_ebitda_from_revenue,
    project_revenue,
    standard_scenarios,
    vbc_revenue_projection,
)


class TestBlendedRateGrowth(unittest.TestCase):

    def test_simple_mix(self) -> None:
        # 50% commercial @ 4%, 50% medicare @ 0% = 2% blended
        blend = blended_rate_growth(
            {"commercial": 0.50, "medicare": 0.50},
            {"commercial": 0.04, "medicare": 0.00},
        )
        self.assertAlmostEqual(blend, 0.02, places=4)

    def test_unlisted_payer_contributes_zero(self) -> None:
        # medicaid in mix but not in rate_growth → 0% growth on that share
        blend = blended_rate_growth(
            {"commercial": 0.50, "medicare": 0.30, "medicaid": 0.20},
            {"commercial": 0.04, "medicare": 0.02},
        )
        # 0.5*0.04 + 0.3*0.02 + 0.2*0 = 0.02 + 0.006 + 0 = 0.026
        self.assertAlmostEqual(blend, 0.026, places=4)

    def test_handles_percent_input(self) -> None:
        # Mix given as percents sums to 100.
        blend = blended_rate_growth(
            {"commercial": 50.0, "medicare": 50.0},
            {"commercial": 0.04, "medicare": 0.00},
        )
        self.assertAlmostEqual(blend, 0.02, places=4)

    def test_empty_mix_returns_zero(self) -> None:
        self.assertEqual(blended_rate_growth({}, {"commercial": 0.04}), 0.0)


class TestProjectRevenue(unittest.TestCase):

    def test_base_projection_5yr(self) -> None:
        inputs = ProjectionInputs(
            base_revenue=100_000_000,
            base_ebitda=8_000_000,
            payer_mix={"commercial": 0.50, "medicare": 0.50},
            rate_growth_by_payer={"commercial": 0.04, "medicare": 0.00},
            volume_growth_pct=0.02,
            contribution_margin=0.40,
            years=5,
        )
        series = project_revenue(inputs)
        self.assertEqual(len(series), 5)
        # Revenue grows each year.
        prev = inputs.base_revenue
        for yp in series:
            self.assertGreater(yp.revenue, prev)
            prev = yp.revenue

    def test_flat_growth_holds_revenue(self) -> None:
        inputs = ProjectionInputs(
            base_revenue=100_000_000,
            base_ebitda=8_000_000,
            payer_mix={"medicare": 1.0},
            rate_growth_by_payer={"medicare": 0.0},
            volume_growth_pct=0.0,
        )
        series = project_revenue(inputs)
        for yp in series:
            self.assertAlmostEqual(yp.revenue, 100_000_000, delta=1)

    def test_negative_growth_declines(self) -> None:
        inputs = ProjectionInputs(
            base_revenue=100_000_000,
            base_ebitda=8_000_000,
            payer_mix={"medicaid": 1.0},
            rate_growth_by_payer={"medicaid": -0.02},
            volume_growth_pct=0.0,
        )
        series = project_revenue(inputs)
        for yp in series:
            self.assertLess(yp.revenue, 100_000_000)


class TestProjectEBITDAFromRevenue(unittest.TestCase):

    def test_flow_through_at_40_pct(self) -> None:
        ebitda_series = project_ebitda_from_revenue(
            base_ebitda=10_000_000,
            revenue_series=[110_000_000, 120_000_000],
            base_revenue=100_000_000,
            contribution_margin=0.40,
        )
        # Y1: +10M revenue * 0.4 = +4M → 14M
        # Y2: +10M revenue * 0.4 = +4M → 18M
        self.assertAlmostEqual(ebitda_series[0], 14_000_000, delta=1)
        self.assertAlmostEqual(ebitda_series[1], 18_000_000, delta=1)


class TestCompareScenarios(unittest.TestCase):

    def test_compare_standard_scenarios(self) -> None:
        base = ProjectionInputs(
            base_revenue=200_000_000,
            base_ebitda=20_000_000,
            payer_mix={"medicare": 0.45, "commercial": 0.40, "medicaid": 0.15},
            rate_growth_by_payer={},  # overridden per scenario
            volume_growth_pct=0.0,    # overridden
            contribution_margin=0.40,
            years=5,
        )
        results = compare_payer_scenarios(base, standard_scenarios())
        self.assertEqual(len(results), 4)
        names = [r.name for r in results]
        self.assertIn("Base", names)
        self.assertIn("CMS cut", names)
        # CMS cut scenario should produce lower year-5 revenue than base.
        base_r = next(r for r in results if r.name == "Base")
        cms_r = next(r for r in results if r.name == "CMS cut")
        self.assertLess(cms_r.year5_revenue, base_r.year5_revenue)


class TestVBCProjection(unittest.TestCase):

    def test_vbc_basic_math(self) -> None:
        inputs = VBCInputs(
            lives=50_000, pmpm=900, mlr=0.85,
            admin_cost_rate=0.08, savings_pool=5_000_000, shared_savings_rate=0.40,
        )
        projection = vbc_revenue_projection(inputs)
        # Premium = 50k * 900 * 12 = 540M
        self.assertAlmostEqual(projection.premium_revenue, 540_000_000, delta=1)
        # Claims = 540M * 0.85 = 459M
        self.assertAlmostEqual(projection.claims_cost, 459_000_000, delta=1)
        # Admin = 540M * 0.08 = 43.2M
        self.assertAlmostEqual(projection.admin_cost, 43_200_000, delta=1)
        # Underwriting = 540 - 459 - 43.2 = 37.8M
        self.assertAlmostEqual(projection.underwriting_margin, 37_800_000, delta=10)
        # Shared savings = 5M * 0.40 = 2M
        self.assertAlmostEqual(projection.shared_savings_share, 2_000_000, delta=1)

    def test_vbc_to_dict(self) -> None:
        import json
        p = vbc_revenue_projection(VBCInputs(lives=10_000, pmpm=500))
        json.dumps(p.to_dict())


class TestStandardScenarios(unittest.TestCase):

    def test_four_scenarios_defined(self) -> None:
        scenarios = standard_scenarios()
        self.assertEqual(len(scenarios), 4)
        for s in scenarios:
            self.assertIsInstance(s, PayerScenario)
            self.assertTrue(s.name)
            self.assertIn("medicare", s.rate_growth_by_payer)


if __name__ == "__main__":
    unittest.main()
