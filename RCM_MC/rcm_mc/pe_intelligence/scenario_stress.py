"""Partner stress tests — mechanical shocks a senior partner applies
to any healthcare deal before signing.

These are NOT Monte Carlo — they are deterministic "what if the one
thing I'm worried about happens" checks. Partners ask five of them on
every deal:

1. **Rate shock** — CMS/commercial rate down-rate by X bps. Does
   EBITDA still cover debt?
2. **Volume shock** — 5-10% volume decline. Does margin survive?
3. **Multiple compression** — exit at flat entry multiple. Does the
   deal still clear the hurdle?
4. **Lever slip** — lever program delivers 50-70% of plan. Does the
   bridge still close?
5. **Labor shock** — 10-15% reset on agency / contract labor rates.
   Is the deal still equity-positive?

This module produces deterministic shock outcomes given model inputs.
The goal is not precision — it's helping the partner ask the right
question ("if exit comps compress 1.5x, am I still above 2.0x MOIC?")
and get a one-number answer they can reason with.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StressResult:
    scenario: str
    description: str
    base_ebitda: Optional[float] = None
    shocked_ebitda: Optional[float] = None
    ebitda_delta_pct: Optional[float] = None
    base_moic: Optional[float] = None
    shocked_moic: Optional[float] = None
    moic_delta: Optional[float] = None
    covenant_breach: Optional[bool] = None
    passes: Optional[bool] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "description": self.description,
            "base_ebitda": self.base_ebitda,
            "shocked_ebitda": self.shocked_ebitda,
            "ebitda_delta_pct": self.ebitda_delta_pct,
            "base_moic": self.base_moic,
            "shocked_moic": self.shocked_moic,
            "moic_delta": self.moic_delta,
            "covenant_breach": self.covenant_breach,
            "passes": self.passes,
            "partner_note": self.partner_note,
        }


@dataclass
class StressInputs:
    """Minimum model state a stress can operate on."""
    base_ebitda: Optional[float] = None                   # $ current EBITDA
    target_ebitda: Optional[float] = None                 # $ projected exit EBITDA
    base_revenue: Optional[float] = None                  # $ current revenue
    entry_multiple: Optional[float] = None
    exit_multiple: Optional[float] = None
    debt_at_close: Optional[float] = None                 # $
    interest_rate: Optional[float] = None                 # fraction, e.g. 0.08
    covenant_leverage: Optional[float] = None             # x, e.g. 6.0
    covenant_coverage: Optional[float] = None             # x EBITDA/interest floor
    contract_labor_spend: Optional[float] = None          # $ current
    lever_contribution: Optional[float] = None            # $ of EBITDA lift
    hold_years: Optional[float] = None
    base_moic: Optional[float] = None
    medicare_revenue: Optional[float] = None              # $ revenue from Medicare
    commercial_revenue: Optional[float] = None            # $ revenue from commercial


# ── Helpers ──────────────────────────────────────────────────────────

def _breach_covenant(
    ebitda: float,
    debt: Optional[float],
    covenant_leverage: Optional[float],
) -> Optional[bool]:
    if debt is None or covenant_leverage is None or ebitda <= 0:
        return None
    return (debt / ebitda) > covenant_leverage


def _coverage_breach(
    ebitda: float,
    debt: Optional[float],
    rate: Optional[float],
    covenant_coverage: Optional[float],
) -> Optional[bool]:
    if debt is None or rate is None or covenant_coverage is None:
        return None
    interest = debt * rate
    if interest <= 0:
        return None
    coverage = ebitda / interest
    return coverage < covenant_coverage


def _delta_pct(base: Optional[float], shocked: Optional[float]) -> Optional[float]:
    if base is None or shocked is None or base == 0:
        return None
    return (shocked - base) / abs(base)


# ── Stresses ─────────────────────────────────────────────────────────

def stress_rate_down(inputs: StressInputs, bps: int = 200) -> StressResult:
    """Drop Medicare reimbursement rate by ``bps`` bps. The shock
    applies to Medicare revenue as a pure top-line hit, flowing to
    EBITDA at 100% margin (rate cuts have no offsetting cost)."""
    if inputs.base_ebitda is None or inputs.medicare_revenue is None:
        return StressResult(
            scenario="rate_down",
            description=f"CMS down-rate by {bps} bps",
            partner_note="Cannot run — base EBITDA or Medicare revenue missing.",
        )
    shock_dollars = inputs.medicare_revenue * (bps / 10000.0)
    shocked = inputs.base_ebitda - shock_dollars
    breach = _breach_covenant(shocked, inputs.debt_at_close, inputs.covenant_leverage)
    passes = shocked > 0 and (breach is False or breach is None)
    note = (
        "Deal absorbs the rate shock without breaching leverage."
        if passes and breach is False else
        "Leverage covenant breaks on this shock — re-size debt at close."
        if breach else
        "EBITDA goes negative under this shock. Deal is not viable."
    )
    return StressResult(
        scenario="rate_down",
        description=f"Medicare rate down {bps} bps",
        base_ebitda=inputs.base_ebitda,
        shocked_ebitda=shocked,
        ebitda_delta_pct=_delta_pct(inputs.base_ebitda, shocked),
        covenant_breach=breach,
        passes=passes,
        partner_note=note,
    )


def stress_volume_down(inputs: StressInputs, pct: float = 0.07) -> StressResult:
    """Decline revenue volume by ``pct``. Assume 40% of the lost
    revenue drops to EBITDA (rest is variable cost)."""
    if inputs.base_ebitda is None or inputs.base_revenue is None:
        return StressResult(
            scenario="volume_down",
            description=f"Volume decline {pct*100:.0f}%",
            partner_note="Cannot run — base EBITDA or revenue missing.",
        )
    lost_rev = inputs.base_revenue * pct
    shocked = inputs.base_ebitda - 0.40 * lost_rev
    breach = _breach_covenant(shocked, inputs.debt_at_close, inputs.covenant_leverage)
    passes = shocked > 0 and (breach is False or breach is None)
    note = (
        "Volume shock is absorbable — operating model has some cushion."
        if passes and (breach is False) else
        "Volume shock breaks the covenant. Tighten the operating plan or reduce leverage."
    )
    return StressResult(
        scenario="volume_down",
        description=f"Volume shock −{pct*100:.0f}% revenue",
        base_ebitda=inputs.base_ebitda,
        shocked_ebitda=shocked,
        ebitda_delta_pct=_delta_pct(inputs.base_ebitda, shocked),
        covenant_breach=breach,
        passes=passes,
        partner_note=note,
    )


def stress_multiple_compression(
    inputs: StressInputs,
    flat_multiple: bool = True,
    compression_turns: float = 1.5,
) -> StressResult:
    """Recompute MOIC at a compressed exit multiple.

    If ``flat_multiple`` is True, set exit == entry. Otherwise
    subtract ``compression_turns`` turns from the modeled exit.
    Returns the MOIC delta, not the full cashflow recalc — that's a
    sensitivity approximation, not a model rebuild.
    """
    if (inputs.entry_multiple is None or inputs.exit_multiple is None
            or inputs.target_ebitda is None or inputs.base_ebitda is None
            or inputs.base_moic is None):
        return StressResult(
            scenario="multiple_compression",
            description="Exit-multiple compression",
            partner_note="Cannot run — multiples, EBITDA, or base MOIC missing.",
        )
    new_exit = (inputs.entry_multiple if flat_multiple
                else max(1.0, inputs.exit_multiple - compression_turns))
    # Approximation: MOIC scales proportionally to exit EV.
    base_exit_ev = inputs.target_ebitda * inputs.exit_multiple
    shocked_exit_ev = inputs.target_ebitda * new_exit
    if base_exit_ev <= 0:
        scale = 1.0
    else:
        scale = shocked_exit_ev / base_exit_ev
    shocked_moic = inputs.base_moic * scale
    passes = shocked_moic >= 2.0
    note = (
        "Deal clears the 2.0x MOIC floor even at a flat multiple."
        if passes else
        f"MOIC drops to {shocked_moic:.2f}x at flat multiple — deal is carried "
        "by multiple expansion."
    )
    return StressResult(
        scenario="multiple_compression",
        description=("Exit at entry multiple (flat)" if flat_multiple
                     else f"Exit compressed by {compression_turns:.1f} turns"),
        base_moic=inputs.base_moic,
        shocked_moic=shocked_moic,
        moic_delta=shocked_moic - inputs.base_moic,
        passes=passes,
        partner_note=note,
    )


def stress_lever_slip(inputs: StressInputs, realization: float = 0.60) -> StressResult:
    """The lever program delivers only ``realization`` fraction of the
    modeled EBITDA lift. Default is 60% — conservative but typical."""
    if inputs.base_ebitda is None or inputs.lever_contribution is None:
        return StressResult(
            scenario="lever_slip",
            description=f"Levers deliver {realization*100:.0f}% of plan",
            partner_note="Cannot run — base EBITDA or lever contribution missing.",
        )
    lost = inputs.lever_contribution * (1.0 - realization)
    # Shocked is the target EBITDA minus the lost lever contribution.
    base_target = inputs.target_ebitda if inputs.target_ebitda else inputs.base_ebitda
    shocked = base_target - lost
    passes = shocked > inputs.base_ebitda  # still above today
    note = (
        "Even at reduced realization the deal adds EBITDA over today."
        if passes else
        "Reduced lever realization leaves exit EBITDA at or below entry. "
        "Thesis is fragile."
    )
    return StressResult(
        scenario="lever_slip",
        description=f"Lever realization at {realization*100:.0f}% of plan",
        base_ebitda=base_target,
        shocked_ebitda=shocked,
        ebitda_delta_pct=_delta_pct(base_target, shocked),
        passes=passes,
        partner_note=note,
    )


def stress_labor_shock(inputs: StressInputs, pct: float = 0.12) -> StressResult:
    """Agency / contract labor rate reset by ``pct``. The shock falls
    100% to EBITDA (labor is already expensed, there's no offset)."""
    if inputs.base_ebitda is None or inputs.contract_labor_spend is None:
        return StressResult(
            scenario="labor_shock",
            description=f"Agency labor +{pct*100:.0f}%",
            partner_note="Cannot run — base EBITDA or contract labor spend missing.",
        )
    shock_dollars = inputs.contract_labor_spend * pct
    shocked = inputs.base_ebitda - shock_dollars
    breach = _breach_covenant(shocked, inputs.debt_at_close, inputs.covenant_leverage)
    passes = shocked > 0 and (breach is False or breach is None)
    note = (
        "Labor shock absorbable at current spend level."
        if passes and (breach is False) else
        "Labor shock tips the deal — reduce agency dependency or re-size debt."
    )
    return StressResult(
        scenario="labor_shock",
        description=f"Agency labor +{pct*100:.0f}%",
        base_ebitda=inputs.base_ebitda,
        shocked_ebitda=shocked,
        ebitda_delta_pct=_delta_pct(inputs.base_ebitda, shocked),
        covenant_breach=breach,
        passes=passes,
        partner_note=note,
    )


# ── Orchestrator ─────────────────────────────────────────────────────

def run_partner_stresses(inputs: StressInputs) -> List[StressResult]:
    """Run the five standard partner stresses against a deal.

    Returns one :class:`StressResult` per scenario — even if the
    inputs don't support computation (the result will have a
    ``partner_note`` explaining why).
    """
    return [
        stress_rate_down(inputs, bps=200),
        stress_volume_down(inputs, pct=0.07),
        stress_multiple_compression(inputs, flat_multiple=True),
        stress_lever_slip(inputs, realization=0.60),
        stress_labor_shock(inputs, pct=0.12),
    ]


def worst_case_summary(results: List[StressResult]) -> Dict[str, Any]:
    """Summarize the worst-case result for the narrative layer."""
    breaches = [r for r in results if r.covenant_breach]
    fails = [r for r in results if r.passes is False]
    worst = None
    if fails:
        worst = min(fails, key=lambda r: (r.ebitda_delta_pct or 0.0))
    return {
        "scenarios_run": len(results),
        "n_breaches": len(breaches),
        "n_fails": len(fails),
        "worst_scenario": worst.scenario if worst else None,
        "worst_note": worst.partner_note if worst else "",
    }
