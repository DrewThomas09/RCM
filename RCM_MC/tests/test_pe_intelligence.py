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


# ── Regulatory watch ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    REGULATORY_REGISTRY,
    RegulatoryItem,
    regulatory_items_for_deal,
    list_regulatory_items,
    regulatory_summary_for_partner,
)


class TestRegulatoryRegistry(unittest.TestCase):

    def test_registry_non_empty(self) -> None:
        self.assertGreater(len(REGULATORY_REGISTRY), 10)

    def test_every_item_has_id_and_title(self) -> None:
        for item in REGULATORY_REGISTRY:
            self.assertTrue(item.id)
            self.assertTrue(item.title)
            self.assertTrue(item.scope)

    def test_filter_by_scope(self) -> None:
        ca = list_regulatory_items(scope="CA")
        self.assertTrue(all(i.scope == "CA" for i in ca))
        self.assertGreaterEqual(len(ca), 1)

    def test_filter_by_status(self) -> None:
        effective = list_regulatory_items(status="effective")
        self.assertTrue(all(i.status == "effective" for i in effective))


class TestRegulatoryForDeal(unittest.TestCase):

    def test_acute_care_national_plus_state(self) -> None:
        items = regulatory_items_for_deal(
            subsector="acute_care", state="CA",
            payer_mix={"medicare": 0.40, "commercial": 0.40, "medicaid": 0.20},
        )
        # Should include both national (e.g. IPPS) and CA-specific (seismic).
        scopes = {i.scope for i in items}
        self.assertIn("national", scopes)
        self.assertIn("CA", scopes)

    def test_state_only_filter(self) -> None:
        items = regulatory_items_for_deal(
            subsector="acute_care", state="NY",
            payer_mix={"medicaid": 0.40, "commercial": 0.40, "medicare": 0.20},
        )
        # NY items should be included.
        ny_hits = [i for i in items if i.scope == "NY"]
        self.assertGreaterEqual(len(ny_hits), 1)

    def test_payer_filter_excludes_non_relevant(self) -> None:
        # A pure commercial deal — 340B (medicare-only) should be filtered.
        items = regulatory_items_for_deal(
            subsector="acute_care", state=None,
            payer_mix={"commercial": 1.0},
        )
        ids = {i.id for i in items}
        # 340B targets medicare; should be excluded.
        self.assertNotIn("340b_payback_schedule", ids)

    def test_behavioral_deal(self) -> None:
        items = regulatory_items_for_deal(
            subsector="behavioral",
            payer_mix={"medicaid": 0.50, "commercial": 0.30, "medicare": 0.20},
        )
        ids = {i.id for i in items}
        # IMD waiver is behavioral-specific.
        self.assertIn("imd_exclusion_waiver", ids)

    def test_summary_shape(self) -> None:
        items = regulatory_items_for_deal(subsector="acute_care")
        summary = regulatory_summary_for_partner(items)
        self.assertIn("regulatory item", summary)

    def test_summary_empty(self) -> None:
        self.assertIn("No active", regulatory_summary_for_partner([]))

    def test_item_to_dict_roundtrip(self) -> None:
        import json
        for item in REGULATORY_REGISTRY[:3]:
            json.dumps(item.to_dict())


# ── LP pitch ─────────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    render_lp_all,
    render_lp_html,
    render_lp_markdown,
)


class TestLPPitch(unittest.TestCase):

    def test_markdown_has_expected_sections(self) -> None:
        review = _review_for_memo()
        md = render_lp_markdown(review)
        for section in ("LP Brief", "Opportunity snapshot", "Why this deal",
                        "Risks and mitigations", "Diligence priorities",
                        "Strengths vs peer"):
            self.assertIn(section, md)

    def test_markdown_softens_partner_language(self) -> None:
        # Build a review that would include hard partner language.
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.70},
            ebitda_m=50.0,
            projected_irr=0.45,           # triggers implausible
            exit_multiple=13.5,
            denial_improvement_bps_per_yr=800,
        )
        review = partner_review_from_context(ctx, deal_name="Hard Deal")
        md = render_lp_markdown(review)
        # "Do not show this" should not appear in LP output.
        self.assertNotIn("Do not show this at IC", md)

    def test_html_escapes_deal_name(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        rv = partner_review_from_context(ctx, deal_name="<script>x</script>")
        h = render_lp_html(rv)
        self.assertNotIn("<script>x</script>", h)
        self.assertIn("&lt;script&gt;", h)

    def test_html_has_article_wrapper(self) -> None:
        review = _review_for_memo()
        h = render_lp_html(review)
        self.assertIn('<article class="lp-brief">', h)
        self.assertIn("</article>", h)

    def test_render_all_returns_two_formats(self) -> None:
        review = _review_for_memo()
        out = render_lp_all(review)
        self.assertEqual(set(out.keys()), {"markdown", "html"})
        for v in out.values():
            self.assertIsInstance(v, str)
            self.assertGreater(len(v), 50)

    def test_no_hard_pass_language_in_lp_brief(self) -> None:
        # Even for a failing deal, LP brief uses soft language.
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.75, "medicaid": 0.20, "commercial": 0.05},
            ebitda_m=30.0,
            exit_multiple=14.0,
            leverage_multiple=6.8,
            covenant_headroom_pct=0.05,
            denial_improvement_bps_per_yr=700,
        )
        review = partner_review_from_context(ctx, deal_name="Hard Deal")
        md = render_lp_markdown(review)
        # Check softening substitution occurred when relevant.
        self.assertNotIn("Hard pass", md)
        self.assertNotIn("this is where deals die", md.lower())


# ── 100-day plan ────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    HundredDayPlan,
    PlanAction,
    generate_plan,
    render_plan_markdown,
)


class TestHundredDayPlanGenerator(unittest.TestCase):

    def test_baseline_plan_has_four_workstreams(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="d1")
        plan = generate_plan(review)
        ws = plan.by_workstream()
        for name in ("operational", "financial", "people", "systems"):
            self.assertIn(name, ws)
            self.assertGreater(len(ws[name]), 0)

    def test_ar_heuristic_adds_ar_diagnosis_action(self) -> None:
        ctx = HeuristicContext(days_in_ar=75,
                               payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="d2")
        plan = generate_plan(review)
        titles = [a.title for a in plan.actions]
        self.assertIn("AR-aging diagnosis + remediation plan", titles)

    def test_covenant_action_when_headroom_tight(self) -> None:
        ctx = HeuristicContext(covenant_headroom_pct=0.08,
                               payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="d3")
        plan = generate_plan(review)
        titles = [a.title for a in plan.actions]
        self.assertIn("Covenant-cushion review + lender engagement", titles)

    def test_medicare_heavy_adds_cms_watch_action(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
            ebitda_m=50.0,
        )
        review = partner_review_from_context(ctx, deal_id="d4")
        plan = generate_plan(review)
        titles = [a.title for a in plan.actions]
        self.assertIn("CMS / IPPS rate-update monitoring", titles)

    def test_actions_sorted_by_due_day(self) -> None:
        ctx = HeuristicContext(
            days_in_ar=75, covenant_headroom_pct=0.08,
            payer_mix={"medicare": 0.60, "commercial": 0.40},
        )
        review = partner_review_from_context(ctx, deal_id="d5")
        plan = generate_plan(review)
        # Ensure sort invariant.
        for i in range(len(plan.actions) - 1):
            self.assertLessEqual(plan.actions[i].due_day,
                                 plan.actions[i + 1].due_day)

    def test_plan_summary_mentions_p0_count(self) -> None:
        ctx = HeuristicContext(
            days_in_ar=75, covenant_headroom_pct=0.08,
            payer_mix={"commercial": 0.55},
        )
        review = partner_review_from_context(ctx, deal_id="d6")
        plan = generate_plan(review)
        self.assertIn("P0", plan.summary)

    def test_plan_to_dict_roundtrip(self) -> None:
        import json
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="d7")
        plan = generate_plan(review)
        json.dumps(plan.to_dict())


class TestHundredDayPlanRender(unittest.TestCase):

    def test_markdown_has_workstream_headers(self) -> None:
        ctx = HeuristicContext(
            days_in_ar=75, covenant_headroom_pct=0.08,
            payer_mix={"commercial": 0.55},
        )
        review = partner_review_from_context(ctx, deal_id="d8", deal_name="Test")
        md = render_plan_markdown(generate_plan(review))
        for heading in ("100-Day Plan", "## Operational",
                        "## Financial", "## People", "## Systems"):
            self.assertIn(heading, md)

    def test_markdown_mentions_day_numbers(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="d9")
        md = render_plan_markdown(generate_plan(review))
        self.assertIn("D+30", md)


# ── IC voting ───────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ROLE_WEIGHTS,
    Vote,
    VoteOutcome,
    Voter,
    aggregate_vote,
    auto_vote_from_review,
    default_committee,
)
from rcm_mc.pe_intelligence.ic_voting import (
    VOTE_ABSTAIN,
    VOTE_NO,
    VOTE_YES,
    VOTE_YES_CAVEATS,
)


class TestVoterWeight(unittest.TestCase):

    def test_role_weight_default(self) -> None:
        v = Voter(name="p", role="partner")
        self.assertEqual(v.effective_weight(), ROLE_WEIGHTS["partner"])

    def test_override_weight(self) -> None:
        v = Voter(name="p", role="partner", weight=3.0)
        self.assertEqual(v.effective_weight(), 3.0)

    def test_recused_is_zero(self) -> None:
        v = Voter(name="p", role="partner", recused=True)
        self.assertEqual(v.effective_weight(), 0.0)


class TestAggregateVote(unittest.TestCase):

    def test_unanimous_yes_approves(self) -> None:
        voters = default_committee()
        votes = [Vote(voter=v.name, vote=VOTE_YES) for v in voters]
        out = aggregate_vote(voters, votes)
        self.assertEqual(out.decision, "APPROVED")
        self.assertAlmostEqual(out.approval_pct, 1.0, places=3)

    def test_majority_yes_but_veto_rejects(self) -> None:
        voters = default_committee()
        votes = [Vote(voter=v.name, vote=VOTE_YES) for v in voters]
        # MP1 has veto — flip their vote to NO.
        votes[0] = Vote(voter="MP1", vote=VOTE_NO, rationale="Doesn't clear my bar.")
        out = aggregate_vote(voters, votes)
        self.assertTrue(out.veto_triggered)
        self.assertEqual(out.decision, "REJECTED")

    def test_caveat_votes_approve_with_conditions(self) -> None:
        voters = default_committee()
        votes = [Vote(voter=v.name, vote=VOTE_YES_CAVEATS,
                      conditions=["Confirm payer mix"])
                 for v in voters]
        out = aggregate_vote(voters, votes)
        self.assertEqual(out.decision, "APPROVED_WITH_CONDITIONS")
        self.assertIn("Confirm payer mix", out.conditions)

    def test_split_vote_below_threshold_rejects(self) -> None:
        voters = default_committee()
        # Half yes, half no.
        votes = [
            Vote(voter="MP1", vote=VOTE_NO, rationale="Risk too high."),
            Vote(voter="MP2", vote=VOTE_NO, rationale="Disagree with thesis."),
            Vote(voter="P1", vote=VOTE_YES),
            Vote(voter="P2", vote=VOTE_YES),
            Vote(voter="PR1", vote=VOTE_YES),
            Vote(voter="VP1", vote=VOTE_YES),
        ]
        out = aggregate_vote(voters, votes)
        # Managing partners carry heavy weight - this should reject.
        # MPs contribute 4 weight NO; everyone else is 4 weight YES.
        # But MP1 has veto.
        self.assertIn(out.decision, ("REJECTED",))

    def test_abstentions_do_not_count(self) -> None:
        voters = default_committee()
        votes = [
            Vote(voter="MP1", vote=VOTE_YES),
            Vote(voter="MP2", vote=VOTE_YES),
            Vote(voter="P1", vote=VOTE_ABSTAIN),
            Vote(voter="P2", vote=VOTE_ABSTAIN),
            Vote(voter="PR1", vote=VOTE_ABSTAIN),
            Vote(voter="VP1", vote=VOTE_ABSTAIN),
        ]
        out = aggregate_vote(voters, votes)
        self.assertEqual(out.decision, "APPROVED")
        self.assertAlmostEqual(out.approval_pct, 1.0, places=2)
        self.assertGreater(out.abstain_weight, 0)

    def test_no_votes_tabled(self) -> None:
        voters = default_committee()
        out = aggregate_vote(voters, [])
        self.assertEqual(out.decision, "TABLED")

    def test_dissent_rationale_recorded(self) -> None:
        voters = default_committee()
        votes = [Vote(voter=v.name, vote=VOTE_YES) for v in voters]
        votes[2] = Vote(voter="P1", vote=VOTE_NO, rationale="Concerns on payer mix")
        out = aggregate_vote(voters, votes)
        self.assertEqual(len(out.dissent_rationales), 1)
        self.assertIn("payer mix", out.dissent_rationales[0])

    def test_outcome_to_dict_roundtrip(self) -> None:
        import json
        voters = default_committee()
        votes = [Vote(voter=v.name, vote=VOTE_YES) for v in voters]
        out = aggregate_vote(voters, votes)
        json.dumps(out.to_dict())


class TestAutoVoteFromReview(unittest.TestCase):

    def test_strong_proceed_yields_all_yes(self) -> None:
        voters = default_committee()
        votes = auto_vote_from_review("STRONG_PROCEED", voters)
        self.assertTrue(all(v.vote == VOTE_YES for v in votes))

    def test_pass_yields_all_no(self) -> None:
        voters = default_committee()
        votes = auto_vote_from_review("PASS", voters)
        self.assertTrue(all(v.vote == VOTE_NO for v in votes))

    def test_caveats_yields_conditions(self) -> None:
        voters = default_committee()
        votes = auto_vote_from_review("PROCEED_WITH_CAVEATS", voters)
        self.assertTrue(all(v.vote == VOTE_YES_CAVEATS for v in votes))
        self.assertGreater(len(votes[0].conditions), 0)


# ── Diligence tracker ──────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    DiligenceBoard,
    DiligenceItem,
    WORKSTREAMS,
    board_from_review,
    render_board_markdown,
)
from rcm_mc.pe_intelligence.diligence_tracker import (
    STATUS_BLOCKED,
    STATUS_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
)


class TestDiligenceBoard(unittest.TestCase):

    def test_add_and_retrieve(self) -> None:
        board = DiligenceBoard()
        item = DiligenceItem(id="f_rev", workstream="financial", title="Revenue QoE")
        board.add(item)
        self.assertIn("f_rev", board.items)

    def test_update_status(self) -> None:
        board = DiligenceBoard()
        board.add(DiligenceItem(id="op_ar", workstream="operational", title="AR aging"))
        board.update_status("op_ar", STATUS_COMPLETE, finding="Clean across buckets")
        self.assertEqual(board.items["op_ar"].status, STATUS_COMPLETE)
        self.assertEqual(board.items["op_ar"].finding, "Clean across buckets")

    def test_update_status_unknown_item_raises(self) -> None:
        board = DiligenceBoard()
        with self.assertRaises(KeyError):
            board.update_status("nope", STATUS_COMPLETE)

    def test_completion_pct(self) -> None:
        board = DiligenceBoard()
        board.add(DiligenceItem(id="a", workstream="financial", title="a"))
        board.add(DiligenceItem(id="b", workstream="financial", title="b"))
        board.add(DiligenceItem(id="c", workstream="financial", title="c"))
        board.update_status("a", STATUS_COMPLETE)
        board.update_status("b", STATUS_COMPLETE)
        # 2/3 = 0.67
        self.assertAlmostEqual(board.completion_pct(), 2 / 3, places=2)

    def test_critical_open_lists_high_priority_open(self) -> None:
        board = DiligenceBoard()
        board.add(DiligenceItem(id="a", workstream="financial",
                                title="a", is_critical=True,
                                status=STATUS_IN_PROGRESS))
        board.add(DiligenceItem(id="b", workstream="financial",
                                title="b", is_critical=False,
                                status=STATUS_IN_PROGRESS))
        board.add(DiligenceItem(id="c", workstream="financial",
                                title="c", is_critical=True,
                                status=STATUS_COMPLETE))
        critical = board.critical_open()
        self.assertEqual({i.id for i in critical}, {"a"})

    def test_is_ic_ready_checks_p0_and_critical_blocked(self) -> None:
        board = DiligenceBoard()
        board.add(DiligenceItem(id="a", workstream="financial",
                                title="a", priority="P0",
                                status=STATUS_COMPLETE))
        self.assertTrue(board.is_ic_ready())
        board.add(DiligenceItem(id="b", workstream="financial",
                                title="b", priority="P0",
                                status=STATUS_IN_PROGRESS))
        self.assertFalse(board.is_ic_ready())

    def test_blockers_returns_only_blocked(self) -> None:
        board = DiligenceBoard()
        board.add(DiligenceItem(id="a", workstream="financial",
                                title="a", status=STATUS_BLOCKED,
                                blocker="Seller stonewalling"))
        board.add(DiligenceItem(id="b", workstream="financial",
                                title="b", status=STATUS_IN_PROGRESS))
        blockers = board.blockers()
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0].id, "a")

    def test_board_to_dict_roundtrip(self) -> None:
        import json
        board = DiligenceBoard(deal_id="x", deal_name="Acme")
        board.add(DiligenceItem(id="op_x", workstream="operational", title="x"))
        json.dumps(board.to_dict())


class TestBoardFromReview(unittest.TestCase):

    def test_board_created_from_review(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
            exit_multiple=11.5, ebitda_m=50.0,
            denial_improvement_bps_per_yr=400,
            covenant_headroom_pct=0.10,
        )
        review = partner_review_from_context(ctx, deal_id="d1", deal_name="Test")
        board = board_from_review(review)
        self.assertEqual(board.deal_id, "d1")
        self.assertGreater(len(board.items), 0)

    def test_hits_mapped_to_workstreams(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=400)
        # contract_labor_share is a red-flag field, set via setattr.
        setattr(ctx, "contract_labor_share", 0.22)
        review = partner_review_from_context(ctx, deal_id="d2")
        board = board_from_review(review)
        ws = {i.workstream for i in board.items.values()}
        # Denial hit → operational; labor red-flag → hr_benefits.
        self.assertIn("operational", ws)


class TestRenderBoardMarkdown(unittest.TestCase):

    def test_markdown_renders_headers(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
            exit_multiple=11.5, ebitda_m=50.0,
            denial_improvement_bps_per_yr=400,
        )
        review = partner_review_from_context(ctx, deal_id="d1", deal_name="Test")
        md = render_board_markdown(board_from_review(review))
        self.assertIn("Diligence Board", md)
        self.assertIn("IC-ready", md)
        self.assertIn("Completion", md)


# ── Comparative analytics ──────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    DealSnapshot,
    DealVsBookFinding,
    concentration_warnings,
    correlation_risk,
    deal_rank_vs_peers,
    deal_vs_book,
    portfolio_concentration,
)


def _sample_book() -> List[DealSnapshot]:
    return [
        DealSnapshot(
            deal_id="d1", sector="acute_care", state="TX", ebitda_m=30,
            payer_mix={"medicare": 0.40, "commercial": 0.40, "medicaid": 0.20},
            projected_irr=0.20, projected_moic=2.3,
            ebitda_margin=0.09, leverage_multiple=4.5,
            days_in_ar=52, denial_rate=0.09,
        ),
        DealSnapshot(
            deal_id="d2", sector="asc", state="CA", ebitda_m=15,
            payer_mix={"commercial": 0.70, "medicare": 0.20, "medicaid": 0.10},
            projected_irr=0.24, projected_moic=2.6,
            ebitda_margin=0.24, leverage_multiple=4.0,
            days_in_ar=35, denial_rate=0.06,
        ),
        DealSnapshot(
            deal_id="d3", sector="acute_care", state="TX", ebitda_m=50,
            payer_mix={"medicare": 0.55, "commercial": 0.30, "medicaid": 0.15},
            projected_irr=0.17, projected_moic=2.1,
            ebitda_margin=0.07, leverage_multiple=5.0,
            days_in_ar=58, denial_rate=0.11,
        ),
    ]


class TestPortfolioConcentration(unittest.TestCase):

    def test_concentration_returns_shares(self) -> None:
        conc = portfolio_concentration(_sample_book())
        self.assertEqual(conc["n_deals"], 3)
        self.assertIn("sector_shares", conc)
        # acute_care = (30 + 50) / 95 = 0.84; should be top sector.
        self.assertIn("acute_care", conc["sector_shares"])
        self.assertAlmostEqual(conc["top_sector"]["share"], 80/95, places=2)

    def test_empty_portfolio_handled(self) -> None:
        conc = portfolio_concentration([])
        self.assertEqual(conc["n_deals"], 0)

    def test_concentration_warnings_fire(self) -> None:
        # 80% acute_care in our sample — should warn.
        conc = portfolio_concentration(_sample_book())
        warnings = concentration_warnings(conc)
        self.assertTrue(any("Sector concentration" in w for w in warnings))


class TestDealVsBook(unittest.TestCase):

    def test_candidate_with_higher_irr_is_better(self) -> None:
        candidate = DealSnapshot(
            deal_id="cand", sector="acute_care", state="NC",
            projected_irr=0.30, ebitda_margin=0.11, days_in_ar=40,
            denial_rate=0.05, leverage_multiple=3.5, projected_moic=2.8,
        )
        findings = deal_vs_book(candidate, _sample_book())
        irr_f = next(f for f in findings if f.metric == "projected_irr")
        self.assertEqual(irr_f.direction, "better")

    def test_days_in_ar_low_is_better(self) -> None:
        candidate = DealSnapshot(
            deal_id="cand", days_in_ar=30, projected_irr=0.20,
        )
        findings = deal_vs_book(candidate, _sample_book())
        ar_f = next(f for f in findings if f.metric == "days_in_ar")
        self.assertEqual(ar_f.direction, "better")

    def test_insufficient_data_returns_na(self) -> None:
        candidate = DealSnapshot(deal_id="cand")
        findings = deal_vs_book(candidate, _sample_book())
        self.assertTrue(any(f.direction == "n/a" for f in findings))


class TestDealRankVsPeers(unittest.TestCase):

    def test_rank_against_peers(self) -> None:
        candidate = DealSnapshot(
            deal_id="best", projected_irr=0.35, ebitda_margin=0.25,
            leverage_multiple=3.0,
        )
        result = deal_rank_vs_peers(candidate, _sample_book())
        self.assertEqual(result["candidate_rank"], 1)

    def test_weak_candidate_ranks_low(self) -> None:
        candidate = DealSnapshot(
            deal_id="weak", projected_irr=0.10, ebitda_margin=0.03,
            leverage_multiple=7.5,
        )
        result = deal_rank_vs_peers(candidate, _sample_book())
        self.assertEqual(result["candidate_rank"], len(_sample_book()) + 1)


class TestCorrelationRisk(unittest.TestCase):

    def test_same_sector_state_flagged(self) -> None:
        candidate = DealSnapshot(
            deal_id="cand", sector="acute_care", state="TX",
            payer_mix={"commercial": 0.60, "medicare": 0.30, "medicaid": 0.10},
        )
        warnings = correlation_risk(candidate, _sample_book())
        # d1 and d3 are TX acute → both flagged.
        tx_flags = [w for w in warnings if "TX" in w or "d1" in w or "d3" in w]
        self.assertGreaterEqual(len(warnings), 1)

    def test_medicare_heavy_correlation(self) -> None:
        candidate = DealSnapshot(
            deal_id="cand", sector="asc", state="FL",
            payer_mix={"medicare": 0.65, "medicaid": 0.15, "commercial": 0.20},
        )
        warnings = correlation_risk(candidate, _sample_book())
        # d3 is Medicare 55%, below 60% threshold → shouldn't pair.
        # None should pair on Medicare-heavy since d1 is 40%, d3 is 55%.
        medicare_flags = [w for w in warnings if "Medicare" in w]
        self.assertEqual(len(medicare_flags), 0)


