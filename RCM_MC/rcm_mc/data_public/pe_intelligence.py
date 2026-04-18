"""PE intelligence layer: reasonableness bands, heuristics, and red-flag detection.

Encodes the intuitions a senior healthcare PE partner applies when stress-testing
a deal model before committing capital.  All thresholds are derived from the
public deals corpus and documented PE industry experience — not arbitrary.

Design:
    1. Reasonableness bands: IRR ceilings / floors by deal type, size, payer mix
    2. Lever timeframe heuristics: how quickly RCM / cost improvements realistically land
    3. Red-flag detector: specific patterns in deal assumptions that senior partners reject
    4. Deal-type classifier: infer deal type from buyer/seller/notes for threshold lookup

Public API:
    DealType enum
    ReasonablenessResult dataclass
    IntelligenceReport dataclass
    classify_deal_type(deal_dict)               -> DealType
    check_reasonableness(deal_dict, benchmarks) -> ReasonablenessResult
    check_lever_timeframes(assumptions_dict)    -> List[str]   (warnings)
    detect_red_flags(deal_dict, assumptions)    -> List[str]   (flags)
    full_intelligence_report(deal, assumptions, corpus_db_path) -> IntelligenceReport
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .base_rates import Benchmarks, get_benchmarks, get_benchmarks_by_payer, get_benchmarks_by_size


class DealType(Enum):
    PE_HOSPITAL_COMMUNITY   = "pe_hospital_community"      # rural/community PE buyout
    PE_HOSPITAL_ACADEMIC    = "pe_hospital_academic"       # AMC-adjacent
    PE_PHYSICIAN_STAFFING   = "pe_physician_staffing"      # EM/anesthesia/hospitalist
    PE_ASC                  = "pe_asc"                     # ambulatory surgery centers
    PE_BEHAVIORAL_HEALTH    = "pe_behavioral_health"       # psychiatric / substance use
    PE_LTAC_REHAB           = "pe_ltac_rehab"              # LTAC / IRF / SNF
    PE_HOME_HEALTH          = "pe_home_health"             # home health / hospice
    STRATEGIC_MERGER        = "strategic_merger"            # health system + health system
    STRATEGIC_ADD_ON        = "strategic_add_on"           # large system buys small
    UNKNOWN                 = "unknown"


# ---------------------------------------------------------------------------
# IRR reasonableness bands by deal type (from corpus analysis + public data)
# These are gross IRR targets; net is typically 200-300bps lower.
# ---------------------------------------------------------------------------
_IRR_BANDS: Dict[DealType, Tuple[float, float]] = {
    # (floor, ceiling) — both in decimal form
    DealType.PE_HOSPITAL_COMMUNITY:  (0.08, 0.25),   # typical 12-18% gross
    DealType.PE_HOSPITAL_ACADEMIC:   (0.06, 0.18),   # lower ceiling; harder to improve
    DealType.PE_PHYSICIAN_STAFFING:  (0.12, 0.35),   # higher ceiling; asset-light
    DealType.PE_ASC:                 (0.14, 0.40),   # high ceiling; capital-light
    DealType.PE_BEHAVIORAL_HEALTH:   (0.10, 0.35),   # wide range; Medicaid dependency risk
    DealType.PE_LTAC_REHAB:          (0.08, 0.22),   # Medicare-dominated; regulatory risk
    DealType.PE_HOME_HEALTH:         (0.08, 0.20),   # rate risk; PDGM complexity
    DealType.STRATEGIC_MERGER:       (0.0,  0.15),   # non-PE; synergy IRRs lower
    DealType.STRATEGIC_ADD_ON:       (0.05, 0.18),
    DealType.UNKNOWN:                (0.05, 0.30),
}

# MOIC bands by deal type
_MOIC_BANDS: Dict[DealType, Tuple[float, float]] = {
    DealType.PE_HOSPITAL_COMMUNITY:  (1.5, 4.0),
    DealType.PE_HOSPITAL_ACADEMIC:   (1.2, 3.0),
    DealType.PE_PHYSICIAN_STAFFING:  (1.8, 6.0),
    DealType.PE_ASC:                 (2.0, 7.0),
    DealType.PE_BEHAVIORAL_HEALTH:   (1.5, 6.0),
    DealType.PE_LTAC_REHAB:          (1.3, 3.5),
    DealType.PE_HOME_HEALTH:         (1.3, 3.0),
    DealType.STRATEGIC_MERGER:       (1.0, 2.5),
    DealType.STRATEGIC_ADD_ON:       (1.2, 3.0),
    DealType.UNKNOWN:                (1.2, 5.0),
}

# Payer-mix-adjusted MOIC haircut: Medicare-heavy = harder to grow revenue
_PAYER_MIX_MOIC_HAIRCUT: Dict[str, float] = {
    "medicare":   -0.3,   # fixed rates; harder to grow top-line
    "medicaid":   -0.5,   # rate uncertainty; state budget risk
    "commercial":  0.3,   # pricing power; RCM upside real
    "self_pay":   -0.2,   # collection risk
}

# EV/EBITDA reasonableness bands by deal type
_EV_EBITDA_BANDS: Dict[DealType, Tuple[float, float]] = {
    DealType.PE_HOSPITAL_COMMUNITY:  (5.0,  12.0),
    DealType.PE_HOSPITAL_ACADEMIC:   (4.0,  10.0),
    DealType.PE_PHYSICIAN_STAFFING:  (8.0,  18.0),
    DealType.PE_ASC:                 (8.0,  20.0),
    DealType.PE_BEHAVIORAL_HEALTH:   (6.0,  14.0),
    DealType.PE_LTAC_REHAB:          (5.0,  11.0),
    DealType.PE_HOME_HEALTH:         (6.0,  14.0),
    DealType.STRATEGIC_MERGER:       (4.0,  14.0),
    DealType.STRATEGIC_ADD_ON:       (4.0,  12.0),
    DealType.UNKNOWN:                (4.0,  18.0),
}

# ---------------------------------------------------------------------------
# RCM / operational lever timeframes (quarters to realistic first cash impact)
# ---------------------------------------------------------------------------
_LEVER_TIMEFRAMES_QTR: Dict[str, Tuple[int, int]] = {
    # lever_name: (min_quarters, realistic_quarters)
    "rcm_coding_improvement":        (2, 4),
    "rcm_denial_reduction":          (3, 6),
    "rcm_prior_auth_optimization":   (4, 8),
    "rcm_vendor_renegotiation":      (4, 8),
    "rcm_staff_training":            (3, 6),
    "managed_care_repricing":        (6, 12),   # payer contract cycles
    "supply_chain_savings":          (3, 6),
    "physician_alignment":           (6, 18),
    "service_line_expansion":        (8, 16),
    "volume_growth_organic":         (4, 12),
    "acquisition_add_on":            (6, 12),
    "real_estate_monetization":      (6, 18),
    "it_system_migration":           (8, 20),
    "labor_productivity":            (4, 10),
    "revenue_cycle_outsourcing":     (4, 8),
}

# ---------------------------------------------------------------------------
# Reasonableness result and intelligence report dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ReasonablenessResult:
    deal_type: DealType
    irr_in_band: Optional[bool]        # None = not enough data
    moic_in_band: Optional[bool]
    ev_ebitda_in_band: Optional[bool]
    irr_band: Tuple[float, float]
    moic_band: Tuple[float, float]
    ev_ebitda_band: Tuple[float, float]
    payer_adjusted_moic_ceiling: Optional[float]
    corpus_moic_p50: Optional[float]
    corpus_irr_p50: Optional[float]
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "deal_type": self.deal_type.value,
            "irr_in_band": self.irr_in_band,
            "moic_in_band": self.moic_in_band,
            "ev_ebitda_in_band": self.ev_ebitda_in_band,
            "irr_band": {"floor": self.irr_band[0], "ceiling": self.irr_band[1]},
            "moic_band": {"floor": self.moic_band[0], "ceiling": self.moic_band[1]},
            "ev_ebitda_band": {"floor": self.ev_ebitda_band[0], "ceiling": self.ev_ebitda_band[1]},
            "payer_adjusted_moic_ceiling": self.payer_adjusted_moic_ceiling,
            "corpus_moic_p50": self.corpus_moic_p50,
            "corpus_irr_p50": self.corpus_irr_p50,
            "warnings": self.warnings,
        }


@dataclass
class IntelligenceReport:
    deal_name: str
    deal_type: DealType
    reasonableness: ReasonablenessResult
    lever_warnings: List[str]
    red_flags: List[str]
    heuristic_notes: List[str]

    @property
    def risk_score(self) -> int:
        """0-10 composite risk score. 10 = maximum red-flag density."""
        n = len(self.red_flags) * 2 + len(self.lever_warnings)
        return min(10, n)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "deal_type": self.deal_type.value,
            "risk_score": self.risk_score,
            "reasonableness": self.reasonableness.as_dict(),
            "lever_warnings": self.lever_warnings,
            "red_flags": self.red_flags,
            "heuristic_notes": self.heuristic_notes,
        }


# ---------------------------------------------------------------------------
# Deal type classifier
# ---------------------------------------------------------------------------

_STAFFING_SIGNALS  = {"emcare", "teamhealth", "envision", "amsurg", "staffing",
                       "physician", "em ", "emergency medicine", "anesthesia",
                       "hospitalist", "radiology"}
_ASC_SIGNALS       = {"surgery partners", "surgicenter", "ambulatory", "asc ",
                       "surgical center", "outpatient surgery"}
_BEHAVIORAL_SIGNALS = {"behavioral", "psychiatric", "acadia", "mental health",
                        "substance", "addiction", "psych"}
_LTAC_SIGNALS      = {"ltac", "long-term acute", "kindred", "scionhealth",
                       "select medical", "encompass", "rehabilitation",
                       "inpatient rehab", "irf "}
_HOME_HEALTH_SIGNALS = {"home health", "hospice", "brightspring", "gentiva",
                         "amedisys", "lhc group", "home care"}
_RURAL_SIGNALS     = {"rural", "community hospital", "critical access",
                       "lifepoint", "quorum", "rcch", "regionalcare", "capella",
                       "steward", "iasis", "ardent"}


def _text_signals(deal: Dict[str, Any]) -> str:
    parts = [
        str(deal.get("deal_name", "")),
        str(deal.get("buyer", "")),
        str(deal.get("seller", "")),
        str(deal.get("notes", "")),
    ]
    return " ".join(parts).lower()


def classify_deal_type(deal: Dict[str, Any]) -> DealType:
    """Infer deal type from deal_name, buyer, seller, and notes."""
    text = _text_signals(deal)
    buyer = str(deal.get("buyer", "")).lower()

    # Specific asset types take precedence — check before buyer type so that
    # strategic acquirers buying home health (e.g. Humana + Kindred at Home)
    # get the asset-type label, not the generic strategic merger label.
    if any(s in text for s in _ASC_SIGNALS):
        return DealType.PE_ASC
    if any(s in text for s in _STAFFING_SIGNALS):
        return DealType.PE_PHYSICIAN_STAFFING
    if any(s in text for s in _BEHAVIORAL_SIGNALS):
        return DealType.PE_BEHAVIORAL_HEALTH
    # Home health before LTAC: "Kindred at Home" has "kindred" (LTAC) but is home health
    if any(s in text for s in _HOME_HEALTH_SIGNALS):
        return DealType.PE_HOME_HEALTH
    if any(s in text for s in _LTAC_SIGNALS):
        return DealType.PE_LTAC_REHAB

    # Non-PE / strategic buyer check (after asset type so home health beats Humana check)
    non_pe_buyers = {"community health systems", "tenet", "hca", "uhs",
                     "advocate", "commonspirit", "atrium", "humana",
                     "mass general brigham", "partners healthcare"}
    if any(nb in buyer for nb in non_pe_buyers) or ("merger" in text and "non-profit" in text):
        return DealType.STRATEGIC_MERGER

    if any(s in text for s in _RURAL_SIGNALS):
        return DealType.PE_HOSPITAL_COMMUNITY
    if "academic" in text or "university" in text or "medical center" in text:
        return DealType.PE_HOSPITAL_ACADEMIC

    # Generic PE hospital if sponsor is known PE firm
    pe_buyers = {"kkr", "blackstone", "tpg", "apollo", "carlyle", "bain",
                 "cerberus", "warburg", "leonard green", "sterling",
                 "h.i.g", "cressey", "waud", "martin ventures"}
    if any(pb in buyer for pb in pe_buyers):
        return DealType.PE_HOSPITAL_COMMUNITY

    return DealType.UNKNOWN


# ---------------------------------------------------------------------------
# Reasonableness check
# ---------------------------------------------------------------------------

def _dominant_payer(payer_mix: Any) -> Optional[str]:
    if not payer_mix:
        return None
    if isinstance(payer_mix, str):
        try:
            payer_mix = json.loads(payer_mix)
        except json.JSONDecodeError:
            return None
    if isinstance(payer_mix, dict) and payer_mix:
        return max(payer_mix, key=lambda k: payer_mix[k])
    return None


def _payer_adjusted_moic_ceiling(deal_type: DealType, payer_mix: Any) -> Optional[float]:
    """Apply payer-mix haircuts to the type-based MOIC ceiling."""
    base_ceiling = _MOIC_BANDS[deal_type][1]
    if not payer_mix:
        return base_ceiling
    if isinstance(payer_mix, str):
        try:
            payer_mix = json.loads(payer_mix)
        except json.JSONDecodeError:
            return base_ceiling
    if not isinstance(payer_mix, dict):
        return base_ceiling

    haircut = 0.0
    for payer, share in payer_mix.items():
        h = _PAYER_MIX_MOIC_HAIRCUT.get(payer, 0.0)
        haircut += h * float(share)

    return max(1.0, base_ceiling + haircut)


def check_reasonableness(
    deal: Dict[str, Any],
    benchmarks: Optional[Benchmarks] = None,
) -> ReasonablenessResult:
    """Check whether deal financials fall within historical reasonableness bands.

    benchmarks: optional Benchmarks from base_rates; used to compare against
    corpus P50 values.  If None, corpus comparisons are skipped.
    """
    deal_type = classify_deal_type(deal)
    irr_band  = _IRR_BANDS[deal_type]
    moic_band = _MOIC_BANDS[deal_type]
    ev_ebitda_band = _EV_EBITDA_BANDS[deal_type]

    proj_irr  = deal.get("realized_irr")   or deal.get("projected_irr")
    proj_moic = deal.get("realized_moic")  or deal.get("projected_moic")
    ev        = deal.get("ev_mm")
    ebitda    = deal.get("ebitda_at_entry_mm")
    payer_mix = deal.get("payer_mix")

    irr_in_band   = (irr_band[0] <= proj_irr   <= irr_band[1])   if proj_irr   is not None else None
    moic_in_band  = (moic_band[0] <= proj_moic <= moic_band[1]) if proj_moic is not None else None
    ev_ebitda_in_band = None
    if ev and ebitda and ebitda > 0:
        multiple = ev / ebitda
        ev_ebitda_in_band = ev_ebitda_band[0] <= multiple <= ev_ebitda_band[1]

    adj_ceiling = _payer_adjusted_moic_ceiling(deal_type, payer_mix)

    warnings: List[str] = []
    if irr_in_band is False:
        if proj_irr > irr_band[1]:
            warnings.append(
                f"Projected IRR {proj_irr:.1%} exceeds ceiling {irr_band[1]:.1%} "
                f"for {deal_type.value} deals in corpus"
            )
        else:
            warnings.append(
                f"Projected IRR {proj_irr:.1%} below floor {irr_band[0]:.1%} "
                f"for {deal_type.value} deals"
            )
    if moic_in_band is False:
        if proj_moic > moic_band[1]:
            warnings.append(
                f"Projected MOIC {proj_moic:.2f}x exceeds ceiling {moic_band[1]:.2f}x "
                f"for {deal_type.value} deals"
            )
    if proj_moic is not None and adj_ceiling is not None and proj_moic > adj_ceiling:
        warnings.append(
            f"Payer-mix-adjusted MOIC ceiling is {adj_ceiling:.2f}x; "
            f"projected {proj_moic:.2f}x exceeds it"
        )
    if ev_ebitda_in_band is False:
        multiple = ev / ebitda if ev and ebitda else 0
        warnings.append(
            f"EV/EBITDA {multiple:.1f}x outside band {ev_ebitda_band[0]:.1f}x–"
            f"{ev_ebitda_band[1]:.1f}x for {deal_type.value}"
        )

    return ReasonablenessResult(
        deal_type             = deal_type,
        irr_in_band           = irr_in_band,
        moic_in_band          = moic_in_band,
        ev_ebitda_in_band     = ev_ebitda_in_band,
        irr_band              = irr_band,
        moic_band             = moic_band,
        ev_ebitda_band        = ev_ebitda_band,
        payer_adjusted_moic_ceiling = adj_ceiling,
        corpus_moic_p50       = benchmarks.moic_p50 if benchmarks else None,
        corpus_irr_p50        = benchmarks.irr_p50  if benchmarks else None,
        warnings              = warnings,
    )


# ---------------------------------------------------------------------------
# Lever timeframe checker
# ---------------------------------------------------------------------------

def check_lever_timeframes(assumptions: Dict[str, Any]) -> List[str]:
    """Return warnings when assumed value-creation lever timelines are too aggressive.

    assumptions: dict with keys matching _LEVER_TIMEFRAMES_QTR, values in quarters.
    Example: {"rcm_denial_reduction": 2, "managed_care_repricing": 4}
    """
    warnings: List[str] = []
    for lever, assumed_qtrs in assumptions.items():
        if lever not in _LEVER_TIMEFRAMES_QTR:
            continue
        min_qtrs, realistic_qtrs = _LEVER_TIMEFRAMES_QTR[lever]
        if assumed_qtrs < min_qtrs:
            warnings.append(
                f"'{lever}': assumed {assumed_qtrs}Q is below minimum realistic "
                f"{min_qtrs}Q — will not land in time for LP distributions"
            )
        elif assumed_qtrs < realistic_qtrs:
            warnings.append(
                f"'{lever}': assumed {assumed_qtrs}Q is optimistic; "
                f"historical median is ~{realistic_qtrs}Q"
            )
    return warnings


# ---------------------------------------------------------------------------
# Red flag detector
# ---------------------------------------------------------------------------

_RED_FLAG_RULES: List[Tuple[str, Any]] = [
    # (flag_description, check_function)
]

def detect_red_flags(
    deal: Dict[str, Any],
    assumptions: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Detect patterns that a senior PE healthcare partner would flag at IC.

    Checks both deal-level financials and model assumptions.  Returns a list
    of plain-English flag strings (empty list = no flags triggered).
    """
    flags: List[str] = []
    assumptions = assumptions or {}

    ev    = deal.get("ev_mm") or 0
    ebitda = deal.get("ebitda_at_entry_mm") or 0
    hold  = deal.get("hold_years")
    moic  = (deal.get("realized_moic") or deal.get("projected_moic")) or 0
    irr   = (deal.get("realized_irr")  or deal.get("projected_irr")) or 0
    payer_mix = deal.get("payer_mix") or {}
    if isinstance(payer_mix, str):
        try:
            payer_mix = json.loads(payer_mix)
        except json.JSONDecodeError:
            payer_mix = {}

    # 1. Leverage check
    debt_mm = assumptions.get("entry_debt_mm")
    if debt_mm and ebitda > 0:
        leverage = debt_mm / ebitda
        if leverage > 8.0:
            flags.append(
                f"RED FLAG: Entry leverage {leverage:.1f}x EBITDA exceeds 8x — "
                "Quorum Health filed Ch. 11 at ~9x; lender syndication risk is high"
            )
        elif leverage > 6.5:
            flags.append(
                f"CAUTION: Entry leverage {leverage:.1f}x EBITDA is above 6.5x — "
                "requires near-perfect operational execution; refinancing risk in rate cycle"
            )

    # 2. Medicare + Medicaid concentration
    medicare_share = float(payer_mix.get("medicare", 0))
    medicaid_share = float(payer_mix.get("medicaid", 0))
    govt_payer = medicare_share + medicaid_share
    if govt_payer > 0.80 and moic > 2.5:
        flags.append(
            f"RED FLAG: {govt_payer:.0%} government payer with {moic:.2f}x MOIC target — "
            "fixed government rates cap revenue growth; corpus shows max ~2.3x for >80% govt payer"
        )

    # 3. Medicaid rate uncertainty
    if medicaid_share > 0.35 and not assumptions.get("medicaid_rate_haircut_modeled"):
        flags.append(
            f"CAUTION: Medicaid is {medicaid_share:.0%} of revenue — "
            "model should include a Medicaid rate cut scenario; "
            "state budget cycles create binary reimbursement risk"
        )

    # 4. IRR too high relative to deal type
    deal_type = classify_deal_type(deal)
    irr_ceiling = _IRR_BANDS[deal_type][1]
    if irr > irr_ceiling * 1.25:
        flags.append(
            f"RED FLAG: Projected IRR {irr:.1%} is >25% above ceiling {irr_ceiling:.1%} "
            f"for {deal_type.value} deals in public corpus — assumptions likely too aggressive"
        )

    # 5. Hold period too short for value creation
    rcm_levers = [k for k in assumptions if k.startswith("rcm_")]
    if rcm_levers and hold is not None and hold < 3.0:
        flags.append(
            f"CAUTION: {len(rcm_levers)} RCM levers modeled with only "
            f"{hold:.1f}-year hold — RCM initiatives typically require 3-4 years "
            "to fully cycle through payer contracts and show in EBITDA"
        )

    # 6. Managed care repricing assumed too fast
    mcp_qtrs = assumptions.get("managed_care_repricing")
    if mcp_qtrs is not None and mcp_qtrs < 6:
        flags.append(
            f"RED FLAG: Managed care repricing modeled in {mcp_qtrs}Q — "
            "payer contract cycles are 2-3 years; you cannot force renegotiation "
            "before the contract anniversary without triggering termination risk"
        )

    # 7. Envision pattern — out-of-network billing dependence
    notes = str(deal.get("notes", "")).lower()
    if ("out-of-network" in notes or "oon billing" in notes) and not assumptions.get("nsa_impact_modeled"):
        flags.append(
            "RED FLAG: Out-of-network billing appears in deal notes — "
            "No Surprises Act (Jan 2022) caps OON reimbursement at in-network median; "
            "Envision lost $1B+ EBITDA post-NSA; model must stress OON revenue to zero"
        )

    # 8. Sale-leaseback without coverage ratio
    if assumptions.get("sale_leaseback_proceeds_mm") and not assumptions.get("rent_coverage_ratio"):
        flags.append(
            "CAUTION: Sale-leaseback modeled without a stated rent coverage ratio — "
            "Steward's collapse was driven by fixed rent obligations; "
            "target ≥2.0x EBITDAR/rent coverage at exit"
        )

    # 9. Unrealistic RCM improvement scope
    rcm_lift_mm = assumptions.get("rcm_revenue_lift_mm")
    if rcm_lift_mm and ebitda > 0:
        pct_of_ebitda = rcm_lift_mm / ebitda
        if pct_of_ebitda > 0.40:
            flags.append(
                f"RED FLAG: RCM improvement of ${rcm_lift_mm:.0f}M = "
                f"{pct_of_ebitda:.0%} of entry EBITDA — "
                "corpus-implied maximum is ~15-25% of EBITDA from pure RCM; "
                "remainder requires volume or rate growth to be credible"
            )
        elif pct_of_ebitda > 0.25:
            flags.append(
                f"CAUTION: RCM improvement of {pct_of_ebitda:.0%} of EBITDA is in the "
                "upper quartile of historical outcomes — requires best-in-class execution "
                "AND favorable payer mix; apply sensitivity"
            )

    # 10. No payer mix in model
    if not payer_mix:
        flags.append(
            "CAUTION: No payer mix provided — payer mix is the single largest driver "
            "of revenue ceiling and RCM complexity; underwriting without it is incomplete"
        )

    # 11. Volume growth assumed in declining market
    vol_growth = assumptions.get("volume_growth_annual_pct")
    if vol_growth is not None and vol_growth > 0.04:
        if medicare_share > 0.50:
            flags.append(
                f"CAUTION: {vol_growth:.1%} annual volume growth assumed with "
                f"{medicare_share:.0%} Medicare — Medicare Advantage site-of-care "
                "shifts to ambulatory are eroding inpatient volume at ~1-3% per year; "
                "positive inpatient volume growth requires strong service line thesis"
            )

    # 12. Acquisition premium vs. EBITDA multiple
    if ev > 0 and ebitda > 0:
        multiple = ev / ebitda
        if multiple > 12 and deal_type == DealType.PE_HOSPITAL_COMMUNITY:
            flags.append(
                f"CAUTION: Entry multiple {multiple:.1f}x EBITDA for community hospital — "
                "historical realized exits cluster at 6-10x; "
                "you need material EBITDA growth just to achieve 1.5x MOIC at 10x exit"
            )

    return flags


