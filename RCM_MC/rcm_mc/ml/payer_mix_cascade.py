"""Payer mix shift cascade model — full downstream impact.

The existing ``data_public/payer_mix_shift_model.py`` projects
payer mix evolution over time and outputs a single EBITDA margin
delta. The directive asks the deeper question: when payer mix
shifts, **every** downstream metric moves — and partner needs to
see the full cascade to size the value-creation story.

Cascade structure:

  Tier 0 — Inputs:
    payer mix vector (medicare/medicaid/commercial/self_pay)

  Tier 1 — Direct rate effects:
    • net_revenue_per_charge ratio (each payer's reimbursement)
    • denial_rate (Medicaid > Medicare > Commercial)
    • days_in_ar (Medicaid > Medicare > Commercial > Self-pay
      pays cash sooner — but rarely)
    • collection_rate (Self-pay << others)

  Tier 2 — Derived:
    • bad_debt_dollars = (1 - collection_rate) × NPR
    • ar_balance = NPR × (DSO/365)
    • cost_to_collect_pct (drives follow-up labor)

  Tier 3 — Terminal:
    • operating_margin (NPR change × ~70% fixed-cost leverage)
    • ebitda_dollars = margin × NPR

Each payer type carries an empirical profile (research-band
calibrated). A mix shift propagates by recomputing the
weighted-average each metric. The cascade output gives
per-metric absolute and percentage delta from baseline plus the
$/year EBITDA impact.

Public API::

    from rcm_mc.ml.payer_mix_cascade import (
        PayerProfile,
        PayerMix,
        CascadeResult,
        DEFAULT_PAYER_PROFILES,
        compute_baseline_metrics,
        cascade_payer_mix_shift,
        sensitivity_sweep,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


PAYER_TYPES = ("medicare", "medicaid", "commercial", "self_pay")


@dataclass
class PayerProfile:
    """Empirical profile for one payer type.

    Reimbursement index is NPR per gross charge (commercial=1.0
    baseline). Denial / DSO / collection are payer-specific
    intrinsic rates that get weighted-averaged at the hospital
    level by the mix.
    """
    payer: str
    reimbursement_index: float       # vs. commercial = 1.0
    denial_rate: float                # 0..1
    days_in_ar: float
    collection_rate: float            # 0..1
    bad_debt_rate: float              # 1 - collection_rate, but
                                      #   tracked separately because
                                      #   self-pay has higher charity
                                      #   write-off vs collection
    cost_to_collect_pct: float        # of NPR


# Research-band calibrated payer profiles. Calibration sources:
#   - Commercial / Medicare reimbursement: rcm_ebitda_bridge bands
#   - Medicaid: HFMA Medicaid case studies (~0.55-0.62 rate index)
#   - Self-pay collection: industry self-pay research (~10-15%
#     of gross collected once charity care is netted)
#   - Denial: HFMA MAP Keys broken out by payer
DEFAULT_PAYER_PROFILES: Dict[str, PayerProfile] = {
    "commercial": PayerProfile(
        payer="commercial",
        reimbursement_index=1.00,
        denial_rate=0.06,
        days_in_ar=38.0,
        collection_rate=0.97,
        bad_debt_rate=0.02,
        cost_to_collect_pct=0.025),
    "medicare": PayerProfile(
        payer="medicare",
        reimbursement_index=0.79,   # blended IP+OP
        denial_rate=0.08,
        days_in_ar=42.0,
        collection_rate=0.96,
        bad_debt_rate=0.03,
        cost_to_collect_pct=0.022),
    "medicaid": PayerProfile(
        payer="medicaid",
        reimbursement_index=0.58,
        denial_rate=0.14,
        days_in_ar=58.0,
        collection_rate=0.91,
        bad_debt_rate=0.06,
        cost_to_collect_pct=0.038),
    "self_pay": PayerProfile(
        payer="self_pay",
        reimbursement_index=0.15,   # net of charity write-off
        denial_rate=0.18,
        days_in_ar=72.0,
        collection_rate=0.50,
        bad_debt_rate=0.30,
        cost_to_collect_pct=0.060),
}


@dataclass
class PayerMix:
    """Mix vector. Sum should equal 1.0 (validated)."""
    medicare: float = 0.40
    medicaid: float = 0.15
    commercial: float = 0.40
    self_pay: float = 0.05

    def to_dict(self) -> Dict[str, float]:
        return {
            "medicare": self.medicare,
            "medicaid": self.medicaid,
            "commercial": self.commercial,
            "self_pay": self.self_pay,
        }

    def normalize(self) -> "PayerMix":
        """Renormalize so the components sum to 1.0."""
        total = (self.medicare + self.medicaid
                 + self.commercial + self.self_pay)
        if total <= 0:
            raise ValueError(
                "PayerMix components sum to zero")
        return PayerMix(
            medicare=self.medicare / total,
            medicaid=self.medicaid / total,
            commercial=self.commercial / total,
            self_pay=self.self_pay / total)


@dataclass
class CascadeResult:
    """Full cascade output."""
    baseline_mix: Dict[str, float]
    new_mix: Dict[str, float]
    mix_delta_pp: Dict[str, float]   # in percentage points

    # Tier 1 — direct
    baseline_revenue_index: float
    new_revenue_index: float
    revenue_index_delta_pct: float

    baseline_denial_rate: float
    new_denial_rate: float
    denial_rate_delta_pp: float

    baseline_days_in_ar: float
    new_days_in_ar: float
    days_in_ar_delta: float

    baseline_collection_rate: float
    new_collection_rate: float
    collection_rate_delta_pp: float

    # Tier 2 — derived (relative to gross-charge volume of $1B)
    baseline_npr_per_billion_charges: float
    new_npr_per_billion_charges: float
    npr_delta_dollars: float

    baseline_bad_debt: float
    new_bad_debt: float
    bad_debt_delta_dollars: float

    baseline_ar_balance: float
    new_ar_balance: float
    ar_balance_delta_dollars: float    # working capital impact

    # Tier 3 — terminal
    baseline_ebitda: float
    new_ebitda: float
    ebitda_delta_dollars: float
    ebitda_delta_pct: float

    # Notes / flags
    notes: List[str] = field(default_factory=list)


# ── Baseline computation ─────────────────────────────────────

def _weighted_metric(
    mix: PayerMix,
    profiles: Dict[str, PayerProfile],
    attr: str,
) -> float:
    """Mix-weighted average of one metric across payers."""
    total = 0.0
    for payer in PAYER_TYPES:
        share = getattr(mix, payer)
        prof = profiles.get(payer)
        if prof is None:
            continue
        total += share * float(getattr(prof, attr))
    return total


def compute_baseline_metrics(
    mix: PayerMix,
    *,
    profiles: Optional[Dict[str, PayerProfile]] = None,
    annual_gross_charges: float = 1_000_000_000.0,
    fixed_cost_share: float = 0.70,
    target_ebitda_margin: float = 0.10,
) -> Dict[str, float]:
    """Compute Tier 1+2+3 metrics for a given mix.

    annual_gross_charges: total gross charges; defaults to $1B for
    a reference computation. Real callers pass their hospital's
    actual gross.
    fixed_cost_share: share of operating costs that are fixed.
    Higher = bigger operating leverage = bigger EBITDA swing per
    dollar of NPR change.
    target_ebitda_margin: assumed margin at the baseline mix —
    used to anchor the EBITDA $ at the starting point. Cascade
    computes deltas from that baseline.
    """
    profs = profiles or DEFAULT_PAYER_PROFILES
    mix = mix.normalize()

    revenue_index = _weighted_metric(
        mix, profs, "reimbursement_index")
    denial_rate = _weighted_metric(
        mix, profs, "denial_rate")
    days_in_ar = _weighted_metric(
        mix, profs, "days_in_ar")
    collection_rate = _weighted_metric(
        mix, profs, "collection_rate")
    bad_debt_rate = _weighted_metric(
        mix, profs, "bad_debt_rate")
    cost_to_collect = _weighted_metric(
        mix, profs, "cost_to_collect_pct")

    npr = annual_gross_charges * revenue_index
    bad_debt = npr * bad_debt_rate
    ar_balance = npr * (days_in_ar / 365.0)
    ebitda = npr * target_ebitda_margin

    return {
        "revenue_index": revenue_index,
        "denial_rate": denial_rate,
        "days_in_ar": days_in_ar,
        "collection_rate": collection_rate,
        "bad_debt_rate": bad_debt_rate,
        "cost_to_collect_pct": cost_to_collect,
        "npr": npr,
        "bad_debt": bad_debt,
        "ar_balance": ar_balance,
        "ebitda": ebitda,
        "annual_gross_charges": annual_gross_charges,
        "fixed_cost_share": fixed_cost_share,
        "target_ebitda_margin": target_ebitda_margin,
    }


# ── Cascade ──────────────────────────────────────────────────

def cascade_payer_mix_shift(
    baseline_mix: PayerMix,
    new_mix: PayerMix,
    *,
    profiles: Optional[Dict[str, PayerProfile]] = None,
    annual_gross_charges: float = 1_000_000_000.0,
    fixed_cost_share: float = 0.70,
    target_ebitda_margin: float = 0.10,
) -> CascadeResult:
    """Compute the full cascade from baseline mix → new mix.

    EBITDA propagation uses the operating-leverage rule: EBITDA
    moves by (NPR_delta) × (1 - fixed_cost_share + margin), since
    fixed costs don't shrink with revenue but variable costs do.
    """
    profs = profiles or DEFAULT_PAYER_PROFILES
    base = compute_baseline_metrics(
        baseline_mix,
        profiles=profs,
        annual_gross_charges=annual_gross_charges,
        fixed_cost_share=fixed_cost_share,
        target_ebitda_margin=target_ebitda_margin)
    new = compute_baseline_metrics(
        new_mix,
        profiles=profs,
        annual_gross_charges=annual_gross_charges,
        fixed_cost_share=fixed_cost_share,
        target_ebitda_margin=target_ebitda_margin)

    base_mix_norm = baseline_mix.normalize()
    new_mix_norm = new_mix.normalize()
    base_dict = base_mix_norm.to_dict()
    new_dict = new_mix_norm.to_dict()
    mix_delta_pp = {
        p: round((new_dict[p] - base_dict[p]) * 100, 2)
        for p in PAYER_TYPES
    }

    # NPR change
    npr_delta = new["npr"] - base["npr"]

    # EBITDA propagation: NPR-delta drops to EBITDA at the
    # contribution-margin rate (1 - variable_cost_share). With
    # fixed_cost_share=0.70 and target_margin=0.10, contribution
    # margin = 1 - 0.20 = 0.80, but that double-counts the
    # margin baseline. Simpler: variable_cost_share = (1 -
    # margin) × (1 - fixed_cost_share). EBITDA delta on NPR
    # delta = NPR_delta × (1 - variable_cost_rate). For the
    # default knobs that's NPR_delta × 0.73 — close to the
    # research band of 70% drop-through on revenue changes.
    variable_cost_rate = (
        (1.0 - target_ebitda_margin)
        * (1.0 - fixed_cost_share))
    drop_through = 1.0 - variable_cost_rate
    ebitda_delta = npr_delta * drop_through
    new_ebitda = base["ebitda"] + ebitda_delta

    notes: List[str] = []
    if mix_delta_pp.get("commercial", 0.0) <= -3.0:
        notes.append(
            f"Commercial dropped "
            f"{abs(mix_delta_pp['commercial']):.1f}pp — "
            f"largest revenue-index hit. Project EBITDA "
            f"margin compression of "
            f"{abs(ebitda_delta) / base['npr'] * 100:.1f}pp.")
    if mix_delta_pp.get("medicaid", 0.0) >= 3.0:
        notes.append(
            f"Medicaid grew "
            f"{mix_delta_pp['medicaid']:.1f}pp — DSO + denial "
            f"+ bad-debt all worsen together. Working capital "
            f"impact: ${(new['ar_balance'] - base['ar_balance']) / 1e6:+.1f}M.")
    if mix_delta_pp.get("self_pay", 0.0) >= 2.0:
        notes.append(
            f"Self-pay grew "
            f"{mix_delta_pp['self_pay']:.1f}pp — collection "
            f"rate falls "
            f"{(base['collection_rate'] - new['collection_rate']) * 100:.1f}pp; "
            f"bad debt + charity care line item up "
            f"${(new['bad_debt'] - base['bad_debt']) / 1e6:+.1f}M.")
    npr_delta_pct = (npr_delta / base["npr"]
                     if base["npr"] > 0 else 0.0)
    if abs(npr_delta_pct) >= 0.05:
        direction = ("compression" if npr_delta < 0
                     else "tailwind")
        notes.append(
            f"NPR moves {npr_delta_pct * 100:+.1f}% — "
            f"material {direction}. "
            f"{drop_through:.0%} drop-through = "
            f"${ebitda_delta / 1e6:+.1f}M EBITDA.")

    return CascadeResult(
        baseline_mix=base_dict,
        new_mix=new_dict,
        mix_delta_pp=mix_delta_pp,
        baseline_revenue_index=round(
            base["revenue_index"], 4),
        new_revenue_index=round(new["revenue_index"], 4),
        revenue_index_delta_pct=round(
            (new["revenue_index"] / base["revenue_index"]
             - 1.0) * 100,
            3) if base["revenue_index"] > 0 else 0.0,
        baseline_denial_rate=round(
            base["denial_rate"], 4),
        new_denial_rate=round(new["denial_rate"], 4),
        denial_rate_delta_pp=round(
            (new["denial_rate"] - base["denial_rate"])
            * 100, 3),
        baseline_days_in_ar=round(base["days_in_ar"], 2),
        new_days_in_ar=round(new["days_in_ar"], 2),
        days_in_ar_delta=round(
            new["days_in_ar"] - base["days_in_ar"], 2),
        baseline_collection_rate=round(
            base["collection_rate"], 4),
        new_collection_rate=round(
            new["collection_rate"], 4),
        collection_rate_delta_pp=round(
            (new["collection_rate"]
             - base["collection_rate"]) * 100, 3),
        baseline_npr_per_billion_charges=round(
            base["npr"], 0),
        new_npr_per_billion_charges=round(new["npr"], 0),
        npr_delta_dollars=round(npr_delta, 0),
        baseline_bad_debt=round(base["bad_debt"], 0),
        new_bad_debt=round(new["bad_debt"], 0),
        bad_debt_delta_dollars=round(
            new["bad_debt"] - base["bad_debt"], 0),
        baseline_ar_balance=round(base["ar_balance"], 0),
        new_ar_balance=round(new["ar_balance"], 0),
        ar_balance_delta_dollars=round(
            new["ar_balance"] - base["ar_balance"], 0),
        baseline_ebitda=round(base["ebitda"], 0),
        new_ebitda=round(new_ebitda, 0),
        ebitda_delta_dollars=round(ebitda_delta, 0),
        ebitda_delta_pct=round(
            (ebitda_delta / base["ebitda"] * 100)
            if base["ebitda"] > 0 else 0.0, 3),
        notes=notes,
    )


# ── Sensitivity sweep ───────────────────────────────────────

def sensitivity_sweep(
    baseline_mix: PayerMix,
    *,
    payer: str,
    deltas_pp: Iterable[float] = (-5, -3, -1, 1, 3, 5),
    counterparty: str = "commercial",
    profiles: Optional[Dict[str, PayerProfile]] = None,
    annual_gross_charges: float = 1_000_000_000.0,
    fixed_cost_share: float = 0.70,
    target_ebitda_margin: float = 0.10,
) -> List[Tuple[float, CascadeResult]]:
    """Run the cascade across a series of mix shocks.

    deltas_pp moves ``payer`` by that many percentage points; the
    counterparty payer absorbs the offsetting change so the mix
    still sums to 1. Useful for the IC tornado question 'what if
    commercial loses 1/3/5pp to Medicaid?'.

    Returns: list of (delta_pp, CascadeResult) tuples, sorted by
    delta_pp ascending.
    """
    if payer not in PAYER_TYPES:
        raise ValueError(f"Unknown payer: {payer}")
    if counterparty not in PAYER_TYPES:
        raise ValueError(
            f"Unknown counterparty: {counterparty}")
    if payer == counterparty:
        raise ValueError(
            "payer and counterparty must differ")

    out: List[Tuple[float, CascadeResult]] = []
    for delta_pp in sorted(deltas_pp):
        new_mix = PayerMix(
            medicare=baseline_mix.medicare,
            medicaid=baseline_mix.medicaid,
            commercial=baseline_mix.commercial,
            self_pay=baseline_mix.self_pay)
        delta_frac = delta_pp / 100.0
        setattr(new_mix, payer,
                getattr(new_mix, payer) + delta_frac)
        setattr(new_mix, counterparty,
                getattr(new_mix, counterparty) - delta_frac)
        # Skip if any component goes < 0
        try:
            new_mix = new_mix.normalize()
        except ValueError:
            continue
        if any(getattr(new_mix, p) < 0
               for p in PAYER_TYPES):
            continue
        result = cascade_payer_mix_shift(
            baseline_mix, new_mix,
            profiles=profiles,
            annual_gross_charges=annual_gross_charges,
            fixed_cost_share=fixed_cost_share,
            target_ebitda_margin=target_ebitda_margin)
        out.append((delta_pp, result))
    return out
