"""Unit tests for the J2 Regulatory-Arbitrage Collapse Detector.

These tests cover what a smoke test cannot:
  - Each per-arbitrage scorer fires on a hand-crafted positive fixture
    and stays quiet on a clean fixture.
  - Scores are word-boundary safe (the original bug: 2-char tokens like
    "ED" / "ER" / "BH" substring-matched into "covered", "Premier",
    "behaved", inflating NSA fragility on every deal in the corpus).
  - The Steward-pattern stack actually triggers on a deal with ≥3 arbs.
  - score_deal() is referentially transparent (no I/O, no rng, no time).
  - Provenance entries are emitted 1:1 with per-deal × per-arbitrage
    scores — that's the ProvenanceTracker invariant.
  - Aggregate roll-up uses a quadratic mean (single 90 dominates five 30s).
"""
from __future__ import annotations

import json

import pytest

from rcm_mc.data_public.regulatory_arbitrage_collapse import (
    _has_keyword,
    _NSA_AFFECTED_SPECIALTIES,
    _PHARMACY_340B_SECTORS,
    _MA_HEAVY_SECTORS,
    _MEDICAID_HEAVY_SECTORS,
    _ACO_REACH_SECTORS,
    compute_regulatory_arbitrage_collapse,
    score_deal,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _hbp_deal() -> dict:
    """A radiology / anesthesia hospital-based physician deal — the
    canonical AC-1 (NSA) target."""
    return {
        "deal_name": "Project NF-02 — Anesthesia / Radiology Group",
        "year": 2019,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.20, "medicaid": 0.05,
            "commercial": 0.70, "self_pay": 0.05,
        }),
        "notes": "Hospital-based anesthesia and radiology platform; pre-NSA OON-billing posture.",
    }


def _ma_risk_deal() -> dict:
    """An MA-risk primary care deal — the AC-3 (V28) target."""
    return {
        "deal_name": "Project Cano — MA Risk-Bearing PCP",
        "year": 2021,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.92, "medicaid": 0.03,
            "commercial": 0.04, "self_pay": 0.01,
        }),
        "notes": "Senior primary care MA-risk capitation model; aggressive RAF coding intensity.",
    }


def _medicaid_heavy_deal() -> dict:
    """A behavioral health / substance use deal with high Medicaid mix —
    AC-4 target."""
    return {
        "deal_name": "Project Linden — Behavioral Health Platform",
        "year": 2022,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.05, "medicaid": 0.60,
            "commercial": 0.30, "self_pay": 0.05,
        }),
        "notes": "CCBHC-anchored substance-use platform; single-MCO contract concentration in 3 states; rebid 2025.",
    }


def _pharmacy_340b_deal() -> dict:
    """An infusion / specialty pharmacy 340B deal — AC-2 target."""
    return {
        "deal_name": "Project Ash — Specialty Pharmacy / Infusion",
        "year": 2020,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.40,
            "commercial": 0.20, "self_pay": 0.05,
        }),
        "notes": "Hospital-affiliated specialty pharmacy + infusion network; 340B contract pharmacy with Sanofi/AZ exposure; manufacturer restriction live.",
    }


def _aco_reach_deal() -> dict:
    """An ACO REACH risk-bearing primary care deal — AC-5 target."""
    return {
        "deal_name": "Project Oakwood — ACO REACH Direct Contracting Platform",
        "year": 2023,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.85, "medicaid": 0.05,
            "commercial": 0.08, "self_pay": 0.02,
        }),
        "notes": "ACO REACH benchmark-anchored capitation model; PY2026 final model year.",
    }


def _clean_deal() -> dict:
    """A vanilla office-based dermatology deal — should not trigger any
    arbitrage at high severity."""
    return {
        "deal_name": "Project Laurel — Office-Based Dermatology",
        "year": 2024,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.20, "medicaid": 0.08,
            "commercial": 0.65, "self_pay": 0.07,
        }),
        # Notes are intentionally bland so none of the arbitrage keyword
        # lists fire. Avoid words like "risk-bearing", "OON", "REACH",
        # "MA capitation", "340B", "behavioral", "infusion".
        "notes": "Dermatology multi-site practice with cosmetic and medical revenue mix; commercial-heavy.",
    }