# ---------------------------------------------------------------------------
# Heuristics from senior PE healthcare partners
# ---------------------------------------------------------------------------

def _heuristic_notes(deal: Dict[str, Any], deal_type: DealType) -> List[str]:
    """Non-fatal observations that experienced investors would raise at IC."""
    notes: List[str] = []
    payer_mix = deal.get("payer_mix") or {}
    if isinstance(payer_mix, str):
        try:
            payer_mix = json.loads(payer_mix)
        except json.JSONDecodeError:
            payer_mix = {}

    commercial = float(payer_mix.get("commercial", 0))
    medicare   = float(payer_mix.get("medicare", 0))
    medicaid   = float(payer_mix.get("medicaid", 0))

    if commercial > 0.45 and deal_type == DealType.PE_HOSPITAL_COMMUNITY:
        notes.append(
            f"Above-average commercial mix ({commercial:.0%}) for community hospital — "
            "verify these are not Medicare Advantage lives being counted as commercial; "
            "MA rates are ~15% below traditional Medicare in many markets"
        )

    if deal_type == DealType.PE_LTAC_REHAB:
        notes.append(
            "LTAC-qualifying patient criteria (25% threshold rule) are the primary "
            "billing/compliance risk; any model should stress 5-10% qualifying rate decline"
        )

    if deal_type == DealType.PE_HOME_HEALTH:
        notes.append(
            "PDGM (Patient-Driven Groupings Model) shifted home health reimbursement "
            "to clinical mix basis in 2020; ensure model uses post-PDGM episode rates "
            "and models LUPA threshold sensitivity"
        )

    if deal_type == DealType.PE_PHYSICIAN_STAFFING:
        notes.append(
            "No Surprises Act IDR process creates timing uncertainty on OON collections; "
            "model cash timing at 90-120 days for arbitration resolution"
        )

    if deal_type == DealType.PE_BEHAVIORAL_HEALTH:
        notes.append(
            "Mental Health Parity law enforcement is increasing scrutiny on "
            "prior auth denial rates; Medicaid managed care contracts are primary "
            "coverage mechanism but vary widely by state"
        )

    year = deal.get("year") or 0
    if year >= 2020:
        notes.append(
            "Post-COVID labor market: travel nurse / locum physician cost normalization "
            "is ongoing; model should show explicit labor cost trajectory vs. 2021-22 peak"
        )

    return notes


