"""Per-archetype valuation engines.

Each archetype has its own valuation logic:

  • strategic_corporate: private-comp multiple + revenue-synergy
    premium (strategics pay for revenue cross-sell).
  • secondary_pe: LBO model — assumes 50% leverage at close, 5-yr
    hold, target 2.5x MOIC.
  • sponsor_to_sponsor: secondary_pe + 0.25 turn relationship premium.
  • take_private: public-comp DCF + 25% control premium.
  • continuation_vehicle: NAV anchored — slight premium over
    secondary_pe to account for LP-side liquidity.
  • ipo: public-comp multiple × (1 − float discount).
  • dividend_recap: not an exit — quantifies leverage capacity at
    target-LBO ratios.
"""
from __future__ import annotations

from typing import List

from .target import ExitTarget, ExitArchetype, ArchetypeResult


def _ev_to_equity(ev: float, target: ExitTarget) -> float:
    return max(0.0, ev - target.net_debt_mm)


def simulate_strategic_exit(target: ExitTarget) -> ArchetypeResult:
    """Strategic buyer pays the private comp multiple plus a 1.5
    turn revenue-synergy premium when the asset has cross-sell
    angle (cash-pay, multi-payer, etc.)."""
    base = target.private_comp_multiple
    synergy_premium = 0.0
    drivers: List[str] = [
        f"Private-comp anchor: {base:.1f}x EBITDA"]
    # Cross-sell heuristic: more diversified payer mix → strategics pay up
    if target.payer_concentration < 0.5:
        synergy_premium += 1.0
        drivers.append("Diversified payer mix → +1.0 turn cross-sell")
    if target.cash_pay_share > 0.15:
        synergy_premium += 0.5
        drivers.append("Cash-pay >15% → +0.5 turn consumer angle")
    multiple = base + synergy_premium
    ev = multiple * target.ttm_ebitda_mm
    return ArchetypeResult(
        archetype=ExitArchetype.STRATEGIC,
        enterprise_value_mm=round(ev, 2),
        equity_value_mm=round(_ev_to_equity(ev, target), 2),
        implied_multiple=round(multiple, 2),
        valuation_method="private_comps_plus_synergy",
        drivers=drivers,
        confidence=0.65,
    )


def simulate_secondary_pe(target: ExitTarget) -> ArchetypeResult:
    """LBO-model valuation: target 2.5x MOIC over 5 years, 50% LTV
    at close, 8% blended cost of debt. Solves for entry EV."""
    # Forward EBITDA at exit (5y CAGR-applied)
    forward_ebitda = (target.ttm_ebitda_mm
                      * ((1.0 + target.growth_rate) ** 5))
    # Exit multiple — assume secondary PE exits at the same private
    # comp multiple (no expansion).
    exit_ev = forward_ebitda * target.private_comp_multiple
    # Solve entry EV: equity grows by 2.5×, debt amortizes 30% over hold
    target_moic = 2.5
    debt_at_close = 0.5  # 50% of EV at close
    debt_amortization = 0.30
    # Entry EV × (1 − debt_at_close) × moic + retained debt = exit equity
    # Simpler: entry_equity × moic + ending_debt = exit_equity_value
    # exit_equity_value = exit_ev − ending_debt
    entry_ev_solved = (exit_ev
                       / ((1.0 - debt_at_close) * target_moic
                          + debt_at_close * (1.0 - debt_amortization)))
    multiple = entry_ev_solved / max(0.1, target.ttm_ebitda_mm)
    return ArchetypeResult(
        archetype=ExitArchetype.SECONDARY_PE,
        enterprise_value_mm=round(entry_ev_solved, 2),
        equity_value_mm=round(_ev_to_equity(entry_ev_solved, target), 2),
        implied_multiple=round(multiple, 2),
        valuation_method="lbo_model_solved_for_entry",
        drivers=[
            f"5y forward EBITDA: ${forward_ebitda:.1f}M",
            f"Exit at {target.private_comp_multiple:.1f}x",
            f"50% LTV close, target 2.5x MOIC",
        ],
        confidence=0.75,
    )


def simulate_sponsor_to_sponsor(target: ExitTarget) -> ArchetypeResult:
    """Same as secondary_pe with a 0.25 turn relationship premium —
    sponsor-to-sponsor deals trade slightly above clean secondary
    auctions because the buyer trusts the seller's process."""
    base = simulate_secondary_pe(target)
    bumped_multiple = base.implied_multiple + 0.25
    ev = bumped_multiple * target.ttm_ebitda_mm
    return ArchetypeResult(
        archetype=ExitArchetype.SPONSOR_TO_SPONSOR,
        enterprise_value_mm=round(ev, 2),
        equity_value_mm=round(_ev_to_equity(ev, target), 2),
        implied_multiple=round(bumped_multiple, 2),
        valuation_method="lbo_plus_relationship_premium",
        drivers=base.drivers + [
            "+0.25 turn for known counterparty trust"],
        confidence=0.70,
    )