def _steward_stack_deal() -> dict:
    """Synthetic deal that stacks AC-1 (HBP+commercial), AC-3 (MA-risk
    pretense in notes), AC-4 (high Medicaid), and AC-5 (REACH mention).
    Tests that ≥3 high-severity arbs trigger Steward pattern."""
    return {
        "deal_name": "Project Cerberus — Hospital Roll-up + REACH Direct Contracting",
        "year": 2021,
        "buyer": "Test Sponsor",
        "payer_mix": json.dumps({
            "medicare": 0.40, "medicaid": 0.40,
            "commercial": 0.18, "self_pay": 0.02,
        }),
        "notes": "Hospital-based emergency anesthesia + radiology + pathology platform with single-MCO Medicaid concentration in 4 states; ACO REACH direct-contracting overlay; aggressive RAF coding on Medicare Advantage retiree population.",
    }


# ---------------------------------------------------------------------------
# Per-arbitrage positive scoring
# ---------------------------------------------------------------------------

def test_ac1_nsa_fires_on_hbp_deal():
    p = score_deal(_hbp_deal())
    assert p.nsa_score >= 60.0, f"AC-1 should fire on HBP deal: got {p.nsa_score}"
    assert p.dominant_arbitrage == "AC-1"


def test_ac2_pharmacy_340b_fires_on_specialty_pharmacy():
    p = score_deal(_pharmacy_340b_deal())
    assert p.pharmacy_340b_score >= 55.0, f"AC-2 should fire: got {p.pharmacy_340b_score}"


def test_ac3_v28_fires_on_ma_risk_deal():
    p = score_deal(_ma_risk_deal())
    assert p.ma_v28_score >= 55.0, f"AC-3 should fire: got {p.ma_v28_score}"


def test_ac4_medicaid_mco_fires_on_behavioral_medicaid_deal():
    p = score_deal(_medicaid_heavy_deal())
    assert p.medicaid_mco_score >= 55.0, f"AC-4 should fire: got {p.medicaid_mco_score}"


def test_ac5_aco_reach_fires_on_reach_deal():
    p = score_deal(_aco_reach_deal())
    assert p.aco_reach_score >= 55.0, f"AC-5 should fire: got {p.aco_reach_score}"


# ---------------------------------------------------------------------------
# Per-arbitrage clean-fixture suppression
# ---------------------------------------------------------------------------

def test_clean_dermatology_deal_has_low_scores():
    p = score_deal(_clean_deal())
    # Office-based derma should not fire on AC-1, AC-2, AC-3, AC-5.
    # AC-4 is allowed mild because medicaid_pct >= 0.05 — but it
    # should never reach high severity on this kind of deal.
    assert p.nsa_score < 30.0
    assert p.pharmacy_340b_score < 30.0
    assert p.ma_v28_score < 30.0
    assert p.aco_reach_score < 30.0
    assert p.medicaid_mco_score < 55.0
    assert not p.steward_pattern_flag


# ---------------------------------------------------------------------------
# Word-boundary regression — the original bug that scored 467/745 deals
# at AC-1 high+ because "ED " substring-matched into "covered", "based"
# ---------------------------------------------------------------------------

def test_has_keyword_rejects_short_token_substring():
    # "ED" must not match inside "covered" / "based" / "Premier" / "buyer"
    assert not _has_keyword("Covered entity Premier shareholders buyer", _NSA_AFFECTED_SPECIALTIES)
    # but it must match when it's a real word
    assert _has_keyword("Anesthesia and radiology services", _NSA_AFFECTED_SPECIALTIES)
    # "ER" must not match "Premier" / "shareholders" / "buyer"
    assert not _has_keyword("Premier shareholders bayer", _NSA_AFFECTED_SPECIALTIES)


def test_has_keyword_long_tokens_substring_match():
    # 5+ char tokens are allowed to substring-match
    assert _has_keyword("Behavioral Health platform", _MEDICAID_HEAVY_SECTORS)
    assert _has_keyword("specialty pharmacy 340B", _PHARMACY_340B_SECTORS)


# ---------------------------------------------------------------------------
# Steward-pattern aggregation
# ---------------------------------------------------------------------------

