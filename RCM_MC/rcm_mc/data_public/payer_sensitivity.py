"""Payer-mix sensitivity analysis for deal underwriting.

Models the financial impact of adverse payer-mix scenarios that a
senior PE healthcare partner would stress in IC:

    1. Medicaid rate cuts (state budget cycles, managed care transitions)
    2. Medicare Advantage mix creep (traditional → MA at lower net rates)
    3. Commercial payer loss (single-payer contract termination)
    4. Uncompensated care spike (economic cycle / ACA rollback)
    5. Payer mix shift (inpatient volume moving to ambulatory)

Why this module exists:
    The base RCM simulator uses point estimates for payer rates.
    This module wraps it with scenario stressing to show how sensitive
    EBITDA and MOIC are to payer-mix assumptions — one of the top-3
    risks flagged in every hospital PE IC deck since 2018.

Public API:
    PayerScenario dataclass
    SensitivityResult dataclass
    run_medicaid_cut_scenario(deal, cut_pct)        -> SensitivityResult
    run_ma_creep_scenario(deal, ma_creep_pct)       -> SensitivityResult
    run_commercial_loss_scenario(deal, loss_pct)    -> SensitivityResult
    run_all_scenarios(deal)                         -> List[SensitivityResult]
    sensitivity_table(deal)                         -> str  (ASCII table)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PayerScenario:
    """Definition of a single payer-mix stress scenario."""
    name: str
    description: str
    # Payer rate multipliers (1.0 = no change, 0.9 = 10% rate cut)
    rate_multipliers: Dict[str, float] = field(default_factory=dict)
    # Volume shifts: fraction of total revenue shifted between payers
    volume_shifts: Dict[str, float] = field(default_factory=dict)


@dataclass
class SensitivityResult:
    scenario_name: str
    scenario_description: str

    base_ev_mm: Optional[float]
    base_ebitda_mm: Optional[float]
    base_moic: Optional[float]

    stressed_ebitda_mm: Optional[float]
    ebitda_delta_mm: Optional[float]
    ebitda_delta_pct: Optional[float]

    stressed_moic: Optional[float]
    moic_delta: Optional[float]

    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario_name,
            "description": self.scenario_description,
            "base_ebitda_mm": self.base_ebitda_mm,
            "stressed_ebitda_mm": round(self.stressed_ebitda_mm, 1) if self.stressed_ebitda_mm else None,
            "ebitda_delta_mm": round(self.ebitda_delta_mm, 1) if self.ebitda_delta_mm else None,
            "ebitda_delta_pct": round(self.ebitda_delta_pct, 3) if self.ebitda_delta_pct else None,
            "stressed_moic": round(self.stressed_moic, 2) if self.stressed_moic else None,
            "moic_delta": round(self.moic_delta, 2) if self.moic_delta else None,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Core calculation helpers
# ---------------------------------------------------------------------------

def _get_payer_mix(deal: Dict[str, Any]) -> Dict[str, float]:
    pm = deal.get("payer_mix") or {}
    if isinstance(pm, str):
        import json
        try:
            pm = json.loads(pm)
        except Exception:
            pm = {}
    return {k: float(v) for k, v in pm.items()} if pm else {}


def _ebitda_impact_from_rate_change(
    ebitda_base: float,
    payer_mix: Dict[str, float],
    rate_multipliers: Dict[str, float],
    ebitda_margin: float = 0.10,
) -> float:
    """Estimate EBITDA impact from payer rate changes.

    Assumes payer revenue is proportional to payer_mix share, and that
    the EBITDA margin on each payer's revenue is approximately equal
    (simplifying assumption — accurate enough for IC-level sensitivity).

    Args:
        ebitda_base:       entry EBITDA in $M
        payer_mix:         dict of payer → share of revenue (sums to ~1.0)
        rate_multipliers:  dict of payer → rate multiplier (0.9 = 10% cut)
        ebitda_margin:     assumed EBITDA/revenue margin for stressed revenue
    """
    if not ebitda_base or not payer_mix:
        return 0.0

    # Implied revenue from EBITDA using assumed margin
    implied_revenue = ebitda_base / ebitda_margin

    delta_ebitda = 0.0
    for payer, mult in rate_multipliers.items():
        share = payer_mix.get(payer, 0.0)
        payer_rev = implied_revenue * share
        rate_impact = payer_rev * (mult - 1.0)
        # Revenue change flows through to EBITDA at ebitda_margin rate
        # (variable cost assumption: ~70-80% of revenue is variable)
        variable_cost_ratio = 0.75
        delta_ebitda += rate_impact * (1.0 - variable_cost_ratio)

    return delta_ebitda


def _compute_stressed_moic(
    base_moic: Optional[float],
    ebitda_base: Optional[float],
    ebitda_delta: float,
    ev_mm: Optional[float],
    hold_years: float = 5.0,
    exit_multiple: float = 8.0,
) -> Optional[float]:
    """Estimate MOIC impact from EBITDA change under simplified LBO math.

    Assumptions:
        - Exit EV = stressed EBITDA × exit_multiple
        - Equity = EV × equity_cushion (40% typical for hospital LBO)
        - MOIC ≈ exit_equity / entry_equity
    """
    if base_moic is None or ev_mm is None or ebitda_base is None:
        return None

    # Entry equity (rough: 40% of EV for hospital deals)
    equity_cushion = 0.40
    entry_equity = ev_mm * equity_cushion

    # Base exit equity (implied from base_moic)
    base_exit_equity = base_moic * entry_equity

    # Stressed exit: delta applied to exit EBITDA × same exit multiple
    stressed_ebitda = ebitda_base + ebitda_delta
    # Implied base exit EBITDA (grows at EBITDA CAGR from base)
    # Approximate: if moic=2.5 at 8x exit, then exit EBITDA ≈ base*(2.5/1)^(1/hold)
    # Simplified: just apply delta to same EBITDA base assumed at exit
    exit_ebitda_delta = ebitda_delta  # delta persists through hold period
    stressed_exit_ev_delta = exit_ebitda_delta * exit_multiple
    stressed_exit_equity = base_exit_equity + stressed_exit_ev_delta * equity_cushion

    if entry_equity <= 0:
        return None
    return max(0.0, stressed_exit_equity / entry_equity)


# ---------------------------------------------------------------------------
# Individual scenario runners
# ---------------------------------------------------------------------------

def run_medicaid_cut_scenario(
    deal: Dict[str, Any],
    cut_pct: float = 0.05,
    ebitda_margin: float = 0.10,
) -> SensitivityResult:
    """Model a state Medicaid rate cut of cut_pct (e.g. 0.05 = 5% cut).

    Historical precedent: CA Medi-Cal cut 10% in 2011; IL cut 8% in 2012;
    TX CHIP/Medicaid cuts 2011-2012; ACA expansion reversed in some states.
    """
    payer_mix = _get_payer_mix(deal)
    ebitda_base = deal.get("ebitda_at_entry_mm")
    ev_mm = deal.get("ev_mm")
    base_moic = deal.get("realized_moic") or deal.get("projected_moic")

    delta = _ebitda_impact_from_rate_change(
        ebitda_base or 0,
        payer_mix,
        {"medicaid": 1.0 - cut_pct},
        ebitda_margin,
    )
    stressed_ebitda = (ebitda_base + delta) if ebitda_base else None
    pct_change = (delta / ebitda_base) if ebitda_base else None
    stressed_moic = _compute_stressed_moic(base_moic, ebitda_base, delta, ev_mm)
    medicaid_share = payer_mix.get("medicaid", 0.0)

    return SensitivityResult(
        scenario_name="medicaid_rate_cut",
        scenario_description=f"Medicaid rate cut of {cut_pct:.0%}",
        base_ev_mm=ev_mm,
        base_ebitda_mm=ebitda_base,
        base_moic=base_moic,
        stressed_ebitda_mm=stressed_ebitda,
        ebitda_delta_mm=delta,
        ebitda_delta_pct=pct_change,
        stressed_moic=stressed_moic,
        moic_delta=(stressed_moic - base_moic) if (stressed_moic and base_moic) else None,
        notes=(
            f"Medicaid share {medicaid_share:.0%}; "
            f"{cut_pct:.0%} rate cut; estimated via variable-cost passthrough model. "
            f"Historical range: 5-15% in state budget crises."
        ),
    )


def run_ma_creep_scenario(
    deal: Dict[str, Any],
    ma_creep_pct: float = 0.10,
    ma_rate_discount: float = 0.12,
    ebitda_margin: float = 0.10,
) -> SensitivityResult:
    """Model Medicare Advantage volume creep from traditional Medicare.

    As MA penetration grows (now ~50% of Medicare nationally), hospitals
    see net rate compression because MA pays ~85-88% of traditional Medicare
    rates on average.

    ma_creep_pct:     fraction of Medicare revenue shifting to MA
    ma_rate_discount: MA rate discount vs traditional Medicare (default 12%)
    """
    payer_mix = _get_payer_mix(deal)
    ebitda_base = deal.get("ebitda_at_entry_mm")
    ev_mm = deal.get("ev_mm")
    base_moic = deal.get("realized_moic") or deal.get("projected_moic")

    medicare_share = payer_mix.get("medicare", 0.0)
    shifted_share = medicare_share * ma_creep_pct
    rate_mult = 1.0 - (shifted_share / medicare_share * ma_rate_discount) if medicare_share > 0 else 1.0

    delta = _ebitda_impact_from_rate_change(
        ebitda_base or 0,
        payer_mix,
        {"medicare": rate_mult},
        ebitda_margin,
    )
    stressed_ebitda = (ebitda_base + delta) if ebitda_base else None
    pct_change = (delta / ebitda_base) if ebitda_base else None
    stressed_moic = _compute_stressed_moic(base_moic, ebitda_base, delta, ev_mm)

    return SensitivityResult(
        scenario_name="medicare_advantage_creep",
        scenario_description=f"MA creep {ma_creep_pct:.0%} of Medicare volume at {ma_rate_discount:.0%} discount",
        base_ev_mm=ev_mm,
        base_ebitda_mm=ebitda_base,
        base_moic=base_moic,
        stressed_ebitda_mm=stressed_ebitda,
        ebitda_delta_mm=delta,
        ebitda_delta_pct=pct_change,
        stressed_moic=stressed_moic,
        moic_delta=(stressed_moic - base_moic) if (stressed_moic and base_moic) else None,
        notes=(
            f"Medicare {medicare_share:.0%} share; {ma_creep_pct:.0%} shifts to MA "
            f"at {ma_rate_discount:.0%} net rate discount vs traditional Medicare. "
            "MA penetration growing ~2-3 pts/year nationally."
        ),
    )


def run_commercial_loss_scenario(
    deal: Dict[str, Any],
    loss_pct: float = 0.15,
    replacement_payer: str = "medicaid",
    ebitda_margin: float = 0.10,
) -> SensitivityResult:
    """Model loss of commercial contract volume (e.g. payer termination).

    Hospitals occasionally face payer network termination disputes.
    Lost commercial volume is assumed to partly convert to Medicaid/self-pay.
    The rate differential drives EBITDA loss.
    """
    payer_mix = _get_payer_mix(deal)
    ebitda_base = deal.get("ebitda_at_entry_mm")
    ev_mm = deal.get("ev_mm")
    base_moic = deal.get("realized_moic") or deal.get("projected_moic")

    commercial_share = payer_mix.get("commercial", 0.0)
    lost_share = commercial_share * loss_pct

    # Replacement payer rate is ~60% of commercial (Medicaid) or 20% (self-pay)
    replacement_rates = {"medicaid": 0.60, "self_pay": 0.20, "medicare": 0.80}
    rate_ratio = replacement_rates.get(replacement_payer, 0.60)

    if ebitda_base and commercial_share > 0:
        implied_rev = ebitda_base / ebitda_margin
        commercial_rev_lost = implied_rev * lost_share
        replacement_rev = commercial_rev_lost * rate_ratio
        net_rev_loss = commercial_rev_lost - replacement_rev
        variable_cost_ratio = 0.75
        delta = -net_rev_loss * (1.0 - variable_cost_ratio)
    else:
        delta = 0.0

    stressed_ebitda = (ebitda_base + delta) if ebitda_base else None
    pct_change = (delta / ebitda_base) if ebitda_base else None
    stressed_moic = _compute_stressed_moic(base_moic, ebitda_base, delta, ev_mm)

    return SensitivityResult(
        scenario_name="commercial_loss",
        scenario_description=f"Commercial contract loss {loss_pct:.0%} → {replacement_payer}",
        base_ev_mm=ev_mm,
        base_ebitda_mm=ebitda_base,
        base_moic=base_moic,
        stressed_ebitda_mm=stressed_ebitda,
        ebitda_delta_mm=delta,
        ebitda_delta_pct=pct_change,
        stressed_moic=stressed_moic,
        moic_delta=(stressed_moic - base_moic) if (stressed_moic and base_moic) else None,
        notes=(
            f"Commercial {commercial_share:.0%} share; {loss_pct:.0%} volume lost; "
            f"replaced by {replacement_payer} at {rate_ratio:.0%} of commercial rate. "
            "Historical: Steward/Tufts dispute 2022 lasted 3 weeks; Sutter/Anthem 2019."
        ),
    )


def run_uncompensated_care_scenario(
    deal: Dict[str, Any],
    spike_pct: float = 0.03,
    ebitda_margin: float = 0.10,
) -> SensitivityResult:
    """Model an uncompensated care spike (e.g. economic recession, ACA rollback).

    spike_pct: additional self-pay/uninsured as fraction of total revenue.
    Self-pay collections average ~10-15% vs list price; effectively
    treating these as lost revenue at 85% of list.
    """
    ebitda_base = deal.get("ebitda_at_entry_mm")
    ev_mm = deal.get("ev_mm")
    base_moic = deal.get("realized_moic") or deal.get("projected_moic")

    if ebitda_base:
        implied_rev = ebitda_base / ebitda_margin
        incremental_self_pay_rev = implied_rev * spike_pct
        collection_rate = 0.15  # 15% collection on self-pay
        net_rev_loss = incremental_self_pay_rev * (1.0 - collection_rate)
        variable_cost_ratio = 0.75
        delta = -net_rev_loss * (1.0 - variable_cost_ratio)
    else:
        delta = 0.0

    stressed_ebitda = (ebitda_base + delta) if ebitda_base else None
    pct_change = (delta / ebitda_base) if ebitda_base else None
    stressed_moic = _compute_stressed_moic(base_moic, ebitda_base, delta, ev_mm)

    return SensitivityResult(
        scenario_name="uncompensated_care_spike",
        scenario_description=f"Uncompensated care spike +{spike_pct:.0%} of revenue",
        base_ev_mm=ev_mm,
        base_ebitda_mm=ebitda_base,
        base_moic=base_moic,
        stressed_ebitda_mm=stressed_ebitda,
        ebitda_delta_mm=delta,
        ebitda_delta_pct=pct_change,
        stressed_moic=stressed_moic,
        moic_delta=(stressed_moic - base_moic) if (stressed_moic and base_moic) else None,
        notes=(
            f"Additional {spike_pct:.0%} of revenue becoming self-pay; "
            "15% collection rate assumed on incremental self-pay; "
            "Medicaid expansion states have 2-3x lower uncompensated care rates."
        ),
    )


# ---------------------------------------------------------------------------
# Combined runner
# ---------------------------------------------------------------------------

def run_all_scenarios(deal: Dict[str, Any]) -> List[SensitivityResult]:
    """Run all standard payer-mix stress scenarios for a deal."""
    return [
        run_medicaid_cut_scenario(deal, cut_pct=0.05),
        run_medicaid_cut_scenario(deal, cut_pct=0.10),
        run_ma_creep_scenario(deal, ma_creep_pct=0.10),
        run_ma_creep_scenario(deal, ma_creep_pct=0.20),
        run_commercial_loss_scenario(deal, loss_pct=0.15),
        run_commercial_loss_scenario(deal, loss_pct=0.30),
        run_uncompensated_care_scenario(deal, spike_pct=0.03),
    ]


def sensitivity_table(deal: Dict[str, Any]) -> str:
    """Return an ASCII table of payer sensitivity results."""
    results = run_all_scenarios(deal)
    lines = [
        f"Payer Sensitivity: {deal.get('deal_name', 'Unknown')}",
        "-" * 85,
        f"{'Scenario':<40} {'EBITDA Δ$M':>10} {'EBITDA Δ%':>10} {'MOIC Δ':>8}",
        "-" * 85,
    ]
    for r in results:
        delta_mm = f"{r.ebitda_delta_mm:+.1f}" if r.ebitda_delta_mm is not None else "  —"
        delta_pct = f"{r.ebitda_delta_pct:+.1%}" if r.ebitda_delta_pct is not None else "  —"
        moic_d = f"{r.moic_delta:+.2f}x" if r.moic_delta is not None else "  —"
        lines.append(
            f"{r.scenario_description[:39]:<40} {delta_mm:>10} {delta_pct:>10} {moic_d:>8}"
        )
    lines.append("-" * 85)
    return "\n".join(lines)