# ── Workbench integration ─────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    archetype_summary,
    build_api_payload,
    build_workbench_bundle,
)


class TestWorkbenchIntegration(unittest.TestCase):

    def test_bundle_has_all_sections(self) -> None:
        packet = _make_packet_dict()
        bundle = build_workbench_bundle(packet)
        for key in ("review", "ic_memo", "lp_pitch",
                    "hundred_day_plan_markdown", "diligence_board_markdown",
                    "bear_patterns", "regulatory_items"):
            self.assertIn(key, bundle)

    def test_bundle_memo_markdown_nonempty(self) -> None:
        packet = _make_packet_dict()
        bundle = build_workbench_bundle(packet)
        self.assertGreater(len(bundle["ic_memo"]["markdown"]), 50)

    def test_bundle_is_json_serializable(self) -> None:
        import json
        packet = _make_packet_dict()
        bundle = build_workbench_bundle(packet)
        json.dumps(bundle, default=str)

    def test_api_payload_is_compact(self) -> None:
        packet = _make_packet_dict()
        payload = build_api_payload(packet)
        # Should not include HTML.
        self.assertNotIn("html", payload)
        for key in ("deal_id", "recommendation", "headline",
                    "bull_case", "bear_case", "key_questions",
                    "severity_counts", "band_counts",
                    "heuristic_hits", "reasonableness_checks",
                    "is_fundable", "has_critical_flag"):
            self.assertIn(key, payload)

    def test_archetype_summary_returns_ranked(self) -> None:
        packet = _make_packet_dict()
        review = partner_review(packet)
        summary = archetype_summary(review)
        self.assertIn("primary", summary)
        self.assertIn("ranked", summary)
        self.assertIsInstance(summary["ranked"], list)


# ── Value creation tracker ─────────────────────────────────────────

from datetime import date as _date

from rcm_mc.pe_intelligence import (
    LeverActual,
    LeverPlan,
    LeverStatus,
    evaluate_lever,
    evaluate_plan,
    rollup_status,
)


class TestEvaluateLever(unittest.TestCase):

    def test_on_track(self) -> None:
        plan = LeverPlan(
            name="denial_rate", unit="bps", baseline=1200,
            year1_target=1000, year2_target=800, year3_target=600,
            lower_is_better=True,
        )
        actual = LeverActual(lever_name="denial_rate", as_of=_date.today(),
                             observed_value=1000)
        status = evaluate_lever(plan, actual, year_in_hold=1)
        self.assertEqual(status.status, "on_track")

    def test_ahead_of_plan(self) -> None:
        plan = LeverPlan(
            name="ar_days", unit="days", baseline=60,
            year1_target=55, lower_is_better=True,
        )
        actual = LeverActual(lever_name="ar_days", as_of=_date.today(),
                             observed_value=50)
        status = evaluate_lever(plan, actual, year_in_hold=1)
        self.assertEqual(status.status, "ahead")

    def test_behind_plan(self) -> None:
        plan = LeverPlan(
            name="ar_days", unit="days", baseline=60,
            year1_target=50, lower_is_better=True,
        )
        actual = LeverActual(lever_name="ar_days", as_of=_date.today(),
                             observed_value=56)
        status = evaluate_lever(plan, actual, year_in_hold=1)
        # Expected delta = -10, actual delta = -4 → pct = 0.4 → off_track.
        self.assertIn(status.status, ("behind", "off_track"))

    def test_off_track(self) -> None:
        plan = LeverPlan(
            name="margin", unit="pct", baseline=0.08,
            year1_target=0.10, year2_target=0.12,
        )
        actual = LeverActual(lever_name="margin", as_of=_date.today(),
                             observed_value=0.081)
        status = evaluate_lever(plan, actual, year_in_hold=2)
        # Expected = 0.04 delta; actual = 0.001; pct = 0.025 → off_track.
        self.assertEqual(status.status, "off_track")

    def test_no_target_unknown(self) -> None:
        plan = LeverPlan(name="x", unit="pct", baseline=10)
        actual = LeverActual(lever_name="x", as_of=_date.today(),
                             observed_value=11)
        status = evaluate_lever(plan, actual, year_in_hold=1)
        self.assertEqual(status.status, "unknown")


class TestEvaluatePlan(unittest.TestCase):

    def test_missing_actual_becomes_unknown(self) -> None:
        plans = [LeverPlan(name="x", unit="pct", baseline=10, year1_target=15)]
        statuses = evaluate_plan(plans, [], year_in_hold=1)
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].status, "unknown")

    def test_multiple_levers_mixed_status(self) -> None:
        plans = [
            LeverPlan(name="a", unit="pct", baseline=10, year1_target=15),
            LeverPlan(name="b", unit="days", baseline=60,
                      year1_target=50, lower_is_better=True),
        ]
        actuals = [
            LeverActual(lever_name="a", as_of=_date.today(), observed_value=15),
            LeverActual(lever_name="b", as_of=_date.today(), observed_value=58),
        ]
        statuses = evaluate_plan(plans, actuals, year_in_hold=1)
        self.assertEqual(len(statuses), 2)


class TestRollupStatus(unittest.TestCase):

    def test_all_on_track_produces_positive_headline(self) -> None:
        statuses = [
            LeverStatus(lever_name="a", unit="pct", baseline=10,
                        target_current=15, observed=15, delta_vs_plan=0,
                        pct_of_plan=1.0, status="on_track"),
            LeverStatus(lever_name="b", unit="pct", baseline=10,
                        target_current=12, observed=13, delta_vs_plan=1,
                        pct_of_plan=1.5, status="ahead"),
        ]
        summary = rollup_status(statuses)
        self.assertEqual(summary["total"], 2)
        self.assertIn("on pace", summary["headline"])

    def test_off_track_escalates(self) -> None:
        statuses = [
            LeverStatus(lever_name="a", unit="pct", baseline=10,
                        target_current=15, observed=10.2,
                        delta_vs_plan=-4.8, pct_of_plan=0.04,
                        status="off_track"),
        ]
        summary = rollup_status(statuses)
        self.assertIn("off-track", summary["headline"])

    def test_empty_returns_no_levers_headline(self) -> None:
        summary = rollup_status([])
        self.assertIn("No levers", summary["headline"])


# ── Exit math ──────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    WaterfallResult,
    exit_waterfall,
    moic_cagr_to_irr,
    project_exit_ev,
    required_exit_ebitda_for_moic,
)


class TestProjectExitEV(unittest.TestCase):

    def test_basic_ev_calc(self) -> None:
        out = project_exit_ev(
            exit_ebitda=50_000_000, exit_multiple=10.0,
            exit_net_debt=100_000_000, transaction_fees_pct=0.015,
        )
        self.assertAlmostEqual(out["exit_ev"], 500_000_000, delta=1)
        self.assertAlmostEqual(out["exit_fees"], 7_500_000, delta=1)
        self.assertAlmostEqual(out["equity_after_fees"], 392_500_000, delta=1)


class TestExitWaterfall(unittest.TestCase):

    def test_waterfall_basic_shape(self) -> None:
        result = exit_waterfall(
            total_proceeds=500_000_000,
            lp_equity_in=200_000_000,
            gp_equity_in=10_000_000,
            hold_years=5.0,
        )
        self.assertIsInstance(result, WaterfallResult)
        # LP and GP together should approximately sum to proceeds.
        self.assertAlmostEqual(result.lp_total + result.gp_total,
                               500_000_000, delta=100)

    def test_gp_catch_up_produces_20pct_of_profit(self) -> None:
        # With catch-up at 100% and 20% carry, GP should end up with
        # roughly 20% of profits above preferred.
        result = exit_waterfall(
            total_proceeds=500_000_000,
            lp_equity_in=200_000_000, gp_equity_in=0,
            hold_years=5.0, preferred_return_rate=0.08,
            gp_catch_up_pct=1.0, carry_pct=0.20,
        )
        profit = 500_000_000 - 200_000_000
        # Carry earned should be ~20% of profit (hurdle compresses it a bit).
        self.assertGreater(result.carry_earned, 50_000_000)
        self.assertLessEqual(result.carry_earned, 65_000_000)

    def test_below_preferred_no_carry(self) -> None:
        result = exit_waterfall(
            total_proceeds=250_000_000,
            lp_equity_in=200_000_000, gp_equity_in=0,
            hold_years=5.0, preferred_return_rate=0.08,
            carry_pct=0.20,
        )
        # profits = 50M; preferred = 200M*(1.08^5 - 1) = 200M * 0.4693 = 93.9M
        # Proceeds below preferred — GP gets no carry.
        self.assertAlmostEqual(result.carry_earned, 0, delta=1)

    def test_zero_proceeds_produces_zeros(self) -> None:
        result = exit_waterfall(
            total_proceeds=0, lp_equity_in=100_000_000, gp_equity_in=0,
            hold_years=5,
        )
        self.assertEqual(result.lp_total, 0)
        self.assertEqual(result.carry_earned, 0)


class TestMOICCAGR(unittest.TestCase):

    def test_2x_over_5yrs_is_14_87_pct(self) -> None:
        cagr = moic_cagr_to_irr(2.0, 5.0)
        self.assertAlmostEqual(cagr, 0.14870, places=3)

    def test_invalid_inputs_return_none(self) -> None:
        self.assertIsNone(moic_cagr_to_irr(0, 5))
        self.assertIsNone(moic_cagr_to_irr(2, 0))


class TestRequiredExitEBITDA(unittest.TestCase):

    def test_reverses_math(self) -> None:
        target_moic = 2.5
        equity_in = 200_000_000
        needed = required_exit_ebitda_for_moic(
            target_moic=target_moic, equity_in=equity_in,
            exit_multiple=10.0, exit_net_debt=100_000_000,
            transaction_fees_pct=0.015,
        )
        self.assertIsNotNone(needed)
        # Verify by running the forward math.
        check = project_exit_ev(
            exit_ebitda=needed, exit_multiple=10.0,
            exit_net_debt=100_000_000, transaction_fees_pct=0.015,
        )
        self.assertAlmostEqual(check["equity_after_fees"] / equity_in,
                               target_moic, places=4)


# ── Deal comparables ───────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    COMPS,
    Comparable,
    filter_comps,
    multiple_stats,
    position_in_comps,
)


class TestCompsRegistry(unittest.TestCase):

    def test_registry_non_empty(self) -> None:
        self.assertGreater(len(COMPS), 10)

    def test_each_comp_has_core_fields(self) -> None:
        for c in COMPS:
            self.assertTrue(c.id)
            self.assertTrue(c.target_name)
            self.assertTrue(c.sector)
            self.assertIsNotNone(c.ev_ebitda_multiple)


class TestFilterComps(unittest.TestCase):

    def test_filter_by_sector(self) -> None:
        acute = filter_comps(sector="acute_care")
        self.assertTrue(all(c.sector == "acute_care" for c in acute))

    def test_filter_by_payer_regime(self) -> None:
        commercial = filter_comps(payer_regime="commercial_heavy")
        self.assertTrue(all(c.payer_regime == "commercial_heavy" for c in commercial))

    def test_filter_by_year_range(self) -> None:
        recent = filter_comps(min_year=2023)
        self.assertTrue(all(c.close_year >= 2023 for c in recent))

    def test_filter_by_size_bucket(self) -> None:
        mid = filter_comps(size_bucket="mid")
        for c in mid:
            self.assertGreaterEqual(c.ebitda_m, 25)
            self.assertLess(c.ebitda_m, 75)


class TestMultipleStats(unittest.TestCase):

    def test_stats_on_full_registry(self) -> None:
        stats = multiple_stats(COMPS)
        self.assertGreater(stats["n"], 0)
        self.assertLess(stats["min"], stats["max"])
        self.assertLessEqual(stats["min"], stats["median"])
        self.assertLessEqual(stats["median"], stats["max"])

    def test_empty_set_returns_zero_n(self) -> None:
        stats = multiple_stats([])
        self.assertEqual(stats["n"], 0)


class TestPositionInComps(unittest.TestCase):

    def test_high_multiple_flags_above_ceiling(self) -> None:
        out = position_in_comps(14.0, filter_comps(sector="acute_care"))
        self.assertGreaterEqual(out["percentile"], 85)

    def test_low_multiple_flags_below_median(self) -> None:
        out = position_in_comps(6.0, filter_comps(sector="acute_care"))
        self.assertLess(out["percentile"], 40)

    def test_empty_returns_none(self) -> None:
        out = position_in_comps(10.0, [])
        self.assertIsNone(out["percentile"])


# ── Debt sizing ────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    covenant_stress_passes,
    leverage_headroom,
    max_interest_rate_to_break,
    prudent_leverage,
)


class TestPrudentLeverage(unittest.TestCase):

    def test_acute_commercial_higher_than_acute_govt(self) -> None:
        acu_com = prudent_leverage("acute_care", "commercial_heavy")
        acu_gov = prudent_leverage("acute_care", "govt_heavy")
        self.assertGreater(acu_com, acu_gov)

    def test_cah_capped_low(self) -> None:
        cah = prudent_leverage("critical_access", "govt_heavy")
        self.assertIsNotNone(cah)
        self.assertLessEqual(cah, 3.0)

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(prudent_leverage("made_up", "balanced"))


class TestLeverageHeadroom(unittest.TestCase):

    def test_conservative_verdict(self) -> None:
        result = leverage_headroom(3.5, subsector="acute_care",
                                   payer_regime="commercial_heavy")
        self.assertEqual(result["verdict"], "conservative")

    def test_at_prudent(self) -> None:
        result = leverage_headroom(5.4, subsector="acute_care",
                                   payer_regime="commercial_heavy")
        self.assertEqual(result["verdict"], "at_prudent")

    def test_over_levered(self) -> None:
        result = leverage_headroom(7.0, subsector="acute_care",
                                   payer_regime="commercial_heavy")
        self.assertEqual(result["verdict"], "over_levered")


class TestMaxInterestRate(unittest.TestCase):

    def test_basic_calc(self) -> None:
        # 30M EBITDA, 150M debt, floor 2.0x → max rate = 30/(150*2) = 10%
        rate = max_interest_rate_to_break(30_000_000, 150_000_000,
                                          coverage_floor=2.0)
        self.assertAlmostEqual(rate, 0.10, places=4)

    def test_zero_debt_returns_none(self) -> None:
        self.assertIsNone(max_interest_rate_to_break(30_000_000, 0))


class TestCovenantStress(unittest.TestCase):

    def test_passing_case(self) -> None:
        result = covenant_stress_passes(
            stressed_ebitda=30_000_000, debt=150_000_000,
            leverage_covenant=6.0, coverage_covenant=2.0,
            interest_rate=0.08,
        )
        # Leverage = 5.0, Coverage = 30M/12M = 2.5 — both pass.
        self.assertTrue(result["passes"])

    def test_leverage_breach(self) -> None:
        result = covenant_stress_passes(
            stressed_ebitda=20_000_000, debt=150_000_000,
            leverage_covenant=6.0, coverage_covenant=2.0,
            interest_rate=0.08,
        )
        # Leverage = 7.5 — breach.
        self.assertFalse(result["leverage_ok"])
        self.assertFalse(result["passes"])

    def test_coverage_breach(self) -> None:
        result = covenant_stress_passes(
            stressed_ebitda=24_000_000, debt=150_000_000,
            leverage_covenant=7.0, coverage_covenant=2.5,
            interest_rate=0.10,
        )
        # Leverage = 6.25 ok (≤7), Coverage = 24/(15) = 1.6 → breach.
        self.assertTrue(result["leverage_ok"])
        self.assertFalse(result["coverage_ok"])
        self.assertFalse(result["passes"])

    def test_negative_ebitda(self) -> None:
        result = covenant_stress_passes(
            stressed_ebitda=-5_000_000, debt=100_000_000,
            leverage_covenant=6.0, coverage_covenant=2.0,
            interest_rate=0.08,
        )
        self.assertFalse(result["passes"])


# ── Management assessment ─────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    DimensionScore,
    ManagementInputs,
    ManagementScore,
    score_management,
)


class TestManagementScoring(unittest.TestCase):

    def test_strong_team_scores_high(self) -> None:
        inputs = ManagementInputs(
            ceo_tenure_years=5, ceo_healthcare_years=15,
            ceo_pe_experience=True, ceo_operator_background=True,
            cfo_pe_experience=True, cfo_tenure_years=4,
            cfo_lbo_close_experience=True,
            coo_present=True, operating_bench_depth=6,
            rcm_leader_named=True, rcm_program_experience=True,
            cmo_present=True, quality_star_rating=4.0,
            equity_rollover_pct=0.25, top20_with_options_pct=0.85,
        )
        score = score_management(inputs)
        self.assertGreaterEqual(score.overall, 80)
        self.assertEqual(score.status, "strong")

    def test_weak_team_triggers_replacement_rec(self) -> None:
        inputs = ManagementInputs(
            ceo_tenure_years=0.5, ceo_healthcare_years=2,
            ceo_pe_experience=False, ceo_operator_background=False,
            cfo_pe_experience=False, cfo_lbo_close_experience=False,
            coo_present=False, operating_bench_depth=0,
            rcm_leader_named=False, rcm_program_experience=False,
            cmo_present=False, quality_star_rating=2.0,
            equity_rollover_pct=0.02, top20_with_options_pct=0.20,
        )
        score = score_management(inputs)
        self.assertLessEqual(score.overall, 55)
        self.assertIn(score.status, ("concerns", "replace"))
        self.assertGreater(len(score.seat_adds), 0)

    def test_no_inputs_produces_unknown_dims(self) -> None:
        score = score_management(ManagementInputs())
        for d in score.dimensions:
            self.assertEqual(d.status, "unknown")

    def test_dimensions_cover_six_areas(self) -> None:
        score = score_management(ManagementInputs())
        names = {d.name for d in score.dimensions}
        self.assertEqual(names, {
            "ceo", "cfo", "operational", "rcm_leadership",
            "clinical", "alignment",
        })

    def test_partial_inputs_blend(self) -> None:
        # CEO strong, nothing else — should be moderate overall.
        inputs = ManagementInputs(
            ceo_tenure_years=5, ceo_healthcare_years=10,
            ceo_pe_experience=True, ceo_operator_background=True,
        )
        score = score_management(inputs)
        # Other dims default to 50 → composite around 60.
        self.assertGreater(score.overall, 55)
        self.assertLess(score.overall, 75)

    def test_seat_adds_surface_weak_areas(self) -> None:
        inputs = ManagementInputs(
            ceo_tenure_years=5, ceo_healthcare_years=10,
            ceo_pe_experience=True, ceo_operator_background=True,
            coo_present=False, operating_bench_depth=0,
        )
        score = score_management(inputs)
        self.assertTrue(any("operational" in s for s in score.seat_adds))

    def test_score_to_dict_roundtrip(self) -> None:
        import json
        score = score_management(ManagementInputs(ceo_tenure_years=3))
        json.dumps(score.to_dict())


# ── Thesis validator ───────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ConsistencyFinding,
    ThesisStatement,
    validate_thesis,
)


class TestThesisValidator(unittest.TestCase):

    def test_rcm_with_short_hold_fires(self) -> None:
        t = ThesisStatement(has_rcm_thesis=True, hold_years=3.0)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "rcm_thesis_needs_4yr_hold"
                            for f in findings))

    def test_vbc_with_ffs_growth_fires(self) -> None:
        t = ThesisStatement(deal_structure="capitation", revenue_cagr=0.08)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "vbc_with_ffs_growth" for f in findings))

    def test_aggressive_irr_flat_multiples_fires(self) -> None:
        t = ThesisStatement(entry_multiple=9.0, exit_multiple=9.0,
                            target_irr=0.22)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "irr_ambition_without_multiple_expansion"
                            for f in findings))

    def test_margin_leapfrog_fires(self) -> None:
        t = ThesisStatement(margin_expansion_bps_per_yr=400, revenue_cagr=0.03)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "margin_leapfrogs_revenue" for f in findings))

    def test_leverage_vs_govt_fires(self) -> None:
        t = ThesisStatement(
            leverage_multiple=6.0,
            payer_mix={"medicare": 0.55, "medicaid": 0.20, "commercial": 0.25},
        )
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "leverage_exceeds_govt_stability"
                            for f in findings))

    def test_turnaround_plus_rollup_fires(self) -> None:
        t = ThesisStatement(has_turnaround_thesis=True, has_rollup_thesis=True)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "turnaround_plus_rollup_too_ambitious"
                            for f in findings))

    def test_moic_irr_mismatch_fires(self) -> None:
        # 3x MOIC over 5yr → 24.6% CAGR; stated IRR 15% → mismatch
        t = ThesisStatement(target_moic=3.0, target_irr=0.15, hold_years=5.0)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "moic_irr_disagree" for f in findings))

    def test_denial_improvement_without_rcm_fires(self) -> None:
        t = ThesisStatement(denial_improvement_bps_per_yr=250,
                            has_rcm_thesis=False)
        findings = validate_thesis(t)
        self.assertTrue(any(f.rule == "denial_improvement_without_rcm_thesis"
                            for f in findings))

    def test_denial_with_rcm_thesis_doesnt_fire(self) -> None:
        t = ThesisStatement(denial_improvement_bps_per_yr=250,
                            has_rcm_thesis=True)
        findings = validate_thesis(t)
        self.assertFalse(any(f.rule == "denial_improvement_without_rcm_thesis"
                             for f in findings))

    def test_empty_thesis_no_findings(self) -> None:
        findings = validate_thesis(ThesisStatement())
        self.assertEqual(findings, [])

    def test_findings_sorted_by_severity(self) -> None:
        t = ThesisStatement(
            has_turnaround_thesis=True, has_rollup_thesis=True,  # high
            has_rcm_thesis=True, hold_years=3.0,                 # medium
            target_moic=3.0, target_irr=0.15,                    # low
        )
        findings = validate_thesis(t)
        severities = [f.severity for f in findings]
        # High first, then medium, then low.
        self.assertEqual(severities, sorted(
            severities, key=lambda s: {"high": 0, "medium": 1, "low": 2}.get(s, 3)
        ))

    def test_finding_to_dict(self) -> None:
        import json
        t = ThesisStatement(deal_structure="capitation", revenue_cagr=0.10)
        findings = validate_thesis(t)
        json.dumps(findings[0].to_dict())


# ── Synergy modeler ───────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    SynergyInputs,
    SynergyResult,
    apply_partner_haircut,
    realization_schedule,
    size_cost_synergies,
    size_procurement_synergies,
    size_rcm_synergies,
    size_revenue_synergies,
    size_synergies,
)


def _synergy_inputs() -> SynergyInputs:
    return SynergyInputs(
        platform_revenue=500_000_000, platform_ebitda=50_000_000,
        addon_revenue=150_000_000, addon_ebitda=12_000_000,
        addon_sga_pct=0.12, platform_sga_pct=0.10,
        cross_sell_pct=0.04,
        rcm_margin_uplift_bps=200,
        procurement_savings_pct=0.03,
        addon_cogs_pct=0.40,
        partner_haircut=0.35,
    )


