"""Counterfactual solvers — one per risk module.

Each solver takes the current finding + returns the minimum input
change that flips the band. We use symbolic inverse against the
threshold YAMLs already in the platform (nothing new is fabricated;
thresholds are our ground truth).

Return type is always a :class:`Counterfactual`. Callers can
accumulate multiple counterfactuals via
:func:`advise_all` and render them in the Risk Workbench or IC
memo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..real_estate import (
    FACTOR_COVERAGE, FACTOR_ESCALATOR, FACTOR_GEOGRAPHY,
    FACTOR_LEASE_DURATION, FACTOR_REIT_LANDLORD,
    StewardRiskTier, StewardScoreResult,
)
from ..regulatory import (
    AntitrustExposure, CPOMReport, NSAExposure, RegulatoryBand,
    SiteNeutralExposure, TEAMExposure,
)


# ── Core dataclass ─────────────────────────────────────────────────

@dataclass
class Counterfactual:
    """One counterfactual recommendation.

    ``target_band`` is the band the recommendation would flip the
    finding to — always *better* than ``original_band`` (or equal,
    in cases where only partial improvement is feasible).
    """
    module: str                        # "CPOM" | "NSA" | "STEWARD" | ...
    original_band: str
    target_band: str                   # next-better band
    lever: str                         # short name of the change
    change_description: str            # human-readable
    estimated_dollar_impact_usd: float  # savings / deferred exposure
    feasibility: str = "MEDIUM"         # HIGH | MEDIUM | LOW
    narrative: str = ""
    deal_structure_implication: str = ""  # what it means for price
                                           # / structure

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class CounterfactualSet:
    """Collection of counterfactuals across modules, with one
    convenience accessor for the largest-impact lever."""
    items: List[Counterfactual] = field(default_factory=list)

    @property
    def largest_lever(self) -> Optional[Counterfactual]:
        if not self.items:
            return None
        return max(
            self.items,
            key=lambda c: abs(c.estimated_dollar_impact_usd),
        )

    @property
    def critical_findings_addressed(self) -> int:
        return sum(
            1 for c in self.items
            if c.original_band in ("RED", "CRITICAL")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [c.to_dict() for c in self.items],
            "largest_lever": (
                self.largest_lever.to_dict()
                if self.largest_lever else None
            ),
            "critical_findings_addressed":
                self.critical_findings_addressed,
        }


# ── CPOM ───────────────────────────────────────────────────────────

def for_cpom(report: CPOMReport) -> Optional[Counterfactual]:
    """If CPOM is RED, the minimum change is to restructure to a
    legal structure that isn't on the banned list in the RED states
    — typically DIRECT_EMPLOYMENT."""
    if report.overall_band != RegulatoryBand.RED:
        return None
    red_states = [
        s for s in report.per_state if s.band == RegulatoryBand.RED
    ]
    red_dollars = sum(s.remediation_cost_usd for s in red_states)
    return Counterfactual(
        module="CPOM",
        original_band="RED",
        target_band="GREEN",
        lever="restructure_to_direct_employment",
        change_description=(
            f"Restructure the target's legal vehicle from "
            f"{report.target_structure} to DIRECT_EMPLOYMENT before "
            f"close in: {', '.join(s.state_code for s in red_states)}."
        ),
        estimated_dollar_impact_usd=red_dollars,
        feasibility="MEDIUM",
        narrative=(
            f"Direct-employment is not on the structure_bans list in "
            f"any of the {len(red_states)} RED states. Restructuring "
            f"costs ~${red_dollars:,.0f} in legal + dissolution fees "
            f"but removes the voided-contract risk entirely."
        ),
        deal_structure_implication=(
            "Bake restructuring cost into the closing balance sheet; "
            "require seller to warrant the old-structure contracts "
            "are being unwound at or before close."
        ),
    )


# ── NSA IDR ────────────────────────────────────────────────────────

# Band thresholds from the YAML.
_NSA_CRITICAL_SHARE = 0.35
_NSA_WATCH_SHARE = 0.20


def for_nsa(exposure: NSAExposure) -> Optional[Counterfactual]:
    """NSA counterfactuals. The only lawful lever is reducing OON
    share via contracting (or shedding OON volume). Rate-
    renegotiation above QPA isn't available under IDR."""
    if exposure.band not in (RegulatoryBand.RED, RegulatoryBand.YELLOW):
        return None

    current_share = exposure.oon_revenue_share
    oon_dollars = exposure.dollars_at_risk_usd

    if exposure.band == RegulatoryBand.RED:
        target_share = _NSA_WATCH_SHARE - 0.01       # fall just below the WATCH line is still YELLOW; we want GREEN
        # To get to GREEN we need below the WATCH threshold
        # AND shortfall below WATCH; easier to state as hitting the
        # WATCH boundary first.
        target_band = "YELLOW"
    else:  # YELLOW
        target_share = _NSA_WATCH_SHARE - 0.01
        target_band = "GREEN"

    # Reduction needed (absolute).
    reduction_pp = current_share - _NSA_WATCH_SHARE
    # Dollar savings proportional to the share reduction.
    if current_share > 0 and exposure.dollars_at_risk_usd > 0:
        savings = oon_dollars * (reduction_pp / current_share)
    else:
        savings = 0.0

    return Counterfactual(
        module="NSA",
        original_band=exposure.band.value,
        target_band=target_band,
        lever="contract_top_payers_to_reduce_oon_share",
        change_description=(
            f"Contract top payers to move {reduction_pp*100:.1f} "
            f"percentage points of volume from OON to in-network. "
            f"Current OON share {current_share*100:.0f}% → "
            f"target ≤{_NSA_WATCH_SHARE*100:.0f}%."
        ),
        estimated_dollar_impact_usd=savings,
        feasibility="MEDIUM",
        narrative=(
            f"Move an estimated ${savings:,.0f} of OON revenue into "
            f"contracted rates. IDR revert to QPA is no longer a "
            f"cliff because the exposed volume drops below the "
            f"{_NSA_WATCH_SHARE*100:.0f}% threshold. Contracting with "
            f"the top 2-3 payers by volume typically achieves this."
        )
        + (f" Matches {exposure.case_study_match}."
           if exposure.case_study_match else ""),
        deal_structure_implication=(
            "Price in the OON-to-INN migration cost (payer rate "
            "concessions, 12-18 month integration); require seller "
            "to warrant no adverse payer termination before close."
        ),
    )