# ---------------------------------------------------------------------------
# Combined report
# ---------------------------------------------------------------------------

def full_intelligence_report(
    deal: Dict[str, Any],
    assumptions: Optional[Dict[str, Any]] = None,
    corpus_db_path: Optional[str] = None,
) -> IntelligenceReport:
    """Generate a complete PE intelligence report for a deal.

    deal: normalized deal dict (from normalizer.normalize_raw or DealsCorpus.get)
    assumptions: model assumptions dict (lever timeframes, leverage, etc.)
    corpus_db_path: path to the corpus SQLite file for benchmark comparison;
                    if None, corpus benchmarks are skipped
    """
    assumptions = assumptions or {}

    benchmarks: Optional[Benchmarks] = None
    if corpus_db_path:
        try:
            benchmarks = get_benchmarks(corpus_db_path)
        except Exception:
            benchmarks = None

    deal_type    = classify_deal_type(deal)
    reasonableness = check_reasonableness(deal, benchmarks)
    lever_warnings = check_lever_timeframes(assumptions)
    red_flags      = detect_red_flags(deal, assumptions)
    heuristics     = _heuristic_notes(deal, deal_type)

    return IntelligenceReport(
        deal_name      = str(deal.get("deal_name", "Unknown")),
        deal_type      = deal_type,
        reasonableness = reasonableness,
        lever_warnings = lever_warnings,
        red_flags      = red_flags,
        heuristic_notes = heuristics,
    )