class TestSynergySizing(unittest.TestCase):

    def test_cost_synergies_on_addon_sga(self) -> None:
        inputs = _synergy_inputs()
        cost = size_cost_synergies(inputs, consolidation_pct=0.40)
        # 150M * 0.12 * 0.40 = 7.2M
        self.assertAlmostEqual(cost, 7_200_000, delta=1)

    def test_rcm_synergies_based_on_bps(self) -> None:
        inputs = _synergy_inputs()
        rcm = size_rcm_synergies(inputs)
        # 150M * 0.02 = 3M
        self.assertAlmostEqual(rcm, 3_000_000, delta=1)

    def test_procurement_synergies(self) -> None:
        inputs = _synergy_inputs()
        proc = size_procurement_synergies(inputs)
        # 150M * 0.40 * 0.03 = 1.8M
        self.assertAlmostEqual(proc, 1_800_000, delta=1)

    def test_revenue_synergies_scale_with_combined_revenue(self) -> None:
        inputs = _synergy_inputs()
        rev = size_revenue_synergies(inputs, margin_on_cross_sell=0.30)
        # combined = 650M; cross-sell = 4% * 650M = 26M; margin = 30% → 7.8M
        self.assertAlmostEqual(rev, 7_800_000, delta=1)


class TestRealizationSchedule(unittest.TestCase):

    def test_default_schedule_is_five_years(self) -> None:
        schedule = realization_schedule(10_000_000)
        self.assertEqual(len(schedule), 5)
        self.assertAlmostEqual(schedule[0]["realized_dollars"], 2_000_000, delta=1)
        self.assertAlmostEqual(schedule[-1]["realized_dollars"], 10_000_000, delta=1)

    def test_custom_ramp(self) -> None:
        schedule = realization_schedule(100, ramp=[0.5, 1.0])
        self.assertEqual(len(schedule), 2)
        self.assertAlmostEqual(schedule[0]["realized_dollars"], 50, delta=1)


class TestSynergyOrchestrator(unittest.TestCase):

    def test_size_synergies_full(self) -> None:
        result = size_synergies(_synergy_inputs(), consolidation_pct=0.40)
        self.assertIsInstance(result, SynergyResult)
        self.assertGreater(result.gross_total, 0)
        # Net should be gross * (1 - haircut).
        self.assertAlmostEqual(result.partner_net_total,
                               result.gross_total * 0.65, delta=10)

    def test_partner_haircut_applied(self) -> None:
        result = size_synergies(_synergy_inputs())
        # 35% haircut → net = 65% of gross.
        self.assertLess(result.partner_net_total, result.gross_total)

    def test_combined_margin_calc(self) -> None:
        result = size_synergies(_synergy_inputs())
        # Combined rev 650M; combined ebitda = platform + addon + net synergy.
        expected_margin = result.combined_ebitda / result.combined_revenue
        self.assertAlmostEqual(result.implied_pro_forma_margin,
                               expected_margin, places=4)

    def test_result_to_dict_roundtrip(self) -> None:
        import json
        result = size_synergies(_synergy_inputs())
        json.dumps(result.to_dict())


class TestApplyPartnerHaircut(unittest.TestCase):

    def test_default_haircut(self) -> None:
        net = apply_partner_haircut(100)
        self.assertAlmostEqual(net, 65, delta=0.1)

    def test_custom_haircut(self) -> None:
        net = apply_partner_haircut(100, haircut=0.50)
        self.assertAlmostEqual(net, 50, delta=0.1)


# ── Working capital ──────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    WCRelease,
    WCSummary,
    WorkingCapitalInputs,
    ap_days_to_cash,
    ar_days_to_cash,
    inventory_days_to_cash,
    total_wc_release,
)


class TestARDaysToCash(unittest.TestCase):

    def test_dso_reduction_releases_cash(self) -> None:
        # 100M revenue; DSO 60 → 50 = 10 days × 100M/365 = ~2.74M
        release = ar_days_to_cash(100_000_000, 60, 50)
        self.assertAlmostEqual(release.cash_released, 2_739_726, delta=5)
        self.assertEqual(release.days_improved, 10)

    def test_no_improvement_zero_cash(self) -> None:
        release = ar_days_to_cash(100_000_000, 60, 60)
        self.assertEqual(release.cash_released, 0)

    def test_small_release_is_modest(self) -> None:
        release = ar_days_to_cash(100_000_000, 50, 47)
        self.assertIn("Modest", release.partner_note)


class TestAPDaysToCash(unittest.TestCase):

    def test_dpo_extension_releases_cash(self) -> None:
        # 40M cogs; DPO 30 → 45 = 15 days × 40M/365 = ~1.64M
        release = ap_days_to_cash(40_000_000, 30, 45)
        self.assertAlmostEqual(release.cash_released, 1_643_835, delta=5)

    def test_large_extension_flagged_aggressive(self) -> None:
        release = ap_days_to_cash(40_000_000, 30, 70)
        self.assertIn("push back", release.partner_note)


class TestInventoryDaysToCash(unittest.TestCase):

    def test_dio_reduction_releases_cash(self) -> None:
        release = inventory_days_to_cash(20_000_000, 30, 20)
        self.assertAlmostEqual(release.cash_released, 547_945, delta=5)


class TestTotalWCRelease(unittest.TestCase):

    def test_combines_all_three(self) -> None:
        inputs = WorkingCapitalInputs(
            annual_revenue=100_000_000, annual_cogs=40_000_000,
            annual_inventory_cost=20_000_000,
            current_dso=60, target_dso=50,
            current_dpo=30, target_dpo=40,
            current_dio=30, target_dio=25,
        )
        summary = total_wc_release(inputs)
        self.assertEqual(len(summary.components), 3)
        self.assertGreater(summary.total_cash_released, 0)

    def test_handles_missing_components(self) -> None:
        inputs = WorkingCapitalInputs(
            annual_revenue=100_000_000,
            current_dso=60, target_dso=50,
        )
        summary = total_wc_release(inputs)
        # Only AR component populated.
        self.assertEqual(len(summary.components), 1)

    def test_large_release_flagged(self) -> None:
        # 100M revenue, 50 day DSO improvement → 13.7M release (>8% of revenue).
        inputs = WorkingCapitalInputs(
            annual_revenue=100_000_000,
            current_dso=70, target_dso=20,
        )
        summary = total_wc_release(inputs)
        self.assertIn("Very large", summary.partner_note)

    def test_summary_to_dict(self) -> None:
        import json
        inputs = WorkingCapitalInputs(
            annual_revenue=100_000_000, current_dso=60, target_dso=50,
        )
        summary = total_wc_release(inputs)
        json.dumps(summary.to_dict())


# ── Fund model ─────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    Fund,
    FundDeal,
    FundProjection,
    commentary_for_quartile,
    fund_vintage_percentile,
    project_fund,
)


class TestFundProjection(unittest.TestCase):

    def test_simple_one_deal_fund(self) -> None:
        fund = Fund(name="F1", fund_size=500_000_000, vintage_year=2024)
        deals = [FundDeal(deal_id="d1", commitment=100_000_000,
                          hold_years=5.0, projected_moic=2.5,
                          investment_year=1)]
        projections = project_fund(fund, deals, horizon_years=8)
        self.assertEqual(len(projections), 8)
        # By year 6 (after exit), deal distributed 100M × 2.5 = 250M.
        y6 = next(p for p in projections if p.year == 6)
        self.assertGreaterEqual(y6.distributions_to_date, 250_000_000)

    def test_tvpi_converges_to_moic(self) -> None:
        fund = Fund(name="F1", fund_size=100_000_000, vintage_year=2024,
                    management_fee_years=0, management_fee_pct=0.0)
        deals = [FundDeal(deal_id="d1", commitment=100_000_000,
                          hold_years=3.0, projected_moic=2.0,
                          investment_year=1)]
        projections = project_fund(fund, deals, horizon_years=6)
        y6 = projections[-1]
        # After exit, distributions = 200M; called = 100M; TVPI ~ 2.0x.
        self.assertAlmostEqual(y6.tvpi, 2.0, places=2)

    def test_nav_tracks_interim_progress(self) -> None:
        fund = Fund(name="F1", fund_size=100_000_000, vintage_year=2024,
                    management_fee_years=0, management_fee_pct=0.0)
        deals = [FundDeal(deal_id="d1", commitment=100_000_000,
                          hold_years=4.0, projected_moic=2.0,
                          investment_year=1)]
        projections = project_fund(fund, deals, horizon_years=5)
        # NAV should grow during the hold, then drop to 0 post-exit.
        nav_series = [p.nav for p in projections]
        self.assertGreater(nav_series[1], nav_series[0])  # year 2 > year 1
        self.assertEqual(nav_series[-1], 0)  # year 5 (post-exit) = 0


class TestFundVintagePercentile(unittest.TestCase):

    def test_high_tvpi_is_top_quartile(self) -> None:
        q = fund_vintage_percentile("tvpi", 2.8, 2024)
        self.assertEqual(q, "Q1")

    def test_low_tvpi_is_bottom_quartile(self) -> None:
        q = fund_vintage_percentile("tvpi", 1.2, 2024)
        self.assertEqual(q, "Q4")

    def test_unknown_metric_returns_none(self) -> None:
        self.assertIsNone(fund_vintage_percentile("made_up", 1.0, 2024))


class TestQuartileCommentary(unittest.TestCase):

    def test_q1_is_positive(self) -> None:
        self.assertIn("Top", commentary_for_quartile("Q1"))

    def test_q4_warns_fundraise(self) -> None:
        self.assertIn("fundraise", commentary_for_quartile("Q4"))


# ── Regulatory stress ──────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    RegulatoryStressInputs,
    StressShock,
    run_regulatory_stresses,
    shock_340b_reduction,
    shock_cms_ipps_cut,
    shock_medicaid_freeze,
    shock_site_neutral,
    shock_snf_vbp_accel,
    summarize_regulatory_exposure,
)


def _reg_inputs() -> RegulatoryStressInputs:
    return RegulatoryStressInputs(
        annual_revenue=500_000_000,
        medicare_revenue_share=0.40,
        medicaid_revenue_share=0.20,
        commercial_revenue_share=0.40,
        hopd_revenue_share=0.15,
        share_340b_of_ebitda=0.15,
        base_ebitda=50_000_000,
        hospital_type="acute_care",
    )


class TestRegulatoryShocks(unittest.TestCase):

    def test_ipps_cut_negative_impact(self) -> None:
        shock = shock_cms_ipps_cut(_reg_inputs(), bps=100)
        # 200M Medicare revenue * 1% = 2M EBITDA hit
        self.assertAlmostEqual(shock.dollar_ebitda_impact, -2_000_000, delta=1)

    def test_medicaid_freeze_calc(self) -> None:
        shock = shock_medicaid_freeze(_reg_inputs(), years_frozen=2,
                                      annual_inflation=0.025)
        # 100M Medicaid * 2.5% * 2 = 5M foregone
        self.assertAlmostEqual(shock.dollar_ebitda_impact, -5_000_000, delta=1)

    def test_340b_reduction_scaled_to_ebitda(self) -> None:
        shock = shock_340b_reduction(_reg_inputs(), reduction_pct=0.50)
        # 50M ebitda * 15% * 50% = 3.75M
        self.assertAlmostEqual(shock.dollar_ebitda_impact, -3_750_000, delta=1)

    def test_site_neutral(self) -> None:
        shock = shock_site_neutral(_reg_inputs(), hopd_rate_compression_pct=0.20)
        # 75M HOPD * 20% = 15M
        self.assertAlmostEqual(shock.dollar_ebitda_impact, -15_000_000, delta=1)

    def test_snf_vbp_only_for_post_acute(self) -> None:
        inputs = _reg_inputs()
        inputs.hospital_type = "acute_care"
        self.assertIsNone(shock_snf_vbp_accel(inputs))

        inputs.hospital_type = "post_acute"
        self.assertIsNotNone(shock_snf_vbp_accel(inputs))


class TestRunRegulatoryStresses(unittest.TestCase):

    def test_orchestrator_produces_shocks(self) -> None:
        shocks = run_regulatory_stresses(_reg_inputs())
        self.assertGreaterEqual(len(shocks), 5)

    def test_sorted_by_absolute_impact(self) -> None:
        shocks = run_regulatory_stresses(_reg_inputs())
        abs_impacts = [abs(s.dollar_ebitda_impact) for s in shocks]
        self.assertEqual(abs_impacts, sorted(abs_impacts, reverse=True))


class TestSummarizeRegulatoryExposure(unittest.TestCase):

    def test_summary_identifies_worst(self) -> None:
        shocks = run_regulatory_stresses(_reg_inputs())
        summary = summarize_regulatory_exposure(shocks, base_ebitda=50_000_000)
        self.assertIn("worst_scenario", summary)
        self.assertIn("headline", summary)

    def test_empty_summary(self) -> None:
        summary = summarize_regulatory_exposure([], base_ebitda=50_000_000)
        self.assertIn("No", summary["headline"])


# ── Cash conversion ────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CashConversionInputs,
    ConversionAssessment,
    assess_conversion,
    cash_conversion_ratio,
    expected_conversion_by_subsector,
)


class TestCashConversion(unittest.TestCase):

    def test_basic_ratio(self) -> None:
        inputs = CashConversionInputs(
            ebitda=100, capex=20, working_capital_change=5, taxes_paid=15,
        )
        ratio = cash_conversion_ratio(inputs)
        self.assertAlmostEqual(ratio, 0.60, places=2)

    def test_missing_optional_fields(self) -> None:
        inputs = CashConversionInputs(ebitda=100, capex=20)
        ratio = cash_conversion_ratio(inputs)
        self.assertAlmostEqual(ratio, 0.80, places=2)

    def test_zero_ebitda_returns_none(self) -> None:
        inputs = CashConversionInputs(ebitda=0)
        self.assertIsNone(cash_conversion_ratio(inputs))


class TestExpectedConversion(unittest.TestCase):

    def test_acute_care_in_band(self) -> None:
        band = expected_conversion_by_subsector("acute_care")
        self.assertIsNotNone(band)
        self.assertEqual(len(band), 3)

    def test_aliases(self) -> None:
        self.assertIsNotNone(expected_conversion_by_subsector("hospital"))
        self.assertIsNotNone(expected_conversion_by_subsector("snf"))
        self.assertIsNotNone(expected_conversion_by_subsector("cah"))

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(expected_conversion_by_subsector("made_up"))


class TestAssessConversion(unittest.TestCase):

    def test_acute_in_band(self) -> None:
        inputs = CashConversionInputs(ebitda=100, capex=25,
                                      working_capital_change=5, taxes_paid=12)
        result = assess_conversion(inputs, subsector="acute_care")
        self.assertEqual(result.status, "in_band")

    def test_above_band(self) -> None:
        inputs = CashConversionInputs(ebitda=100, capex=5)  # 95% conversion
        result = assess_conversion(inputs, subsector="acute_care")
        self.assertEqual(result.status, "above")

    def test_below_band(self) -> None:
        inputs = CashConversionInputs(ebitda=100, capex=60)  # 40% conversion
        result = assess_conversion(inputs, subsector="acute_care")
        self.assertEqual(result.status, "below")

    def test_no_subsector_returns_unknown(self) -> None:
        inputs = CashConversionInputs(ebitda=100, capex=20)
        result = assess_conversion(inputs)
        self.assertEqual(result.status, "unknown")

    def test_result_to_dict(self) -> None:
        import json
        inputs = CashConversionInputs(ebitda=100, capex=20)
        result = assess_conversion(inputs, subsector="acute_care")
        json.dumps(result.to_dict())


# ── LP side-letter conformance ─────────────────────────────────────

from rcm_mc.pe_intelligence import (
    SideLetterRule,
    SideLetterSet,
    check_side_letters,
    has_breach,
)
from rcm_mc.pe_intelligence.lp_side_letter_flags import ConformanceFinding


class TestSideLetterChecks(unittest.TestCase):

    def test_sector_exclusion_triggers_breach(self) -> None:
        sls = SideLetterSet(sector_exclusions=["asc"])
        findings = check_side_letters(sls=sls, deal_sector="asc")
        self.assertTrue(has_breach(findings))

    def test_sector_not_in_exclusion_passes(self) -> None:
        sls = SideLetterSet(sector_exclusions=["asc"])
        findings = check_side_letters(sls=sls, deal_sector="acute_care")
        self.assertFalse(has_breach(findings))

    def test_state_exclusion(self) -> None:
        sls = SideLetterSet(state_exclusions=["CA"])
        findings = check_side_letters(sls=sls, deal_state="CA")
        self.assertTrue(has_breach(findings))

    def test_deal_concentration_cap(self) -> None:
        sls = SideLetterSet(max_single_deal_pct_of_fund=0.15)
        findings = check_side_letters(
            sls=sls, equity_check=300_000_000, fund_size=1_000_000_000,
        )
        self.assertTrue(has_breach(findings))

    def test_govt_payer_cap_warns(self) -> None:
        sls = SideLetterSet(max_govt_payer_pct=0.70)
        findings = check_side_letters(
            sls=sls,
            payer_mix={"medicare": 0.50, "medicaid": 0.30, "commercial": 0.20},
        )
        self.assertTrue(any(f.severity == "warning" for f in findings))

    def test_tobacco_screen(self) -> None:
        sls = SideLetterSet(no_tobacco=True)
        findings = check_side_letters(
            sls=sls, deal_notes="Company also distributes tobacco products.",
        )
        self.assertTrue(has_breach(findings))

    def test_short_term_detention_screen(self) -> None:
        sls = SideLetterSet(no_short_term_detention=True)
        findings = check_side_letters(
            sls=sls, deal_notes="Facility provides short-term detention services.",
        )
        self.assertTrue(has_breach(findings))

    def test_empty_inputs_no_findings(self) -> None:
        findings = check_side_letters(sls=SideLetterSet())
        self.assertEqual(findings, [])

    def test_findings_json_serializable(self) -> None:
        import json
        sls = SideLetterSet(sector_exclusions=["asc"])
        findings = check_side_letters(sls=sls, deal_sector="asc")
        json.dumps([f.to_dict() for f in findings])


# ── Pipeline tracker ───────────────────────────────────────────────

from datetime import date as _d

from rcm_mc.pe_intelligence import (
    FunnelStats,
    PIPELINE_STAGES,
    PipelineDeal,
    funnel_stats,
    source_mix,
    stale_deals,
)


def _pipeline_sample() -> List[PipelineDeal]:
    return [
        PipelineDeal(deal_id="a", current_stage="sourced", source="banker"),
        PipelineDeal(deal_id="b", current_stage="sourced", source="direct"),
        PipelineDeal(deal_id="c", current_stage="screened", source="banker"),
        PipelineDeal(deal_id="d", current_stage="ioi", source="sponsor"),
        PipelineDeal(deal_id="e", current_stage="loi", source="banker"),
        PipelineDeal(deal_id="f", current_stage="closed", source="direct"),
        PipelineDeal(deal_id="g", current_stage="passed", source="banker"),
    ]


class TestFunnelStats(unittest.TestCase):

    def test_counts_at_or_beyond(self) -> None:
        stats = funnel_stats(_pipeline_sample())
        # Exclude "passed" (g). Total non-passed = 6.
        self.assertEqual(stats.n_by_stage["sourced"], 6)
        self.assertEqual(stats.n_by_stage["ioi"], 3)  # d, e, f
        self.assertEqual(stats.n_by_stage["closed"], 1)

    def test_yields_populated(self) -> None:
        stats = funnel_stats(_pipeline_sample())
        self.assertIn("sourced->screened", stats.yields)
        self.assertIn("loi->exclusive", stats.yields)

    def test_empty_pipeline(self) -> None:
        stats = funnel_stats([])
        self.assertEqual(sum(stats.n_by_stage.values()), 0)


class TestStaleDeals(unittest.TestCase):

    def test_old_deals_flagged(self) -> None:
        today = _d(2026, 4, 17)
        deals = [
            PipelineDeal(deal_id="x", current_stage="ioi",
                         last_activity_date=_d(2025, 12, 1)),
            PipelineDeal(deal_id="y", current_stage="ioi",
                         last_activity_date=_d(2026, 3, 1)),
        ]
        stale = stale_deals(deals, today=today, days_threshold=60)
        self.assertEqual([d.deal_id for d in stale], ["x"])

    def test_terminal_stages_excluded(self) -> None:
        today = _d(2026, 4, 17)
        deals = [
            PipelineDeal(deal_id="x", current_stage="closed",
                         last_activity_date=_d(2024, 1, 1)),
        ]
        stale = stale_deals(deals, today=today, days_threshold=60)
        self.assertEqual(stale, [])

    def test_missing_activity_date_flagged(self) -> None:
        today = _d(2026, 4, 17)
        deals = [PipelineDeal(deal_id="x", current_stage="ioi")]
        stale = stale_deals(deals, today=today)
        self.assertEqual(len(stale), 1)


class TestSourceMix(unittest.TestCase):

    def test_breakdown_sums_to_one(self) -> None:
        mix = source_mix(_pipeline_sample())
        self.assertAlmostEqual(sum(mix.values()), 1.0, places=4)

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(source_mix([]), {})


# ── KPI cascade ────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    KPICascadeInputs,
    KPIMovement,
    build_cascade,
    top_levers,
    total_ebitda_impact,
)


def _kpi_cascade_inputs() -> KPICascadeInputs:
    return KPICascadeInputs(
        annual_revenue=500_000_000,
        current_denial_rate=0.12, target_denial_rate=0.08,
        current_final_writeoff=0.06, target_final_writeoff=0.04,
        current_days_in_ar=60, target_days_in_ar=50,
        current_clean_claim_rate=0.88, target_clean_claim_rate=0.94,
        current_labor_pct_of_rev=0.52, target_labor_pct_of_rev=0.50,
    )