# ── Steward Score ─────────────────────────────────────────────────

_STEWARD_FACTOR_LEVERS = {
    FACTOR_LEASE_DURATION: (
        "shorten_lease_to_15y",
        "Negotiate lease term to ≤15 years at signing "
        "(or include mutual termination rights at year 15).",
        "Landlord may concede for a higher escalator trade-off — "
        "compute the NPV trade-off explicitly before agreeing.",
    ),
    FACTOR_ESCALATOR: (
        "cap_escalator_at_3_pct",
        "Cap annual escalator at ≤3.0% (or CPI-linked with 3% cap).",
        "Reduces the 5-10 year PV of lease obligations materially.",
    ),
    FACTOR_COVERAGE: (
        "improve_ebitdar_coverage",
        "Improve EBITDAR coverage to ≥1.4x via post-close "
        "contract renegotiation or rent-reduction amendment.",
        "Requires operating-side intervention + landlord cooperation.",
    ),
    FACTOR_GEOGRAPHY: (
        "cannot_change_geography",
        "Geographic exposure is structural — cannot counterfactual.",
        "Remaining counterfactuals focus on the other four factors.",
    ),
    FACTOR_REIT_LANDLORD: (
        "transition_to_non_reit_landlord",
        "Transition to a non-REIT landlord (ground-lease swap, "
        "buyout, or structural separation) before close.",
        "High-cost but ELIMINATES the Steward-pattern match.",
    ),
}


