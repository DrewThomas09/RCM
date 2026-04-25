"""Orthogonal value-creation decomposition.

Bain-style additive attribution. Starting from entry equity and
ending at exit equity (plus interim distributions), decompose
the total value created into seven labeled components:

  1. Revenue growth — organic (same-store)
  2. Revenue growth — M&A (add-on contribution)
  3. Margin expansion (entry margin → exit margin)
  4. Multiple expansion (entry EV/EBITDA → exit EV/EBITDA)
  5. Leverage / debt paydown
  6. FX translation
  7. Dividend recap distributions
  8. Sub-line credit savings

Plus a residual "cross-terms" bucket for the multiplicative
interaction terms that don't have a clean linear attribution.
The cross-terms bucket should be a small fraction of total value
created — if it's >15%, that's a signal the underlying assumptions
have drift and the decomposition needs human review.

Math (all amounts in $M of EBITDA contribution × the entry
multiple, then cumulated up to total $M of value):

    Revenue contribution    = (Revenue_exit − Revenue_entry)
                            × entry_margin × entry_multiple
    Margin contribution    = entry_revenue
                            × (exit_margin − entry_margin)
                            × entry_multiple
    Multiple contribution  = entry_EBITDA × (exit_mult − entry_mult)
    Cross-terms            = total_EV_change − sum(above)
    Leverage contribution  = (debt_at_entry − debt_at_exit)
                            (debt amortization is value creation
                             since it's equity that didn't have to
                             be put in)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .components import (
    DealCashflows, AttributionComponents, AttributionResult,
)
from .irr import compute_irr, compute_moic


def _safe_div(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def decompose_value_creation(
    cashflows: DealCashflows,
) -> AttributionResult:
    """Compute the orthogonal attribution.

    Returns an AttributionResult with the components dataclass
    populated + the LP IRR + MOIC computed from the cashflow
    trail.
    """
    entry_revenue = cashflows.revenue_at_entry_mm
    exit_revenue = cashflows.revenue_at_exit_mm
    entry_margin = _safe_div(
        cashflows.ebitda_at_entry_mm, cashflows.revenue_at_entry_mm)
    exit_margin = _safe_div(
        cashflows.ebitda_at_exit_mm, cashflows.revenue_at_exit_mm)
    entry_multiple = _safe_div(
        cashflows.ev_at_entry_mm, cashflows.ebitda_at_entry_mm)
    exit_multiple = _safe_div(
        cashflows.ev_at_exit_mm, cashflows.ebitda_at_exit_mm)

    # Revenue split: M&A contribution + organic remainder
    addon = max(0.0, cashflows.addon_revenue_contribution_mm)
    delta_revenue = exit_revenue - entry_revenue
    organic_revenue = delta_revenue - addon

    revenue_contribution_organic = (
        organic_revenue * entry_margin * entry_multiple)
    revenue_contribution_ma = (
        addon * entry_margin * entry_multiple)

    # Margin contribution
    margin_contribution = (
        entry_revenue * (exit_margin - entry_margin) * entry_multiple)

    # Multiple expansion contribution
    multiple_contribution = (
        cashflows.ebitda_at_entry_mm
        * (exit_multiple - entry_multiple))

    # Leverage / debt paydown
    leverage_contribution = (
        cashflows.net_debt_at_entry_mm
        - cashflows.net_debt_at_exit_mm)

    # FX (use as-supplied; can be negative if USD strengthened)
    fx_contribution = cashflows.fx_translation_loss_mm

    # Dividend recap distributions before exit (any positive flow
    # before the final cashflow timestamp)
    div_recap = 0.0
    if cashflows.cashflows:
        # Sort by year; consider all positive flows except the
        # last one as recap distributions.
        sorted_cf = sorted(
            cashflows.cashflows, key=lambda c: c[0])
        for yr, amt in sorted_cf[:-1]:
            if amt > 0:
                div_recap += amt

    sub_line = cashflows.sub_line_credit_savings_mm

    # Total EV change (the "ground truth" we're decomposing)
    total_ev_change = cashflows.ev_at_exit_mm - cashflows.ev_at_entry_mm

    # Sum of the EBITDA-driven components
    ebitda_driven_sum = (
        revenue_contribution_organic
        + revenue_contribution_ma
        + margin_contribution
        + multiple_contribution
    )
    cross_terms = total_ev_change - ebitda_driven_sum

    # Total value created from LP perspective:
    #   ΔEV + leverage_paydown (equity not called)
    #   + dividend_recap (already received)
    #   + FX + sub_line
    total_value_created = (
        total_ev_change
        + leverage_contribution
        + fx_contribution
        + div_recap
        + sub_line
    )

    components = AttributionComponents(
        revenue_growth_organic_mm=round(revenue_contribution_organic, 2),
        revenue_growth_ma_mm=round(revenue_contribution_ma, 2),
        margin_expansion_mm=round(margin_contribution, 2),
        multiple_expansion_mm=round(multiple_contribution, 2),
        leverage_mm=round(leverage_contribution, 2),
        fx_mm=round(fx_contribution, 2),
        dividend_recap_mm=round(div_recap, 2),
        sub_line_credit_mm=round(sub_line, 2),
        cross_terms_mm=round(cross_terms, 2),
        total_value_created_mm=round(total_value_created, 2),
    )

    irr = compute_irr(cashflows.cashflows)
    moic = compute_moic(cashflows.cashflows)
    entry_equity = (cashflows.ev_at_entry_mm
                    - cashflows.net_debt_at_entry_mm)
    exit_equity = (cashflows.ev_at_exit_mm
                   - cashflows.net_debt_at_exit_mm)

    # Component shares (signed)
    denom = (abs(components.revenue_growth_organic_mm)
             + abs(components.revenue_growth_ma_mm)
             + abs(components.margin_expansion_mm)
             + abs(components.multiple_expansion_mm)
             + abs(components.leverage_mm)
             + abs(components.fx_mm)
             + abs(components.dividend_recap_mm)
             + abs(components.sub_line_credit_mm)
             + abs(components.cross_terms_mm)) or 1.0
    share = {
        "revenue_growth_organic": components.revenue_growth_organic_mm / denom,
        "revenue_growth_ma": components.revenue_growth_ma_mm / denom,
        "margin_expansion": components.margin_expansion_mm / denom,
        "multiple_expansion": components.multiple_expansion_mm / denom,
        "leverage": components.leverage_mm / denom,
        "fx": components.fx_mm / denom,
        "dividend_recap": components.dividend_recap_mm / denom,
        "sub_line_credit": components.sub_line_credit_mm / denom,
        "cross_terms": components.cross_terms_mm / denom,
    }
    share = {k: round(v, 4) for k, v in share.items()}

    return AttributionResult(
        deal_name=cashflows.deal_name,
        entry_equity_mm=round(entry_equity, 2),
        exit_equity_mm=round(exit_equity, 2),
        irr=round(irr, 4),
        moic=round(moic, 4),
        components=components,
        component_share=share,
    )