class TestBuildCascade(unittest.TestCase):

    def test_cascade_produces_movements(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        self.assertEqual(len(cascade), 5)

    def test_sorted_desc_by_abs_impact(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        impacts = [abs(m.ebitda_impact) for m in cascade]
        self.assertEqual(impacts, sorted(impacts, reverse=True))

    def test_denial_impact_calculation(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        denial = next(m for m in cascade if m.kpi == "initial_denial_rate")
        # 500M * 4% * 50% = 10M
        self.assertAlmostEqual(denial.ebitda_impact, 10_000_000, delta=1)
        self.assertAlmostEqual(denial.delta, 400, delta=1)  # 400 bps

    def test_writeoff_full_flowthrough(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        wo = next(m for m in cascade if m.kpi == "final_writeoff_rate")
        # 500M * 2% = 10M
        self.assertAlmostEqual(wo.ebitda_impact, 10_000_000, delta=1)

    def test_ar_days_reports_cash_not_ebitda(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        ar = next(m for m in cascade if m.kpi == "days_in_ar")
        # 500M * 10 / 365 = ~13.7M
        self.assertAlmostEqual(ar.ebitda_impact, 13_698_630, delta=5)
        self.assertIn("one-time", ar.partner_note)

    def test_missing_fields_skipped(self) -> None:
        inputs = KPICascadeInputs(
            annual_revenue=500_000_000,
            current_denial_rate=0.10, target_denial_rate=0.08,
        )
        cascade = build_cascade(inputs)
        self.assertEqual(len(cascade), 1)


class TestTopLevers(unittest.TestCase):

    def test_returns_top_n(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        top = top_levers(cascade, n=3)
        self.assertEqual(len(top), 3)


class TestTotalEBITDAImpact(unittest.TestCase):

    def test_excludes_ar_days(self) -> None:
        cascade = build_cascade(_kpi_cascade_inputs())
        total = total_ebitda_impact(cascade)
        # Should exclude the AR one-time cash.
        ar_impact = next(m for m in cascade if m.kpi == "days_in_ar").ebitda_impact
        sum_all = sum(m.ebitda_impact for m in cascade)
        self.assertAlmostEqual(total, sum_all - ar_impact, delta=1)


# ── Commercial due diligence ──────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CDDFinding,
    CDDInputs,
    competitive_position,
    growth_plausibility,
    market_share_check,
    market_size_sanity,
    run_cdd_checks,
)


class TestMarketSizeSanity(unittest.TestCase):

    def test_tam_within_ceiling_passes(self) -> None:
        finding = market_size_sanity(CDDInputs(
            subsector="asc", stated_tam_usd_b=40.0,
        ))
        self.assertEqual(finding.status, "pass")

    def test_tam_exceeds_ceiling_flagged(self) -> None:
        finding = market_size_sanity(CDDInputs(
            subsector="asc", stated_tam_usd_b=80.0,
        ))
        self.assertEqual(finding.status, "flag")

    def test_missing_tam_unknown(self) -> None:
        finding = market_size_sanity(CDDInputs(subsector="asc"))
        self.assertEqual(finding.status, "unknown")


class TestMarketShareCheck(unittest.TestCase):

    def test_small_share_passes(self) -> None:
        finding = market_share_check(CDDInputs(
            subsector="asc", target_revenue_m=500, stated_tam_usd_b=40,
        ))
        self.assertEqual(finding.status, "pass")

    def test_dominant_share_flagged(self) -> None:
        finding = market_share_check(CDDInputs(
            subsector="asc", target_revenue_m=12_000, stated_tam_usd_b=40,
        ))
        self.assertEqual(finding.status, "flag")


class TestGrowthPlausibility(unittest.TestCase):

    def test_norm_growth_passes(self) -> None:
        finding = growth_plausibility(CDDInputs(
            subsector="asc", stated_market_growth_pct=0.07,
        ))
        self.assertEqual(finding.status, "pass")

    def test_above_norm_flagged(self) -> None:
        finding = growth_plausibility(CDDInputs(
            subsector="asc", stated_market_growth_pct=0.14,
        ))
        self.assertEqual(finding.status, "flag")

    def test_percent_input_normalized(self) -> None:
        finding = growth_plausibility(CDDInputs(
            subsector="acute_care", stated_market_growth_pct=3.0,
        ))
        # 3.0 treated as 3% (normalized). Should pass.
        self.assertEqual(finding.status, "pass")


class TestCompetitivePosition(unittest.TestCase):

    def test_leader_position(self) -> None:
        finding = competitive_position(CDDInputs(
            subsector="asc", differentiation="high",
            competitive_intensity="low",
        ))
        self.assertEqual(finding.status, "pass")
        self.assertIn("leader", finding.detail)

    def test_weak_position_flagged(self) -> None:
        finding = competitive_position(CDDInputs(
            subsector="asc", differentiation="low",
            competitive_intensity="high",
        ))
        self.assertEqual(finding.status, "flag")
        self.assertIn("weak_position", finding.detail)

    def test_missing_inputs_unknown(self) -> None:
        finding = competitive_position(CDDInputs(subsector="asc"))
        self.assertEqual(finding.status, "unknown")


class TestRunCDDChecks(unittest.TestCase):

    def test_full_cdd_run(self) -> None:
        findings = run_cdd_checks(CDDInputs(
            subsector="asc", stated_tam_usd_b=40, target_revenue_m=500,
            stated_market_growth_pct=0.07, differentiation="moderate",
            competitive_intensity="moderate",
        ))
        self.assertEqual(len(findings), 4)

    def test_finding_to_dict(self) -> None:
        import json
        findings = run_cdd_checks(CDDInputs(
            subsector="asc", stated_tam_usd_b=40,
        ))
        json.dumps([f.to_dict() for f in findings])


# ── IC-Ready gate ──────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ICReadinessResult,
    evaluate_ic_readiness,
)


class TestICReadinessGate(unittest.TestCase):

    def test_clean_deal_is_ready(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55},
            ebitda_m=30.0, hospital_type="acute_care",
            exit_multiple=9.0, entry_multiple=8.5,
            hold_years=5.0, projected_irr=0.19,
            data_coverage_pct=0.80, has_case_mix_data=True,
            ebitda_margin=0.09, days_in_ar=48, denial_rate=0.08,
            final_writeoff_rate=0.04,
        )
        review = partner_review_from_context(ctx, deal_id="clean")
        result = evaluate_ic_readiness(review)
        self.assertTrue(result.ic_ready)
        self.assertEqual(result.blockers, [])

    def test_critical_hit_blocks(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=700)
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review)
        self.assertFalse(result.ic_ready)
        self.assertTrue(any("critical" in b.lower() for b in result.blockers))

    def test_implausible_band_blocks(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.70},
            ebitda_m=50.0, projected_irr=0.45,
        )
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review)
        self.assertFalse(result.ic_ready)
        self.assertTrue(any("implausible" in b.lower() for b in result.blockers))

    def test_low_data_coverage_blocks(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55},
            ebitda_m=30.0, projected_irr=0.18,
            data_coverage_pct=0.35,
        )
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review)
        self.assertFalse(result.ic_ready)
        self.assertTrue(any("Data coverage" in b for b in result.blockers))

    def test_diligence_board_open_p0_blocks(self) -> None:
        from rcm_mc.pe_intelligence import DiligenceBoard, DiligenceItem
        board = DiligenceBoard()
        board.add(DiligenceItem(id="a", workstream="financial",
                                title="QoE", priority="P0",
                                status="in_progress"))
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30.0,
            data_coverage_pct=0.80,
        )
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review, diligence_board=board)
        self.assertFalse(result.ic_ready)
        self.assertTrue(any("P0 diligence" in b for b in result.blockers))

    def test_side_letter_breach_blocks(self) -> None:
        from rcm_mc.pe_intelligence import SideLetterSet, check_side_letters
        sls = SideLetterSet(sector_exclusions=["asc"])
        findings = check_side_letters(sls=sls, deal_sector="asc")
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30.0,
            data_coverage_pct=0.80,
        )
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review, side_letter_findings=findings)
        self.assertFalse(result.ic_ready)

    def test_replace_management_blocks(self) -> None:
        from rcm_mc.pe_intelligence import ManagementInputs, score_management
        weak = score_management(ManagementInputs(
            ceo_tenure_years=0.5, ceo_pe_experience=False,
            ceo_operator_background=False, cfo_pe_experience=False,
            coo_present=False, operating_bench_depth=0,
            rcm_leader_named=False, cmo_present=False,
            equity_rollover_pct=0.01,
        ))
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30.0,
            data_coverage_pct=0.80,
        )
        review = partner_review_from_context(ctx)
        result = evaluate_ic_readiness(review, management=weak)
        self.assertFalse(result.ic_ready)

    def test_result_to_dict(self) -> None:
        import json
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        result = evaluate_ic_readiness(partner_review_from_context(ctx))
        json.dumps(result.to_dict())


# ── Cohort tracker ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CohortDeal,
    CohortRanking,
    CohortStats,
    bottom_decile,
    cohort_stats,
    compare_to_cohort,
    group_by_vintage,
    rank_within_cohort,
    top_decile,
)


def _cohort_sample() -> List[CohortDeal]:
    return [
        CohortDeal(deal_id="a", vintage_year=2023,
                   projected_irr=0.22, projected_moic=2.5, ebitda_margin=0.10),
        CohortDeal(deal_id="b", vintage_year=2023,
                   projected_irr=0.18, projected_moic=2.2, ebitda_margin=0.08),
        CohortDeal(deal_id="c", vintage_year=2023,
                   projected_irr=0.14, projected_moic=1.9, ebitda_margin=0.07),
        CohortDeal(deal_id="d", vintage_year=2023,
                   projected_irr=0.28, projected_moic=3.0, ebitda_margin=0.13),
        CohortDeal(deal_id="e", vintage_year=2024,
                   projected_irr=0.20, projected_moic=2.3, ebitda_margin=0.09),
    ]


class TestGroupByVintage(unittest.TestCase):

    def test_grouping(self) -> None:
        g = group_by_vintage(_cohort_sample())
        self.assertEqual(len(g[2023]), 4)
        self.assertEqual(len(g[2024]), 1)


class TestCohortStats(unittest.TestCase):

    def test_percentiles_populated(self) -> None:
        stats = cohort_stats(_cohort_sample(), 2023)
        self.assertEqual(stats.n_deals, 4)
        self.assertIsNotNone(stats.irr_p50)
        self.assertGreater(stats.irr_p75, stats.irr_p25)

    def test_empty_vintage_has_none_percentiles(self) -> None:
        stats = cohort_stats(_cohort_sample(), 2022)
        self.assertEqual(stats.n_deals, 0)
        self.assertIsNone(stats.irr_p50)


class TestRankWithinCohort(unittest.TestCase):

    def test_best_deal_is_rank_one(self) -> None:
        rankings = rank_within_cohort(_cohort_sample(), 2023)
        self.assertEqual(rankings[0].deal_id, "d")

    def test_weakest_is_last(self) -> None:
        rankings = rank_within_cohort(_cohort_sample(), 2023)
        self.assertEqual(rankings[-1].deal_id, "c")


class TestDecileFlags(unittest.TestCase):

    def test_top_decile_contains_best(self) -> None:
        top = top_decile(_cohort_sample(), 2023)
        self.assertIn("d", top)

    def test_bottom_decile_contains_weakest(self) -> None:
        bot = bottom_decile(_cohort_sample(), 2023)
        self.assertIn("c", bot)


class TestCompareToCohort(unittest.TestCase):

    def test_metric_deltas_reported(self) -> None:
        candidate = CohortDeal(deal_id="cand", vintage_year=2023,
                               projected_irr=0.25, projected_moic=2.7,
                               ebitda_margin=0.11)
        cmp = compare_to_cohort(candidate, _cohort_sample())
        self.assertIn("irr_delta_vs_median", cmp)
        self.assertIn("moic_delta_vs_median", cmp)
        self.assertGreater(cmp["irr_delta_vs_median"], 0)


# ── Partner discussion ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    DiscussionItem,
    build_discussion,
    render_discussion_markdown,
)


class TestBuildDiscussion(unittest.TestCase):

    def test_medicare_exit_generates_qa(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25, "medicaid": 0.10},
            exit_multiple=11.5,
        )
        review = partner_review_from_context(ctx)
        items = build_discussion(review)
        self.assertTrue(any("comp" in i.question.lower() for i in items))

    def test_clean_deal_has_no_discussion(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30.0,
            exit_multiple=9.0, projected_irr=0.18,
            ebitda_margin=0.09,
        )
        review = partner_review_from_context(ctx)
        items = build_discussion(review)
        self.assertEqual(items, [])

    def test_deduplicates_by_source_id(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65},
            exit_multiple=11.5,
        )
        review = partner_review_from_context(ctx)
        items = build_discussion(review)
        ids = [i.source_id for i in items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_item_to_dict_roundtrip(self) -> None:
        import json
        ctx = HeuristicContext(denial_improvement_bps_per_yr=400)
        review = partner_review_from_context(ctx)
        items = build_discussion(review)
        if items:
            json.dumps(items[0].to_dict())


class TestRenderDiscussionMarkdown(unittest.TestCase):

    def test_renders_qa_format(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=400)
        review = partner_review_from_context(ctx)
        items = build_discussion(review)
        md = render_discussion_markdown(items)
        self.assertIn("Partner Discussion", md)
        self.assertIn("**Q:**", md)
        self.assertIn("**A:**", md)

    def test_empty_renders_placeholder(self) -> None:
        md = render_discussion_markdown([])
        self.assertIn("No discussion", md)


# ── KPI alert rules ────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    KPI_DEFAULT_RULES,
    KPIAlert,
    KPIObservation,
    KPIRule,
    evaluate_kpi,
    evaluate_kpi_alerts,
    summarize_kpi_alerts,
)


class TestEvaluateKPI(unittest.TestCase):

    def test_denial_within_band_no_alert(self) -> None:
        rule = next(r for r in KPI_DEFAULT_RULES if r.kpi == "initial_denial_rate")
        alert = evaluate_kpi(KPIObservation(kpi="initial_denial_rate", value=0.09), rule)
        self.assertIsNone(alert)

    def test_denial_above_guardrail_medium(self) -> None:
        rule = next(r for r in KPI_DEFAULT_RULES if r.kpi == "initial_denial_rate")
        alert = evaluate_kpi(KPIObservation(kpi="initial_denial_rate", value=0.16), rule)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "medium")

    def test_denial_above_ceiling_high(self) -> None:
        rule = next(r for r in KPI_DEFAULT_RULES if r.kpi == "initial_denial_rate")
        alert = evaluate_kpi(KPIObservation(kpi="initial_denial_rate", value=0.22), rule)
        self.assertEqual(alert.severity, "high")

    def test_clean_claim_below_floor_high(self) -> None:
        rule = next(r for r in KPI_DEFAULT_RULES if r.kpi == "clean_claim_rate")
        alert = evaluate_kpi(KPIObservation(kpi="clean_claim_rate", value=0.75), rule)
        self.assertEqual(alert.severity, "high")

    def test_high_margin_not_flagged_for_higher_is_better(self) -> None:
        # EBITDA margin above upper guardrail is NOT flagged when
        # higher-is-better (no ceiling defined for the upside).
        rule = next(r for r in KPI_DEFAULT_RULES if r.kpi == "ebitda_margin")
        alert = evaluate_kpi(KPIObservation(kpi="ebitda_margin", value=0.30), rule)
        self.assertIsNone(alert)


class TestEvaluateAll(unittest.TestCase):

    def test_mixed_batch(self) -> None:
        obs = [
            KPIObservation(kpi="initial_denial_rate", value=0.16),  # medium alert
            KPIObservation(kpi="days_in_ar", value=50),               # no alert
            KPIObservation(kpi="clean_claim_rate", value=0.72),       # high alert
        ]
        alerts = evaluate_kpi_alerts(obs)
        self.assertEqual(len(alerts), 2)
        # Highest severity first.
        self.assertEqual(alerts[0].severity, "high")

    def test_unknown_kpi_ignored(self) -> None:
        alerts = evaluate_kpi_alerts([
            KPIObservation(kpi="made_up", value=100),
        ])
        self.assertEqual(alerts, [])


class TestSummarizeAlerts(unittest.TestCase):

    def test_empty_summary(self) -> None:
        summary = summarize_kpi_alerts([])
        self.assertEqual(summary["total"], 0)
        self.assertIn("No", summary["headline"])

    def test_mixed_summary(self) -> None:
        alerts = evaluate_kpi_alerts([
            KPIObservation(kpi="initial_denial_rate", value=0.22),   # high
            KPIObservation(kpi="days_in_ar", value=65),                # medium
        ])
        summary = summarize_kpi_alerts(alerts)
        self.assertEqual(summary["counts"]["high"], 1)
        self.assertEqual(summary["counts"]["medium"], 1)


# ── Recon ──────────────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ReconFinding,
    has_mismatch,
    reconcile,
)


class TestReconcile(unittest.TestCase):

    def test_clean_deal_reconciles(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx)
        findings = reconcile(review)
        self.assertFalse(has_mismatch(findings))

    def test_plan_coverage_check_with_high_hit(self) -> None:
        from rcm_mc.pe_intelligence import generate_plan
        ctx = HeuristicContext(denial_improvement_bps_per_yr=400,
                               days_in_ar=70)
        review = partner_review_from_context(ctx)
        plan = generate_plan(review)
        findings = reconcile(review, plan=plan)
        # Should be OK because denial + AR hits map to plan actions.
        # At minimum, no mismatch on CRITICAL (none fire).
        plan_check = next(f for f in findings
                          if f.check == "plan_covers_high_hits")
        self.assertIsNotNone(plan_check)

    def test_board_coverage_check(self) -> None:
        from rcm_mc.pe_intelligence import DiligenceBoard
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx)
        board = DiligenceBoard()
        findings = reconcile(review, board=board)
        # Only testing that the check runs, not whether it passes.
        self.assertTrue(any(f.check == "board_p0_covers_critical"
                            for f in findings))

    def test_finding_to_dict(self) -> None:
        import json
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        findings = reconcile(partner_review_from_context(ctx))
        json.dumps([f.to_dict() for f in findings])


# ── Capital plan ──────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CapexLine,
    CapitalPlan,
    CapitalPlanFinding,
    has_plan_mismatch,
    validate_capital_plan,
)


def _valid_plan() -> CapitalPlan:
    return CapitalPlan(
        deal_id="d1", subsector="acute_care",
        annual_revenue=500_000_000, horizon_years=5,
        lines=[
            CapexLine(purpose="maintenance", year=1, amount=10_000_000),
            CapexLine(purpose="maintenance", year=2, amount=10_000_000),
            CapexLine(purpose="maintenance", year=3, amount=10_000_000),
            CapexLine(purpose="growth", year=1, amount=5_000_000),
            CapexLine(purpose="growth", year=2, amount=8_000_000),
            CapexLine(purpose="it", year=1, amount=3_000_000),
        ],
    )


class TestCapitalPlan(unittest.TestCase):

    def test_totals(self) -> None:
        plan = _valid_plan()
        self.assertEqual(plan.total_capex(), 46_000_000)
        self.assertEqual(plan.total_by_year()[1], 18_000_000)

    def test_validate_within_intensity(self) -> None:
        plan = _valid_plan()
        findings = validate_capital_plan(plan)
        self.assertFalse(has_plan_mismatch(findings))

    def test_intensity_breach_flagged(self) -> None:
        plan = _valid_plan()
        plan.lines.append(CapexLine(purpose="growth", year=3, amount=200_000_000))
        findings = validate_capital_plan(plan)
        self.assertTrue(has_plan_mismatch(findings))

    def test_year1_concentration_flagged(self) -> None:
        plan = CapitalPlan(
            deal_id="d2", subsector="acute_care",
            annual_revenue=100_000_000, horizon_years=5,
            lines=[
                CapexLine(purpose="maintenance", year=1, amount=15_000_000),
            ],
        )
        findings = validate_capital_plan(plan)
        self.assertTrue(any(f.check == "year1_concentration" and not f.passed
                            for f in findings))

    def test_missing_revenue_returns_warning(self) -> None:
        plan = CapitalPlan(deal_id="d3", subsector="acute_care", annual_revenue=None)
        findings = validate_capital_plan(plan)
        self.assertTrue(any(f.severity == "warning" for f in findings))

    def test_plan_to_dict(self) -> None:
        import json
        plan = _valid_plan()
        json.dumps(plan.to_dict())


# ── Auditor view ──────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    AuditEntry,
    AuditTrail,
    build_audit_trail,
    filter_entries,
    summarize_trail,
)


class TestBuildAuditTrail(unittest.TestCase):

    def test_trail_has_entries_for_each_source(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65}, exit_multiple=11.5,
        )
        review = partner_review_from_context(ctx, deal_id="d1")
        trail = build_audit_trail(review)
        sources = {e.source for e in trail.entries}
        self.assertIn("context", sources)
        self.assertIn("band", sources)
        self.assertIn("heuristic", sources)
        self.assertIn("narrative", sources)

    def test_trail_preserves_deal_id(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="X", deal_name="Demo")
        trail = build_audit_trail(review)
        self.assertEqual(trail.deal_id, "X")
        self.assertEqual(trail.deal_name, "Demo")

    def test_trail_to_dict_serializable(self) -> None:
        import json
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.35},
            denial_improvement_bps_per_yr=400,
        )
        review = partner_review_from_context(ctx)
        trail = build_audit_trail(review)
        s = json.dumps(trail.to_dict(), default=str)
        self.assertIn("recommendation", s)


class TestFilterEntries(unittest.TestCase):

    def test_filter_by_source(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        trail = build_audit_trail(partner_review_from_context(ctx))
        bands = filter_entries(trail, source="band")
        self.assertTrue(all(e.source == "band" for e in bands))

    def test_filter_by_severity(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65}, exit_multiple=11.5,
            denial_improvement_bps_per_yr=500,
        )
        trail = build_audit_trail(partner_review_from_context(ctx))
        highs = filter_entries(trail, severity="HIGH")
        self.assertTrue(all(e.severity == "HIGH" for e in highs))


class TestSummarizeTrail(unittest.TestCase):

    def test_summary_has_expected_keys(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        trail = build_audit_trail(partner_review_from_context(ctx))
        summary = summarize_trail(trail)
        self.assertIn("total_entries", summary)
        self.assertIn("counts_by_source", summary)


# ── Thesis templates ──────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    THESIS_TEMPLATES,
    ThesisTemplate,
    fill_template,
    get_template,
    list_templates,
    render_template_markdown,
)


class TestThesisTemplates(unittest.TestCase):

    def test_list_templates_non_empty(self) -> None:
        templates = list_templates()
        self.assertGreaterEqual(len(templates), 6)
        self.assertIn("platform_rollup", templates)
        self.assertIn("turnaround", templates)

    def test_get_template(self) -> None:
        t = get_template("platform_rollup")
        self.assertIsNotNone(t)
        self.assertEqual(t.name, "Platform + tuck-ins")

    def test_unknown_template_returns_none(self) -> None:
        self.assertIsNone(get_template("made_up"))

    def test_fill_template(self) -> None:
        t = get_template("platform_rollup")
        text = fill_template(t, {
            "subsector": "ASC", "entry_multiple": 9.0,
            "n_addons": 4, "hold_years": 5,
        })
        self.assertIn("ASC", text)
        self.assertIn("9.00x", text)

    def test_unknown_placeholder_left_as_is(self) -> None:
        t = get_template("platform_rollup")
        text = fill_template(t, {"subsector": "ASC"})
        # Missing fields preserved as literal placeholders.
        self.assertIn("{entry_multiple", text)

    def test_render_markdown(self) -> None:
        t = get_template("turnaround")
        md = render_template_markdown(t, {
            "subsector": "Behavioral", "current_margin": 3,
            "peer_margin": 8, "hold_years": 5,
        })
        self.assertIn("# Thesis:", md)
        self.assertIn("## Bull case", md)
        self.assertIn("Behavioral", md)

    def test_template_to_dict(self) -> None:
        import json
        t = get_template("platform_rollup")
        json.dumps(t.to_dict())


# ── Regime classifier ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ALL_REGIMES,
    RegimeInputs,
    RegimeResult,
    classify_regime,
    rank_all_regimes,
)
from rcm_mc.pe_intelligence.regime_classifier import (
    REGIME_DECLINING_RISK,
    REGIME_DURABLE_GROWTH,
    REGIME_EMERGING_VOLATILE,
    REGIME_STAGNANT,
    REGIME_STEADY,
)


class TestRegimeClassifier(unittest.TestCase):

    def test_durable_growth_profile(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=0.10, revenue_growth_stddev=0.02,
            positive_growth_years_out_of_5=5, margin_trend_bps=50,
        ))
        self.assertEqual(result.regime, REGIME_DURABLE_GROWTH)
        self.assertGreater(result.confidence, 0.70)

    def test_declining_risk_profile(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=-0.03, ebitda_cagr_3yr=-0.05,
            margin_trend_bps=-200,
        ))
        self.assertEqual(result.regime, REGIME_DECLINING_RISK)

    def test_stagnant_profile(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=0.005, ebitda_cagr_3yr=0.01,
            margin_trend_bps=20,
        ))
        self.assertEqual(result.regime, REGIME_STAGNANT)

    def test_steady_profile(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=0.04, revenue_growth_stddev=0.015,
            positive_growth_years_out_of_5=5, margin_trend_bps=20,
        ))
        self.assertEqual(result.regime, REGIME_STEADY)

    def test_emerging_volatile_profile(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=0.15, revenue_growth_stddev=0.09,
            positive_growth_years_out_of_5=3,
        ))
        self.assertEqual(result.regime, REGIME_EMERGING_VOLATILE)

    def test_no_inputs_returns_steady_zero_confidence(self) -> None:
        result = classify_regime(RegimeInputs())
        self.assertEqual(result.regime, REGIME_STEADY)
        self.assertEqual(result.confidence, 0.0)

    def test_playbook_and_risk_populated(self) -> None:
        result = classify_regime(RegimeInputs(
            revenue_cagr_3yr=0.10, revenue_growth_stddev=0.02,
            positive_growth_years_out_of_5=5,
        ))
        self.assertTrue(result.playbook)
        self.assertTrue(result.key_risk)

    def test_rank_returns_all_five(self) -> None:
        ranked = rank_all_regimes(RegimeInputs(
            revenue_cagr_3yr=0.10, revenue_growth_stddev=0.02,
            positive_growth_years_out_of_5=5,
        ))
        self.assertEqual(len(ranked), 5)
        self.assertEqual({r.regime for r in ranked}, set(ALL_REGIMES))

    def test_result_to_dict(self) -> None:
        import json
        result = classify_regime(RegimeInputs(revenue_cagr_3yr=0.08))
        json.dumps(result.to_dict())