def for_steward(
    result: StewardScoreResult,
    *,
    annual_rent_usd: Optional[float] = None,
    current_escalator_pct: Optional[float] = None,
    current_term_years: Optional[int] = None,
    hold_years: int = 10,
    discount_rate: float = 0.075,
) -> Optional[Counterfactual]:
    """Steward Score counterfactuals with real PV savings when
    lease details are supplied.

    When ``annual_rent_usd`` + ``current_escalator_pct`` are
    supplied, computes the NPV savings from capping the escalator
    at 3.0% over the hold period. Otherwise falls back to a
    qualitative (zero-dollar) recommendation.

    Strategy: prefer the most feasible lever that moves the tier
    downward. Geography is immovable; escalator is easiest;
    REIT-landlord swap is highest-impact but lowest-feasibility.
    """
    if result.tier not in (StewardRiskTier.CRITICAL, StewardRiskTier.HIGH):
        return None
    removable = [
        f for f in result.factors_hit
        if f != FACTOR_GEOGRAPHY
    ]
    if not removable:
        return None
    preferred_order = [
        FACTOR_ESCALATOR,
        FACTOR_LEASE_DURATION,
        FACTOR_COVERAGE,
        FACTOR_REIT_LANDLORD,
    ]
    chosen = next(
        (f for f in preferred_order if f in removable), removable[0],
    )
    lever_name, change, implication = _STEWARD_FACTOR_LEVERS[chosen]
    new_count = result.factor_count - 1
    target_band = (
        "CRITICAL" if new_count >= 5 else
        "HIGH" if new_count == 4 else
        "MEDIUM" if new_count == 3 else "LOW"
    )
    feasibility = (
        "HIGH" if chosen == FACTOR_ESCALATOR else
        "MEDIUM" if chosen == FACTOR_LEASE_DURATION else
        "LOW"
    )

    # Dollar impact — NPV of the escalator delta when the numbers
    # are available.
    dollar_impact = 0.0
    if (chosen == FACTOR_ESCALATOR
            and annual_rent_usd and annual_rent_usd > 0
            and current_escalator_pct is not None
            and current_escalator_pct > 0.03):
        dollar_impact = _escalator_cap_pv_savings(
            annual_rent_usd=annual_rent_usd,
            current_escalator_pct=current_escalator_pct,
            target_escalator_pct=0.03,
            hold_years=min(
                hold_years,
                current_term_years if current_term_years else hold_years,
            ),
            discount_rate=discount_rate,
        )
    elif (chosen == FACTOR_LEASE_DURATION
            and annual_rent_usd and annual_rent_usd > 0
            and current_term_years and current_term_years > 15):
        # For shortening a lease to ≤15y, the dollar impact is the
        # PV of rent we avoid paying (post-year-15 exit optionality
        # value). We conservatively quote 1/3 of the post-15-year
        # rent PV as the captured savings.
        extra_years = current_term_years - 15
        if extra_years > 0:
            dollar_impact = _post_term_rent_pv_share(
                annual_rent_usd=annual_rent_usd,
                escalator_pct=current_escalator_pct or 0.03,
                extra_years=extra_years,
                start_year=16,
                discount_rate=discount_rate,
            ) / 3.0

    narrative = (
        f"Removing the {chosen} factor drops the Steward Score "
        f"from {result.factor_count}/5 to {new_count}/5 — "
        f"tier {result.tier.value} → {target_band}."
    )
    if dollar_impact > 0:
        if chosen == FACTOR_ESCALATOR:
            narrative += (
                f" PV savings from the escalator cap: "
                f"${dollar_impact:,.0f} over {hold_years}y at "
                f"{discount_rate*100:.1f}% discount."
            )
        elif chosen == FACTOR_LEASE_DURATION:
            narrative += (
                f" Exit-optionality value from shortening the lease: "
                f"~${dollar_impact:,.0f} NPV."
            )
    return Counterfactual(
        module="STEWARD",
        original_band=result.tier.value,
        target_band=target_band,
        lever=lever_name,
        change_description=change,
        estimated_dollar_impact_usd=dollar_impact,
        feasibility=feasibility,
        narrative=narrative,
        deal_structure_implication=implication,
    )


def _escalator_cap_pv_savings(
    *,
    annual_rent_usd: float,
    current_escalator_pct: float,
    target_escalator_pct: float,
    hold_years: int,
    discount_rate: float,
) -> float:
    """NPV of the rent differential when swapping one escalator for
    a lower one, evaluated over the hold period."""
    r = discount_rate
    cur = sum(
        annual_rent_usd * ((1 + current_escalator_pct) ** (y - 1))
        / ((1 + r) ** y)
        for y in range(1, hold_years + 1)
    )
    tgt = sum(
        annual_rent_usd * ((1 + target_escalator_pct) ** (y - 1))
        / ((1 + r) ** y)
        for y in range(1, hold_years + 1)
    )
    return max(0.0, cur - tgt)


def _post_term_rent_pv_share(
    *,
    annual_rent_usd: float,
    escalator_pct: float,
    extra_years: int,
    start_year: int,
    discount_rate: float,
) -> float:
    """PV of rent payments from ``start_year`` through
    ``start_year + extra_years - 1``."""
    r = discount_rate
    return sum(
        annual_rent_usd * ((1 + escalator_pct) ** (y - 1))
        / ((1 + r) ** y)
        for y in range(start_year, start_year + extra_years)
    )


# ── TEAM ──────────────────────────────────────────────────────────

