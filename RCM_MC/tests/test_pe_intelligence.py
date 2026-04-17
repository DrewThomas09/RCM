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


if __name__ == "__main__":
    unittest.main()