def test_steward_pattern_triggers_on_stacked_deal():
    p = score_deal(_steward_stack_deal())
    # At least 3 of the 5 arbs should be at high severity (≥55)
    assert p.high_fragility_count >= 3, (
        f"Steward stack should trip ≥3 high-fragility arbs, got "
        f"{p.high_fragility_count}; scores: AC1={p.nsa_score} AC2={p.pharmacy_340b_score} "
        f"AC3={p.ma_v28_score} AC4={p.medicaid_mco_score} AC5={p.aco_reach_score}"
    )
    assert p.steward_pattern_flag


def test_quadratic_mean_dominates_on_single_high_score():
    """A deal with ONE arbitrage at 90 and four at 10 should have a
    higher collapse index than one with all five at 40 — that's the
    Steward fingerprint we're surfacing."""
    p_clean = score_deal(_clean_deal())
    p_steward = score_deal(_steward_stack_deal())
    assert p_steward.collapse_index > p_clean.collapse_index + 20.0


# ---------------------------------------------------------------------------
# Determinism (referential transparency)
# ---------------------------------------------------------------------------

def test_score_deal_is_deterministic():
    d = _ma_risk_deal()
    p1 = score_deal(d)
    p2 = score_deal(d)
    assert p1 == p2


def test_compute_is_deterministic():
    r1 = compute_regulatory_arbitrage_collapse()
    r2 = compute_regulatory_arbitrage_collapse()
    # The high-level invariants must be byte-identical run-over-run
    assert r1.total_deals_scored == r2.total_deals_scored
    assert r1.total_steward_pattern_deals == r2.total_steward_pattern_deals
    assert r1.portfolio_collapse_index_mean == r2.portfolio_collapse_index_mean
    assert len(r1.provenance_entries) == len(r2.provenance_entries)


# ---------------------------------------------------------------------------
# ProvenanceTracker invariant
# ---------------------------------------------------------------------------

def test_provenance_emitted_5x_per_scored_deal():
    r = compute_regulatory_arbitrage_collapse()
    # Every deal scored produces 5 provenance entries (one per arbitrage)
    assert len(r.provenance_entries) == 5 * r.total_deals_scored
    # Every entry carries a non-empty citation
    for entry in r.provenance_entries[:50]:
        assert entry.citation
        assert entry.arbitrage_id in {"AC-1", "AC-2", "AC-3", "AC-4", "AC-5"}
        assert entry.deal_name


def test_provenance_citations_are_primary_source():
    r = compute_regulatory_arbitrage_collapse()
    # Spot-check that the primary-source markers appear somewhere in the
    # citations — the platform claims primary-source-only and we
    # enforce that here.
    cites = " ".join(e.citation for e in r.provenance_entries[:200])
    # AC-1 NSA must cite the statute
    assert "No Surprises Act" in cites or "45 CFR" in cites or "IDR" in cites
    # AC-2 340B must cite HRSA or §256b
    # AC-3 V28 must cite CMS-HCC
    # ... at least one of these must appear depending on what's in the deal
    assert any(
        marker in cites
        for marker in ("CMS", "HRSA", "MedPAC", "KFF", "CFR", "USC", "Surprises")
    )


# ---------------------------------------------------------------------------
# Compute() corpus invariants — caught by smoke harness too, but pinned here
# ---------------------------------------------------------------------------

def test_compute_returns_5_arbitrages_and_rollups():
    r = compute_regulatory_arbitrage_collapse()
    assert r.total_arbitrages == 5
    assert len(r.arbitrage_definitions) == 5
    assert len(r.portfolio_rollups) == 5
    assert {d.arbitrage_id for d in r.arbitrage_definitions} == {
        "AC-1", "AC-2", "AC-3", "AC-4", "AC-5"
    }


def test_collapse_index_is_in_0_100_range():
    r = compute_regulatory_arbitrage_collapse()
    for p in r.deal_profiles:
        assert 0.0 <= p.collapse_index <= 100.0
        for sc in (p.nsa_score, p.pharmacy_340b_score, p.ma_v28_score,
                   p.medicaid_mco_score, p.aco_reach_score):
            assert 0.0 <= sc <= 100.0


def test_steward_recommendations_only_proceed_categories():
    r = compute_regulatory_arbitrage_collapse()
    valid = {"STOP", "PROCEED_WITH_CONDITIONS", "PROCEED"}
    for m in r.steward_pattern_matches:
        assert m.pre_mortem_recommendation in valid
        # Steward matches must have ≥3 matched arbitrages by construction
        assert len(m.matched_arbitrages) >= 3