def for_team(exposure: TEAMExposure) -> Optional[Counterfactual]:
    """TEAM counterfactuals. If RED, the lawful lever is electing a
    more conservative track (Track 1 has no downside in year 1)."""
    if exposure.band != RegulatoryBand.RED:
        return None
    # The CMS TEAM rule only offers Track 1 in year 1 (2026).
    # Recommend Track 1 enrollment as the counterfactual.
    current_track = exposure.track
    if current_track == "track_1":
        return None                 # already safest track
    target_track = "track_1"
    # Zero-downside track → annual_pnl_impact = 0 or positive (cap
    # at upside only).
    estimated_savings = abs(exposure.annual_pnl_impact_usd)
    return Counterfactual(
        module="TEAM",
        original_band=exposure.band.value,
        target_band="GREEN",
        lever="elect_track_1_no_downside",
        change_description=(
            f"Elect TEAM Track 1 (upside-only, capped +10%) for "
            f"year 1 (2026). Re-evaluate tracks 2/3 post-close "
            f"after one operating year of actual performance data."
        ),
        estimated_dollar_impact_usd=estimated_savings,
        feasibility="HIGH",
        narrative=(
            f"Track 1 has zero downside exposure. Current track "
            f"{current_track} projects "
            f"${exposure.annual_pnl_impact_usd:,.0f}/yr loss; "
            f"Track 1 caps loss at zero. Year-2 decision to move to "
            f"Track 2 is reversible; downside-exposed tracks are not."
        ),
        deal_structure_implication=(
            "Require seller to pre-elect Track 1 (or allow buyer to "
            "elect post-close by 2025-12-31 deadline)."
        ),
    )


# ── Antitrust ─────────────────────────────────────────────────────

def for_antitrust(
    exposure: AntitrustExposure,
) -> Optional[Counterfactual]:
    """Antitrust counterfactuals. The only lawful lever is
    divestiture of the concentration-producing holdings, or a
    geographic carve-out."""
    if exposure.band != RegulatoryBand.RED:
        return None
    return Counterfactual(
        module="ANTITRUST",
        original_band="RED",
        target_band="YELLOW",
        lever="divest_or_carve_out_overlap_msas",
        change_description=(
            f"Divest or carve out the {', '.join(exposure.target_msas)} "
            f"same-specialty overlap. Alternatively, structure as "
            f"MSO-only (management services, no practice roll-up) to "
            f"avoid the HHI contribution entirely."
        ),
        estimated_dollar_impact_usd=0.0,  # depends on holdings size
        feasibility="LOW",
        narrative=(
            f"Antitrust band RED means the 30-day FTC prior-notice "
            f"regime likely applies. A pre-signing carve-out or "
            f"structural separation is the only path to YELLOW. "
            f"Matching precedents: "
            f"{', '.join(exposure.matching_precedents) or 'USAP'}."
        ),
        deal_structure_implication=(
            "Build a divest-or-terminate covenant into the SPA; "
            "set 30-day FTC-review period between sign and close."
        ),
    )


# ── Cyber ─────────────────────────────────────────────────────────