class TestRegimeWiredIntoReview(unittest.TestCase):

    def test_review_populates_regime_field(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx, deal_id="r1")
        self.assertIsNotNone(review.regime)
        self.assertIn("regime", review.regime)

    def test_review_regime_in_dict(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx)
        d = review.to_dict()
        self.assertIn("regime", d)
        self.assertIsNotNone(d["regime"])


# ── Market structure ─────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    HHI_HIGHLY_CONCENTRATED,
    HHI_UNCONCENTRATED,
    MarketStructureResult,
    analyze_market_structure,
    compute_cr3,
    compute_cr5,
    compute_hhi,
    is_consolidation_play,
)


class TestHHIComputation(unittest.TestCase):

    def test_monopoly_hhi_is_10000(self) -> None:
        self.assertAlmostEqual(compute_hhi({"a": 1.0}), 10000, places=1)

    def test_equal_split_hhi(self) -> None:
        # 4 equal players at 25% each: HHI = 4 * 25^2 = 2500
        hhi = compute_hhi({"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25})
        self.assertAlmostEqual(hhi, 2500, places=1)

    def test_hhi_scale_invariant(self) -> None:
        # Input as percents vs fractions should produce the same HHI.
        pct = compute_hhi({"a": 60.0, "b": 40.0})
        frac = compute_hhi({"a": 0.60, "b": 0.40})
        self.assertAlmostEqual(pct, frac, places=2)

    def test_empty_hhi_is_zero(self) -> None:
        self.assertEqual(compute_hhi({}), 0.0)


class TestCR3CR5(unittest.TestCase):

    def test_cr3_sums_top_three(self) -> None:
        shares = {"a": 0.30, "b": 0.25, "c": 0.20, "d": 0.15, "e": 0.10}
        self.assertAlmostEqual(compute_cr3(shares), 0.75, places=4)

    def test_cr5_sums_top_five(self) -> None:
        shares = {"a": 0.30, "b": 0.25, "c": 0.20, "d": 0.15, "e": 0.10}
        self.assertAlmostEqual(compute_cr5(shares), 1.0, places=4)

    def test_cr_handles_fewer_than_n(self) -> None:
        # Only 2 players but requesting CR5.
        self.assertAlmostEqual(compute_cr5({"a": 0.7, "b": 0.3}), 1.0, places=2)


class TestAnalyzeMarketStructure(unittest.TestCase):

    def test_fragmented_rollup_setup(self) -> None:
        # 20 players at 5% each → HHI 500, CR5 0.25, strong rollup.
        shares = {f"p{i}": 0.05 for i in range(20)}
        result = analyze_market_structure(shares)
        self.assertEqual(result.fragmentation_verdict, "fragmented")
        self.assertGreater(result.consolidation_play_score, 0.55)
        self.assertTrue(is_consolidation_play(result))

    def test_consolidated_market_discourages_rollup(self) -> None:
        # 3 players at 40/35/25 → high HHI, CR5 = 100%.
        shares = {"a": 0.40, "b": 0.35, "c": 0.25}
        result = analyze_market_structure(shares)
        self.assertEqual(result.fragmentation_verdict, "consolidated")
        self.assertFalse(is_consolidation_play(result))

    def test_empty_shares_safe(self) -> None:
        result = analyze_market_structure({})
        self.assertEqual(result.n_players, 0)
        self.assertEqual(result.fragmentation_verdict, "unknown")

    def test_result_to_dict_roundtrip(self) -> None:
        import json
        result = analyze_market_structure({"a": 0.60, "b": 0.40})
        json.dumps(result.to_dict())


class TestMarketStructureWiredIntoReview(unittest.TestCase):

    def test_no_shares_produces_note(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        review = partner_review_from_context(ctx)
        self.assertIsNotNone(review.market_structure)
        self.assertIn("note", review.market_structure)

    def test_packet_with_shares_analyzed(self) -> None:
        packet = _make_packet_dict()
        packet["profile"]["market_shares"] = {
            f"p{i}": 0.05 for i in range(20)
        }
        review = partner_review(packet)
        self.assertIsNotNone(review.market_structure)
        self.assertEqual(review.market_structure["fragmentation_verdict"],
                         "fragmented")
        self.assertGreater(review.market_structure["consolidation_play_score"], 0.50)


# ── Stress grid ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ScenarioOutcome,
    StressGridResult,
    run_stress_grid,
)


def _stress_grid_inputs():
    return StressInputs(
        base_ebitda=30_000_000, target_ebitda=45_000_000,
        base_revenue=250_000_000, entry_multiple=8.0, exit_multiple=9.5,
        debt_at_close=150_000_000, interest_rate=0.09,
        covenant_leverage=6.0, covenant_coverage=2.0,
        contract_labor_spend=30_000_000, lever_contribution=15_000_000,
        hold_years=5.0, base_moic=2.5,
        medicare_revenue=100_000_000, commercial_revenue=120_000_000,
    )


class TestRunStressGrid(unittest.TestCase):

    def test_grid_produces_outcomes(self) -> None:
        grid = run_stress_grid(_stress_grid_inputs())
        self.assertGreater(len(grid.outcomes), 5)
        # Both downside and upside scenarios present.
        severities = {o.severity for o in grid.outcomes}
        self.assertIn("downside", severities)
        self.assertIn("upside", severities)

    def test_grade_populated(self) -> None:
        grid = run_stress_grid(_stress_grid_inputs())
        self.assertIn(grid.robustness_grade, ("A", "B", "C", "D", "F", "?"))

    def test_worst_and_best_case_populated(self) -> None:
        grid = run_stress_grid(_stress_grid_inputs())
        self.assertIsNotNone(grid.worst_case_delta_pct)

    def test_pass_rate_between_0_and_1(self) -> None:
        grid = run_stress_grid(_stress_grid_inputs())
        self.assertGreaterEqual(grid.downside_pass_rate, 0.0)
        self.assertLessEqual(grid.downside_pass_rate, 1.0)

    def test_weak_deal_grades_poorly(self) -> None:
        weak = StressInputs(
            base_ebitda=5_000_000, target_ebitda=6_000_000,
            base_revenue=50_000_000,
            entry_multiple=8.0, exit_multiple=8.5,
            debt_at_close=30_000_000, interest_rate=0.10,
            covenant_leverage=5.0, covenant_coverage=2.5,
            contract_labor_spend=15_000_000, lever_contribution=1_000_000,
            hold_years=5.0, base_moic=1.8,
            medicare_revenue=25_000_000, commercial_revenue=15_000_000,
        )
        grid = run_stress_grid(weak)
        self.assertIn(grid.robustness_grade, ("C", "D", "F"))

    def test_grid_to_dict_json_safe(self) -> None:
        import json
        grid = run_stress_grid(_stress_grid_inputs())
        json.dumps(grid.to_dict(), default=str)


# ── Operating posture ───────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ALL_POSTURES,
    PostureInputs,
    PostureResult,
    classify_posture,
    posture_from_stress_and_heuristics,
)
from rcm_mc.pe_intelligence.operating_posture import (
    POSTURE_BALANCED,
    POSTURE_CONCENTRATION_RISK,
    POSTURE_GROWTH_OPTIONAL,
    POSTURE_RESILIENT_CORE,
    POSTURE_SCENARIO_LEADER,
)


class TestClassifyPosture(unittest.TestCase):

    def test_scenario_leader(self) -> None:
        result = classify_posture(PostureInputs(
            downside_pass_rate=0.90, upside_capture_rate=0.80,
        ))
        self.assertEqual(result.posture, POSTURE_SCENARIO_LEADER)

    def test_resilient_core(self) -> None:
        result = classify_posture(PostureInputs(
            downside_pass_rate=0.90, upside_capture_rate=0.30,
        ))
        self.assertEqual(result.posture, POSTURE_RESILIENT_CORE)

    def test_growth_optional(self) -> None:
        result = classify_posture(PostureInputs(
            downside_pass_rate=0.40, upside_capture_rate=0.80,
        ))
        self.assertEqual(result.posture, POSTURE_GROWTH_OPTIONAL)

    def test_balanced_default(self) -> None:
        result = classify_posture(PostureInputs(
            downside_pass_rate=0.60, upside_capture_rate=0.55,
        ))
        self.assertEqual(result.posture, POSTURE_BALANCED)

    def test_concentration_risk_dominates(self) -> None:
        result = classify_posture(PostureInputs(
            downside_pass_rate=0.90, upside_capture_rate=0.70,
            concentration_flags=["payer_concentration_risk",
                                 "service_line_concentration"],
        ))
        self.assertEqual(result.posture, POSTURE_CONCENTRATION_RISK)

    def test_no_inputs_is_balanced_low_confidence(self) -> None:
        result = classify_posture(PostureInputs())
        self.assertEqual(result.posture, POSTURE_BALANCED)
        self.assertLess(result.confidence, 0.50)

    def test_posture_to_dict(self) -> None:
        import json
        result = classify_posture(PostureInputs(downside_pass_rate=0.90))
        json.dumps(result.to_dict())


class TestPostureFromStressAndHeuristics(unittest.TestCase):

    def test_pulls_from_grid_dict(self) -> None:
        stress_dict = {
            "downside_pass_rate": 0.90,
            "upside_capture_rate": 0.80,
            "n_covenant_breaches": 0,
            "robustness_grade": "A",
        }
        hits = []
        posture = posture_from_stress_and_heuristics(stress_dict, hits)
        self.assertEqual(posture.posture, POSTURE_SCENARIO_LEADER)


class TestStressAndPostureWiredIntoReview(unittest.TestCase):

    def test_review_includes_stress_scenarios(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
            ebitda_margin=0.10, leverage_multiple=5.0,
            exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
            projected_moic=2.3,
        )
        review = partner_review_from_context(ctx)
        self.assertIsNotNone(review.stress_scenarios)
        self.assertIn("robustness_grade", review.stress_scenarios)

    def test_review_includes_operating_posture(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
            ebitda_margin=0.10, leverage_multiple=5.0,
            exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
            projected_moic=2.3,
        )
        review = partner_review_from_context(ctx)
        self.assertIsNotNone(review.operating_posture)
        self.assertIn("posture", review.operating_posture)
        self.assertIn(review.operating_posture["posture"], ALL_POSTURES)


# ── White space ───────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    WhiteSpaceInputs,
    WhiteSpaceOpportunity,
    WhiteSpaceResult,
    detect_white_space,
    top_opportunities,
)


class TestDetectWhiteSpace(unittest.TestCase):

    def test_geographic_adjacency_scores_higher(self) -> None:
        # NY (existing), NJ (adjacent), CA (distant).
        result = detect_white_space(WhiteSpaceInputs(
            subsector="acute_care", state="NY",
            existing_states=["NY"],
            candidate_states=["NJ", "CA"],
        ))
        by_name = {o.name: o for o in result.opportunities
                   if o.dimension == "geographic"}
        self.assertIn("NJ", by_name)
        self.assertIn("CA", by_name)
        self.assertGreater(by_name["NJ"].score, by_name["CA"].score)

    def test_existing_state_excluded(self) -> None:
        result = detect_white_space(WhiteSpaceInputs(
            subsector="acute_care", existing_states=["TX"],
            candidate_states=["TX", "OK"],
        ))
        geo = {o.name for o in result.opportunities
               if o.dimension == "geographic"}
        self.assertNotIn("TX", geo)
        self.assertIn("OK", geo)

    def test_segment_registry_adjacency(self) -> None:
        # Acute-care registry adjacencies include "outpatient imaging".
        result = detect_white_space(WhiteSpaceInputs(
            subsector="acute_care",
            existing_segments=[],
            candidate_segments=[],
        ))
        segs = [o for o in result.opportunities if o.dimension == "segment"]
        self.assertTrue(any("outpatient imaging" in o.name for o in segs))

    def test_channel_registry_adjacency_for_behavioral(self) -> None:
        result = detect_white_space(WhiteSpaceInputs(
            subsector="behavioral",
        ))
        channels = [o for o in result.opportunities if o.dimension == "channel"]
        self.assertGreater(len(channels), 0)

    def test_existing_segments_excluded(self) -> None:
        result = detect_white_space(WhiteSpaceInputs(
            subsector="acute_care",
            existing_segments=["outpatient imaging"],
        ))
        segs = [o.name for o in result.opportunities
                if o.dimension == "segment"]
        self.assertNotIn("outpatient imaging", segs)

    def test_top_opportunities_n(self) -> None:
        result = detect_white_space(WhiteSpaceInputs(subsector="acute_care"))
        top = top_opportunities(result, n=2)
        self.assertEqual(len(top), min(2, len(result.opportunities)))

    def test_top_dimension_populated(self) -> None:
        result = detect_white_space(WhiteSpaceInputs(subsector="acute_care"))
        self.assertIn(result.top_dimension, ("geographic", "segment", "channel", None))

    def test_result_to_dict(self) -> None:
        import json
        result = detect_white_space(WhiteSpaceInputs(subsector="asc"))
        json.dumps(result.to_dict())


class TestWhiteSpaceWiredIntoReview(unittest.TestCase):

    def test_review_includes_white_space(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30,
            hospital_type="acute_care", state="TX",
        )
        review = partner_review_from_context(ctx)
        self.assertIsNotNone(review.white_space)
        self.assertIn("opportunities", review.white_space)

    def test_packet_fields_feed_into_white_space(self) -> None:
        packet = _make_packet_dict()
        packet["profile"]["existing_states"] = ["TX"]
        packet["profile"]["candidate_states"] = ["OK", "LA"]
        review = partner_review(packet)
        names = [o["name"] for o in review.white_space["opportunities"]
                 if o["dimension"] == "geographic"]
        self.assertIn("OK", names)


# ── Investability scorer ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    InvestabilityInputs,
    InvestabilityResult,
    investability_inputs_from_review,
    score_investability,
)


class TestInvestabilityScorer(unittest.TestCase):

    def test_strong_deal_scores_high(self) -> None:
        inputs = InvestabilityInputs(
            consolidation_play_score=0.70, fragmentation_verdict="fragmented",
            white_space_top_score=0.75,
            projected_irr=0.22, projected_moic=2.6,
            irr_verdict="IN_BAND", exit_multiple_verdict="IN_BAND",
            robustness_grade="A", downside_pass_rate=0.95,
            regime="durable_growth", posture="scenario_leader",
            n_critical_hits=0, n_high_hits=0, n_covenant_breaches=0,
        )
        result = score_investability(inputs)
        self.assertGreaterEqual(result.score, 80)
        self.assertIn(result.grade, ("A", "B"))

    def test_weak_deal_scores_low(self) -> None:
        inputs = InvestabilityInputs(
            fragmentation_verdict="consolidated",
            projected_irr=0.07, projected_moic=1.3,
            irr_verdict="OUT_OF_BAND", exit_multiple_verdict="IMPLAUSIBLE",
            robustness_grade="F", downside_pass_rate=0.10,
            regime="declining_risk", posture="concentration_risk",
            n_critical_hits=2, n_high_hits=3, n_covenant_breaches=2,
        )
        result = score_investability(inputs)
        self.assertLessEqual(result.score, 40)
        self.assertIn(result.grade, ("D", "F"))

    def test_strengths_and_weaknesses_populated(self) -> None:
        inputs = InvestabilityInputs(
            consolidation_play_score=0.70,
            projected_irr=0.22, projected_moic=2.8,
            irr_verdict="IN_BAND",
            robustness_grade="A", regime="durable_growth",
            posture="scenario_leader",
        )
        result = score_investability(inputs)
        self.assertGreater(len(result.strengths), 0)

    def test_empty_inputs_produces_neutral_score(self) -> None:
        result = score_investability(InvestabilityInputs())
        self.assertGreater(result.score, 30)
        self.assertLess(result.score, 70)

    def test_partner_note_mentions_grade(self) -> None:
        result = score_investability(InvestabilityInputs(
            projected_irr=0.22, irr_verdict="IN_BAND",
            robustness_grade="A",
        ))
        self.assertTrue(result.partner_note)

    def test_result_to_dict(self) -> None:
        import json
        result = score_investability(InvestabilityInputs())
        json.dumps(result.to_dict())


class TestInvestabilityWiredIntoReview(unittest.TestCase):

    def test_review_contains_investability(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
            ebitda_margin=0.10, leverage_multiple=5.0,
            exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
            projected_irr=0.20, projected_moic=2.3,
            hospital_type="acute_care", state="TX",
        )
        review = partner_review_from_context(ctx)
        self.assertIsNotNone(review.investability)
        self.assertIn("score", review.investability)
        self.assertIn("grade", review.investability)
        self.assertIn("partner_note", review.investability)

    def test_inputs_from_review_roundtrip(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
            projected_irr=0.20, projected_moic=2.3,
        )
        review = partner_review_from_context(ctx)
        inputs = investability_inputs_from_review(review)
        self.assertIsInstance(inputs, InvestabilityInputs)


class TestFullReviewToDict(unittest.TestCase):

    def test_to_dict_includes_all_six_fields(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30,
            hospital_type="acute_care", state="TX",
        )
        review = partner_review_from_context(ctx)
        d = review.to_dict()
        for key in ("regime", "market_structure", "stress_scenarios",
                    "operating_posture", "white_space", "investability"):
            self.assertIn(key, d)

    def test_to_dict_json_serializable_end_to_end(self) -> None:
        import json
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30,
            hospital_type="acute_care", state="TX",
        )
        review = partner_review_from_context(ctx)
        json.dumps(review.to_dict(), default=str)


# ── Extra heuristics ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    run_all_plus_extras,
    run_extra_heuristics,
)


class TestExtraHeuristics(unittest.TestCase):

    def test_clean_claim_low_fires(self) -> None:
        ctx = HeuristicContext(clean_claim_rate=0.82)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "clean_claim_rate_low" for h in hits))

    def test_clean_claim_high_does_not_fire(self) -> None:
        ctx = HeuristicContext(clean_claim_rate=0.93)
        hits = run_extra_heuristics(ctx)
        self.assertFalse(any(h.id == "clean_claim_rate_low" for h in hits))

    def test_growth_volatility_without_driver_fires(self) -> None:
        ctx = HeuristicContext(revenue_growth_pct_per_yr=15.0)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "growth_volatility_without_driver" for h in hits))

    def test_payer_contract_staleness_fires(self) -> None:
        ctx = HeuristicContext(clean_claim_rate=0.83,
                               denial_improvement_bps_per_yr=100)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "payer_contract_staleness" for h in hits))

    def test_large_deal_concentration_fires(self) -> None:
        ctx = HeuristicContext(ebitda_m=400)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "check_size_concentration" for h in hits))

    def test_missing_ttm_fires(self) -> None:
        ctx = HeuristicContext(data_coverage_pct=0.30)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "missing_ttm_kpi_reporting" for h in hits))

    def test_cah_teaching_mismatch_fires(self) -> None:
        ctx = HeuristicContext(hospital_type="critical_access",
                               teaching_status="major")
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "cah_teaching_mismatch" for h in hits))

    def test_urban_outpatient_premium_fires(self) -> None:
        ctx = HeuristicContext(
            hospital_type="outpatient", urban_rural="urban",
            payer_mix={"commercial": 0.70, "medicare": 0.20, "medicaid": 0.10},
            exit_multiple=13.0,
        )
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "urban_outpatient_gold_rush" for h in hits))

    def test_hold_moic_inconsistency_fires(self) -> None:
        # 4x MOIC in 3 years → ~59% CAGR.
        ctx = HeuristicContext(projected_moic=4.0, hold_years=3.0)
        hits = run_extra_heuristics(ctx)
        self.assertTrue(any(h.id == "hold_moic_inconsistency" for h in hits))

    def test_results_sorted_by_severity(self) -> None:
        ctx = HeuristicContext(
            clean_claim_rate=0.75, ebitda_m=400, data_coverage_pct=0.30,
            projected_moic=4.0, hold_years=3.0,
        )
        hits = run_extra_heuristics(ctx)
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        ranks = [order.get(h.severity, 5) for h in hits]
        self.assertEqual(ranks, sorted(ranks))


class TestRunAllPlusExtras(unittest.TestCase):

    def test_union_dedupes_by_id(self) -> None:
        ctx = HeuristicContext(
            clean_claim_rate=0.82,
            denial_improvement_bps_per_yr=400,  # base heuristic
        )
        hits = run_all_plus_extras(ctx)
        ids = [h.id for h in hits]
        self.assertEqual(len(ids), len(set(ids)))

    def test_union_includes_extras(self) -> None:
        ctx = HeuristicContext(clean_claim_rate=0.82)
        hits = run_all_plus_extras(ctx)
        self.assertTrue(any(h.id == "clean_claim_rate_low" for h in hits))


# ── Extra bands ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    check_bed_occupancy,
    check_capex_intensity,
    check_case_mix_index,
    check_length_of_stay,
    check_rvu_per_provider,
    run_extra_bands,
)