def simulate_take_private(target: ExitTarget) -> ArchetypeResult:
    """Public-comp DCF + 25% control premium. Only viable for
    assets with public comparables ≥ 12x EV/EBITDA."""
    if target.public_comp_multiple < 10:
        return ArchetypeResult(
            archetype=ExitArchetype.TAKE_PRIVATE,
            enterprise_value_mm=0.0, equity_value_mm=0.0,
            implied_multiple=0.0,
            valuation_method="not_viable",
            drivers=["Public comps too low for take-private"],
            confidence=0.30,
        )
    multiple = target.public_comp_multiple * 1.25
    ev = multiple * target.ttm_ebitda_mm
    return ArchetypeResult(
        archetype=ExitArchetype.TAKE_PRIVATE,
        enterprise_value_mm=round(ev, 2),
        equity_value_mm=round(_ev_to_equity(ev, target), 2),
        implied_multiple=round(multiple, 2),
        valuation_method="public_comp_plus_control_premium",
        drivers=[
            f"Public comp {target.public_comp_multiple:.1f}x",
            "+25% control premium",
        ],
        confidence=0.55,
    )


def simulate_continuation_vehicle(target: ExitTarget) -> ArchetypeResult:
    """Continuation vehicle anchors at NAV — typically 1.05–1.10×
    the secondary PE valuation due to the liquidity premium for
    LPs rolling forward."""
    sec = simulate_secondary_pe(target)
    multiple = sec.implied_multiple * 1.07
    ev = multiple * target.ttm_ebitda_mm
    return ArchetypeResult(
        archetype=ExitArchetype.CONTINUATION,
        enterprise_value_mm=round(ev, 2),
        equity_value_mm=round(_ev_to_equity(ev, target), 2),
        implied_multiple=round(multiple, 2),
        valuation_method="nav_anchored_with_liquidity_premium",
        drivers=sec.drivers + ["+7% NAV liquidity premium"],
        confidence=0.60,
    )


def simulate_ipo(target: ExitTarget) -> ArchetypeResult:
    """IPO at public-comp multiple minus a 15% float discount.
    Only viable when revenue >= $200M and growth durability is
    above the median."""
    viable = (target.ttm_revenue_mm >= 200
              and target.growth_durability_score >= 0.6)
    if not viable:
        return ArchetypeResult(
            archetype=ExitArchetype.IPO,
            enterprise_value_mm=0.0, equity_value_mm=0.0,
            implied_multiple=0.0,
            valuation_method="not_viable",
            drivers=[
                f"Revenue ${target.ttm_revenue_mm:.0f}M < $200M floor "
                f"or durability {target.growth_durability_score:.2f} "
                f"< 0.6 floor",
            ],
            confidence=0.40,
        )
    multiple = target.public_comp_multiple * 0.85
    ev = multiple * target.ttm_ebitda_mm
    return ArchetypeResult(
        archetype=ExitArchetype.IPO,
        enterprise_value_mm=round(ev, 2),
        equity_value_mm=round(_ev_to_equity(ev, target), 2),
        implied_multiple=round(multiple, 2),
        valuation_method="public_comp_minus_float_discount",
        drivers=[
            f"Public comp {target.public_comp_multiple:.1f}x",
            "−15% float discount on first-day pricing",
        ],
        confidence=0.50,
    )


def simulate_dividend_recap(target: ExitTarget) -> ArchetypeResult:
    """Not technically an exit — quantifies the leverage capacity
    at industry-standard 5.5× EBITDA total leverage."""
    target_lev = 5.5
    new_debt = target.ttm_ebitda_mm * target_lev
    distribution = max(0.0, new_debt - target.net_debt_mm)
    return ArchetypeResult(
        archetype=ExitArchetype.DIVIDEND_RECAP,
        enterprise_value_mm=0.0,
        equity_value_mm=round(distribution, 2),
        implied_multiple=target_lev,
        valuation_method="leverage_capacity_to_5_5x",
        drivers=[
            f"Target total lev: {target_lev:.1f}x EBITDA",
            f"New debt capacity: ${new_debt:.1f}M",
            f"Existing net debt: ${target.net_debt_mm:.1f}M",
            f"Distribution: ${distribution:.1f}M",
        ],
        confidence=0.80,
    )
