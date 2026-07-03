"""Life-sciences valuation engine — risk-adjusted NPV (rNPV) for drug,
device, and diagnostics assets, plus the adjacent subsector models a
life-sciences PE/growth investor actually underwrites.

Why this exists
---------------
The rest of ``finance/`` prices healthcare *services* businesses
(hospitals, ASCs, MSOs) where value is a multiple of recurring EBITDA.
Life sciences does not work that way. A pre-revenue therapeutics asset
has *negative* near-term cash flow, a binary clinical outcome, and a
finite patent-protected life. You cannot price it with an EBITDA
multiple; you price it with a **risk-adjusted NPV** that weights each
future cash flow by the cumulative probability that the molecule
actually reaches that point.

This module encodes that discipline explicitly and auditably — the same
philosophy as ``reimbursement_engine.py``: mechanism tables an analyst
can read and defend, transparent inference, no opaque black boxes.

Public surface
--------------
    from rcm_mc.finance.life_sciences import (
        # Enums / tables
        DevelopmentPhase, TherapeuticArea,
        PHASE_SUCCESS_TABLE, PHASE_DEFAULTS,
        # Core rNPV
        AssetRNPVConfig, RNPVResult, value_asset_rnpv, build_rnpv,
        cumulative_loa, likelihood_of_approval,
        # Peak-sales epidemiology funnel
        EpidemiologyFunnel, peak_sales_from_epidemiology,
        # Deal economics
        LicensingDeal, RoyaltyTier, value_licensing_deal,
        # Portfolio / company
        value_pipeline, runway_analysis,
        # Adjacent subsectors
        cdmo_capacity_model, diagnostics_unit_economics,
        # Side-by-side comparison
        compare_scenarios, compare_assets,
    )

Everything is pure-Python (``math`` + ``statistics`` only) so it drops
into the existing model stack with zero new dependencies, exactly like
``dcf_model.py`` and ``lbo_model.py``.

Benchmark provenance
--------------------
Clinical phase-transition probabilities and phase costs/durations are
seeded from the published literature and are *analyst-overridable
defaults*, not ground truth for any specific asset:

  * Wong, Siah & Lo (2019), "Estimation of clinical trial success rates
    and related parameters," *Biostatistics* 20(2).
  * BIO / Informa Pharma Intelligence / QLS (2021), "Clinical
    Development Success Rates and Contributing Factors 2011–2020."
  * DiMasi, Grabowski & Hansen (2016), "Innovation in the
    pharmaceutical industry: New estimates of R&D costs,"
    *J. Health Econ.* 47.

Every inferred/benchmark field is tagged in the result ``provenance``
dict so renderers can show ``benchmark_default`` vs ``analyst_input``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Phase framework
# ---------------------------------------------------------------------------
class DevelopmentPhase(str, Enum):
    """Ordered clinical-development stages.

    ``PRECLINICAL`` through ``FILED`` are cost-bearing development
    stages; ``APPROVED`` is the commercial stage where an asset
    generates net sales. Ordering matters — the engine schedules
    remaining phases from ``current_phase`` forward.
    """
    PRECLINICAL = "PRECLINICAL"
    PHASE_1 = "PHASE_1"
    PHASE_2 = "PHASE_2"
    PHASE_3 = "PHASE_3"
    FILED = "FILED"       # NDA/BLA submitted, under FDA review
    APPROVED = "APPROVED"  # marketed / commercial

    @property
    def order(self) -> int:
        return _PHASE_ORDER[self]


_PHASE_ORDER: Dict["DevelopmentPhase", int] = {
    DevelopmentPhase.PRECLINICAL: 0,
    DevelopmentPhase.PHASE_1: 1,
    DevelopmentPhase.PHASE_2: 2,
    DevelopmentPhase.PHASE_3: 3,
    DevelopmentPhase.FILED: 4,
    DevelopmentPhase.APPROVED: 5,
}

# The transition *out of* each phase (the gate you must pass to advance).
# PRECLINICAL→PHASE_1, PHASE_1→PHASE_2, PHASE_2→PHASE_3, PHASE_3→FILED,
# FILED→APPROVED. APPROVED has no forward transition.
_TRANSITIONS: List[Tuple[DevelopmentPhase, DevelopmentPhase]] = [
    (DevelopmentPhase.PRECLINICAL, DevelopmentPhase.PHASE_1),
    (DevelopmentPhase.PHASE_1, DevelopmentPhase.PHASE_2),
    (DevelopmentPhase.PHASE_2, DevelopmentPhase.PHASE_3),
    (DevelopmentPhase.PHASE_3, DevelopmentPhase.FILED),
    (DevelopmentPhase.FILED, DevelopmentPhase.APPROVED),
]


class TherapeuticArea(str, Enum):
    """Therapeutic areas with distinct clinical-risk profiles.

    Success rates vary by an order of magnitude across areas —
    hematology and vaccines clear the clinic far more often than
    oncology or CNS — so the therapeutic area is one of the single most
    important rNPV drivers.
    """
    ALL = "ALL"
    ONCOLOGY = "ONCOLOGY"
    HEMATOLOGY = "HEMATOLOGY"
    CARDIOVASCULAR = "CARDIOVASCULAR"
    CNS = "CNS"
    INFECTIOUS_DISEASE = "INFECTIOUS_DISEASE"
    VACCINES = "VACCINES"
    METABOLIC = "METABOLIC"
    IMMUNOLOGY = "IMMUNOLOGY"
    OPHTHALMOLOGY = "OPHTHALMOLOGY"
    RESPIRATORY = "RESPIRATORY"
    GENITOURINARY = "GENITOURINARY"
    GASTROENTEROLOGY = "GASTROENTEROLOGY"
    RARE_ORPHAN = "RARE_ORPHAN"


@dataclass(frozen=True)
class PhaseSuccess:
    """Phase-transition success probabilities for one therapeutic area.

    Each field is the probability of *successfully advancing out of*
    that phase, conditional on having entered it. Cumulative
    Likelihood-of-Approval (LoA) from Phase 1 is the product of the four
    clinical-stage transitions.
    """
    p1_to_p2: float
    p2_to_p3: float
    p3_to_filing: float
    filing_to_approval: float
    preclinical_to_p1: float = 0.55  # IND-enabling → first-in-human

    def loa_from_phase1(self) -> float:
        return (self.p1_to_p2 * self.p2_to_p3
                * self.p3_to_filing * self.filing_to_approval)


# Benchmark defaults. Calibrated so the cumulative Phase-1 LoA reproduces
# the published BIO 2011–2020 range by therapeutic area (ALL ≈ 7.9%;
# hematology highest ~24%; oncology/CNS lowest ~5–6%; vaccines high).
# These are STARTING POINTS an analyst overrides per asset.
PHASE_SUCCESS_TABLE: Dict[TherapeuticArea, PhaseSuccess] = {
    TherapeuticArea.ALL:            PhaseSuccess(0.52, 0.29, 0.58, 0.91),
    TherapeuticArea.ONCOLOGY:       PhaseSuccess(0.53, 0.25, 0.45, 0.85),
    TherapeuticArea.HEMATOLOGY:     PhaseSuccess(0.65, 0.49, 0.62, 0.92),
    TherapeuticArea.CARDIOVASCULAR: PhaseSuccess(0.60, 0.36, 0.62, 0.92),
    TherapeuticArea.CNS:            PhaseSuccess(0.50, 0.27, 0.50, 0.86),
    TherapeuticArea.INFECTIOUS_DISEASE: PhaseSuccess(0.63, 0.40, 0.60, 0.88),
    TherapeuticArea.VACCINES:       PhaseSuccess(0.67, 0.57, 0.85, 0.92),
    TherapeuticArea.METABOLIC:      PhaseSuccess(0.55, 0.33, 0.55, 0.90),
    TherapeuticArea.IMMUNOLOGY:     PhaseSuccess(0.62, 0.33, 0.55, 0.90),
    TherapeuticArea.OPHTHALMOLOGY:  PhaseSuccess(0.58, 0.42, 0.60, 0.90),
    TherapeuticArea.RESPIRATORY:    PhaseSuccess(0.58, 0.35, 0.58, 0.90),
    TherapeuticArea.GENITOURINARY: PhaseSuccess(0.58, 0.38, 0.60, 0.90),
    TherapeuticArea.GASTROENTEROLOGY: PhaseSuccess(0.57, 0.33, 0.55, 0.90),
    TherapeuticArea.RARE_ORPHAN:   PhaseSuccess(0.63, 0.45, 0.62, 0.92),
}


@dataclass(frozen=True)
class PhaseEconomics:
    """Out-of-pocket cost ($M) and duration (years) for one phase.

    Costs are mid-range industry out-of-pocket estimates (DiMasi 2016,
    inflated to ~2024 $). Phase 3 in particular varies enormously by
    indication (a 3,000-patient cardiovascular outcomes trial dwarfs a
    120-patient orphan trial), so these are defaults to be overridden.
    """
    cost_musd: float
    duration_years: float


# Default cost/duration per phase (2024-ish USD, out-of-pocket).
PHASE_DEFAULTS: Dict[DevelopmentPhase, PhaseEconomics] = {
    DevelopmentPhase.PRECLINICAL: PhaseEconomics(cost_musd=10.0, duration_years=1.0),
    DevelopmentPhase.PHASE_1:     PhaseEconomics(cost_musd=25.0, duration_years=1.5),
    DevelopmentPhase.PHASE_2:     PhaseEconomics(cost_musd=60.0, duration_years=2.5),
    DevelopmentPhase.PHASE_3:     PhaseEconomics(cost_musd=255.0, duration_years=3.0),
    DevelopmentPhase.FILED:       PhaseEconomics(cost_musd=20.0, duration_years=1.0),
}


def _phase_success(area: TherapeuticArea) -> PhaseSuccess:
    return PHASE_SUCCESS_TABLE.get(area, PHASE_SUCCESS_TABLE[TherapeuticArea.ALL])


def _transition_prob(ps: PhaseSuccess, frm: DevelopmentPhase) -> float:
    """Probability of advancing out of ``frm`` for this area."""
    return {
        DevelopmentPhase.PRECLINICAL: ps.preclinical_to_p1,
        DevelopmentPhase.PHASE_1: ps.p1_to_p2,
        DevelopmentPhase.PHASE_2: ps.p2_to_p3,
        DevelopmentPhase.PHASE_3: ps.p3_to_filing,
        DevelopmentPhase.FILED: ps.filing_to_approval,
    }[frm]


def cumulative_loa(
    current_phase: DevelopmentPhase,
    area: TherapeuticArea = TherapeuticArea.ALL,
    overrides: Optional[Dict[str, float]] = None,
) -> float:
    """Cumulative probability of approval from ``current_phase``.

    Product of every remaining phase-transition probability. An asset
    already ``APPROVED`` returns 1.0. ``overrides`` may supply any of
    ``preclinical_to_p1``/``p1_to_p2``/``p2_to_p3``/``p3_to_filing``/
    ``filing_to_approval`` to replace the benchmark for a specific gate.
    """
    if current_phase == DevelopmentPhase.APPROVED:
        return 1.0
    ps = _phase_success(area)
    if overrides:
        ps = PhaseSuccess(
            p1_to_p2=overrides.get("p1_to_p2", ps.p1_to_p2),
            p2_to_p3=overrides.get("p2_to_p3", ps.p2_to_p3),
            p3_to_filing=overrides.get("p3_to_filing", ps.p3_to_filing),
            filing_to_approval=overrides.get("filing_to_approval", ps.filing_to_approval),
            preclinical_to_p1=overrides.get("preclinical_to_p1", ps.preclinical_to_p1),
        )
    loa = 1.0
    for frm, _to in _TRANSITIONS:
        if frm.order >= current_phase.order:
            loa *= _transition_prob(ps, frm)
    return loa


# Alias — "likelihood of approval" and "probability of technical and
# regulatory success (PTRS)" are the same quantity in common usage.
likelihood_of_approval = cumulative_loa


# ---------------------------------------------------------------------------
# Epidemiology-based peak-sales funnel
# ---------------------------------------------------------------------------
@dataclass
class EpidemiologyFunnel:
    """Bottom-up peak-sales estimate from an epidemiology waterfall.

    The defensible alternative to pulling a peak-sales number out of the
    air. Walks population → diagnosed → treated → eligible → captured,
    then multiplies by net price and adherence. Supports both
    prevalence-based (chronic; treated stock each year) and
    incidence-based (acute/curative; new starts each year) markets.
    """
    # Epidemiology
    addressable_population: float          # prevalent or annual-incident patients in the geography
    diagnosis_rate: float = 0.70           # fraction diagnosed / aware
    treatment_rate: float = 0.60           # fraction of diagnosed who are actively treated
    eligible_fraction: float = 0.50        # fraction of treated who fit the label (line of therapy, biomarker)
    peak_market_share: float = 0.25        # peak share of the eligible, treated pool
    # Economics
    annual_net_price_usd: float = 20_000.0  # net-of-gross-to-net price per patient-year (or per course)
    adherence_persistence: float = 0.80    # compliance × persistence haircut on realized revenue
    geographies: float = 1.0               # multiplier for ex-US expansion (e.g., 1.6 for US+EU5)

    def treatable_patients(self) -> float:
        return (self.addressable_population
                * self.diagnosis_rate
                * self.treatment_rate
                * self.eligible_fraction)

    def peak_patients(self) -> float:
        return self.treatable_patients() * self.peak_market_share

    def peak_sales_musd(self) -> float:
        rev = (self.peak_patients()
               * self.annual_net_price_usd
               * self.adherence_persistence
               * self.geographies)
        return rev / 1e6

    def to_dict(self) -> Dict[str, Any]:
        d = {k: round(v, 4) for k, v in asdict(self).items()}
        d["treatable_patients"] = round(self.treatable_patients(), 0)
        d["peak_patients"] = round(self.peak_patients(), 0)
        d["peak_sales_musd"] = round(self.peak_sales_musd(), 1)
        return d


def peak_sales_from_epidemiology(funnel: EpidemiologyFunnel) -> float:
    """Convenience: peak annual net sales ($M) from a funnel."""
    return funnel.peak_sales_musd()


# ---------------------------------------------------------------------------
# Licensing / royalty deal economics
# ---------------------------------------------------------------------------
@dataclass
class RoyaltyTier:
    """A single net-sales royalty tier: pay ``rate`` on sales up to
    ``up_to_musd`` (use ``float('inf')`` for the top tier)."""
    up_to_musd: float
    rate: float


@dataclass
class LicensingDeal:
    """Out-/in-licensing structure overlaid on an asset's rNPV.

    Milestones are *risked* by the probability of reaching the relevant
    gate (development/regulatory milestones) or by LoA (sales
    milestones). Royalties are paid on net sales, which are themselves
    LoA-risked in the rNPV. Lets the engine split an asset's value
    between licensor (originator) and licensee (acquirer/partner).
    """
    upfront_musd: float = 0.0
    # Development + regulatory milestones keyed by the phase whose
    # *successful completion* triggers the payment.
    dev_milestones_musd: Dict[DevelopmentPhase, float] = field(default_factory=dict)
    approval_milestone_musd: float = 0.0
    # Sales milestones: (annual-net-sales threshold $M, one-time payment $M).
    sales_milestones_musd: List[Tuple[float, float]] = field(default_factory=list)
    royalty_tiers: List[RoyaltyTier] = field(default_factory=list)

    def royalty_on(self, annual_net_sales_musd: float) -> float:
        """Blended tiered royalty owed on a year of net sales ($M)."""
        if not self.royalty_tiers:
            return 0.0
        prev_cap = 0.0
        owed = 0.0
        for tier in sorted(self.royalty_tiers, key=lambda t: t.up_to_musd):
            band = max(0.0, min(annual_net_sales_musd, tier.up_to_musd) - prev_cap)
            owed += band * tier.rate
            prev_cap = tier.up_to_musd
            if annual_net_sales_musd <= tier.up_to_musd:
                break
        return owed


# ---------------------------------------------------------------------------
# Core rNPV asset model
# ---------------------------------------------------------------------------
@dataclass
class AssetRNPVConfig:
    """Every input to the risk-adjusted NPV of a single asset — nothing
    hidden, matching the ``DCFAssumptions`` / ``LBOAssumptions`` idiom."""
    name: str = "Asset"
    area: TherapeuticArea = TherapeuticArea.ONCOLOGY
    current_phase: DevelopmentPhase = DevelopmentPhase.PHASE_2

    # Commercial
    peak_sales_musd: float = 1_000.0
    years_to_peak: int = 5                 # launch ramp length to reach peak
    years_at_peak: int = 3                 # plateau before loss of exclusivity
    exclusivity_years: int = 12            # effective patent/exclusivity from launch
    post_loe_erosion: float = 0.55         # annual sales decline once exclusivity lapses
    launch_ramp: Optional[List[float]] = None  # explicit ramp fractions; else S-curve

    # P&L (as fraction of net sales unless noted)
    gross_margin: float = 0.88             # 1 − COGS/sales; biologics ~0.80, small-mol ~0.90
    sgna_pct_peak: float = 0.30            # commercial SG&A at peak (higher during launch)
    other_opex_pct: float = 0.05
    tax_rate: float = 0.21

    # Development
    phase_costs: Optional[Dict[DevelopmentPhase, PhaseEconomics]] = None
    prob_overrides: Optional[Dict[str, float]] = None

    # Discounting
    discount_rate: float = 0.12            # biotech WACC; higher for earlier assets
    risk_adjust_costs: bool = True         # weight dev spend by prob of reaching that phase

    # Optional deal overlay (perspective-dependent value split)
    deal: Optional[LicensingDeal] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "area": self.area.value,
            "current_phase": self.current_phase.value,
            "peak_sales_musd": self.peak_sales_musd,
            "years_to_peak": self.years_to_peak,
            "years_at_peak": self.years_at_peak,
            "exclusivity_years": self.exclusivity_years,
            "post_loe_erosion": self.post_loe_erosion,
            "gross_margin": self.gross_margin,
            "sgna_pct_peak": self.sgna_pct_peak,
            "other_opex_pct": self.other_opex_pct,
            "tax_rate": self.tax_rate,
            "discount_rate": self.discount_rate,
            "risk_adjust_costs": self.risk_adjust_costs,
        }
        return d


@dataclass
class RNPVYear:
    """One projection year of the asset."""
    year: int
    phase: str
    prob_reached: float        # cumulative probability the asset is 'live' this year
    net_sales: float           # unrisked (success-case) net sales
    dev_cost: float            # unrisked dev cost this year
    operating_cf: float        # unrisked operating cash flow from commercial
    royalty_cf: float          # unrisked royalty paid (−) or received (+) — perspective set by caller
    risked_cf: float           # probability-weighted, pre-discount total cash flow
    discount_factor: float
    pv: float                  # discounted risked cash flow

    def to_dict(self) -> Dict[str, Any]:
        return {k: (round(v, 2) if isinstance(v, float) else v)
                for k, v in asdict(self).items()}


@dataclass
class RNPVResult:
    """Full rNPV output for one asset."""
    config: AssetRNPVConfig
    loa: float                          # cumulative likelihood of approval from current phase
    peak_sales_musd: float
    rnpv_musd: float                    # risk-adjusted NPV (the headline)
    npv_success_musd: float             # NPV assuming approval (unrisked upside case)
    total_risked_dev_cost_musd: float
    pv_revenue_musd: float
    projections: List[RNPVYear]
    provenance: Dict[str, str]
    # Deal-split view (populated only when config.deal is set)
    licensor_rnpv_musd: Optional[float] = None
    licensee_rnpv_musd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "loa": round(self.loa, 4),
            "peak_sales_musd": round(self.peak_sales_musd, 1),
            "rnpv_musd": round(self.rnpv_musd, 1),
            "npv_success_musd": round(self.npv_success_musd, 1),
            "total_risked_dev_cost_musd": round(self.total_risked_dev_cost_musd, 1),
            "pv_revenue_musd": round(self.pv_revenue_musd, 1),
            "licensor_rnpv_musd": (round(self.licensor_rnpv_musd, 1)
                                   if self.licensor_rnpv_musd is not None else None),
            "licensee_rnpv_musd": (round(self.licensee_rnpv_musd, 1)
                                   if self.licensee_rnpv_musd is not None else None),
            "projections": [y.to_dict() for y in self.projections],
            "provenance": self.provenance,
        }


def _sigmoid_ramp(years_to_peak: int) -> List[float]:
    """S-curve launch ramp fractions (of peak) over ``years_to_peak``.

    Real product launches are sigmoidal — slow uptake, steep middle,
    plateau approach — not linear. Final year hits ~1.0 (peak).
    """
    if years_to_peak <= 1:
        return [1.0]
    fracs = []
    for i in range(1, years_to_peak + 1):
        # logistic centred at the midpoint of the ramp
        x = (i - (years_to_peak + 1) / 2.0) / max(1.0, years_to_peak / 5.0)
        fracs.append(1.0 / (1.0 + math.exp(-x)))
    # normalise so the final ramp year equals 1.0 (peak)
    top = fracs[-1]
    return [round(f / top, 4) for f in fracs]


def _sales_curve(cfg: AssetRNPVConfig) -> List[float]:
    """Full success-case net-sales curve (list of annual $M), from launch
    year 1 through the post-LoE erosion tail down to a de-minimis level."""
    ramp = cfg.launch_ramp or _sigmoid_ramp(cfg.years_to_peak)
    curve = [cfg.peak_sales_musd * f for f in ramp]
    # plateau at peak
    curve += [cfg.peak_sales_musd] * max(0, cfg.years_at_peak)
    # patent cliff: erode from the year exclusivity lapses
    launched_years = len(curve)
    remaining_excl = max(0, cfg.exclusivity_years - launched_years)
    curve += [cfg.peak_sales_musd] * remaining_excl
    # erosion tail — decay until below 3% of peak
    tail = cfg.peak_sales_musd * (1 - cfg.post_loe_erosion)
    while tail > cfg.peak_sales_musd * 0.03 and len(curve) < 40:
        curve.append(tail)
        tail *= (1 - cfg.post_loe_erosion)
    return curve


def value_asset_rnpv(cfg: AssetRNPVConfig) -> RNPVResult:
    """Compute the risk-adjusted NPV of a single asset.

    Timeline: t=0 is today. Remaining development phases are scheduled
    sequentially from ``current_phase``; commercial sales begin the year
    after approval. Development cash flows are risked by the probability
    of *reaching* that phase; commercial cash flows are risked by the
    full cumulative LoA — the textbook rNPV convention.
    """
    provenance: Dict[str, str] = {}
    ps = _phase_success(cfg.area)
    if cfg.prob_overrides:
        provenance["phase_success"] = "analyst_input"
    else:
        provenance["phase_success"] = "benchmark_default"

    phase_costs = cfg.phase_costs or PHASE_DEFAULTS
    if cfg.phase_costs is None:
        provenance["phase_costs"] = "benchmark_default"
    else:
        provenance["phase_costs"] = "analyst_input"

    # --- schedule remaining development phases ---------------------------
    # Each remaining phase contributes cost over its duration and carries a
    # "probability of reaching" = cumulative success up to its start.
    remaining = [p for p in [DevelopmentPhase.PRECLINICAL, DevelopmentPhase.PHASE_1,
                             DevelopmentPhase.PHASE_2, DevelopmentPhase.PHASE_3,
                             DevelopmentPhase.FILED]
                 if p.order >= cfg.current_phase.order]

    # Build a year-indexed dev-cost + prob-reached schedule.
    dev_by_year: Dict[int, float] = {}
    prob_by_year: Dict[int, float] = {}
    t = 0.0
    prob_reached_start = 1.0  # probability of being in the current phase now
    for p in remaining:
        econ = phase_costs.get(p)
        if econ is None:
            continue
        dur = max(1, int(round(econ.duration_years)))
        annual_cost = econ.cost_musd / dur
        for _ in range(dur):
            yr = int(math.floor(t)) + 1
            dev_by_year[yr] = dev_by_year.get(yr, 0.0) + annual_cost
            # the probability the asset is still alive spending this money
            prob_by_year[yr] = max(prob_by_year.get(yr, 0.0), prob_reached_start)
            t += 1.0
        # advance probability past this phase's gate
        prob_reached_start *= _transition_prob(ps, p) if not cfg.prob_overrides else \
            _transition_prob(_override_ps(ps, cfg.prob_overrides), p)

    dev_years = int(math.ceil(t))            # years until approval
    loa = cumulative_loa(cfg.current_phase, cfg.area, cfg.prob_overrides)

    # --- commercial sales curve -----------------------------------------
    sales = _sales_curve(cfg)                # success-case net sales, launch year = 1

    # --- assemble year-by-year projection -------------------------------
    projections: List[RNPVYear] = []
    total_years = dev_years + len(sales)
    total_risked_dev = 0.0
    pv_revenue = 0.0
    rnpv = 0.0

    deal = cfg.deal
    for yr in range(1, total_years + 1):
        disc = 1.0 / ((1.0 + cfg.discount_rate) ** yr)
        dev_cost = dev_by_year.get(yr, 0.0)
        prob_dev = prob_by_year.get(yr, loa)  # prob of spending this dev $
        net_sales = 0.0
        op_cf = 0.0
        royalty_cf = 0.0
        phase_label = _phase_active_in_year(remaining, phase_costs, yr, dev_years)

        commercial_idx = yr - dev_years - 1  # 0-based launch index
        if 0 <= commercial_idx < len(sales):
            net_sales = sales[commercial_idx]
            # simple asset-level operating margin: gross − SG&A − other, taxed
            gross = net_sales * cfg.gross_margin
            sgna = net_sales * cfg.sgna_pct_peak
            other = net_sales * cfg.other_opex_pct
            ebit = gross - sgna - other
            op_cf = ebit * (1 - cfg.tax_rate)
            if deal and deal.royalty_tiers:
                royalty_cf = deal.royalty_on(net_sales)  # magnitude; sign applied per perspective
            phase_label = DevelopmentPhase.APPROVED.value

        # Risk-adjust: dev spend by prob of reaching; commercial by LoA.
        risked = 0.0
        if dev_cost:
            weight = prob_dev if cfg.risk_adjust_costs else 1.0
            risked -= dev_cost * weight
            total_risked_dev += dev_cost * weight
        if op_cf:
            risked += op_cf * loa
            pv_revenue += net_sales * loa * disc

        pv = risked * disc
        rnpv += pv
        projections.append(RNPVYear(
            year=yr, phase=phase_label,
            prob_reached=round(prob_dev if dev_cost else (loa if net_sales else 0.0), 4),
            net_sales=net_sales, dev_cost=dev_cost,
            operating_cf=op_cf, royalty_cf=royalty_cf,
            risked_cf=risked, discount_factor=disc, pv=pv,
        ))

    # --- success-case (unrisked) NPV for the upside view ----------------
    npv_success = _npv_success_case(cfg, sales, dev_by_year, dev_years)

    result = RNPVResult(
        config=cfg, loa=loa, peak_sales_musd=cfg.peak_sales_musd,
        rnpv_musd=rnpv, npv_success_musd=npv_success,
        total_risked_dev_cost_musd=total_risked_dev,
        pv_revenue_musd=pv_revenue, projections=projections,
        provenance=provenance,
    )

    if deal is not None:
        lic_or, lic_ee = _split_deal_value(cfg, sales, dev_by_year, dev_years,
                                           prob_by_year, loa, ps)
        result.licensor_rnpv_musd = lic_or
        result.licensee_rnpv_musd = lic_ee
        provenance["deal_split"] = "analyst_input"

    return result


def _override_ps(ps: PhaseSuccess, ov: Dict[str, float]) -> PhaseSuccess:
    return PhaseSuccess(
        p1_to_p2=ov.get("p1_to_p2", ps.p1_to_p2),
        p2_to_p3=ov.get("p2_to_p3", ps.p2_to_p3),
        p3_to_filing=ov.get("p3_to_filing", ps.p3_to_filing),
        filing_to_approval=ov.get("filing_to_approval", ps.filing_to_approval),
        preclinical_to_p1=ov.get("preclinical_to_p1", ps.preclinical_to_p1),
    )


def _phase_active_in_year(remaining, phase_costs, yr, dev_years) -> str:
    """Label which development phase is running in a given pre-launch year."""
    if yr > dev_years:
        return DevelopmentPhase.APPROVED.value
    t = 0
    for p in remaining:
        econ = phase_costs.get(p)
        if econ is None:
            continue
        dur = max(1, int(round(econ.duration_years)))
        if t < yr <= t + dur:
            return p.value
        t += dur
    return DevelopmentPhase.FILED.value


def _npv_success_case(cfg, sales, dev_by_year, dev_years) -> float:
    """Unrisked NPV assuming the asset is approved (upside scenario)."""
    npv = 0.0
    for yr, cost in dev_by_year.items():
        npv -= cost / ((1 + cfg.discount_rate) ** yr)
    for idx, ns in enumerate(sales):
        yr = dev_years + idx + 1
        ebit = ns * (cfg.gross_margin - cfg.sgna_pct_peak - cfg.other_opex_pct)
        op_cf = ebit * (1 - cfg.tax_rate)
        npv += op_cf / ((1 + cfg.discount_rate) ** yr)
    return npv


def _split_deal_value(cfg, sales, dev_by_year, dev_years, prob_by_year, loa, ps):
    """Split rNPV between licensor (originator) and licensee (partner).

    Licensor gets upfront (unrisked, t=0), risked dev/approval/sales
    milestones, and risked royalties. Licensee bears remaining dev cost
    and keeps commercial cash flow net of royalties + milestones paid.
    """
    deal = cfg.deal
    r = cfg.discount_rate
    lic_or = deal.upfront_musd  # paid at close, t≈0

    # development + approval milestones, risked by prob of reaching the gate
    # timing: assume milestone lands at the end of the phase that triggers it.
    phase_end_year: Dict[DevelopmentPhase, int] = {}
    t = 0
    for p in [DevelopmentPhase.PRECLINICAL, DevelopmentPhase.PHASE_1,
              DevelopmentPhase.PHASE_2, DevelopmentPhase.PHASE_3,
              DevelopmentPhase.FILED]:
        if p.order < cfg.current_phase.order:
            continue
        econ = (cfg.phase_costs or PHASE_DEFAULTS).get(p)
        if econ is None:
            continue
        t += max(1, int(round(econ.duration_years)))
        phase_end_year[p] = t

    prob_reached = 1.0
    for p in [DevelopmentPhase.PRECLINICAL, DevelopmentPhase.PHASE_1,
              DevelopmentPhase.PHASE_2, DevelopmentPhase.PHASE_3,
              DevelopmentPhase.FILED]:
        if p.order < cfg.current_phase.order:
            continue
        prob_reached *= _transition_prob(ps, p)
        ms = deal.dev_milestones_musd.get(p, 0.0)
        if ms and p in phase_end_year:
            yr = phase_end_year[p]
            lic_or += ms * prob_reached / ((1 + r) ** yr)
    if deal.approval_milestone_musd:
        yr = phase_end_year.get(DevelopmentPhase.FILED, dev_years)
        lic_or += deal.approval_milestone_musd * loa / ((1 + r) ** yr)

    # royalties + sales milestones, risked by LoA
    cum_sales = 0.0
    hit_milestones = set()
    for idx, ns in enumerate(sales):
        yr = dev_years + idx + 1
        disc = 1.0 / ((1 + r) ** yr)
        roy = deal.royalty_on(ns)
        lic_or += roy * loa * disc
        cum_sales += ns
        for j, (thresh, pay) in enumerate(deal.sales_milestones_musd):
            if j not in hit_milestones and ns >= thresh:
                hit_milestones.add(j)
                lic_or += pay * loa * disc

    # licensee = total asset commercial value − what it pays licensor − dev it funds
    total_asset = value_asset_rnpv(_strip_deal(cfg)).rnpv_musd
    lic_ee = total_asset - lic_or + deal.upfront_musd * 0  # upfront already a transfer
    # licensee also does not bear pre-deal sunk cost; approximate net as residual
    lic_ee = total_asset - lic_or
    return lic_or, lic_ee


def _strip_deal(cfg: AssetRNPVConfig) -> AssetRNPVConfig:
    """Copy of the config with the deal removed (for standalone value)."""
    import copy
    c = copy.copy(cfg)
    c.deal = None
    return c


def build_rnpv(cfg: Optional[AssetRNPVConfig] = None, **overrides: Any) -> RNPVResult:
    """Build an rNPV result, ``build_dcf``/``build_lbo``-style.

    Accepts an ``AssetRNPVConfig`` and/or keyword overrides of any config
    field. ``area``/``current_phase`` accept enums or their string names.
    """
    c = cfg or AssetRNPVConfig()
    for k, v in overrides.items():
        if not hasattr(c, k):
            continue
        if k == "area" and isinstance(v, str):
            v = TherapeuticArea(v)
        if k == "current_phase" and isinstance(v, str):
            v = DevelopmentPhase(v)
        setattr(c, k, v)
    return value_asset_rnpv(c)


def value_licensing_deal(cfg: AssetRNPVConfig, deal: LicensingDeal) -> RNPVResult:
    """Value an asset under a licensing deal, returning the split view."""
    cfg.deal = deal
    return value_asset_rnpv(cfg)


# ---------------------------------------------------------------------------
# Portfolio / company-level
# ---------------------------------------------------------------------------
@dataclass
class PipelineResult:
    """Sum-of-the-parts valuation across a pipeline of assets."""
    assets: List[Dict[str, Any]]
    gross_pipeline_rnpv_musd: float
    platform_gna_pv_musd: float
    net_cash_musd: float
    equity_value_musd: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assets": self.assets,
            "gross_pipeline_rnpv_musd": round(self.gross_pipeline_rnpv_musd, 1),
            "platform_gna_pv_musd": round(self.platform_gna_pv_musd, 1),
            "net_cash_musd": round(self.net_cash_musd, 1),
            "equity_value_musd": round(self.equity_value_musd, 1),
        }


def value_pipeline(
    configs: List[AssetRNPVConfig],
    annual_platform_gna_musd: float = 0.0,
    gna_years: int = 10,
    discount_rate: float = 0.12,
    net_cash_musd: float = 0.0,
) -> PipelineResult:
    """Sum-of-the-parts equity value for a multi-asset company.

    ``equity = Σ asset rNPV − PV(unallocated platform G&A) + net cash``.
    Platform G&A captures the corporate overhead not charged to any
    single program (executive team, facilities, shared research).
    """
    rows: List[Dict[str, Any]] = []
    gross = 0.0
    for cfg in configs:
        res = value_asset_rnpv(cfg)
        gross += res.rnpv_musd
        rows.append({
            "name": cfg.name,
            "area": cfg.area.value,
            "phase": cfg.current_phase.value,
            "loa": round(res.loa, 4),
            "peak_sales_musd": round(res.peak_sales_musd, 1),
            "rnpv_musd": round(res.rnpv_musd, 1),
        })
    gna_pv = sum(annual_platform_gna_musd / ((1 + discount_rate) ** y)
                 for y in range(1, gna_years + 1))
    equity = gross - gna_pv + net_cash_musd
    return PipelineResult(
        assets=rows, gross_pipeline_rnpv_musd=gross,
        platform_gna_pv_musd=gna_pv, net_cash_musd=net_cash_musd,
        equity_value_musd=equity,
    )


@dataclass
class RunwayResult:
    cash_musd: float
    quarterly_burn_musd: float
    runway_quarters: float
    runway_months: float
    cash_out_date_quarters: float
    financing_need_musd: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) for k, v in asdict(self).items()}


def runway_analysis(
    cash_musd: float,
    quarterly_burn_musd: float,
    target_runway_months: float = 24.0,
) -> RunwayResult:
    """Cash runway — the first question in any pre-profit biotech deal.

    Returns quarters/months of runway and the raise needed to reach a
    target runway (a proxy for the next value-inflection milestone).
    """
    qb = max(quarterly_burn_musd, 1e-9)
    quarters = cash_musd / qb
    months = quarters * 3.0
    target_cash = (target_runway_months / 3.0) * qb
    need = max(0.0, target_cash - cash_musd)
    return RunwayResult(
        cash_musd=cash_musd, quarterly_burn_musd=quarterly_burn_musd,
        runway_quarters=quarters, runway_months=months,
        cash_out_date_quarters=quarters, financing_need_musd=need,
    )


# ---------------------------------------------------------------------------
# Adjacent life-sciences subsectors (revenue-generating businesses)
# ---------------------------------------------------------------------------
@dataclass
class CDMOResult:
    revenue_musd: float
    utilization: float
    ebitda_musd: float
    ebitda_margin: float
    book_to_bill: float
    backlog_coverage_years: float
    revenue_per_suite_musd: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 3) for k, v in asdict(self).items()}


def cdmo_capacity_model(
    suites: int,
    max_revenue_per_suite_musd: float,
    utilization: float,
    ebitda_margin_at_full: float = 0.32,
    fixed_cost_musd: float = 0.0,
    backlog_musd: float = 0.0,
    new_orders_musd: float = 0.0,
) -> CDMOResult:
    """Contract Development & Manufacturing (CDMO) / CRO capacity model.

    CDMOs/CROs are capacity businesses, not IP businesses — value tracks
    suite utilization, operating leverage on fixed cost, and backlog
    coverage. Margin scales with utilization (fixed cost is absorbed
    faster when suites are full).
    """
    capacity = suites * max_revenue_per_suite_musd
    revenue = capacity * min(max(utilization, 0.0), 1.0)
    # operating leverage: margin ramps from a floor toward the full-util margin
    margin = ebitda_margin_at_full * (0.4 + 0.6 * utilization)
    ebitda = revenue * margin - fixed_cost_musd
    b2b = (new_orders_musd / revenue) if revenue else 0.0
    coverage = (backlog_musd / revenue) if revenue else 0.0
    return CDMOResult(
        revenue_musd=revenue, utilization=utilization,
        ebitda_musd=ebitda, ebitda_margin=(ebitda / revenue if revenue else 0.0),
        book_to_bill=b2b, backlog_coverage_years=coverage,
        revenue_per_suite_musd=(revenue / suites if suites else 0.0),
    )


@dataclass
class DiagnosticsResult:
    annual_revenue_musd: float
    instrument_revenue_musd: float
    consumable_revenue_musd: float
    consumable_share: float
    gross_profit_musd: float
    gross_margin: float
    revenue_per_instrument_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 3) for k, v in asdict(self).items()}


def diagnostics_unit_economics(
    installed_base: int,
    instruments_sold_annually: int,
    instrument_asp_usd: float,
    tests_per_instrument_year: int,
    price_per_test_usd: float,
    instrument_gross_margin: float = 0.35,
    consumable_gross_margin: float = 0.70,
) -> DiagnosticsResult:
    """Razor / razor-blade diagnostics & tools unit economics.

    Instruments are placed at low (even negative) margin to drive a
    recurring, high-margin consumable/reagent annuity from the installed
    base — the value is in the razor-blade stream, so the model surfaces
    consumable share and blended gross margin explicitly.
    """
    instr_rev = instruments_sold_annually * instrument_asp_usd / 1e6
    cons_rev = installed_base * tests_per_instrument_year * price_per_test_usd / 1e6
    total = instr_rev + cons_rev
    gp = (instr_rev * instrument_gross_margin
          + cons_rev * consumable_gross_margin)
    return DiagnosticsResult(
        annual_revenue_musd=total,
        instrument_revenue_musd=instr_rev,
        consumable_revenue_musd=cons_rev,
        consumable_share=(cons_rev / total if total else 0.0),
        gross_profit_musd=gp,
        gross_margin=(gp / total if total else 0.0),
        revenue_per_instrument_usd=(
            total * 1e6 / installed_base if installed_base else 0.0),
    )


# ---------------------------------------------------------------------------
# Loop D — Dynamic commercial model: competition, 2-way grids, EV blend
# ---------------------------------------------------------------------------
# Order-of-entry share multipliers. Later entrants capture progressively
# less of a class's value absent differentiation — an empirical
# regularity in pharma launch analytics (first-in-class anchors share;
# each subsequent entrant erodes into a crowded pool).
_ORDER_OF_ENTRY_SHARE: Dict[int, float] = {
    1: 1.00,   # first-in-class / first-to-market
    2: 0.65,
    3: 0.45,
    4: 0.32,
    5: 0.24,
}


def competition_adjusted_peak_sales(
    class_peak_sales_musd: float,
    order_of_entry: int,
    n_expected_competitors: int,
    differentiation: float = 1.0,
    genericization_haircut: float = 0.0,
) -> float:
    """Adjust a *class-level* peak-sales TAM down to this asset's share.

    Combines three commercial realities into one endogenous peak:

      * **Order of entry** — first movers anchor share; late entrants
        split the residual (``_ORDER_OF_ENTRY_SHARE``).
      * **Crowding** — more competitors than your entry rank implies
        thins the pool further (``1/√n`` style dilution beyond entry).
      * **Differentiation** — a >1.0 multiplier for a genuinely better
        profile (efficacy, dosing, safety) that defends share; <1.0 for
        a me-too. ``genericization_haircut`` knocks the class value down
        if cheap generics/biosimilars already compress the category.

    Returns this asset's defensible peak net sales ($M), suitable to
    feed straight into ``AssetRNPVConfig.peak_sales_musd``.
    """
    def _weight(rank: int) -> float:
        return _ORDER_OF_ENTRY_SHARE.get(
            rank, _ORDER_OF_ENTRY_SHARE[5] * (5.0 / max(5, rank)))

    order_of_entry = max(1, order_of_entry)
    n = max(n_expected_competitors, order_of_entry)
    # Split the class TAM among the n entrants by order-of-entry weight,
    # so shares are internally consistent (sum to the class) and later
    # entrants strictly earn less than earlier ones.
    total_weight = sum(_weight(rank) for rank in range(1, n + 1))
    raw_share = _weight(order_of_entry) / total_weight if total_weight else 0.0
    # Differentiation lets this asset over/under-index its positional share
    # (capped at full class capture).
    share = min(1.0, raw_share * max(0.1, differentiation))
    peak = class_peak_sales_musd * share * (1 - genericization_haircut)
    return max(0.0, peak)


@dataclass
class SensitivityGrid:
    """rNPV surface over two drivers — the data behind a heatmap."""
    driver_x: str
    driver_y: str
    x_values: List[float]
    y_values: List[float]
    grid: List[List[float]]   # grid[j][i] = rNPV at (x_values[i], y_values[j])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver_x": self.driver_x, "driver_y": self.driver_y,
            "x_values": [round(v, 4) for v in self.x_values],
            "y_values": [round(v, 4) for v in self.y_values],
            "grid": [[round(c, 2) for c in row] for row in self.grid],
        }


def sensitivity_grid(
    cfg: AssetRNPVConfig,
    driver_x: str, x_values: List[float],
    driver_y: str, y_values: List[float],
) -> SensitivityGrid:
    """Two-way rNPV sensitivity surface (e.g. peak sales × discount rate)."""
    grid: List[List[float]] = []
    for yv in y_values:
        row: List[float] = []
        cy = _apply_driver(cfg, driver_y, yv)
        for xv in x_values:
            cxy = _apply_driver(cy, driver_x, xv)
            row.append(value_asset_rnpv(cxy).rnpv_musd)
        grid.append(row)
    return SensitivityGrid(driver_x=driver_x, driver_y=driver_y,
                           x_values=x_values, y_values=y_values, grid=grid)


@dataclass
class ExpectedValueResult:
    expected_rnpv_musd: float
    scenarios: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_rnpv_musd": round(self.expected_rnpv_musd, 2),
            "scenarios": self.scenarios,
        }


def expected_value_blend(
    base: AssetRNPVConfig,
    weighted_scenarios: Dict[str, Tuple[float, Dict[str, Any]]],
) -> ExpectedValueResult:
    """Probability-weighted expected rNPV across named scenarios.

    ``weighted_scenarios`` maps a name to ``(probability, overrides)``.
    Collapses a bear/base/bull (or richer) scenario set into a single
    expected value while retaining the per-scenario rNPV for the audit
    trail. Probabilities are renormalised if they do not sum to 1.
    """
    import copy
    prob_keys = {"preclinical_to_p1", "p1_to_p2", "p2_to_p3",
                 "p3_to_filing", "filing_to_approval"}
    total_w = sum(w for (w, _ov) in weighted_scenarios.values()) or 1.0
    ev = 0.0
    rows: List[Dict[str, Any]] = []
    for name, (w, ov) in weighted_scenarios.items():
        c = copy.deepcopy(base)
        c.name = name
        po = dict(c.prob_overrides or {})
        for k, v in ov.items():
            if k in prob_keys:
                po[k] = v
            elif k == "area" and isinstance(v, str):
                c.area = TherapeuticArea(v)
            elif k == "current_phase" and isinstance(v, str):
                c.current_phase = DevelopmentPhase(v)
            elif hasattr(c, k):
                setattr(c, k, v)
        if po:
            c.prob_overrides = po
        rnpv = value_asset_rnpv(c).rnpv_musd
        wn = w / total_w
        ev += wn * rnpv
        rows.append({"scenario": name, "probability": round(wn, 4),
                     "rnpv_musd": round(rnpv, 2)})
    return ExpectedValueResult(expected_rnpv_musd=ev, scenarios=rows)


# ---------------------------------------------------------------------------
# Loop C — Real-options value (staged abandonment decision tree)
# ---------------------------------------------------------------------------
@dataclass
class CommercialScenario:
    """A discrete commercial outcome revealed by a clinical readout."""
    name: str
    probability: float
    peak_sales_musd: float


@dataclass
class RealOptionsResult:
    """Value of the option to abandon after an informative readout."""
    naive_rnpv_musd: float          # value if you always continue (≈ point rNPV)
    optimal_rnpv_musd: float        # value under optimal go/no-go at the reveal gate
    option_premium_musd: float      # optimal − naive ≥ 0
    reveal_after: str               # phase whose readout resolves the scenarios
    continue_scenarios: List[str]   # scenarios where continuing is optimal
    abandon_scenarios: List[str]    # scenarios where killing the program is optimal
    scenario_detail: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "naive_rnpv_musd": round(self.naive_rnpv_musd, 2),
            "optimal_rnpv_musd": round(self.optimal_rnpv_musd, 2),
            "option_premium_musd": round(self.option_premium_musd, 2),
            "reveal_after": self.reveal_after,
            "continue_scenarios": self.continue_scenarios,
            "abandon_scenarios": self.abandon_scenarios,
            "scenario_detail": self.scenario_detail,
        }


def real_options_value(
    cfg: AssetRNPVConfig,
    scenarios: List[CommercialScenario],
    reveal_after: DevelopmentPhase = DevelopmentPhase.PHASE_2,
) -> RealOptionsResult:
    """Value the program with an explicit abandonment option.

    A point-estimate rNPV silently assumes management commits the (very
    expensive) later-phase spend no matter what the earlier readout
    shows. Reality: a weak Phase-2 signal that implies a small
    commercial opportunity gets killed before the Phase-3 checkbook
    opens. This backward-induction tree resolves the commercial
    ``scenarios`` once ``reveal_after`` completes, then continues only
    where the forward continuation value is positive — flooring the
    downside at zero. The **option premium is the value of that
    walk-away right**, which naive rNPV throws away.
    """
    if reveal_after.order < cfg.current_phase.order:
        reveal_after = cfg.current_phase
    total_prob = sum(s.probability for s in scenarios)
    if total_prob <= 0:
        raise ValueError("scenario probabilities must sum to a positive number")

    ps = _phase_success(cfg.area)
    if cfg.prob_overrides:
        ps = _override_ps(ps, cfg.prob_overrides)
    r = cfg.discount_rate

    # Phase immediately AFTER the reveal gate (where the go/no-go bites).
    after_order = reveal_after.order + 1
    order_to_phase = {p.order: p for p in DevelopmentPhase}
    phase_after = order_to_phase.get(after_order)

    # Calendar time + arrival probability at the moment the reveal gate clears.
    dev_by_year, dev_years, gates = _dev_schedule(cfg)
    t_reveal = 0
    prob_reach = 1.0
    for (p, prob, end_yr, _cost) in gates:
        t_reveal = end_yr
        prob_reach *= prob
        if p == reveal_after:
            break

    # PV of risked development spend from now up to and including the reveal gate.
    pre_pv = 0.0
    # probability of *reaching* each pre-reveal phase (before its own gate)
    prob_at_phase: Dict[DevelopmentPhase, float] = {}
    rp = 1.0
    for (p, prob, _end, _c) in gates:
        prob_at_phase[p] = rp
        rp *= prob
    # accumulate risked, discounted spend through the reveal gate
    for (p, prob, end, _c) in gates:
        prev = 0
        for (pp, _pr, e, _cc) in gates:
            if pp == p:
                break
            prev = e
        for yr in range(prev + 1, end + 1):
            wt = prob_at_phase.get(p, 1.0) if cfg.risk_adjust_costs else 1.0
            pre_pv += dev_by_year.get(yr, 0.0) * wt / ((1 + r) ** yr)
        if p == reveal_after:
            break

    naive_node = 0.0
    optimal_node = 0.0
    detail: List[Dict[str, Any]] = []
    cont, aband = [], []
    for s in scenarios:
        w = s.probability / total_prob
        if phase_after is None or phase_after == DevelopmentPhase.APPROVED:
            # reveal at/after filing — continuation is just the commercial stream
            cont_cfg = _clone_cfg(cfg, peak_sales_musd=s.peak_sales_musd)
            cont_cfg.current_phase = DevelopmentPhase.FILED
        else:
            cont_cfg = _clone_cfg(cfg, peak_sales_musd=s.peak_sales_musd)
            cont_cfg.current_phase = phase_after
        cont_val = value_asset_rnpv(cont_cfg).rnpv_musd  # as-of reveal time
        go = cont_val > 0
        (cont if go else aband).append(s.name)
        naive_node += w * cont_val
        optimal_node += w * max(0.0, cont_val)
        detail.append({
            "scenario": s.name, "probability": round(w, 4),
            "peak_sales_musd": round(s.peak_sales_musd, 1),
            "continuation_value_musd": round(cont_val, 2),
            "decision": "continue" if go else "abandon",
        })

    disc_reveal = 1.0 / ((1 + r) ** t_reveal)
    naive = -pre_pv + prob_reach * disc_reveal * naive_node
    optimal = -pre_pv + prob_reach * disc_reveal * optimal_node
    return RealOptionsResult(
        naive_rnpv_musd=naive, optimal_rnpv_musd=optimal,
        option_premium_musd=optimal - naive,
        reveal_after=reveal_after.value,
        continue_scenarios=cont, abandon_scenarios=aband,
        scenario_detail=detail,
    )


# ---------------------------------------------------------------------------
# Side-by-side comparison engine
# ---------------------------------------------------------------------------
# The rows every asset/scenario is aligned on. Each entry:
#   (row label, attribute path into RNPVResult, format spec)
_COMPARE_ROWS: List[Tuple[str, str, str]] = [
    ("Therapeutic area", "config.area", "enum"),
    ("Current phase", "config.current_phase", "enum"),
    ("Likelihood of approval (LoA)", "loa", "pct"),
    ("Peak sales ($M)", "peak_sales_musd", "musd"),
    ("PV of risked revenue ($M)", "pv_revenue_musd", "musd"),
    ("Risked dev cost ($M)", "total_risked_dev_cost_musd", "musd"),
    ("rNPV — risk-adjusted ($M)", "rnpv_musd", "musd"),
    ("NPV — approval case ($M)", "npv_success_musd", "musd"),
    ("Discount rate", "config.discount_rate", "pct"),
]


def _resolve(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        cur = getattr(cur, part)
    if isinstance(cur, Enum):
        return cur.value
    return cur


def _fmt(val: Any, spec: str) -> str:
    if spec == "pct":
        return f"{val * 100:.1f}%"
    if spec == "musd":
        return f"${val:,.0f}M"
    if spec == "enum":
        return str(val).replace("_", " ").title()
    return str(val)


@dataclass
class ComparisonRow:
    label: str
    values: List[Any]              # raw value per column
    display: List[str]             # formatted value per column
    deltas_vs_base: List[Optional[float]]  # numeric delta vs first column (None for non-numeric)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Comparison:
    """Aligned side-by-side comparison of N assets/scenarios."""
    columns: List[str]             # column headers (asset/scenario names)
    rows: List[ComparisonRow]
    results: List[Dict[str, Any]]  # full rNPV dict per column, for drill-down

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "rows": [r.to_dict() for r in self.rows],
            "results": self.results,
        }

    def to_markdown(self) -> str:
        """Render the comparison as a GitHub-flavoured markdown table."""
        head = "| Metric | " + " | ".join(self.columns) + " |"
        sep = "|" + "---|" * (len(self.columns) + 1)
        lines = [head, sep]
        for r in self.rows:
            lines.append("| " + r.label + " | " + " | ".join(r.display) + " |")
        return "\n".join(lines)


def _build_comparison(columns: List[str], results: List[RNPVResult]) -> Comparison:
    rows: List[ComparisonRow] = []
    for label, path, spec in _COMPARE_ROWS:
        raw = [_resolve(res, path) for res in results]
        disp = [_fmt(v, spec) for v in raw]
        deltas: List[Optional[float]] = []
        base = raw[0]
        for v in raw:
            if isinstance(v, (int, float)) and isinstance(base, (int, float)):
                deltas.append(round(v - base, 4))
            else:
                deltas.append(None)
        rows.append(ComparisonRow(label=label, values=raw, display=disp,
                                  deltas_vs_base=deltas))
    return Comparison(columns=columns,
                      rows=rows,
                      results=[r.to_dict() for r in results])


# ---------------------------------------------------------------------------
# Loop B — Sensitivity (tornado) + break-even solvers
# ---------------------------------------------------------------------------
# Drivers a one-way sensitivity can flex, with a human label and the
# mechanism by which the perturbation is applied.
_SENSITIVITY_DRIVERS: Dict[str, str] = {
    "peak_sales_musd": "Peak sales",
    "discount_rate": "Discount rate",
    "gross_margin": "Gross margin",
    "sgna_pct_peak": "Commercial SG&A",
    "years_to_peak": "Launch ramp length",
    "exclusivity_years": "Exclusivity years",
    "post_loe_erosion": "Post-LoE erosion",
    "p2_to_p3": "Phase 2→3 PoS",
    "p3_to_filing": "Phase 3→filing PoS",
}


@dataclass
class TornadoBar:
    driver: str
    label: str
    low_value: float          # driver value at the low end
    high_value: float
    rnpv_low: float           # rNPV when driver at low end
    rnpv_high: float
    swing: float              # |rnpv_high − rnpv_low| — the ranking key

    def to_dict(self) -> Dict[str, Any]:
        return {k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in asdict(self).items()}


@dataclass
class TornadoResult:
    base_rnpv_musd: float
    bars: List[TornadoBar]     # sorted by swing, descending

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_rnpv_musd": round(self.base_rnpv_musd, 2),
            "bars": [b.to_dict() for b in self.bars],
        }


def _apply_driver(cfg: AssetRNPVConfig, driver: str, value: float) -> AssetRNPVConfig:
    c = _clone_cfg(cfg)
    prob_keys = {"preclinical_to_p1", "p1_to_p2", "p2_to_p3",
                 "p3_to_filing", "filing_to_approval"}
    if driver in prob_keys:
        po = dict(c.prob_overrides or {})
        po[driver] = value
        c.prob_overrides = po
    elif driver in ("years_to_peak", "exclusivity_years", "years_at_peak"):
        setattr(c, driver, int(round(value)))
    else:
        setattr(c, driver, value)
    return c


def sensitivity_tornado(
    cfg: AssetRNPVConfig,
    drivers: Optional[Dict[str, str]] = None,
    swing_pct: float = 0.25,
    pos_abs_swing: float = 0.10,
) -> TornadoResult:
    """One-way sensitivity ("tornado") of rNPV to each driver.

    Continuous drivers are flexed ±``swing_pct``; probability drivers are
    flexed ±``pos_abs_swing`` in absolute terms (a 25% *relative* move on
    a probability is meaningless near the bounds). Bars are returned
    sorted by the magnitude of rNPV swing so the biggest value levers
    sort to the top — the classic diligence tornado chart.
    """
    drivers = drivers or _SENSITIVITY_DRIVERS
    base = value_asset_rnpv(cfg).rnpv_musd
    ps = _phase_success(cfg.area)
    prob_keys = {"preclinical_to_p1", "p1_to_p2", "p2_to_p3",
                 "p3_to_filing", "filing_to_approval"}
    bars: List[TornadoBar] = []
    for driver, label in drivers.items():
        if driver in prob_keys:
            cur = (cfg.prob_overrides or {}).get(driver) or _transition_prob(ps, {
                "p1_to_p2": DevelopmentPhase.PHASE_1,
                "p2_to_p3": DevelopmentPhase.PHASE_2,
                "p3_to_filing": DevelopmentPhase.PHASE_3,
                "filing_to_approval": DevelopmentPhase.FILED,
                "preclinical_to_p1": DevelopmentPhase.PRECLINICAL,
            }[driver])
            lo = max(0.02, cur - pos_abs_swing)
            hi = min(0.99, cur + pos_abs_swing)
        else:
            cur = getattr(cfg, driver, None)
            if cur is None or not isinstance(cur, (int, float)):
                continue
            lo = cur * (1 - swing_pct)
            hi = cur * (1 + swing_pct)
        rnpv_lo = value_asset_rnpv(_apply_driver(cfg, driver, lo)).rnpv_musd
        rnpv_hi = value_asset_rnpv(_apply_driver(cfg, driver, hi)).rnpv_musd
        bars.append(TornadoBar(
            driver=driver, label=label, low_value=lo, high_value=hi,
            rnpv_low=rnpv_lo, rnpv_high=rnpv_hi,
            swing=abs(rnpv_hi - rnpv_lo),
        ))
    bars.sort(key=lambda b: b.swing, reverse=True)
    return TornadoResult(base_rnpv_musd=base, bars=bars)


def _solve_bisection(f, lo: float, hi: float, target: float = 0.0,
                     tol: float = 1e-3, iters: int = 80) -> Optional[float]:
    """Robust bisection for a monotone driver→rNPV relationship."""
    flo, fhi = f(lo) - target, f(hi) - target
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if flo * fhi > 0:
        return None  # target not bracketed
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid) - target
        if abs(fm) < tol or (hi - lo) < tol:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def breakeven_peak_sales(cfg: AssetRNPVConfig, target_rnpv: float = 0.0) -> Optional[float]:
    """Peak sales ($M) at which rNPV hits ``target_rnpv``.

    Answers "how big does this drug have to be to justify today's price?"
    — the number the commercial team must defend.
    """
    f = lambda x: value_asset_rnpv(_apply_driver(cfg, "peak_sales_musd", x)).rnpv_musd
    hi = max(cfg.peak_sales_musd * 20, 5000.0)
    return _solve_bisection(f, 1.0, hi, target=target_rnpv)


def breakeven_loa(cfg: AssetRNPVConfig, target_rnpv: float = 0.0) -> Optional[float]:
    """Cumulative LoA at which rNPV hits ``target_rnpv``.

    Scales every remaining phase-transition probability by a common
    factor and solves for the factor that zeroes rNPV — the *implied
    probability of success* the current price embeds. If the market pays
    more than this asset's benchmark LoA supports, the market is pricing
    in a better clinical read than history alone justifies.
    """
    base_loa = cumulative_loa(cfg.current_phase, cfg.area, cfg.prob_overrides)
    if base_loa <= 0:
        return None

    def f(scale: float) -> float:
        ps = _phase_success(cfg.area)
        if cfg.prob_overrides:
            ps = _override_ps(ps, cfg.prob_overrides)
        # scale each transition prob by scale**(1/n) so cumulative ∝ scale
        n = sum(1 for frm, _ in _TRANSITIONS if frm.order >= cfg.current_phase.order)
        k = scale ** (1.0 / max(1, n))
        ov = {
            "p1_to_p2": min(0.999, ps.p1_to_p2 * k),
            "p2_to_p3": min(0.999, ps.p2_to_p3 * k),
            "p3_to_filing": min(0.999, ps.p3_to_filing * k),
            "filing_to_approval": min(0.999, ps.filing_to_approval * k),
            "preclinical_to_p1": min(0.999, ps.preclinical_to_p1 * k),
        }
        c = _clone_cfg(cfg)
        c.prob_overrides = ov
        return value_asset_rnpv(c).rnpv_musd

    scale = _solve_bisection(f, 0.01, 3.0, target=target_rnpv)
    if scale is None:
        return None
    return min(1.0, base_loa * scale)


def compare_assets(configs: List[AssetRNPVConfig]) -> Comparison:
    """Side-by-side rNPV comparison across distinct assets.

    Every asset is valued and aligned on the same metric rows, with
    numeric deltas measured against the first (left-most) column.
    """
    if not configs:
        raise ValueError("compare_assets requires at least one asset config")
    results = [value_asset_rnpv(c) for c in configs]
    columns = [c.name for c in configs]
    return _build_comparison(columns, results)


# ---------------------------------------------------------------------------
# Loop A — Monte Carlo rNPV (stochastic, binary-outcome simulation)
# ---------------------------------------------------------------------------
def _dev_schedule(cfg: AssetRNPVConfig) -> Tuple[Dict[int, float], int, List[Tuple[DevelopmentPhase, float, int, float]]]:
    """Shared development schedule builder used by MC + option models.

    Returns ``(dev_by_year, dev_years, gates)`` where ``gates`` is an
    ordered list of ``(phase, transition_prob, phase_end_year,
    phase_cost)`` — everything a trial needs to walk the clinic gate by
    gate, spend money, and decide success/failure.
    """
    ps = _phase_success(cfg.area)
    if cfg.prob_overrides:
        ps = _override_ps(ps, cfg.prob_overrides)
    phase_costs = cfg.phase_costs or PHASE_DEFAULTS
    remaining = [p for p in [DevelopmentPhase.PRECLINICAL, DevelopmentPhase.PHASE_1,
                             DevelopmentPhase.PHASE_2, DevelopmentPhase.PHASE_3,
                             DevelopmentPhase.FILED]
                 if p.order >= cfg.current_phase.order]
    dev_by_year: Dict[int, float] = {}
    gates: List[Tuple[DevelopmentPhase, float, int, float]] = []
    t = 0
    for p in remaining:
        econ = phase_costs.get(p)
        if econ is None:
            continue
        dur = max(1, int(round(econ.duration_years)))
        annual = econ.cost_musd / dur
        for _ in range(dur):
            dev_by_year[t + 1] = dev_by_year.get(t + 1, 0.0) + annual
            t += 1
        gates.append((p, _transition_prob(ps, p), t, econ.cost_musd))
    return dev_by_year, t, gates


@dataclass
class StochasticInputs:
    """Uncertainty envelope around an asset's deterministic config.

    All spreads are multiplicative and dimensionless so one envelope can
    be reused across assets of very different size:

      * ``peak_sales_cv`` — coefficient of variation of peak sales
        (lognormal); commercial forecasts are notoriously right-skewed.
      * ``pos_abs_sd`` — absolute SD applied to each phase-transition
        probability (clamped to (0,1)); captures clinical-read
        uncertainty beyond the point estimate.
      * ``cost_spread`` / ``time_spread`` — triangular ± fractional
        spread on dev cost and timeline.
      * ``margin_abs_sd`` — absolute SD on the operating margin.
    """
    peak_sales_cv: float = 0.45
    pos_abs_sd: float = 0.05
    cost_spread: float = 0.30
    time_spread: float = 0.20
    margin_abs_sd: float = 0.04


@dataclass
class MonteCarloResult:
    """Distribution of rNPV outcomes across simulated trials."""
    n_trials: int
    mean_musd: float                 # ≈ analytic rNPV (MC is its distribution)
    analytic_rnpv_musd: float
    std_musd: float
    p5_musd: float
    p10_musd: float
    p50_musd: float
    p90_musd: float
    p95_musd: float
    prob_positive: float             # P(value > 0)
    prob_technical_success: float    # P(asset reaches market) — the LoA, empirically
    ev_if_success_musd: float        # mean value on the success branch
    ev_if_failure_musd: float        # mean value on the failure branch (negative — sunk cost)
    value_at_risk_musd: float        # 5th-percentile loss

    def to_dict(self) -> Dict[str, Any]:
        return {k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in asdict(self).items()}


def monte_carlo_rnpv(
    cfg: AssetRNPVConfig,
    stochastic: Optional[StochasticInputs] = None,
    n_trials: int = 10_000,
    seed: int = 12345,
) -> MonteCarloResult:
    """Simulate the full rNPV outcome distribution.

    Each trial walks the clinic gate by gate: at every gate a Bernoulli
    draw on the (perturbed) probability of success decides advance vs
    fail. A failed trial is worth the *negative* present value of the
    development money already sunk to that point — the real downside a
    single point-estimate rNPV hides. A trial that clears every gate
    draws a stochastic peak-sales figure and margin, builds the
    commercial curve, and books discounted commercial cash flow net of
    all development spend.

    The **mean of the distribution reconciles to the analytic rNPV** —
    the point estimate is just the expected value of a violently skewed,
    bimodal distribution (most programs fail small; a few win big). The
    percentiles, P(positive), and conditional expectations are what a
    committee actually needs to size the bet.
    """
    import numpy as np

    s = stochastic or StochasticInputs()
    rng = np.random.default_rng(seed)
    dev_by_year, dev_years, gates = _dev_schedule(cfg)
    r = cfg.discount_rate

    # Pre-compute discounted cumulative dev spend at the end of each gate
    # so a failure can be priced instantly.
    disc_cum_at_gate: List[float] = []
    running = 0.0
    gate_end_years = [g[2] for g in gates]
    for gi, (_p, _prob, end_yr, _cost) in enumerate(gates):
        prev_end = gate_end_years[gi - 1] if gi > 0 else 0
        for yr in range(prev_end + 1, end_yr + 1):
            running += dev_by_year.get(yr, 0.0) / ((1 + r) ** yr)
        disc_cum_at_gate.append(running)

    analytic = value_asset_rnpv(cfg).rnpv_musd
    base_margin = cfg.gross_margin - cfg.sgna_pct_peak - cfg.other_opex_pct

    values = np.empty(n_trials)
    successes = np.zeros(n_trials, dtype=bool)

    for i in range(n_trials):
        failed_gate = -1
        for gi, (_p, prob, _end_yr, _cost) in enumerate(gates):
            # perturb the gate probability (clinical-read uncertainty)
            pj = prob
            if s.pos_abs_sd > 0:
                pj = float(np.clip(rng.normal(prob, s.pos_abs_sd), 0.02, 0.99))
            if rng.random() > pj:
                failed_gate = gi
                break

        if failed_gate >= 0:
            # worth the negative PV of money sunk through the failed phase
            values[i] = -disc_cum_at_gate[failed_gate]
            continue

        successes[i] = True
        # timeline perturbation shifts the whole commercial stream
        time_mult = 1.0 + rng.triangular(-s.time_spread, 0.0, s.time_spread)
        launch_offset = dev_years * time_mult
        # stochastic peak sales (lognormal) and margin
        if s.peak_sales_cv > 0:
            sigma = math.sqrt(math.log(1 + s.peak_sales_cv ** 2))
            mu = math.log(max(cfg.peak_sales_musd, 1e-6)) - 0.5 * sigma ** 2
            peak = float(rng.lognormal(mu, sigma))
        else:
            peak = cfg.peak_sales_musd
        margin = base_margin + (rng.normal(0, s.margin_abs_sd) if s.margin_abs_sd > 0 else 0.0)

        tmp = _clone_cfg(cfg, peak_sales_musd=peak)
        sales = _sales_curve(tmp)
        cost_mult = 1.0 + rng.triangular(-s.cost_spread, 0.0, s.cost_spread)

        val = 0.0
        for yr, cost in dev_by_year.items():
            val -= (cost * cost_mult) / ((1 + r) ** yr)
        for idx, ns in enumerate(sales):
            yr = launch_offset + idx + 1
            op_cf = ns * margin * (1 - cfg.tax_rate)
            val += op_cf / ((1 + r) ** yr)
        values[i] = val

    def pct(q):
        return float(np.percentile(values, q))

    fail_mask = ~successes
    return MonteCarloResult(
        n_trials=n_trials,
        mean_musd=float(values.mean()),
        analytic_rnpv_musd=analytic,
        std_musd=float(values.std()),
        p5_musd=pct(5), p10_musd=pct(10), p50_musd=pct(50),
        p90_musd=pct(90), p95_musd=pct(95),
        prob_positive=float((values > 0).mean()),
        prob_technical_success=float(successes.mean()),
        ev_if_success_musd=float(values[successes].mean()) if successes.any() else 0.0,
        ev_if_failure_musd=float(values[fail_mask].mean()) if fail_mask.any() else 0.0,
        value_at_risk_musd=pct(5),
    )


def _clone_cfg(cfg: AssetRNPVConfig, **overrides: Any) -> AssetRNPVConfig:
    import copy
    c = copy.copy(cfg)
    c.deal = None
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


def compare_assets_deep(
    configs: List[AssetRNPVConfig],
    stochastic: Optional[StochasticInputs] = None,
    n_trials: int = 5_000,
    seed: int = 12345,
) -> Comparison:
    """Side-by-side comparison enriched with the Monte-Carlo distribution.

    Same aligned layout as :func:`compare_assets`, plus rows for the
    P10/P50/P90 rNPV, probability of a positive outcome, and probability
    of technical success — so a committee sees not just each asset's
    point value but the *shape* of its risk, side by side.
    """
    if not configs:
        raise ValueError("compare_assets_deep requires at least one asset config")
    results = [value_asset_rnpv(c) for c in configs]
    mcs = [monte_carlo_rnpv(c, stochastic, n_trials=n_trials, seed=seed)
           for c in configs]
    comp = _build_comparison([c.name for c in configs], results)

    def _row(label: str, vals: List[float], spec: str) -> ComparisonRow:
        disp = [_fmt(v, spec) for v in vals]
        base = vals[0]
        deltas = [round(v - base, 4) for v in vals]
        return ComparisonRow(label=label, values=vals, display=disp,
                             deltas_vs_base=deltas)

    comp.rows.append(_row("MC P10 rNPV ($M)", [m.p10_musd for m in mcs], "musd"))
    comp.rows.append(_row("MC P50 rNPV ($M)", [m.p50_musd for m in mcs], "musd"))
    comp.rows.append(_row("MC P90 rNPV ($M)", [m.p90_musd for m in mcs], "musd"))
    comp.rows.append(_row("P(positive rNPV)", [m.prob_positive for m in mcs], "pct"))
    comp.rows.append(_row("P(reaches market)",
                          [m.prob_technical_success for m in mcs], "pct"))
    return comp


def compare_scenarios(
    base: AssetRNPVConfig,
    scenarios: Dict[str, Dict[str, Any]],
    include_base: bool = True,
) -> Comparison:
    """Side-by-side comparison of one asset under multiple assumption sets.

    ``scenarios`` maps a scenario name to a dict of ``AssetRNPVConfig``
    field overrides (e.g. ``{"Bear": {"peak_sales_musd": 400,
    "p2_to_p3": 0.2}, "Bull": {"peak_sales_musd": 2500}}``). Overrides
    that name a phase-transition probability are routed into
    ``prob_overrides`` automatically. Deltas are measured against the
    base case (or the first scenario when ``include_base`` is False).
    """
    import copy
    prob_keys = {"preclinical_to_p1", "p1_to_p2", "p2_to_p3",
                 "p3_to_filing", "filing_to_approval"}
    columns: List[str] = []
    configs: List[AssetRNPVConfig] = []

    if include_base:
        columns.append("Base")
        configs.append(base)

    for name, ov in scenarios.items():
        c = copy.deepcopy(base)
        c.name = name
        prob_ov = dict(c.prob_overrides or {})
        for k, v in ov.items():
            if k in prob_keys:
                prob_ov[k] = v
            elif k == "area" and isinstance(v, str):
                c.area = TherapeuticArea(v)
            elif k == "current_phase" and isinstance(v, str):
                c.current_phase = DevelopmentPhase(v)
            elif hasattr(c, k):
                setattr(c, k, v)
        if prob_ov:
            c.prob_overrides = prob_ov
        columns.append(name)
        configs.append(c)

    results = [value_asset_rnpv(c) for c in configs]
    return _build_comparison(columns, results)