class TestCapexIntensityBand(unittest.TestCase):

    def test_acute_normal(self) -> None:
        r = check_capex_intensity(0.05, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_acute_above_ceiling(self) -> None:
        r = check_capex_intensity(0.18, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_missing_input_unknown(self) -> None:
        r = check_capex_intensity(None, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestBedOccupancyBand(unittest.TestCase):

    def test_acute_normal(self) -> None:
        r = check_bed_occupancy(0.65, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_acute_under_utilized(self) -> None:
        r = check_bed_occupancy(0.45, hospital_type="acute_care")
        self.assertIn(r.verdict, (VERDICT_OUT_OF_BAND, VERDICT_STRETCH,
                                  VERDICT_IMPLAUSIBLE))

    def test_unknown_sector_returns_unknown(self) -> None:
        r = check_bed_occupancy(0.85, hospital_type="asc")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestRVUPerProviderBand(unittest.TestCase):

    def test_outpatient_normal(self) -> None:
        r = check_rvu_per_provider(6200, hospital_type="outpatient")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_outpatient_high(self) -> None:
        # 9000 is above high=8000 but below stretch_high=10000 → STRETCH.
        r = check_rvu_per_provider(9000, hospital_type="outpatient")
        self.assertEqual(r.verdict, VERDICT_STRETCH)

    def test_ignores_non_outpatient(self) -> None:
        r = check_rvu_per_provider(6000, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestCMIBand(unittest.TestCase):

    def test_acute_normal(self) -> None:
        r = check_case_mix_index(1.45, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_ignores_non_acute(self) -> None:
        r = check_case_mix_index(1.45, hospital_type="asc")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_high_cmi_flagged(self) -> None:
        r = check_case_mix_index(4.0, hospital_type="acute_care")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)


class TestLOSBand(unittest.TestCase):

    def test_behavioral_normal(self) -> None:
        r = check_length_of_stay(12, hospital_type="behavioral")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_post_acute_extreme(self) -> None:
        r = check_length_of_stay(150, hospital_type="post_acute")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_ignores_non_applicable(self) -> None:
        r = check_length_of_stay(3, hospital_type="asc")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)


class TestRunExtraBands(unittest.TestCase):

    def test_orchestrator_produces_five_checks(self) -> None:
        checks = run_extra_bands(
            hospital_type="acute_care",
            capex_pct_of_revenue=0.05, bed_occupancy=0.65,
            rvu_per_provider=None, case_mix_index=1.50,
            avg_length_of_stay=None,
        )
        self.assertEqual(len(checks), 5)

    def test_missing_inputs_produce_unknowns(self) -> None:
        checks = run_extra_bands(hospital_type="acute_care")
        for c in checks:
            self.assertEqual(c.verdict, VERDICT_UNKNOWN)


# ── Narrative styles ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ALL_NARRATIVE_STYLES,
    compose_analyst_brief,
    compose_bullish_view,
    compose_founder_voice,
    compose_skeptic_view,
    compose_styled_narrative,
    compose_three_sentence,
)


def _sample_narrative_inputs():
    ctx = HeuristicContext(
        payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
        ebitda_m=30.0, hospital_type="acute_care",
        exit_multiple=11.0, entry_multiple=8.0,
        hold_years=5.0, projected_irr=0.18, projected_moic=2.3,
        denial_improvement_bps_per_yr=250,
    )
    review = partner_review_from_context(ctx)
    return review.reasonableness_checks, review.heuristic_hits


class TestNarrativeStyles(unittest.TestCase):

    def test_analyst_brief_shape(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_analyst_brief(
            bands=bands, hits=hits,
            hospital_type="acute_care", ebitda_m=30,
            payer_mix={"medicare": 0.60},
        )
        self.assertEqual(out["style"], "analyst_brief")
        self.assertIn("Recommendation", out["headline"])

    def test_skeptic_focuses_on_kills(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_skeptic_view(
            bands=bands, hits=hits,
            hospital_type="acute_care", ebitda_m=30,
            payer_mix={"medicare": 0.60},
        )
        self.assertEqual(out["style"], "skeptic")
        self.assertIn("Pre-mortem", out["headline"])

    def test_founder_voice_reads_like_target(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_founder_voice(
            bands=bands, hits=hits,
            hospital_type="acute_care", ebitda_m=30,
            payer_mix={"medicare": 0.60},
        )
        self.assertEqual(out["style"], "founder_voice")
        self.assertIn("founder", out["headline"].lower())

    def test_bullish_view(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_bullish_view(
            bands=bands, hits=hits,
            hospital_type="acute_care", ebitda_m=30,
            payer_mix={"medicare": 0.60},
        )
        self.assertEqual(out["style"], "bullish")

    def test_three_sentence_is_compact(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_three_sentence(
            bands=bands, hits=hits,
            hospital_type="acute_care", ebitda_m=30,
            payer_mix={"medicare": 0.60},
        )
        self.assertEqual(out["style"], "three_sentence")
        # Should be composed of ≤ 4 sentences.
        self.assertLessEqual(out["headline"].count("."), 4)

    def test_dispatcher_matches(self) -> None:
        bands, hits = _sample_narrative_inputs()
        for style in ALL_NARRATIVE_STYLES:
            out = compose_styled_narrative(
                style, bands=bands, hits=hits,
                hospital_type="acute_care", ebitda_m=30,
            )
            self.assertEqual(out["style"], style)

    def test_unknown_style_falls_back(self) -> None:
        bands, hits = _sample_narrative_inputs()
        out = compose_styled_narrative(
            "made_up", bands=bands, hits=hits,
        )
        self.assertEqual(out["style"], "analyst_brief")


# ── Memo formats ───────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    render_all_memo_formats,
    render_deck_bullets,
    render_memo_email,
    render_one_pager,
    render_pdf_ready,
    render_memo_slack,
)


class TestMemoFormats(unittest.TestCase):

    def _review(self):
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
            ebitda_margin=0.10, hospital_type="acute_care",
            exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
            projected_irr=0.20, projected_moic=2.3,
            denial_improvement_bps_per_yr=350,
        )
        return partner_review_from_context(ctx, deal_name="Demo Hospital")

    def test_one_pager_has_headline_and_rec(self) -> None:
        md = render_one_pager(self._review())
        self.assertIn("Recommendation", md)
        self.assertIn("Demo Hospital", md)

    def test_slack_format_uses_stars(self) -> None:
        txt = render_memo_slack(self._review())
        self.assertIn("*", txt)  # slack bold markers
        self.assertIn("Demo Hospital", txt)

    def test_email_returns_subject_and_body(self) -> None:
        email = render_memo_email(self._review())
        self.assertIn("subject", email)
        self.assertIn("body", email)
        self.assertIn("Demo Hospital", email["subject"])

    def test_pdf_ready_includes_pagebreaks(self) -> None:
        md = render_pdf_ready(self._review())
        self.assertIn("\\pagebreak", md)

    def test_deck_bullets_is_short_list(self) -> None:
        bullets = render_deck_bullets(self._review())
        self.assertIsInstance(bullets, list)
        self.assertLessEqual(len(bullets), 10)

    def test_all_formats_dispatcher(self) -> None:
        out = render_all_memo_formats(self._review())
        for key in ("one_pager", "slack", "email", "pdf_ready", "deck_bullets"):
            self.assertIn(key, out)


# ── Extra archetypes ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ExtraArchetypeContext,
    ExtraArchetypeHit,
    classify_extra_archetypes,
)


class TestExtraArchetypes(unittest.TestCase):

    def test_de_novo_build_fires(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_pre_revenue=True, has_ebitda=False,
        ))
        self.assertTrue(any(h.archetype == "de_novo_build" for h in hits))

    def test_jv_fires(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_jv=True, jv_partner_is_strategic=True,
        ))
        self.assertTrue(any(h.archetype == "joint_venture" for h in hits))

    def test_distressed_fires(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            covenant_in_breach=True, in_bankruptcy=True,
        ))
        self.assertTrue(any(h.archetype == "distressed_restructuring" for h in hits))

    def test_carveout_platform(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_carveout=True, has_rollup_thesis=True,
        ))
        self.assertTrue(any(h.archetype == "carveout_platform" for h in hits))

    def test_succession_transition(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_family_owned=True, founder_exiting=True,
        ))
        self.assertTrue(any(h.archetype == "succession_transition" for h in hits))

    def test_public_tender(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            tender_offer_planned=True,
        ))
        self.assertTrue(any(h.archetype == "public_to_private_tender" for h in hits))

    def test_spinco_rmt(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            rmt_structure=True,
        ))
        self.assertTrue(any(h.archetype == "spinco_carveout" for h in hits))

    def test_late_stage_growth(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_minority=True, pre_ipo=True, revenue_cagr=0.30,
        ))
        self.assertTrue(any(h.archetype == "late_stage_growth" for h in hits))

    def test_empty_context_no_fires(self) -> None:
        hits = classify_extra_archetypes(ExtraArchetypeContext())
        self.assertEqual(hits, [])

    def test_hit_to_dict_json(self) -> None:
        import json
        hits = classify_extra_archetypes(ExtraArchetypeContext(
            is_jv=True, jv_partner_is_strategic=True,
        ))
        json.dumps(hits[0].to_dict())


# ── Extra red flags ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    EXTRA_RED_FLAG_FIELDS,
    run_extra_red_flags,
)


def _ctx_with(**extras):
    ctx = HeuristicContext()
    for k, v in extras.items():
        setattr(ctx, k, v)
    return ctx


class TestExtraRedFlags(unittest.TestCase):

    def test_physician_turnover(self) -> None:
        hits = run_extra_red_flags(_ctx_with(physician_retention_pct=0.78))
        self.assertTrue(any(h.id == "physician_turnover_high" for h in hits))

    def test_rn_shortage_critical(self) -> None:
        hits = run_extra_red_flags(_ctx_with(unfilled_rn_positions_pct=0.28))
        hit = next(h for h in hits if h.id == "clinical_staff_shortage")
        self.assertEqual(hit.severity, "CRITICAL")

    def test_denial_spike(self) -> None:
        hits = run_extra_red_flags(_ctx_with(denial_rate_qoq_delta_bps=250))
        self.assertTrue(any(h.id == "payer_denial_spike" for h in hits))

    def test_bad_debt_spike(self) -> None:
        ctx = _ctx_with(bad_debt_growth_yoy_pct=20.0)
        ctx.revenue_growth_pct_per_yr = 5.0
        hits = run_extra_red_flags(ctx)
        self.assertTrue(any(h.id == "bad_debt_spike" for h in hits))

    def test_it_system_eol(self) -> None:
        ctx = _ctx_with(ehr_eol_years=3.0)
        ctx.hold_years = 5.0
        hits = run_extra_red_flags(ctx)
        self.assertTrue(any(h.id == "it_system_eol" for h in hits))

    def test_lease_cluster(self) -> None:
        hits = run_extra_red_flags(_ctx_with(leased_site_pct_expiring_in_hold=0.55))
        hit = next(h for h in hits if h.id == "lease_expiration_cluster")
        self.assertEqual(hit.severity, "HIGH")

    def test_open_inspection(self) -> None:
        hits = run_extra_red_flags(_ctx_with(open_cms_inspection="2023 OIG review"))
        self.assertTrue(any(h.id == "regulatory_inspection_open" for h in hits))

    def test_self_insurance_gap(self) -> None:
        hits = run_extra_red_flags(_ctx_with(self_insurance_reserve_gap_m=12.0))
        self.assertTrue(any(h.id == "self_insurance_tail" for h in hits))

    def test_capex_deferral(self) -> None:
        hits = run_extra_red_flags(_ctx_with(capex_to_da_ratio=0.50))
        self.assertTrue(any(h.id == "capex_deferral_pattern" for h in hits))

    def test_key_payer_churn(self) -> None:
        hits = run_extra_red_flags(_ctx_with(top_payer_churn_risk="Aetna contract expires Q2 2027"))
        self.assertTrue(any(h.id == "key_payer_churn" for h in hits))

    def test_empty_context_no_fires(self) -> None:
        hits = run_extra_red_flags(HeuristicContext())
        self.assertEqual(hits, [])

    def test_fields_list_non_empty(self) -> None:
        self.assertGreaterEqual(len(EXTRA_RED_FLAG_FIELDS), 10)


# ── Scenario narrative ──────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ScenarioNarrativeResult,
    render_scenario_markdown,
    render_scenario_narrative,
)


def _scenario_grid_from_stress():
    # Build a grid via the real stress_test orchestrator.
    inputs = StressInputs(
        base_ebitda=30_000_000, target_ebitda=45_000_000,
        base_revenue=250_000_000, entry_multiple=8.0, exit_multiple=9.5,
        debt_at_close=150_000_000, interest_rate=0.09,
        covenant_leverage=6.0, covenant_coverage=2.0,
        contract_labor_spend=30_000_000, lever_contribution=15_000_000,
        hold_years=5.0, base_moic=2.5,
        medicare_revenue=100_000_000, commercial_revenue=120_000_000,
    )
    return run_stress_grid(inputs).to_dict()


class TestScenarioNarrative(unittest.TestCase):

    def test_narrative_has_all_sections(self) -> None:
        grid = _scenario_grid_from_stress()
        narr = render_scenario_narrative(grid)
        self.assertIsInstance(narr, ScenarioNarrativeResult)
        self.assertTrue(narr.headline)
        self.assertTrue(narr.worst_case_sentence)
        self.assertTrue(narr.passing_downside_summary)

    def test_grade_a_headline(self) -> None:
        grid = {"robustness_grade": "A", "downside_pass_rate": 0.95,
                "outcomes": []}
        narr = render_scenario_narrative(grid)
        self.assertIn("durable", narr.headline.lower())

    def test_grade_f_headline(self) -> None:
        grid = {"robustness_grade": "F", "downside_pass_rate": 0.10,
                "outcomes": []}
        narr = render_scenario_narrative(grid)
        self.assertIn("brittle", narr.headline.lower())

    def test_empty_outcomes_no_crash(self) -> None:
        narr = render_scenario_narrative({})
        self.assertIsInstance(narr, ScenarioNarrativeResult)

    def test_markdown_contains_worst_case(self) -> None:
        grid = _scenario_grid_from_stress()
        md = render_scenario_markdown(grid)
        self.assertIn("Worst case", md)
        self.assertIn("Absorbs", md)

    def test_result_to_dict_serializable(self) -> None:
        import json
        grid = _scenario_grid_from_stress()
        narr = render_scenario_narrative(grid)
        json.dumps(narr.to_dict())


# ── Deal comparison ──────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ComparisonFinding,
    ComparisonResult,
    compare_reviews,
    render_comparison_markdown,
)


def _review_for_compare(*, irr, moic, leverage, grade_hint="B", deal_id="x"):
    ctx = HeuristicContext(
        payer_mix={"commercial": 0.55}, ebitda_m=30, revenue_m=250,
        ebitda_margin=0.10, leverage_multiple=leverage,
        exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
        projected_irr=irr, projected_moic=moic,
        hospital_type="acute_care", state="TX",
    )
    return partner_review_from_context(ctx, deal_id=deal_id)


class TestDealComparison(unittest.TestCase):

    def test_better_irr_wins_irr_dimension(self) -> None:
        a = _review_for_compare(irr=0.25, moic=2.8, leverage=4.5, deal_id="A")
        b = _review_for_compare(irr=0.15, moic=2.0, leverage=5.5, deal_id="B")
        result = compare_reviews(a, b)
        irr_f = next(f for f in result.findings if f.dimension == "projected_irr")
        self.assertEqual(irr_f.winner, "left")

    def test_lower_leverage_wins(self) -> None:
        a = _review_for_compare(irr=0.20, moic=2.3, leverage=4.0, deal_id="A")
        b = _review_for_compare(irr=0.20, moic=2.3, leverage=6.0, deal_id="B")
        result = compare_reviews(a, b)
        lev = next(f for f in result.findings if f.dimension == "leverage_multiple")
        self.assertEqual(lev.winner, "left")

    def test_overall_winner_populated(self) -> None:
        a = _review_for_compare(irr=0.25, moic=2.8, leverage=4.0, deal_id="A")
        b = _review_for_compare(irr=0.15, moic=2.0, leverage=6.5, deal_id="B")
        result = compare_reviews(a, b)
        self.assertEqual(result.overall_winner, "left")

    def test_tied_deals_tie_overall(self) -> None:
        a = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0, deal_id="A")
        b = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0, deal_id="B")
        result = compare_reviews(a, b)
        self.assertEqual(result.overall_winner, "tie")

    def test_markdown_has_table_headers(self) -> None:
        a = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0, deal_id="A")
        b = _review_for_compare(irr=0.18, moic=2.1, leverage=5.5, deal_id="B")
        result = compare_reviews(a, b)
        md = render_comparison_markdown(result)
        self.assertIn("| Dimension", md)
        self.assertIn("A", md)
        self.assertIn("B", md)

    def test_to_dict_json_roundtrip(self) -> None:
        import json
        a = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0, deal_id="A")
        b = _review_for_compare(irr=0.18, moic=2.1, leverage=5.5, deal_id="B")
        result = compare_reviews(a, b)
        json.dumps(result.to_dict(), default=str)


# ── Priority scoring ───────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    PriorityInputs,
    PriorityScore,
    rank_deal_portfolio,
    render_priority_list_markdown,
    score_deal_priority,
)


class TestPriorityScoring(unittest.TestCase):

    def test_urgent_deal_scores_high(self) -> None:
        review = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                     deal_id="U")
        score = score_deal_priority(
            review, PriorityInputs(urgency_days=2),
        )
        self.assertGreater(score.urgency_score, 0.90)

    def test_flagship_adds_strategic_score(self) -> None:
        review = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                     deal_id="F")
        score = score_deal_priority(
            review, PriorityInputs(is_flagship=True),
        )
        self.assertGreater(score.strategic_score, 0.0)

    def test_blocked_zeroes_leverage(self) -> None:
        review = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                     deal_id="B")
        score = score_deal_priority(
            review, PriorityInputs(is_blocked=True),
        )
        self.assertEqual(score.leverage_score, 0.0)

    def test_rank_populates_order(self) -> None:
        reviews = [
            _review_for_compare(irr=0.22, moic=2.5, leverage=4.5, deal_id="A"),
            _review_for_compare(irr=0.18, moic=2.1, leverage=5.0, deal_id="B"),
            _review_for_compare(irr=0.12, moic=1.8, leverage=6.0, deal_id="C"),
        ]
        inputs = [
            PriorityInputs(urgency_days=5, is_flagship=True),     # A
            PriorityInputs(urgency_days=60),                        # B
            PriorityInputs(urgency_days=90),                        # C
        ]
        ranked = rank_deal_portfolio(list(zip(reviews, inputs)))
        self.assertEqual(ranked[0].deal_id, "A")
        self.assertEqual(ranked[0].rank, 1)
        self.assertEqual(ranked[-1].rank, 3)

    def test_bare_review_acceptable(self) -> None:
        reviews = [_review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                       deal_id="X")]
        ranked = rank_deal_portfolio(reviews)
        self.assertEqual(len(ranked), 1)
        self.assertIsNotNone(ranked[0].composite)

    def test_markdown_table_renders(self) -> None:
        reviews = [_review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                       deal_id="X")]
        md = render_priority_list_markdown(rank_deal_portfolio(reviews))
        self.assertIn("Deal priority queue", md)
        self.assertIn("| Rank", md)

    def test_score_to_dict(self) -> None:
        import json
        review = _review_for_compare(irr=0.20, moic=2.3, leverage=5.0,
                                     deal_id="X")
        score = score_deal_priority(review, None)
        json.dumps(score.to_dict())


# ── Board memo ─────────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    render_board_memo,
    render_board_memo_markdown,
)


class TestBoardMemo(unittest.TestCase):

    def test_board_memo_has_all_sections(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30,
            hospital_type="acute_care",
        )
        review = partner_review_from_context(ctx, deal_name="Test Co.")
        d = render_board_memo(review)
        for key in ("deal_name", "board_recommendation",
                    "executive_summary", "fiduciary_reminder",
                    "approval_matrix", "required_disclosures",
                    "action_list"):
            self.assertIn(key, d)

    def test_board_rec_translates_ic_rec(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55}, ebitda_m=30,
                               hospital_type="acute_care")
        review = partner_review_from_context(ctx)
        d = render_board_memo(review)
        self.assertIn(d["board_recommendation"],
                      {"APPROVE", "APPROVE subject to caveats", "DECLINE"})

    def test_pass_becomes_decline(self) -> None:
        ctx = HeuristicContext(denial_improvement_bps_per_yr=700)
        review = partner_review_from_context(ctx)
        d = render_board_memo(review)
        self.assertEqual(d["board_recommendation"], "DECLINE")

    def test_disclosures_include_lpa_reminder(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55}, ebitda_m=30,
                               hospital_type="acute_care")
        review = partner_review_from_context(ctx)
        d = render_board_memo(review)
        text = " ".join(d["required_disclosures"])
        self.assertIn("LPA", text)

    def test_approval_matrix_has_core_items(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55}, ebitda_m=30,
                               hospital_type="acute_care")
        review = partner_review_from_context(ctx)
        d = render_board_memo(review)
        items = {row["item"] for row in d["approval_matrix"]}
        self.assertIn("Final purchase price / valuation", items)
        self.assertIn("Capital structure at close (debt, equity)", items)

    def test_markdown_renders(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55}, ebitda_m=30,
                               hospital_type="acute_care")
        review = partner_review_from_context(ctx, deal_name="Test Co.")
        md = render_board_memo_markdown(review)
        self.assertIn("# Board Memo — Test Co.", md)
        self.assertIn("## Fiduciary reminder", md)
        self.assertIn("## Approval matrix", md)

    def test_json_serializable(self) -> None:
        import json
        ctx = HeuristicContext(payer_mix={"commercial": 0.55}, ebitda_m=30,
                               hospital_type="acute_care")
        d = render_board_memo(partner_review_from_context(ctx))
        json.dumps(d)


# ── Contract diligence ─────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ContractPortfolio,
    ContractRisk,
    PayerContract,
    analyze_contract_portfolio,
    render_contract_diligence_markdown,
)


class TestContractScoring(unittest.TestCase):

    def test_high_risk_contract_scored_high(self) -> None:
        c = PayerContract(
            payer_name="BCBS-TX", revenue_share=0.35,
            expiry_years=2.0, termination_mechanic="at_will",
            rate_reset_mechanic="cpi_only",
            is_top3=True,
        )
        pf = analyze_contract_portfolio([c], hold_years=5.0)
        self.assertEqual(len(pf.per_contract), 1)
        self.assertGreater(pf.per_contract[0].score, 0.60)
        self.assertEqual(pf.per_contract[0].action, "renegotiate_pre_close")

    def test_safe_contract_scored_low(self) -> None:
        c = PayerContract(
            payer_name="SmallRegional", revenue_share=0.05,
            expiry_years=8.0, termination_mechanic="standard",
            rate_reset_mechanic="market",
        )
        pf = analyze_contract_portfolio([c], hold_years=5.0)
        self.assertLess(pf.per_contract[0].score, 0.35)
        self.assertEqual(pf.per_contract[0].action, "note")

    def test_maturity_wall_summed(self) -> None:
        contracts = [
            PayerContract(payer_name="A", revenue_share=0.30,
                          expiry_years=2.0),
            PayerContract(payer_name="B", revenue_share=0.20,
                          expiry_years=3.0),
            PayerContract(payer_name="C", revenue_share=0.10,
                          expiry_years=8.0),
        ]
        pf = analyze_contract_portfolio(contracts, hold_years=5.0)
        self.assertAlmostEqual(pf.maturity_wall_pct, 0.50, places=2)

    def test_top3_concentration(self) -> None:
        contracts = [
            PayerContract(payer_name=f"P{i}", revenue_share=s)
            for i, s in enumerate([0.30, 0.25, 0.15, 0.10, 0.08])
        ]
        pf = analyze_contract_portfolio(contracts, hold_years=5.0)
        self.assertAlmostEqual(pf.portfolio_concentration, 0.70, places=2)

    def test_volatile_state_government_score(self) -> None:
        c = PayerContract(
            payer_name="IL-Medicaid", revenue_share=0.20,
            is_government=True, state="IL",
            expiry_years=3.0,
        )
        pf = analyze_contract_portfolio([c], hold_years=5.0)
        flags = pf.per_contract[0].flags
        self.assertTrue(any("IL" in f or "volatile" in f for f in flags))

    def test_empty_portfolio(self) -> None:
        pf = analyze_contract_portfolio([], hold_years=5.0)
        self.assertEqual(pf.per_contract, [])
        self.assertEqual(pf.maturity_wall_pct, 0.0)
        self.assertEqual(pf.high_risk_count, 0)

    def test_actions_list_prioritizes_high_risk(self) -> None:
        c = PayerContract(
            payer_name="BadContract", revenue_share=0.40,
            expiry_years=2.0, termination_mechanic="at_will",
            is_top3=True,
        )
        pf = analyze_contract_portfolio([c], hold_years=5.0)
        self.assertTrue(any("BadContract" in a for a in pf.actions_needed))

    def test_markdown_renders(self) -> None:
        c = PayerContract(payer_name="P", revenue_share=0.20, expiry_years=3.0)
        md = render_contract_diligence_markdown(
            analyze_contract_portfolio([c], hold_years=5.0))
        self.assertIn("# Payer contract diligence", md)

    def test_portfolio_to_dict(self) -> None:
        import json
        c = PayerContract(payer_name="P", revenue_share=0.20, expiry_years=3.0)
        pf = analyze_contract_portfolio([c], hold_years=5.0)
        json.dumps(pf.to_dict())


# ── Service-line analysis ─────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ServiceLine,
    ServiceLinePortfolio,
    ServiceLineRisk,
    analyze_service_lines,
    render_service_lines_markdown,
)


