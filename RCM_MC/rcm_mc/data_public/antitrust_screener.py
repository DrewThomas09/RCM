"""Anti-Trust / FTC Review Screener.

Pre-close anti-trust risk assessment for PE healthcare roll-ups.
Became critical after FTC v. USAP / Welsh Carson (2023) expanded "serial
acquisition" enforcement theory. Tracks HSR thresholds, market
concentration (HHI, CR3, CR5), state-AG review exposure, and overlap
analysis against prior platform holdings.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class HHIAnalysis:
    market: str
    msa: str
    pre_merger_hhi: int
    post_merger_hhi: int
    delta_hhi: int
    concentration_flag: str
    cr3_share_pct: float


@dataclass
class HSRThreshold:
    threshold: str
    current_value_mm: float
    threshold_value_mm: float
    filing_required: bool
    waiting_period_days: int
    filing_fee_k: float


@dataclass
class MarketOverlap:
    geography: str
    platform_share_pct: float
    target_share_pct: float
    combined_share_pct: float
    next_competitor_pct: float
    overlap_severity: str
    remediation_required: str


@dataclass
class CaseLaw:
    case: str
    year: int
    parties: str
    outcome: str
    precedent_for_platform: str
    relevance_score: int


@dataclass
class StateReview:
    state: str
    review_trigger: str
    notice_days: int
    notification_fee_k: float
    state_ag_posture: str
    historical_challenge_rate_pct: float


@dataclass
class RemediationOption:
    option: str
    description: str
    timeline_months: int
    financial_cost_mm: float
    deal_value_impact_pct: float
    probability_of_approval: float


@dataclass
class AntitrustResult:
    deal_size_mm: float
    hsr_required: bool
    second_request_probability: float
    overall_risk_score: int
    recommended_timeline_months: int
    hhi_analysis: List[HHIAnalysis]
    hsr_thresholds: List[HSRThreshold]
    overlaps: List[MarketOverlap]
    case_law: List[CaseLaw]
    state_reviews: List[StateReview]
    remediations: List[RemediationOption]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 107):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_hhi() -> List[HHIAnalysis]:
    items = [
        ("Anesthesiology Services", "Houston MSA", 2850, 3650, 800, "highly concentrated", 72),
        ("Anesthesiology Services", "Dallas MSA", 2420, 3180, 760, "highly concentrated", 68),
        ("Anesthesiology Services", "Austin MSA", 2650, 3420, 770, "highly concentrated", 71),
        ("Anesthesiology Services", "San Antonio MSA", 1850, 2320, 470, "moderately concentrated", 58),
        ("Ambulatory Surgery", "Houston MSA", 1850, 2280, 430, "moderately concentrated", 55),
        ("Ambulatory Surgery", "Dallas MSA", 1620, 2050, 430, "moderately concentrated", 52),
        ("Gastroenterology", "Houston MSA", 2450, 2950, 500, "moderately concentrated", 62),
        ("Gastroenterology", "Austin MSA", 2280, 2750, 470, "moderately concentrated", 60),
    ]
    rows = []
    for m, msa, pre, post, delta, flag, cr3 in items:
        rows.append(HHIAnalysis(
            market=m, msa=msa,
            pre_merger_hhi=pre, post_merger_hhi=post, delta_hhi=delta,
            concentration_flag=flag, cr3_share_pct=cr3 / 100,
        ))
    return rows


def _build_hsr() -> List[HSRThreshold]:
    return [
        HSRThreshold("Size of Transaction", 485.0, 119.5, True, 30, 280.0),
        HSRThreshold("Size of Person (Acquirer)", 1850.0, 239.0, True, 0, 0.0),
        HSRThreshold("Size of Person (Target)", 285.0, 23.9, True, 0, 0.0),
        HSRThreshold("Filing Fee Tier (>$500M)", 485.0, 500.0, False, 0, 0.0),
        HSRThreshold("Filing Fee Tier ($100-500M)", 485.0, 100.0, True, 0, 280.0),
        HSRThreshold("Early Termination", 485.0, 0.0, True, 0, 0.0),
    ]


def _build_overlaps() -> List[MarketOverlap]:
    return [
        MarketOverlap("Austin MSA (Anesthesiology)", 42.5, 18.5, 61.0, 12.5, "severe — likely 2R",
                      "Divest 2-3 practices; consent decree expected"),
        MarketOverlap("Houston MSA (Anesthesiology)", 38.5, 12.8, 51.3, 14.5, "severe — likely 2R",
                      "Divest 2 practices; hold-separate order"),
        MarketOverlap("Dallas MSA (Anesthesiology)", 32.5, 15.5, 48.0, 16.5, "material — monitor",
                      "Behavioral remedies; avoid most overlap"),
        MarketOverlap("San Antonio (Anesthesiology)", 28.5, 8.2, 36.7, 22.0, "moderate", "Standard review"),
        MarketOverlap("Austin MSA (ASC)", 22.0, 8.5, 30.5, 18.0, "moderate", "Standard review"),
        MarketOverlap("Houston MSA (GI)", 18.5, 12.0, 30.5, 22.5, "moderate", "Standard review"),
        MarketOverlap("Dallas MSA (ASC)", 15.5, 9.2, 24.7, 20.5, "low", "Standard review"),
    ]


def _build_case_law() -> List[CaseLaw]:
    return [
        CaseLaw("FTC v. USAP / Welsh Carson", 2023, "FTC vs USAP/Welsh Carson", "case dismissed (2024) re: WC directly — USAP case ongoing",
                "clarified 'serial acquisition' theory; platform-level sponsor liability", 95),
        CaseLaw("FTC v. Amerigas / SCA", 2017, "FTC vs Surgical Care Affiliates/UnitedHealth", "cleared with divestitures",
                "ASC roll-up precedent; behavioral remedies", 85),
        CaseLaw("FTC v. Steward Health / IASIS", 2018, "FTC vs Steward Health Care", "cleared with divestitures",
                "hospital roll-up; market overlap analysis", 72),
        CaseLaw("FTC v. Envision/KKR", 2018, "FTC vs KKR/Envision", "cleared (no challenge)",
                "large emergency medicine deal cleared", 65),
        CaseLaw("FTC v. Fresenius/NxStage", 2019, "FTC vs Fresenius", "cleared with divestitures",
                "dialysis concentration remedy", 58),
        CaseLaw("FTC v. Change Healthcare/UNH", 2022, "FTC vs UnitedHealth/Change", "initially challenged; cleared 2022",
                "vertical integration challenge", 45),
    ]


def _build_state_reviews() -> List[StateReview]:
    return [
        StateReview("California (Office of Health Care Affordability)", "all acquisitions >$25M", 90, 25.0, "active scrutiny", 0.18),
        StateReview("New York (Article 28)", "certificate of need trigger", 120, 15.0, "active scrutiny", 0.15),
        StateReview("Oregon (OHA)", "any healthcare acquisition", 180, 25.0, "active scrutiny", 0.22),
        StateReview("Massachusetts (HPC)", "≥$15M annual net patient service", 60, 10.0, "active review", 0.12),
        StateReview("Washington (AG)", "healthcare acquisition notification", 60, 0.0, "standard review", 0.08),
        StateReview("Connecticut (AG)", "hospital & large provider acquisition", 90, 0.0, "standard review", 0.06),
        StateReview("Illinois (AG)", "healthcare acquisition notification", 45, 0.0, "standard review", 0.05),
        StateReview("Colorado (AG)", "healthcare acquisition notification (SB 21-003)", 60, 0.0, "standard review", 0.04),
        StateReview("Texas (AG)", "standard HSR review", 30, 0.0, "minimal scrutiny", 0.02),
        StateReview("Florida (AHCA)", "license transfer / CON", 60, 5.0, "minimal scrutiny", 0.02),
    ]


def _build_remediations() -> List[RemediationOption]:
    return [
        RemediationOption("Divest 2 practices (Austin + Houston)", "Hold-separate trustee for 12-18 months",
                          12, 38.5, 0.068, 0.85),
        RemediationOption("Behavioral remedies only", "Firewall policies, no price coordination",
                          3, 2.5, 0.005, 0.45),
        RemediationOption("Restructure deal (exclude 2 overlap markets)", "Carve-out $125M value",
                          6, 0.0, 0.258, 0.92),
        RemediationOption("Consent decree (hybrid)", "1-practice divestiture + behavioral",
                          9, 22.5, 0.042, 0.78),
        RemediationOption("Abandon deal", "Total termination",
                          0, 15.0, 1.000, 1.00),
        RemediationOption("Litigate FTC challenge", "Contest Second Request + PI",
                          24, 85.0, 0.175, 0.35),
    ]


# State-AG posture → a 0-20 review-risk contribution. The most aggressive
# merger-review states (CA OHCA, OR, NY) drive real timeline + challenge risk.
_STATE_POSTURE_RISK = {
    "active scrutiny": 20.0,
    "active review": 12.0,
    "standard review": 6.0,
    "minimal scrutiny": 2.0,
}


def _state_posture(state_reviews: List[StateReview], state: str) -> tuple:
    """Resolve a 2-letter / name state input to (matched_review, posture).
    Falls back to 'standard review' for states not in the illustrative set."""
    s = (state or "").strip().lower()
    if not s:
        return None, "standard review"
    for rv in state_reviews:
        full = rv.state.lower()
        # match on the leading state name or a parenthetical 2-letter-ish token
        if full.startswith(s) or f"({s}" in full or s in full.split(" (")[0]:
            return rv, rv.state_ag_posture
    # common abbreviations → posture even if not in the table
    abbr = {
        "ca": "active scrutiny", "or": "active scrutiny", "ny": "active scrutiny",
        "ma": "active review", "wa": "standard review", "ct": "standard review",
        "il": "standard review", "co": "standard review", "tx": "minimal scrutiny",
        "fl": "minimal scrutiny",
    }
    return None, abbr.get(s, "standard review")


def compute_antitrust_screener(
    deal_size_mm: float = 485.0,
    *,
    acquirer_size_mm: float = 1850.0,
    combined_share_pct: float = None,
    state: str = "TX",
) -> AntitrustResult:
    """Input-driven antitrust risk.

    The headline risk now genuinely responds to the levers a partner can
    change — deal size, acquirer size, the deal's top-market combined share
    (the real concentration signal), and the primary review state — instead of
    being dominated by a fixed Texas-anesthesiology scenario (which left the
    score unchanged no matter the deal size). The MSA/HHI/overlap tables below
    remain an illustrative worked example; the SCORE is computed from inputs.
    """
    corpus = _load_corpus()

    hhi = _build_hhi()
    hsr = _build_hsr()
    overlaps = _build_overlaps()
    case_law = _build_case_law()
    state_reviews = _build_state_reviews()
    remediations = _build_remediations()

    # Combined market share is the dominant antitrust driver. If the caller
    # doesn't supply one, fall back to the worked example's worst market.
    if combined_share_pct is None:
        combined_share_pct = max((o.combined_share_pct for o in overlaps), default=40.0)
    combined_share_pct = max(0.0, min(100.0, float(combined_share_pct)))

    hsr_req = deal_size_mm >= 119.5

    # ── Risk components, each genuinely input-driven (sum capped at 100) ──
    # Concentration (0-45): <25% benign; 35-50% material; >50% presumptively
    # anticompetitive under the 2023 Merger Guidelines (30%+ share + HHI bump).
    share_risk = max(0.0, min(45.0, (combined_share_pct - 25.0) * 1.45))
    # Deal size (0-20): bigger transactions draw more scrutiny + HSR fee tiers.
    size_risk = max(0.0, min(20.0, (deal_size_mm - 119.5) / 70.0))
    # Serial acquirer (0-15): post-USAP/Welsh Carson, large sponsors with big
    # existing footprints face serial-acquisition theory.
    serial_risk = max(0.0, min(15.0, acquirer_size_mm / 350.0))
    # Primary-state AG posture (0-20).
    _matched, posture = _state_posture(state_reviews, state)
    state_risk = _STATE_POSTURE_RISK.get(posture, 6.0)

    risk_score = int(round(min(100.0, share_risk + size_risk + serial_risk + state_risk)))

    # Second-Request probability rises with concentration, size, and a
    # serial-acquirer footprint; HSR is a precondition.
    if not hsr_req:
        second_req_prob = 0.02
    else:
        second_req_prob = min(0.95, max(
            0.05,
            (combined_share_pct / 100.0) * 0.70
            + max(0.0, (deal_size_mm - 500.0) / 4000.0)
            + min(0.15, acquirer_size_mm / 12000.0),
        ))

    recommended_timeline = 6 if second_req_prob < 0.25 else (12 if second_req_prob < 0.5 else 18)

    return AntitrustResult(
        deal_size_mm=deal_size_mm,
        hsr_required=hsr_req,
        second_request_probability=round(second_req_prob, 3),
        overall_risk_score=risk_score,
        recommended_timeline_months=recommended_timeline,
        hhi_analysis=hhi,
        hsr_thresholds=hsr,
        overlaps=overlaps,
        case_law=case_law,
        state_reviews=state_reviews,
        remediations=remediations,
        corpus_deal_count=len(corpus),
    )