def for_cyber(score: Any) -> Optional[Counterfactual]:
    """Cyber counterfactuals. Levers:
        - Replace Change Healthcare BA (removes cascade 2.5x)
        - Migrate EHR if overdue
        - IT staffing ratio adjustment (cheapest)

    Handles RED → YELLOW and YELLOW → GREEN transitions. When BI
    expected loss is known, quotes the expected-loss delta as the
    dollar impact (BA swap removes the cascade multiplier, dropping
    BI expected loss by the observed delta)."""
    band = getattr(score, "band", None)
    if band not in ("RED", "YELLOW"):
        return None
    findings = getattr(score, "findings", []) or []
    has_change_healthcare = any(
        "Change Healthcare" in str(f) for f in findings
    )
    bi_exp = float(getattr(score, "bi_expected_loss_usd", 0) or 0)
    target_band = "YELLOW" if band == "RED" else "GREEN"

    if has_change_healthcare:
        lever = "replace_change_healthcare_ba"
        change = (
            "Replace Change Healthcare / Optum clearinghouse with an "
            "alternative BA (Availity, pVerify, Waystar) before "
            "close."
        )
        feasibility = "MEDIUM"
        narrative = (
            "Change Healthcare's 2.5x cascade-risk multiplier drives "
            "the majority of the cyber rating. Swapping the BA "
            "removes the single largest systemic risk; migration "
            "runs 3-6 months with $500k-$1.5M in switching cost."
        )
        implication = (
            "Require BA migration covenant in the purchase agreement "
            "with a 180-day post-close deadline."
        )
        # BA swap removes the 2.5x cascade multiplier. BI expected
        # loss scales linearly with cascade; savings ≈ 1 − (1/2.5) ×
        # BI expected loss = 60% of BI.
        impact = bi_exp * 0.60
    elif band == "RED":
        lever = "close_it_staffing_gap"
        change = (
            "Close the IT staffing gap to benchmark (typically +3-8 "
            "FTE at a community-hospital target)."
        )
        feasibility = "HIGH"
        narrative = (
            "IT staffing at below-benchmark is the cheapest lever "
            "to flip Cyber YELLOW. A $500k-$1M recruiting spend "
            "in Y1 is material but small vs. the bridge-reserve "
            "savings."
        )
        implication = "Add IT staffing to the 100-day plan."
        impact = 0.0
    else:
        # YELLOW → GREEN path. No Change Healthcare; the next
        # highest-leverage move is migrating off an overdue EHR or
        # hiring external-rating-move staff.
        lever = "migrate_overdue_ehr_or_external_rating"
        change = (
            "Prioritise the single highest-risk finding: migrate off "
            "an overdue EHR (Epic >10y, community EHR >7y) or "
            "engage an external rating provider (BitSight / "
            "SecurityScorecard) and close the top-3 findings."
        )
        feasibility = "MEDIUM"
        narrative = (
            "YELLOW → GREEN requires addressing the top-3 external-"
            "rating findings or replacing an overdue EHR. Lower-"
            "priority than BA cascade removal but typically faster "
            "than RED remediation."
        )
        implication = (
            "Integrate with the 100-day plan as a governance item; "
            "target green-band within 12 months."
        )
        impact = 0.0
    return Counterfactual(
        module="CYBER",
        original_band=band,
        target_band=target_band,
        lever=lever,
        change_description=change,
        estimated_dollar_impact_usd=impact,
        feasibility=feasibility,
        narrative=narrative,
        deal_structure_implication=implication,
    )


# ── Site-neutral ──────────────────────────────────────────────────

def for_site_neutral(
    exposure: SiteNeutralExposure,
) -> Optional[Counterfactual]:
    """Site-neutral counterfactuals. The only lever is to
    re-categorize or divest the exposed HOPDs before the
    grandfathering expires."""
    if exposure.band != RegulatoryBand.RED:
        return None
    return Counterfactual(
        module="SITE_NEUTRAL",
        original_band="RED",
        target_band="YELLOW",
        lever="divest_or_recategorize_grandfathered_hopds",
        change_description=(
            "Divest the grandfathered off-campus HOPDs or convert "
            "them to provider-based clinics that meet the on-campus "
            "status exemption before 2026-01-01."
        ),
        estimated_dollar_impact_usd=(
            exposure.annual_revenue_erosion_usd * 0.6
        ),
        feasibility="LOW",
        narrative=(
            f"Site-neutral erosion of "
            f"${exposure.annual_revenue_erosion_usd:,.0f}/yr "
            f"({exposure.annual_revenue_erosion_pct*100:.1f}%) is "
            f"already the current CMS rule. Recategorizing to "
            f"on-campus status eliminates roughly 60% of the "
            f"exposure; the remaining 40% is MedPAC-scenario tail "
            f"risk."
        ),
        deal_structure_implication=(
            "Price in 100% of the current-scenario erosion; take a "
            "20-30% reserve against the MedPAC tail."
        ),
    )


# ── Orchestration ─────────────────────────────────────────────────

def advise_all(
    *,
    cpom: Optional[CPOMReport] = None,
    nsa: Optional[NSAExposure] = None,
    steward: Optional[StewardScoreResult] = None,
    team: Optional[TEAMExposure] = None,
    antitrust: Optional[AntitrustExposure] = None,
    cyber: Optional[Any] = None,
    site_neutral: Optional[SiteNeutralExposure] = None,
) -> CounterfactualSet:
    """Accumulate counterfactuals across every supplied module."""
    items: List[Counterfactual] = []
    for solver, arg in (
        (for_cpom, cpom),
        (for_nsa, nsa),
        (for_steward, steward),
        (for_team, team),
        (for_antitrust, antitrust),
        (for_cyber, cyber),
        (for_site_neutral, site_neutral),
    ):
        if arg is None:
            continue
        try:
            cf = solver(arg)
        except Exception:  # noqa: BLE001 — one bad module doesn't break the set
            cf = None
        if cf is not None:
            items.append(cf)
    return CounterfactualSet(items=items)