class TestServiceLineAnalysis(unittest.TestCase):

    def test_anchor_dependent_verdict(self) -> None:
        lines = [
            ServiceLine(name="Cardiology", revenue_share=0.55,
                        ebitda_margin=0.20),
            ServiceLine(name="Ortho", revenue_share=0.20,
                        ebitda_margin=0.15),
            ServiceLine(name="General", revenue_share=0.15,
                        ebitda_margin=0.08),
            ServiceLine(name="Other", revenue_share=0.10,
                        ebitda_margin=0.05),
        ]
        pf = analyze_service_lines(lines)
        self.assertEqual(pf.portfolio_verdict, "anchor_dependent")
        self.assertAlmostEqual(pf.concentration_top_line, 0.55, places=2)

    def test_well_diversified_verdict(self) -> None:
        lines = [
            ServiceLine(name=f"L{i}", revenue_share=0.125,
                        ebitda_margin=0.10)
            for i in range(8)
        ]
        pf = analyze_service_lines(lines)
        self.assertEqual(pf.portfolio_verdict, "well_diversified")

    def test_specialty_concentration_verdict(self) -> None:
        # Top line is 25% revenue but carries most of the EBITDA.
        lines = [
            ServiceLine(name="HighMargin", revenue_share=0.25,
                        ebitda_margin=0.35),
            ServiceLine(name="LowA", revenue_share=0.25,
                        ebitda_margin=0.05),
            ServiceLine(name="LowB", revenue_share=0.25,
                        ebitda_margin=0.05),
            ServiceLine(name="LowC", revenue_share=0.25,
                        ebitda_margin=0.05),
        ]
        pf = analyze_service_lines(lines)
        self.assertEqual(pf.portfolio_verdict, "specialty_concentration")

    def test_reimbursement_exposure_compounds(self) -> None:
        line = ServiceLine(name="Cardio", revenue_share=0.35,
                           ebitda_margin=0.20,
                           is_reimbursement_exposed=True)
        pf = analyze_service_lines([line])
        risk = pf.per_line[0]
        self.assertGreater(risk.risk_score, 0.80)

    def test_ebitda_contribution_sums_to_one(self) -> None:
        lines = [
            ServiceLine(name="A", revenue_share=0.50, ebitda_margin=0.10),
            ServiceLine(name="B", revenue_share=0.30, ebitda_margin=0.15),
            ServiceLine(name="C", revenue_share=0.20, ebitda_margin=0.05),
        ]
        pf = analyze_service_lines(lines)
        total = sum(r.ebitda_contribution_share for r in pf.per_line)
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_empty_returns_unknown(self) -> None:
        pf = analyze_service_lines([])
        self.assertEqual(pf.portfolio_verdict, "unknown")

    def test_markdown_renders(self) -> None:
        lines = [ServiceLine(name="Test", revenue_share=0.5,
                             ebitda_margin=0.10)]
        md = render_service_lines_markdown(analyze_service_lines(lines))
        self.assertIn("# Service-line portfolio", md)

    def test_portfolio_json_serializable(self) -> None:
        import json
        lines = [ServiceLine(name="Test", revenue_share=0.5,
                             ebitda_margin=0.10)]
        pf = analyze_service_lines(lines)
        json.dumps(pf.to_dict())


# ── Quality metrics ───────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    QualityImpact,
    QualityInputs,
    QualityProfile,
    analyze_quality_profile,
    render_quality_profile_markdown,
)


class TestQualityMetrics(unittest.TestCase):

    def test_top_quality_leader(self) -> None:
        pf = analyze_quality_profile(QualityInputs(
            cms_star_rating=4.5, readmission_percentile=15,
            hcahps_percentile=85, hac_program_bottom_quartile=False,
            mortality_percentile=20,
            annual_medicare_revenue=100_000_000,
        ))
        self.assertEqual(pf.verdict, "leader")
        self.assertGreater(pf.total_payment_impact, 0)

    def test_drag_profile(self) -> None:
        pf = analyze_quality_profile(QualityInputs(
            cms_star_rating=1.5, readmission_percentile=85,
            hcahps_percentile=15, hac_program_bottom_quartile=True,
            mortality_percentile=80,
            annual_medicare_revenue=100_000_000,
        ))
        self.assertEqual(pf.verdict, "drag")
        self.assertLess(pf.total_payment_impact, 0)

    def test_average_stays_neutral(self) -> None:
        pf = analyze_quality_profile(QualityInputs(
            cms_star_rating=3.0, readmission_percentile=50,
            hcahps_percentile=55, hac_program_bottom_quartile=False,
            mortality_percentile=50,
            annual_medicare_revenue=100_000_000,
        ))
        self.assertIn(pf.verdict, ("average", "leader"))

    def test_missing_metrics_returns_unknown(self) -> None:
        pf = analyze_quality_profile(QualityInputs())
        self.assertEqual(pf.verdict, "unknown")

    def test_hrrp_penalty_scales_with_medicare_revenue(self) -> None:
        pf1 = analyze_quality_profile(QualityInputs(
            readmission_percentile=80,
            annual_medicare_revenue=100_000_000,
        ))
        pf2 = analyze_quality_profile(QualityInputs(
            readmission_percentile=80,
            annual_medicare_revenue=200_000_000,
        ))
        # pf2 should have more-negative impact.
        self.assertLess(pf2.total_payment_impact, pf1.total_payment_impact)

    def test_markdown_renders(self) -> None:
        pf = analyze_quality_profile(QualityInputs(
            cms_star_rating=4.0,
            annual_medicare_revenue=100_000_000,
        ))
        md = render_quality_profile_markdown(pf)
        self.assertIn("# Quality metrics profile", md)

    def test_profile_json(self) -> None:
        import json
        pf = analyze_quality_profile(QualityInputs(cms_star_rating=3.5))
        json.dumps(pf.to_dict())


# ── Labor cost analytics ───────────────────────────────────────

from rcm_mc.pe_intelligence import (
    LaborFinding,
    LaborInputs,
    LaborProfile,
    analyze_labor_profile,
    render_labor_profile_markdown,
)


class TestLaborAnalytics(unittest.TestCase):

    def test_strong_profile(self) -> None:
        pf = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.05, overtime_share=0.03,
            nurse_patient_ratio=4.0, wage_growth_yoy=0.03,
            local_cpi=0.03, productivity_volume_per_fte=1.10,
            peer_productivity=1.00, total_labor_spend=200_000_000,
        ))
        self.assertEqual(pf.verdict, "strong")

    def test_drag_profile(self) -> None:
        pf = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.28, overtime_share=0.20,
            nurse_patient_ratio=8.5, wage_growth_yoy=0.07,
            local_cpi=0.03, productivity_volume_per_fte=0.80,
            peer_productivity=1.00, total_labor_spend=200_000_000,
        ))
        self.assertEqual(pf.verdict, "drag")

    def test_shock_impact_scales(self) -> None:
        pf1 = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.10, total_labor_spend=100_000_000,
        ))
        pf2 = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.10, total_labor_spend=300_000_000,
        ))
        self.assertLess(pf2.shock_impact_10pct_wage,
                        pf1.shock_impact_10pct_wage)

    def test_productivity_lever_scales(self) -> None:
        pf = analyze_labor_profile(LaborInputs(
            total_labor_spend=100_000_000, contract_labor_share=0.10,
        ))
        self.assertAlmostEqual(pf.lever_savings_5pct_productivity,
                               5_000_000, delta=1)

    def test_empty_returns_unknown(self) -> None:
        pf = analyze_labor_profile(LaborInputs())
        self.assertEqual(pf.verdict, "unknown")

    def test_markdown_renders(self) -> None:
        pf = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.12, total_labor_spend=100_000_000,
        ))
        md = render_labor_profile_markdown(pf)
        self.assertIn("# Labor profile", md)

    def test_profile_json(self) -> None:
        import json
        pf = analyze_labor_profile(LaborInputs(
            contract_labor_share=0.10,
        ))
        json.dumps(pf.to_dict())


# ── Analyst cheatsheet ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    build_cheatsheet,
    render_cheatsheet_markdown,
)


class TestAnalystCheatsheet(unittest.TestCase):

    def _review(self):
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
            ebitda_m=30, revenue_m=250, ebitda_margin=0.10,
            hospital_type="acute_care", state="TX",
            exit_multiple=11.0, entry_multiple=8.0, hold_years=5,
            projected_irr=0.22, projected_moic=2.5,
            leverage_multiple=5.0, denial_improvement_bps_per_yr=350,
        )
        return partner_review_from_context(ctx, deal_name="Demo")

    def test_cheatsheet_has_all_sections(self) -> None:
        sheet = build_cheatsheet(self._review())
        for key in ("deal_id", "deal_name", "recommendation",
                    "top_facts", "top_flags", "top_questions",
                    "quick_numbers"):
            self.assertIn(key, sheet)

    def test_top_flags_limited_to_five(self) -> None:
        sheet = build_cheatsheet(self._review())
        self.assertLessEqual(len(sheet["top_flags"]), 5)

    def test_top_questions_limited_to_three(self) -> None:
        sheet = build_cheatsheet(self._review())
        self.assertLessEqual(len(sheet["top_questions"]), 3)

    def test_quick_numbers_populated(self) -> None:
        sheet = build_cheatsheet(self._review())
        qn = sheet["quick_numbers"]
        for key in ("irr", "moic", "leverage", "investability", "stress_grade"):
            self.assertIn(key, qn)

    def test_markdown_renders(self) -> None:
        md = render_cheatsheet_markdown(self._review())
        self.assertIn("Analyst Cheatsheet", md)
        self.assertIn("Quick numbers", md)
        self.assertIn("Top flags", md)


# ── Reimbursement bands ───────────────────────────────────────

from rcm_mc.pe_intelligence import (
    check_gross_to_net,
    check_payer_rate_growth,
    check_site_neutral_parity,
    run_reimbursement_bands,
)


class TestPayerRateGrowth(unittest.TestCase):

    def test_medicare_normal(self) -> None:
        r = check_payer_rate_growth(0.02, payer="medicare")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_commercial_aggressive_flagged(self) -> None:
        r = check_payer_rate_growth(0.12, payer="commercial")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_unknown_payer_unknown(self) -> None:
        r = check_payer_rate_growth(0.03, payer="made_up")
        self.assertEqual(r.verdict, VERDICT_UNKNOWN)

    def test_negative_medicaid_out_of_band(self) -> None:
        # -2% in medicaid is in `STRETCH` territory per the band.
        r = check_payer_rate_growth(-0.03, payer="medicaid")
        self.assertIn(r.verdict, (VERDICT_STRETCH, VERDICT_OUT_OF_BAND,
                                  VERDICT_IMPLAUSIBLE))


class TestGrossToNet(unittest.TestCase):

    def test_commercial_mid_range(self) -> None:
        r = check_gross_to_net(0.55, payer="commercial")
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_medicare_extreme_implausible(self) -> None:
        r = check_gross_to_net(0.80, payer="medicare")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)

    def test_medicaid_too_low(self) -> None:
        r = check_gross_to_net(0.05, payer="medicaid")
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)


class TestSiteNeutral(unittest.TestCase):

    def test_normal_parity(self) -> None:
        r = check_site_neutral_parity(1.40)
        self.assertEqual(r.verdict, VERDICT_IN_BAND)

    def test_too_high(self) -> None:
        r = check_site_neutral_parity(2.50)
        self.assertEqual(r.verdict, VERDICT_IMPLAUSIBLE)


class TestRunReimbursementBands(unittest.TestCase):

    def test_orchestrator_runs_all(self) -> None:
        checks = run_reimbursement_bands(
            payer_rate_growths={"medicare": 0.02, "commercial": 0.045},
            gross_to_net_ratios={"medicare": 0.32, "commercial": 0.55},
            hopd_asc_parity=1.40,
        )
        self.assertEqual(len(checks), 5)

    def test_empty_produces_empty(self) -> None:
        self.assertEqual(run_reimbursement_bands(), [])


# ── EBITDA quality ─────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    AddbackFinding,
    EBITDAAddback,
    EBITDAQualityReport,
    assess_ebitda_quality,
    render_ebitda_quality_markdown,
)


class TestEBITDAQuality(unittest.TestCase):

    def test_clean_ebitda_is_high_quality(self) -> None:
        report = assess_ebitda_quality(
            reported_ebitda=50_000_000,
            addbacks=[
                EBITDAAddback(name="legal_settlement", amount=500_000,
                              category="one_time", evidence="documented"),
            ],
        )
        self.assertEqual(report.quality_verdict, "high")

    def test_synergy_heavy_is_implausible(self) -> None:
        report = assess_ebitda_quality(
            reported_ebitda=30_000_000,
            addbacks=[
                EBITDAAddback(name="run_rate_synergy", amount=10_000_000,
                              category="synergy", evidence="projected"),
                EBITDAAddback(name="rent_addback", amount=8_000_000,
                              category="normalization", evidence="estimated"),
            ],
        )
        self.assertIn(report.quality_verdict, ("implausible", "low"))
        # Partner EBITDA should be materially lower than reported + gross.
        self.assertLess(report.partner_ebitda,
                        report.reported_ebitda + report.gross_addbacks)

    def test_haircut_scaled_by_category(self) -> None:
        report = assess_ebitda_quality(
            reported_ebitda=10_000_000,
            addbacks=[
                EBITDAAddback(name="real", amount=1_000_000,
                              category="one_time", evidence="documented"),
                EBITDAAddback(name="phantom", amount=1_000_000,
                              category="synergy", evidence="projected"),
            ],
        )
        # Synergy haircut >= one_time haircut.
        haircuts = {f.addback.name: f.haircut_pct for f in report.findings}
        self.assertGreaterEqual(haircuts["phantom"], haircuts["real"])

    def test_documented_synergy_still_aggressive(self) -> None:
        report = assess_ebitda_quality(
            reported_ebitda=10_000_000,
            addbacks=[
                EBITDAAddback(name="planned_synergy", amount=2_000_000,
                              category="synergy", evidence="documented"),
            ],
        )
        finding = report.findings[0]
        self.assertEqual(finding.classification, "aggressive")

    def test_empty_addbacks_high_quality(self) -> None:
        report = assess_ebitda_quality(reported_ebitda=50_000_000,
                                        addbacks=[])
        self.assertEqual(report.quality_verdict, "high")
        self.assertEqual(report.gross_addbacks, 0)

    def test_report_to_dict(self) -> None:
        import json
        report = assess_ebitda_quality(
            reported_ebitda=20_000_000,
            addbacks=[EBITDAAddback(name="x", amount=1_000_000,
                                    category="one_time")],
        )
        json.dumps(report.to_dict())

    def test_markdown_renders(self) -> None:
        report = assess_ebitda_quality(
            reported_ebitda=20_000_000,
            addbacks=[EBITDAAddback(name="x", amount=1_000_000,
                                    category="one_time")],
        )
        md = render_ebitda_quality_markdown(report)
        self.assertIn("EBITDA quality report", md)


# ── Covenant monitor ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CovenantDefinition,
    CovenantObservation,
    CovenantReport,
    CovenantStatus,
    evaluate_covenant,
    monitor_covenants,
    render_covenant_report_markdown,
)


class TestCovenantMonitor(unittest.TestCase):

    def test_comfortable_leverage_is_green(self) -> None:
        d = CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0)
        s = evaluate_covenant(d, observed=4.0, debt=100_000_000)
        self.assertEqual(s.status, "green")

    def test_tight_leverage_is_amber(self) -> None:
        d = CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0)
        s = evaluate_covenant(d, observed=5.5, debt=100_000_000)
        self.assertEqual(s.status, "amber")

    def test_breached_leverage_is_red(self) -> None:
        d = CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0)
        s = evaluate_covenant(d, observed=5.95)
        self.assertEqual(s.status, "red")

    def test_coverage_min_direction(self) -> None:
        d = CovenantDefinition(name="interest_coverage", direction="min",
                               threshold=2.0)
        s = evaluate_covenant(d, observed=3.0, interest=10_000_000)
        self.assertEqual(s.status, "green")

    def test_break_ebitda_computed_for_leverage(self) -> None:
        d = CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0)
        s = evaluate_covenant(d, observed=5.0, debt=150_000_000)
        # Break EBITDA = debt / threshold = 150M / 6 = 25M.
        self.assertAlmostEqual(s.break_ebitda, 25_000_000, delta=1)

    def test_break_ebitda_computed_for_coverage(self) -> None:
        d = CovenantDefinition(name="interest_coverage", direction="min",
                               threshold=2.5)
        s = evaluate_covenant(d, observed=3.0, interest=10_000_000)
        # Break EBITDA = threshold * interest = 2.5 * 10M = 25M.
        self.assertAlmostEqual(s.break_ebitda, 25_000_000, delta=1)

    def test_trend_projection(self) -> None:
        d = CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0)
        s = evaluate_covenant(d, observed=4.0, trend_per_quarter=0.30)
        self.assertAlmostEqual(s.projected_next_q, 4.30, places=2)

    def test_monitor_report_with_mix(self) -> None:
        defs = [
            CovenantDefinition(name="net_leverage", direction="max",
                               threshold=6.0),
            CovenantDefinition(name="interest_coverage", direction="min",
                               threshold=2.0),
        ]
        obs = [
            CovenantObservation(covenant_name="net_leverage",
                                observed_value=5.95),       # red
            CovenantObservation(covenant_name="interest_coverage",
                                observed_value=3.0),        # green
        ]
        report = monitor_covenants(defs, obs, debt=100_000_000,
                                   interest=8_000_000)
        self.assertEqual(report.worst_status, "red")
        self.assertEqual(report.red_count, 1)

    def test_no_observations_produces_empty(self) -> None:
        report = monitor_covenants([CovenantDefinition(
            name="net_leverage", direction="max", threshold=6.0,
        )], [])
        self.assertEqual(report.statuses, [])

    def test_markdown_renders(self) -> None:
        defs = [CovenantDefinition(name="net_leverage", direction="max",
                                   threshold=6.0)]
        obs = [CovenantObservation(covenant_name="net_leverage",
                                   observed_value=4.5)]
        md = render_covenant_report_markdown(
            monitor_covenants(defs, obs, debt=100_000_000))
        self.assertIn("# Covenant monitor", md)

    def test_report_json(self) -> None:
        import json
        defs = [CovenantDefinition(name="net_leverage", direction="max",
                                   threshold=6.0)]
        obs = [CovenantObservation(covenant_name="net_leverage",
                                   observed_value=4.5)]
        r = monitor_covenants(defs, obs, debt=100_000_000)
        json.dumps(r.to_dict())


# ── Liquidity monitor ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    CashWeek,
    LiquidityReport,
    project_cash_detail,
    project_cash_runway,
    render_liquidity_markdown,
)


class TestLiquidityMonitor(unittest.TestCase):

    def test_positive_cash_flow_is_green(self) -> None:
        r = project_cash_runway(
            current_cash=10_000_000,
            weekly_collections=2_500_000,
            weekly_operating_outflows=2_000_000,
            weekly_debt_service=100_000,
            weeks_to_project=13,
        )
        self.assertEqual(r.status, "green")
        # Ending balance grows.
        self.assertGreater(r.weeks[-1].ending_balance, r.weeks[0].opening_balance)

    def test_burn_triggers_breach(self) -> None:
        r = project_cash_runway(
            current_cash=3_000_000,
            weekly_collections=1_000_000,
            weekly_operating_outflows=1_400_000,
            weekly_debt_service=100_000,
            weeks_to_project=13,
            minimum_cash=500_000,
            covenant_floor=1_000_000,
        )
        self.assertIsNotNone(r.breach_week)
        self.assertEqual(r.status, "red")

    def test_runway_calculation(self) -> None:
        # Burn rate = 400k/week; starting 5M; runway ~= 12.5 weeks.
        r = project_cash_runway(
            current_cash=5_000_000,
            weekly_collections=1_000_000,
            weekly_operating_outflows=1_400_000,
            weeks_to_project=4,
        )
        self.assertAlmostEqual(r.weeks_of_runway, 12.5, delta=0.5)

    def test_project_cash_detail_variable_weekly(self) -> None:
        detail = [
            (2_000_000, 2_000_000, 0),       # break-even week
            (2_500_000, 2_300_000, 100_000), # slight positive
            (1_000_000, 2_000_000, 100_000), # negative
        ]
        r = project_cash_detail(
            current_cash=1_000_000, weekly_detail=detail,
            minimum_cash=100_000, covenant_floor=200_000,
        )
        self.assertEqual(len(r.weeks), 3)

    def test_markdown_renders(self) -> None:
        r = project_cash_runway(
            current_cash=1_000_000,
            weekly_collections=500_000,
            weekly_operating_outflows=500_000,
            weeks_to_project=4,
        )
        md = render_liquidity_markdown(r)
        self.assertIn("# Liquidity monitor", md)

    def test_report_json(self) -> None:
        import json
        r = project_cash_runway(
            current_cash=1_000_000, weekly_collections=500_000,
            weekly_operating_outflows=500_000, weeks_to_project=4,
        )
        json.dumps(r.to_dict())


# ── M&A pipeline ─────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ADDON_STAGES,
    AddOnTarget,
    PipelineSummary,
    analyze_pipeline,
    render_pipeline_markdown,
)


class TestMAPipeline(unittest.TestCase):

    def test_stage_inventory_counts(self) -> None:
        targets = [
            AddOnTarget(name="A", stage="sourced", ebitda_m=5),
            AddOnTarget(name="B", stage="outreach", ebitda_m=8),
            AddOnTarget(name="C", stage="loi", ebitda_m=10),
            AddOnTarget(name="D", stage="diligence", ebitda_m=12),
            AddOnTarget(name="E", stage="closed", ebitda_m=6),
            AddOnTarget(name="F", stage="passed"),
        ]
        s = analyze_pipeline(targets)
        self.assertEqual(s.inventory["sourced"], 1)
        self.assertEqual(s.inventory["diligence"], 1)
        self.assertEqual(s.inventory["closed"], 1)
        # Active count excludes closed + passed.
        self.assertEqual(s.n_active, 4)

    def test_weighted_close_by_stage(self) -> None:
        # Diligence stage has highest conversion — should weight most.
        targets = [
            AddOnTarget(name="dd", stage="diligence", ebitda_m=10),
            AddOnTarget(name="sourced1", stage="sourced", ebitda_m=10),
        ]
        s = analyze_pipeline(targets)
        self.assertGreater(s.weighted_ebitda_close, 0)

    def test_capacity_ratio_against_platform(self) -> None:
        targets = [
            AddOnTarget(name="big", stage="diligence", ebitda_m=20),
        ]
        s = analyze_pipeline(targets, platform_ebitda_m=50)
        self.assertIsNotNone(s.capacity_ratio)

    def test_empty_pipeline(self) -> None:
        s = analyze_pipeline([])
        self.assertEqual(s.n_active, 0)
        self.assertIn("No active pipeline", s.partner_note)

    def test_markdown_renders(self) -> None:
        targets = [AddOnTarget(name="A", stage="loi", ebitda_m=8)]
        md = render_pipeline_markdown(analyze_pipeline(targets))
        self.assertIn("# M&A pipeline", md)

    def test_summary_json(self) -> None:
        import json
        targets = [AddOnTarget(name="A", stage="loi", ebitda_m=8)]
        s = analyze_pipeline(targets)
        json.dumps(s.to_dict())


# ── ESG screen ───────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    ESGFlag,
    ESGInputs,
    ESGReport,
    render_esg_markdown,
    screen_esg,
)


