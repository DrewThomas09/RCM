"""Exit math — waterfall / preferred / carry calculations.

Partners at exit ask: "what does the equity waterfall look like, and
how much carry will we actually earn?" Standard US PE waterfall:

1. Return of capital (to all equity holders).
2. Preferred return (hurdle) to LP.
3. GP catch-up — 100% to GP until GP has 20% of total profit above hurdle.
4. 80/20 LP/GP split thereafter (or similar).

This module models that waterfall deterministically. It's not a
replacement for the LPA — it's a partner-tool answer to "given exit
EV of $X, what's my carry."

Functions:

- :func:`exit_waterfall` — return a breakdown of proceeds.
- :func:`moic_cagr_to_irr` — quick CAGR from MOIC + years.
- :func:`project_exit_ev` — exit EV = target EBITDA × exit multiple
  − net debt at exit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WaterfallResult:
    total_proceeds: float
    total_equity_in: float
    lp_equity_in: float
    gp_equity_in: float

    return_of_capital_lp: float
    return_of_capital_gp: float
    preferred_return: float
    gp_catch_up: float
    post_catch_up_lp: float
    post_catch_up_gp: float
    lp_total: float
    gp_total: float
    carry_earned: float
    lp_moic: float
    gp_moic: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_proceeds": self.total_proceeds,
            "total_equity_in": self.total_equity_in,
            "lp_equity_in": self.lp_equity_in,
            "gp_equity_in": self.gp_equity_in,
            "return_of_capital_lp": self.return_of_capital_lp,
            "return_of_capital_gp": self.return_of_capital_gp,
            "preferred_return": self.preferred_return,
            "gp_catch_up": self.gp_catch_up,
            "post_catch_up_lp": self.post_catch_up_lp,
            "post_catch_up_gp": self.post_catch_up_gp,
            "lp_total": self.lp_total,
            "gp_total": self.gp_total,
            "carry_earned": self.carry_earned,
            "lp_moic": self.lp_moic,
            "gp_moic": self.gp_moic,
        }


def project_exit_ev(
    exit_ebitda: float,
    exit_multiple: float,
    exit_net_debt: float,
    transaction_fees_pct: float = 0.015,
) -> Dict[str, float]:
    """Simple exit EV model: EV = EBITDA × multiple.

    Returns gross EV, equity at exit (EV − debt), and proceeds after
    ``transaction_fees_pct`` of EV in fees.
    """
    ev = exit_ebitda * exit_multiple
    fees = ev * transaction_fees_pct
    equity_gross = ev - exit_net_debt
    equity_after_fees = equity_gross - fees
    return {
        "exit_ev": ev,
        "exit_fees": fees,
        "equity_gross": equity_gross,
        "equity_after_fees": equity_after_fees,
    }


def exit_waterfall(
    *,
    total_proceeds: float,
    lp_equity_in: float,
    gp_equity_in: float,
    hold_years: float,
    preferred_return_rate: float = 0.08,
    gp_catch_up_pct: float = 1.0,
    carry_pct: float = 0.20,
) -> WaterfallResult:
    """Compute a standard 8% preferred / GP catch-up / 80-20 waterfall.

    All monetary inputs are in the same units (typically $). The LPA
    variant with GP catch-up at 100% (``gp_catch_up_pct=1.0``) means
    the GP takes 100% of profits above preferred until GP has earned
    20% of total profit; then the split reverts to 80/20 LP/GP.
    """
    total_equity = lp_equity_in + gp_equity_in
    if total_proceeds <= 0 or total_equity <= 0:
        return WaterfallResult(
            total_proceeds=total_proceeds, total_equity_in=total_equity,
            lp_equity_in=lp_equity_in, gp_equity_in=gp_equity_in,
            return_of_capital_lp=0, return_of_capital_gp=0,
            preferred_return=0, gp_catch_up=0,
            post_catch_up_lp=0, post_catch_up_gp=0,
            lp_total=0, gp_total=0, carry_earned=0,
            lp_moic=0, gp_moic=0,
        )
    remaining = total_proceeds

    # Stage 1: Return of capital
    roc_lp = min(lp_equity_in, remaining * (lp_equity_in / total_equity))
    roc_gp = min(gp_equity_in, remaining * (gp_equity_in / total_equity))
    # Scaled — if proceeds too low, pro-rate.
    if roc_lp + roc_gp > remaining:
        scale = remaining / (roc_lp + roc_gp)
        roc_lp *= scale
        roc_gp *= scale
    remaining -= roc_lp + roc_gp

    # Stage 2: Preferred return on LP capital only.
    pref = lp_equity_in * ((1 + preferred_return_rate) ** hold_years - 1)
    pref_actual = min(pref, remaining)
    remaining -= pref_actual

    # Stage 3: GP catch-up. Target: GP has earned ``carry_pct`` of total profit.
    # Profit so far (above return of capital): pref_actual (all to LP) + gp_catch_up
    # GP wants: carry_pct * (pref_actual + gp_catch_up)
    # GP has: 0 from stage 2, so solve:
    #   gp_catch_up = carry_pct * (pref_actual + gp_catch_up) / (1 - catch_up_pct + catch_up_pct)
    # For catch_up_pct == 1 (100% to GP):
    #   gp_catch_up = pref_actual * carry_pct / (1 - carry_pct)
    if gp_catch_up_pct >= 1.0:
        gp_catch_up_target = pref_actual * carry_pct / max(1e-9, 1 - carry_pct)
    else:
        # Partial catch-up: catch-up builds at catch_up_pct until GP reaches target.
        gp_catch_up_target = pref_actual * carry_pct / max(1e-9, gp_catch_up_pct - carry_pct)
    gp_catch_up_actual = min(gp_catch_up_target, remaining)
    remaining -= gp_catch_up_actual

    # Stage 4: 80/20 split of remaining.
    lp_split = remaining * (1 - carry_pct)
    gp_split = remaining * carry_pct

    lp_total = roc_lp + pref_actual + lp_split
    gp_total = roc_gp + gp_catch_up_actual + gp_split
    carry_earned = gp_catch_up_actual + gp_split

    lp_moic = lp_total / max(lp_equity_in, 1e-9)
    gp_moic = gp_total / max(gp_equity_in, 1e-9)

    return WaterfallResult(
        total_proceeds=total_proceeds,
        total_equity_in=total_equity,
        lp_equity_in=lp_equity_in,
        gp_equity_in=gp_equity_in,
        return_of_capital_lp=roc_lp,
        return_of_capital_gp=roc_gp,
        preferred_return=pref_actual,
        gp_catch_up=gp_catch_up_actual,
        post_catch_up_lp=lp_split,
        post_catch_up_gp=gp_split,
        lp_total=lp_total,
        gp_total=gp_total,
        carry_earned=carry_earned,
        lp_moic=lp_moic,
        gp_moic=gp_moic,
    )


def moic_cagr_to_irr(moic: float, years: float) -> Optional[float]:
    """Return implied CAGR (IRR approximation) from MOIC + hold years."""
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def required_exit_ebitda_for_moic(
    *,
    target_moic: float,
    equity_in: float,
    exit_multiple: float,
    exit_net_debt: float,
    transaction_fees_pct: float = 0.015,
) -> Optional[float]:
    """Reverse the exit math: what exit EBITDA is needed to hit a
    target equity MOIC?

    Useful for partner sensitivities: "what does EBITDA have to reach
    at exit for us to clear 2.5x?"

    Assumes equity_out = EV - fees - debt; EV = EBITDA × multiple.
    equity_out / equity_in = target_moic → solve for EBITDA.
    """
    if exit_multiple <= 0:
        return None
    # equity_out = EBITDA * multiple * (1 - fees_pct) - debt
    # target_moic * equity_in = EBITDA * multiple * (1 - fees_pct) - debt
    # EBITDA = (target_moic * equity_in + debt) / (multiple * (1 - fees_pct))
    denom = exit_multiple * (1 - transaction_fees_pct)
    if denom <= 0:
        return None
    return (target_moic * equity_in + exit_net_debt) / denom