class TestESGScreen(unittest.TestCase):

    def test_clean_profile_scores_high(self) -> None:
        r = screen_esg(ESGInputs(
            tobacco_exposure=False, firearms_exposure=False,
            short_term_detention=False, fossil_fuel_primary=False,
            environmental_score=0.80, social_score=0.75,
            governance_score=0.80,
            scope1_emissions_tracked=True,
            scope2_emissions_tracked=True,
            dei_metrics_tracked=True,
            worker_safety_tracked=True,
            board_diversity_pct=0.35,
        ))
        self.assertFalse(r.is_excluded)
        self.assertIn(r.grade, ("A", "B"))

    def test_tobacco_triggers_exclusion(self) -> None:
        r = screen_esg(ESGInputs(tobacco_exposure=True))
        self.assertTrue(r.is_excluded)
        self.assertEqual(r.score, 0)
        self.assertEqual(r.grade, "F")

    def test_reporting_gaps_penalize_score(self) -> None:
        r_with_gaps = screen_esg(ESGInputs(
            environmental_score=0.80, social_score=0.75,
            governance_score=0.80,
            scope1_emissions_tracked=False,
            scope2_emissions_tracked=False,
            dei_metrics_tracked=False,
            worker_safety_tracked=False,
        ))
        r_without_gaps = screen_esg(ESGInputs(
            environmental_score=0.80, social_score=0.75,
            governance_score=0.80,
            scope1_emissions_tracked=True,
            scope2_emissions_tracked=True,
            dei_metrics_tracked=True,
            worker_safety_tracked=True,
        ))
        self.assertLess(r_with_gaps.score, r_without_gaps.score)

    def test_board_diversity_scoring(self) -> None:
        r_low = screen_esg(ESGInputs(
            environmental_score=0.5, social_score=0.5, governance_score=0.5,
            board_diversity_pct=0.05,
        ))
        r_high = screen_esg(ESGInputs(
            environmental_score=0.5, social_score=0.5, governance_score=0.5,
            board_diversity_pct=0.40,
        ))
        self.assertLess(r_low.score, r_high.score)

    def test_empty_inputs_safe(self) -> None:
        r = screen_esg(ESGInputs())
        # Neutral 50% composite → score around 50.
        self.assertGreater(r.score, 30)
        self.assertLess(r.score, 70)

    def test_multiple_exclusions_listed(self) -> None:
        r = screen_esg(ESGInputs(
            tobacco_exposure=True, firearms_exposure=True,
        ))
        self.assertEqual(len(r.exclusion_flags), 2)

    def test_markdown_renders(self) -> None:
        r = screen_esg(ESGInputs(environmental_score=0.7))
        md = render_esg_markdown(r)
        self.assertIn("# ESG screen", md)

    def test_report_json(self) -> None:
        import json
        r = screen_esg(ESGInputs(environmental_score=0.7))
        json.dumps(r.to_dict())


# ── Deep-dive heuristics ───────────────────────────────────────

from rcm_mc.pe_intelligence import (
    DEEP_DIVE_FIELDS,
    run_deepdive_heuristics,
)


def _deep_ctx(**extras) -> HeuristicContext:
    ctx = HeuristicContext()
    for k, v in extras.items():
        setattr(ctx, k, v)
    return ctx


class TestDeepDiveHeuristics(unittest.TestCase):

    def test_flat_multiple_short_hold(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            entry_multiple=9.0, exit_multiple=9.1, hold_years=3.0,
        ))
        self.assertTrue(any(h.id == "entry_equals_exit_same_year" for h in hits))

    def test_rural_govt_concentration(self) -> None:
        ctx = _deep_ctx(
            payer_mix={"medicare": 0.55, "medicaid": 0.25,
                       "commercial": 0.20},
            urban_rural="rural",
        )
        hits = run_deepdive_heuristics(ctx)
        self.assertTrue(any(h.id == "rural_govt_concentration" for h in hits))

    def test_teaching_cmi_mismatch(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            teaching_status="major", case_mix_index=1.30,
        ))
        self.assertTrue(any(h.id == "teaching_cmi_mismatch" for h in hits))

    def test_margin_without_volume(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            margin_expansion_bps_per_yr=300, revenue_growth_pct_per_yr=2.0,
        ))
        self.assertTrue(any(h.id == "ebitda_growth_no_volume" for h in hits))

    def test_long_hold_thin_margin(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            hold_years=8.0, ebitda_margin=0.06,
        ))
        self.assertTrue(any(h.id == "long_hold_thin_conversion" for h in hits))

    def test_no_operating_partner(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            denial_improvement_bps_per_yr=150,
            has_operating_partner=False,
        ))
        self.assertTrue(any(h.id == "no_operating_partner_assigned" for h in hits))

    def test_high_rollover(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(equity_rollover_pct=0.40))
        self.assertTrue(any(h.id == "mgmt_rollover_too_high" for h in hits))

    def test_staff_turnover_trend(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(staff_turnover_trend_pct=0.04))
        self.assertTrue(any(h.id == "staff_turnover_trend_up" for h in hits))

    def test_pending_cms_rule(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(
            pending_cms_rule="Medicare Outpatient Rate -2% proposal",
        ))
        self.assertTrue(any(h.id == "pending_cms_rule" for h in hits))

    def test_gp_mark_aggressive(self) -> None:
        hits = run_deepdive_heuristics(_deep_ctx(gp_mark_vs_peer_multiple=2.0))
        self.assertTrue(any(h.id == "gp_valuation_too_aggressive" for h in hits))

    def test_empty_context_no_hits(self) -> None:
        hits = run_deepdive_heuristics(HeuristicContext())
        self.assertEqual(hits, [])

    def test_fields_list_non_empty(self) -> None:
        self.assertGreaterEqual(len(DEEP_DIVE_FIELDS), 5)


# ── Master bundle ─────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    build_master_bundle,
    bundle_index,
)


class TestMasterBundle(unittest.TestCase):

    def test_bundle_has_all_artifacts(self) -> None:
        packet = _make_packet_dict()
        bundle = build_master_bundle(packet)
        expected = {
            "review", "ic_memo", "lp_pitch", "memo_formats",
            "analyst_cheatsheet", "board_memo",
            "hundred_day_plan_markdown", "narrative_styles",
            "extra_heuristics", "extra_red_flags",
            "deepdive_heuristics", "bear_patterns",
            "regulatory_items", "scenario_narrative",
            "partner_discussion", "audit_trail",
        }
        actual = set(bundle_index(bundle))
        self.assertEqual(actual, expected)

    def test_bundle_json_serializable(self) -> None:
        import json
        packet = _make_packet_dict()
        bundle = build_master_bundle(packet)
        json.dumps(bundle, default=str)

    def test_bundle_guards_failures(self) -> None:
        # Empty packet should still produce a bundle without raising.
        bundle = build_master_bundle({})
        self.assertIn("review", bundle)


# ── Tax structuring ────────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    TaxFinding,
    TaxStructureInputs,
    TaxStructureReport,
    analyze_tax_structure,
    render_tax_structure_markdown,
)


class TestTaxStructuring(unittest.TestCase):

    def test_partnership_step_up(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership",
            state_of_primary_operation="TX",
        ))
        self.assertTrue(r.step_up_available)

    def test_c_corp_blocks_step_up(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="c_corp",
            state_of_primary_operation="TX",
        ))
        self.assertFalse(r.step_up_available)

    def test_f_reorg_unblocks_c_corp(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="c_corp",
            state_of_primary_operation="TX",
            use_f_reorg=True,
        ))
        # Step-up becomes feasible with F-reorg.
        self.assertIsNone(r.step_up_available)  # not auto-true, but not blocked

    def test_high_tax_state_warning(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership",
            state_of_primary_operation="NY",
        ))
        state_finding = next(f for f in r.findings if f.area == "state_tax")
        self.assertEqual(state_finding.status, "warning")

    def test_no_tax_state_favorable(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership",
            state_of_primary_operation="FL",
        ))
        state_finding = next(f for f in r.findings if f.area == "state_tax")
        self.assertEqual(state_finding.status, "favorable")

    def test_163j_interest_cap_warning(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            ebitda_m=20,                         # $20M EBITDA
            debt_at_close=150_000_000,           # $150M debt
            interest_rate=0.10,                  # 10% → $15M interest
        ))
        cap_finding = next(f for f in r.findings if f.area == "163j_interest_cap")
        # 30% of 20M EBITDA = 6M cap; 15M interest exceeds → warning.
        self.assertEqual(cap_finding.status, "warning")

    def test_qsbs_eligible_with_5yr_hold(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership",
            state_of_primary_operation="TX",
            is_qsbs_eligible=True, holding_period_years=5.0,
        ))
        qsbs = next(f for f in r.findings if f.area == "qsbs")
        self.assertEqual(qsbs.status, "favorable")

    def test_international_triggers_warning(self) -> None:
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership",
            international_exposure=True,
        ))
        intl = next(f for f in r.findings if f.area == "international")
        self.assertEqual(intl.status, "warning")

    def test_markdown_renders(self) -> None:
        md = render_tax_structure_markdown(analyze_tax_structure(
            TaxStructureInputs(seller_entity_type="partnership",
                               state_of_primary_operation="TX")))
        self.assertIn("# Tax structure report", md)

    def test_report_json(self) -> None:
        import json
        r = analyze_tax_structure(TaxStructureInputs(
            seller_entity_type="partnership"))
        json.dumps(r.to_dict())


# ── Insurance diligence ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    InsuranceGap,
    InsuranceInputs,
    InsuranceReport,
    render_insurance_report_markdown,
    screen_insurance,
)


class TestInsuranceDiligence(unittest.TestCase):

    def test_adequate_pl_limit(self) -> None:
        r = screen_insurance(InsuranceInputs(
            subsector="acute_care", ebitda_m=30,
            professional_liability_limit_m=100,
        ))
        pl = next(g for g in r.gaps if g.area == "professional_liability")
        self.assertEqual(pl.severity, "info")

    def test_pl_limit_too_low_flagged(self) -> None:
        r = screen_insurance(InsuranceInputs(
            subsector="acute_care", ebitda_m=30,
            professional_liability_limit_m=50,
        ))
        pl = next(g for g in r.gaps if g.area == "professional_liability")
        self.assertEqual(pl.severity, "high")

    def test_low_cyber_limit(self) -> None:
        r = screen_insurance(InsuranceInputs(cyber_limit_m=2))
        cyber = next(g for g in r.gaps if g.area == "cyber")
        self.assertEqual(cyber.severity, "medium")

    def test_sir_unfunded_high(self) -> None:
        r = screen_insurance(InsuranceInputs(
            sir_m=10, sir_funded_m=3,
        ))
        sir = next(g for g in r.gaps if g.area == "sir_funding")
        self.assertEqual(sir.severity, "high")

    def test_claims_elevated(self) -> None:
        r = screen_insurance(InsuranceInputs(claims_last_24mo=10))
        claims = next(g for g in r.gaps if g.area == "claims_frequency")
        self.assertEqual(claims.severity, "medium")

    def test_claims_systemic(self) -> None:
        r = screen_insurance(InsuranceInputs(claims_last_24mo=25))
        claims = next(g for g in r.gaps if g.area == "claims_frequency")
        self.assertEqual(claims.severity, "high")

    def test_largest_claim_requires_escrow(self) -> None:
        r = screen_insurance(InsuranceInputs(
            ebitda_m=30, largest_open_claim_m=15,
        ))
        claim = next(g for g in r.gaps
                     if g.area == "largest_open_claim")
        self.assertEqual(claim.severity, "high")

    def test_markdown_renders(self) -> None:
        md = render_insurance_report_markdown(screen_insurance(
            InsuranceInputs(subsector="acute_care", ebitda_m=30,
                            professional_liability_limit_m=100)))
        self.assertIn("# Insurance diligence", md)

    def test_report_json(self) -> None:
        import json
        r = screen_insurance(InsuranceInputs(ebitda_m=30))
        json.dumps(r.to_dict())


# ── Portfolio dashboard ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    PortfolioDashboard,
    build_portfolio_dashboard,
    render_portfolio_dashboard_markdown,
)


class TestPortfolioDashboard(unittest.TestCase):

    def _multi_reviews(self):
        reviews = []
        # Clean acute_care in TX
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55}, ebitda_m=30,
            hospital_type="acute_care", state="TX",
            exit_multiple=9.0, entry_multiple=8.0, hold_years=5,
            projected_irr=0.20, projected_moic=2.3, leverage_multiple=5.0,
        )
        reviews.append(partner_review_from_context(ctx, deal_id="D1",
                                                    deal_name="Clean A"))
        # Problematic Medicare-heavy
        ctx2 = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25,
                       "medicaid": 0.10},
            ebitda_m=50, hospital_type="acute_care", state="NY",
            exit_multiple=12.0, leverage_multiple=6.5,
            covenant_headroom_pct=0.05,
            denial_improvement_bps_per_yr=700,  # critical
        )
        reviews.append(partner_review_from_context(ctx2, deal_id="D2",
                                                    deal_name="Risky B"))
        # Mid deal
        ctx3 = HeuristicContext(
            payer_mix={"commercial": 0.60, "medicare": 0.30,
                       "medicaid": 0.10},
            ebitda_m=20, hospital_type="asc", state="FL",
            exit_multiple=10.5, entry_multiple=9.0,
        )
        reviews.append(partner_review_from_context(ctx3, deal_id="D3",
                                                    deal_name="Med C"))
        return reviews

    def test_dashboard_counts_deals(self) -> None:
        d = build_portfolio_dashboard(self._multi_reviews())
        self.assertEqual(d.n_deals, 3)

    def test_critical_flagged_deals_surfaced(self) -> None:
        d = build_portfolio_dashboard(self._multi_reviews())
        # Risky B has a CRITICAL hit from denial_improvement.
        self.assertIn("D2", d.deals_with_critical)

    def test_sector_mix(self) -> None:
        d = build_portfolio_dashboard(self._multi_reviews())
        self.assertEqual(d.sector_counts.get("acute_care", 0), 2)
        self.assertEqual(d.sector_counts.get("asc", 0), 1)

    def test_state_mix(self) -> None:
        d = build_portfolio_dashboard(self._multi_reviews())
        self.assertEqual(sum(d.state_counts.values()), 3)

    def test_recommendation_counts(self) -> None:
        d = build_portfolio_dashboard(self._multi_reviews())
        self.assertEqual(sum(d.recommendation_counts.values()), 3)

    def test_empty_portfolio_safe(self) -> None:
        d = build_portfolio_dashboard([])
        self.assertEqual(d.n_deals, 0)
        self.assertIn("No deals", d.partner_summary)

    def test_markdown_renders(self) -> None:
        md = render_portfolio_dashboard_markdown(
            build_portfolio_dashboard(self._multi_reviews()))
        self.assertIn("# Portfolio dashboard", md)

    def test_dashboard_json(self) -> None:
        import json
        d = build_portfolio_dashboard(self._multi_reviews())
        json.dumps(d.to_dict())


# ── Integration readiness ────────────────────────────────────

from rcm_mc.pe_intelligence import (
    IntegrationFinding,
    IntegrationInputs,
    IntegrationReport,
    assess_integration_readiness,
    render_integration_report_markdown,
)


class TestIntegrationReadiness(unittest.TestCase):

    def test_fully_ready(self) -> None:
        r = assess_integration_readiness(IntegrationInputs(
            integration_officer_named=True,
            day_one_system_plan_ready=True,
            management_retention_signed=True,
            management_comp_aligned=True,
            rcm_lead_named=True, it_lead_named=True,
            clinical_lead_named=True, finance_lead_named=True,
            hr_lead_named=True,
            integration_budget_sized=True,
            communications_plan_ready=True,
            tsa_duration_months=6,
        ))
        self.assertEqual(r.verdict, "ready")
        self.assertEqual(r.gap_count, 0)

    def test_not_ready_no_officer(self) -> None:
        r = assess_integration_readiness(IntegrationInputs(
            integration_officer_named=False,
            day_one_system_plan_ready=False,
            management_retention_signed=False,
            rcm_lead_named=False, it_lead_named=False,
            clinical_lead_named=False, finance_lead_named=False,
            hr_lead_named=False,
            integration_budget_sized=False,
            communications_plan_ready=False,
        ))
        self.assertEqual(r.verdict, "not_ready")
        self.assertGreater(r.gap_count, 5)

    def test_long_tsa_penalty(self) -> None:
        ready_inputs = IntegrationInputs(
            integration_officer_named=True,
            day_one_system_plan_ready=True,
            management_retention_signed=True,
            management_comp_aligned=True,
            rcm_lead_named=True, it_lead_named=True,
            clinical_lead_named=True, finance_lead_named=True,
            hr_lead_named=True,
            integration_budget_sized=True,
            communications_plan_ready=True,
        )
        baseline = assess_integration_readiness(ready_inputs)
        with_long_tsa = assess_integration_readiness(
            IntegrationInputs(**ready_inputs.__dict__, )
        )
        with_long_tsa.score = baseline.score  # sanity baseline
        # Now apply long TSA.
        inputs_long_tsa = IntegrationInputs(**{
            **ready_inputs.__dict__,
            "tsa_duration_months": 18,
        })
        r_long = assess_integration_readiness(inputs_long_tsa)
        self.assertLess(r_long.score, baseline.score)

    def test_rollup_without_officer_penalized(self) -> None:
        baseline = assess_integration_readiness(IntegrationInputs(
            integration_officer_named=False,
            day_one_system_plan_ready=True,
            management_retention_signed=True,
        ))
        with_rollup = assess_integration_readiness(IntegrationInputs(
            integration_officer_named=False,
            day_one_system_plan_ready=True,
            management_retention_signed=True,
            has_rollup_thesis=True,
        ))
        self.assertLess(with_rollup.score, baseline.score)

    def test_empty_inputs_unknown_majority(self) -> None:
        r = assess_integration_readiness(IntegrationInputs())
        # All dimensions unknown → score ~ 50.
        self.assertGreater(r.score, 30)
        self.assertLess(r.score, 70)

    def test_markdown_renders(self) -> None:
        md = render_integration_report_markdown(
            assess_integration_readiness(IntegrationInputs(
                integration_officer_named=True,
            )))
        self.assertIn("# Integration readiness", md)

    def test_json(self) -> None:
        import json
        r = assess_integration_readiness(IntegrationInputs())
        json.dumps(r.to_dict())


# ── Management compensation ───────────────────────────────────

from rcm_mc.pe_intelligence import (
    CompFinding,
    CompPlanInputs,
    CompReport,
    render_comp_plan_markdown,
    review_comp_plan,
)


class TestManagementComp(unittest.TestCase):

    def test_standard_plan(self) -> None:
        r = review_comp_plan(CompPlanInputs(
            mip_pool_pct=0.10, ceo_mip_share_pct=0.40,
            vesting_years=4.0, cliff_months=12,
            acceleration_type="double",
            ceo_equity_rollover_pct=0.10,
            ltip_bonus_multiple_base=0.50,
            performance_vesting_pct=0.40,
        ))
        for f in r.findings:
            self.assertEqual(f.status, "standard")

    def test_single_trigger_flagged_aggressive(self) -> None:
        r = review_comp_plan(CompPlanInputs(acceleration_type="single"))
        accel = next(f for f in r.findings if f.area == "acceleration")
        self.assertEqual(accel.status, "aggressive")

    def test_small_pool_flagged_light(self) -> None:
        r = review_comp_plan(CompPlanInputs(mip_pool_pct=0.03))
        pool = next(f for f in r.findings if f.area == "mip_pool")
        self.assertEqual(pool.status, "light")

    def test_oversized_pool_flagged_aggressive(self) -> None:
        r = review_comp_plan(CompPlanInputs(mip_pool_pct=0.25))
        pool = next(f for f in r.findings if f.area == "mip_pool")
        self.assertEqual(pool.status, "aggressive")

    def test_ceo_rollover_band(self) -> None:
        r_low = review_comp_plan(CompPlanInputs(ceo_equity_rollover_pct=0.02))
        r_std = review_comp_plan(CompPlanInputs(ceo_equity_rollover_pct=0.10))
        r_high = review_comp_plan(CompPlanInputs(ceo_equity_rollover_pct=0.40))
        self.assertEqual(next(f for f in r_low.findings
                              if f.area == "ceo_rollover").status, "light")
        self.assertEqual(next(f for f in r_std.findings
                              if f.area == "ceo_rollover").status, "standard")
        self.assertEqual(next(f for f in r_high.findings
                              if f.area == "ceo_rollover").status, "aggressive")

    def test_vesting_band(self) -> None:
        r_short = review_comp_plan(CompPlanInputs(vesting_years=2.0))
        r_long = review_comp_plan(CompPlanInputs(vesting_years=7.0))
        self.assertEqual(next(f for f in r_short.findings
                              if f.area == "vesting").status, "light")
        self.assertEqual(next(f for f in r_long.findings
                              if f.area == "vesting").status, "aggressive")

    def test_ltip_band(self) -> None:
        r_light = review_comp_plan(CompPlanInputs(ltip_bonus_multiple_base=0.10))
        r_agg = review_comp_plan(CompPlanInputs(ltip_bonus_multiple_base=1.5))
        self.assertEqual(next(f for f in r_light.findings
                              if f.area == "ltip").status, "light")
        self.assertEqual(next(f for f in r_agg.findings
                              if f.area == "ltip").status, "aggressive")

    def test_markdown_renders(self) -> None:
        md = render_comp_plan_markdown(review_comp_plan(CompPlanInputs(
            mip_pool_pct=0.10, ceo_mip_share_pct=0.40,
            vesting_years=4.0, cliff_months=12,
        )))
        self.assertIn("# Management compensation review", md)

    def test_json(self) -> None:
        import json
        r = review_comp_plan(CompPlanInputs(mip_pool_pct=0.10))
        json.dumps(r.to_dict())


# ── Red-team review ────────────────────────────────────────

from rcm_mc.pe_intelligence import (
    RedTeamAttack,
    RedTeamReport,
    build_red_team_report,
    render_red_team_markdown,
)


class TestRedTeamReview(unittest.TestCase):

    def test_aggressive_deal_surfaces_attacks(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65, "commercial": 0.25,
                       "medicaid": 0.10},
            ebitda_m=50, hospital_type="acute_care",
            exit_multiple=12.0, entry_multiple=8.0,
            leverage_multiple=6.5, covenant_headroom_pct=0.05,
            denial_improvement_bps_per_yr=500,
        )
        review = partner_review_from_context(ctx, deal_id="R1")
        report = build_red_team_report(review)
        self.assertGreaterEqual(len(report.top_attacks), 2)

    def test_clean_deal_no_attacks(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"commercial": 0.55, "medicare": 0.30,
                       "medicaid": 0.15},
            ebitda_m=30, hospital_type="acute_care",
            exit_multiple=9.0, entry_multiple=8.5, hold_years=5,
            projected_irr=0.18, leverage_multiple=4.0,
        )
        review = partner_review_from_context(ctx, deal_id="R2")
        report = build_red_team_report(review)
        # Few/no attacks on a clean deal.
        self.assertLessEqual(len(report.top_attacks), 1)

    def test_severity_ordering(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65},
            exit_multiple=12.0,
            leverage_multiple=6.5,
        )
        review = partner_review_from_context(ctx, deal_id="R3")
        report = build_red_team_report(review)
        rank = {"high": 0, "medium": 1, "low": 2}
        ranks = [rank.get(a.severity, 3) for a in report.top_attacks]
        self.assertEqual(ranks, sorted(ranks))

    def test_pass_rationale_populated(self) -> None:
        ctx = HeuristicContext(
            payer_mix={"medicare": 0.65}, leverage_multiple=6.5,
        )
        report = build_red_team_report(partner_review_from_context(ctx))
        self.assertTrue(report.pass_rationale)

    def test_markdown_renders(self) -> None:
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        report = build_red_team_report(partner_review_from_context(ctx))
        md = render_red_team_markdown(report)
        self.assertIn("Red-team review", md)

    def test_report_json(self) -> None:
        import json
        ctx = HeuristicContext(payer_mix={"commercial": 0.55})
        report = build_red_team_report(partner_review_from_context(ctx))
        json.dumps(report.to_dict())


if __name__ == "__main__":
    unittest.main()
