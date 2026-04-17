"""PE fund waterfall distribution engine (Prompt 46).

Implements a standard American 4-tier GP/LP waterfall:

    Tier 1 — Return of Capital: LPs get back their contributed capital.
    Tier 2 — Preferred Return: LPs receive a preferred return (hurdle)
             on their contributed capital (default 8% IRR).
    Tier 3 — GP Catch-up: GP receives distributions until they have
             received their carry share of all profits so far (default
             80/20 split to GP during catch-up).
    Tier 4 — Carried Interest: Remaining distributions split between
             GP carry (default 20%) and LP (80%).

Management fees are deducted from LP commitments before computing
returns. The model is deal-level (not fund-level) for diligence use
cases — sponsors run this per-deal to show LPs expected economics.

Public API:
    compute_waterfall(waterfall, deal_returns)
        -> WaterfallResult
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


# ── Data types ──────────────────────────────────────────────────────────


@dataclass
class WaterfallStructure:
    """Fund waterfall terms.

    All rates are annualised decimals. The catch-up split determines how
    aggressively the GP catches up after the preferred return — 100%
    means all distributions go to GP until caught up (a "full catch-up"),
    80% is a common partial catch-up.
    """
    preferred_return: float = 0.08      # 8% annual hurdle
    catch_up_pct: float = 0.80          # GP gets 80% during catch-up
    carry_pct: float = 0.20             # 20% carried interest
    mgmt_fee_pct: float = 0.02          # 2% annual management fee
    gp_commit_pct: float = 0.02         # GP co-invest (2% of fund)


@dataclass
class DealReturn:
    """Cash flows for a single deal from the LP's perspective.

    Parameters
    ----------
    invested : float
        Total capital invested at entry ($).
    exit_proceeds : float
        Total cash returned at exit ($), including any interim
        distributions.
    hold_years : float
        Holding period in years (supports fractional).
    interim_distributions : list[float]
        Any cash returned *before* exit (dividends, recaps). Each
        entry is a distribution amount at year-end (index 0 = year 1).
    """
    invested: float
    exit_proceeds: float
    hold_years: float
    interim_distributions: List[float] = field(default_factory=list)


@dataclass
class TierAllocation:
    """How much LP and GP receive in each waterfall tier."""
    tier: str
    lp_amount: float
    gp_amount: float
    description: str = ""


@dataclass
class WaterfallResult:
    """Complete waterfall computation result."""
    # Inputs echoed
    invested: float
    exit_proceeds: float
    hold_years: float
    mgmt_fees_total: float

    # Net amounts after fees
    net_invested: float       # invested less GP commit portion
    total_distributable: float

    # Tier breakdown
    tiers: List[TierAllocation] = field(default_factory=list)

    # Summary
    lp_total: float = 0.0
    gp_total: float = 0.0
    lp_moic: float = 0.0
    gp_moic: float = 0.0
    lp_irr: float = 0.0
    gross_moic: float = 0.0
    gross_irr: float = 0.0


# ── Validation ──────────────────────────────────────────────────────────


def _validate(wf: WaterfallStructure, dr: DealReturn) -> None:
    if dr.invested <= 0:
        raise ValueError(f"invested must be positive (got {dr.invested})")
    if dr.exit_proceeds < 0:
        raise ValueError("exit_proceeds cannot be negative")
    if dr.hold_years <= 0:
        raise ValueError(f"hold_years must be positive (got {dr.hold_years})")
    if not (0 <= wf.preferred_return <= 1):
        raise ValueError("preferred_return must be in [0, 1]")
    if not (0 <= wf.carry_pct <= 1):
        raise ValueError("carry_pct must be in [0, 1]")
    if not (0 <= wf.catch_up_pct <= 1):
        raise ValueError("catch_up_pct must be in [0, 1]")
    if not (0 <= wf.mgmt_fee_pct <= 0.10):
        raise ValueError("mgmt_fee_pct must be in [0, 0.10]")


# ── IRR solver ──────────────────────────────────────────────────────────


def _compute_irr(
    invested: float,
    proceeds: float,
    hold_years: float,
    interim: Optional[List[float]] = None,
) -> float:
    """Simple IRR via Newton's method on the NPV equation.

    For a single entry/exit with optional interim distributions, this is
    more robust than scipy and avoids the dependency. Falls back to 0.0
    if convergence fails (total loss scenarios).
    """
    if invested <= 0 or hold_years <= 0:
        return 0.0

    # Build cash flow vector: [-invested, interim..., proceeds]
    n_years = max(int(math.ceil(hold_years)), 1)
    cf = [0.0] * (n_years + 1)
    cf[0] = -invested
    if interim:
        for i, d in enumerate(interim):
            if i + 1 < len(cf):
                cf[i + 1] += d
    # Put exit proceeds at the hold_years point (may be fractional)
    # For simplicity, put it at the last index
    cf[-1] += proceeds

    # Newton's method
    r = 0.10  # initial guess
    for _ in range(200):
        npv = 0.0
        dnpv = 0.0
        for t, c in enumerate(cf):
            disc = (1 + r) ** t
            if disc == 0:
                break
            npv += c / disc
            if t > 0:
                dnpv -= t * c / ((1 + r) ** (t + 1))
        if abs(dnpv) < 1e-14:
            break
        step = npv / dnpv
        r -= step
        # Clamp to avoid divergence
        r = max(r, -0.99)
        if abs(step) < 1e-10:
            break

    # Sanity: if IRR is absurd, return simple annualised return
    if r < -0.99 or r > 10.0 or math.isnan(r):
        moic = proceeds / invested if invested > 0 else 0
        if moic <= 0:
            return -1.0
        return moic ** (1.0 / hold_years) - 1.0

    return r


# ── Core waterfall engine ───────────────────────────────────────────────


def compute_waterfall(
    waterfall: WaterfallStructure,
    deal_returns: DealReturn,
) -> WaterfallResult:
    """Compute the 4-tier American waterfall distribution.

    Parameters
    ----------
    waterfall : WaterfallStructure
        Fund terms (hurdle, catch-up, carry, fees).
    deal_returns : DealReturn
        Deal-level cash flows.

    Returns
    -------
    WaterfallResult
        Full tier breakdown with LP/GP splits and net returns.
    """
    _validate(waterfall, deal_returns)

    invested = deal_returns.invested
    proceeds = deal_returns.exit_proceeds
    hold_years = deal_returns.hold_years
    interim = deal_returns.interim_distributions

    # Management fees reduce LP returns (charged on committed capital)
    mgmt_fees = invested * waterfall.mgmt_fee_pct * hold_years

    # GP co-invest
    gp_invest = invested * waterfall.gp_commit_pct
    lp_invest = invested - gp_invest

    # Total cash available for distribution (proceeds + interim)
    total_interim = sum(interim) if interim else 0.0
    total_cash = proceeds + total_interim

    # Gross metrics (before waterfall)
    gross_moic = total_cash / invested if invested > 0 else 0.0
    gross_irr = _compute_irr(invested, proceeds, hold_years, interim)

    # Net distributable to LPs (after mgmt fees)
    lp_distributable = total_cash * (lp_invest / invested) - mgmt_fees
    gp_distributable = total_cash * (gp_invest / invested) if gp_invest > 0 else 0.0

    tiers: List[TierAllocation] = []
    lp_distributed = 0.0
    gp_distributed = 0.0
    remaining = max(0.0, lp_distributable)

    # ── Tier 1: Return of Capital ──────────────────────────────
    roc = min(remaining, lp_invest)
    tiers.append(TierAllocation(
        tier="Return of Capital",
        lp_amount=roc,
        gp_amount=0.0,
        description="LP capital returned before any profit split",
    ))
    lp_distributed += roc
    remaining -= roc

    # ── Tier 2: Preferred Return ──────────────────────────────
    # Compound preferred return on LP capital
    pref_amount = lp_invest * ((1 + waterfall.preferred_return) ** hold_years - 1)
    pref_paid = min(remaining, pref_amount)
    tiers.append(TierAllocation(
        tier="Preferred Return",
        lp_amount=pref_paid,
        gp_amount=0.0,
        description=f"{waterfall.preferred_return:.0%} compounded hurdle",
    ))
    lp_distributed += pref_paid
    remaining -= pref_paid

    # ── Tier 3: GP Catch-up ───────────────────────────────────
    # GP catches up to their carry share of total profit distributed so far
    # After Tier 2, total profit to LP = pref_paid
    # GP needs carry_pct / (1 - carry_pct) * total_lp_profit to be "caught up"
    if waterfall.carry_pct > 0 and remaining > 0:
        # GP target: carry_pct of total profits (pref + catch-up)
        # If catch-up is 80%: GP gets 80% of distributions in this tier
        # until GP has carry_pct of all cumulative profits.
        target_gp = (waterfall.carry_pct / (1 - waterfall.carry_pct)) * pref_paid
        catch_up_total = target_gp / waterfall.catch_up_pct if waterfall.catch_up_pct > 0 else 0
        catch_up_total = min(catch_up_total, remaining)
        gp_catch = catch_up_total * waterfall.catch_up_pct
        lp_catch = catch_up_total - gp_catch
    else:
        gp_catch = 0.0
        lp_catch = 0.0
        catch_up_total = 0.0

    tiers.append(TierAllocation(
        tier="GP Catch-up",
        lp_amount=lp_catch,
        gp_amount=gp_catch,
        description=f"{waterfall.catch_up_pct:.0%} to GP until caught up",
    ))
    lp_distributed += lp_catch
    gp_distributed += gp_catch
    remaining -= catch_up_total

    # ── Tier 4: Carried Interest ──────────────────────────────
    if remaining > 0:
        gp_carry = remaining * waterfall.carry_pct
        lp_carry = remaining * (1 - waterfall.carry_pct)
    else:
        gp_carry = 0.0
        lp_carry = 0.0

    tiers.append(TierAllocation(
        tier="Carried Interest",
        lp_amount=lp_carry,
        gp_amount=gp_carry,
        description=f"{waterfall.carry_pct:.0%} GP / {1 - waterfall.carry_pct:.0%} LP split",
    ))
    lp_distributed += lp_carry
    gp_distributed += gp_carry

    # Add GP co-invest return
    gp_distributed += gp_distributable

    # LP net metrics
    lp_moic = lp_distributed / lp_invest if lp_invest > 0 else 0.0
    gp_moic = gp_distributed / gp_invest if gp_invest > 0 else 0.0
    lp_irr = _compute_irr(lp_invest, lp_distributed, hold_years)

    return WaterfallResult(
        invested=invested,
        exit_proceeds=proceeds,
        hold_years=hold_years,
        mgmt_fees_total=round(mgmt_fees, 2),
        net_invested=round(lp_invest, 2),
        total_distributable=round(total_cash, 2),
        tiers=tiers,
        lp_total=round(lp_distributed, 2),
        gp_total=round(gp_distributed, 2),
        lp_moic=round(lp_moic, 4),
        gp_moic=round(gp_moic, 4),
        lp_irr=round(lp_irr, 4),
        gross_moic=round(gross_moic, 4),
        gross_irr=round(gross_irr, 4),
    )


# ── Convenience helpers ─────────────────────────────────────────────────


def quick_lp_economics(
    invested: float,
    exit_proceeds: float,
    hold_years: float,
    *,
    preferred_return: float = 0.08,
    carry_pct: float = 0.20,
    mgmt_fee_pct: float = 0.02,
) -> dict:
    """One-liner LP economics summary for quick screening."""
    wf = WaterfallStructure(
        preferred_return=preferred_return,
        carry_pct=carry_pct,
        mgmt_fee_pct=mgmt_fee_pct,
    )
    dr = DealReturn(invested=invested, exit_proceeds=exit_proceeds,
                    hold_years=hold_years)
    result = compute_waterfall(wf, dr)
    return {
        "lp_moic": result.lp_moic,
        "lp_irr": result.lp_irr,
        "gross_moic": result.gross_moic,
        "gross_irr": result.gross_irr,
        "mgmt_fees": result.mgmt_fees_total,
        "gp_total": result.gp_total,
        "lp_total": result.lp_total,
    }


def format_waterfall_summary(result: WaterfallResult) -> str:
    """Terminal-friendly waterfall display."""
    lines = [
        f"Invested:     ${result.invested:,.0f}",
        f"Proceeds:     ${result.exit_proceeds:,.0f}",
        f"Hold:         {result.hold_years:.1f} years",
        f"Mgmt Fees:    ${result.mgmt_fees_total:,.0f}",
        "",
        f"{'Tier':<25} {'LP':>12} {'GP':>12}",
        "-" * 51,
    ]
    for t in result.tiers:
        lines.append(
            f"{t.tier:<25} ${t.lp_amount:>11,.0f} ${t.gp_amount:>11,.0f}"
        )
    lines.append("-" * 51)
    lines.append(
        f"{'Total':<25} ${result.lp_total:>11,.0f} ${result.gp_total:>11,.0f}"
    )
    lines.append("")
    lines.append(f"Gross MOIC: {result.gross_moic:.2f}x  |  "
                 f"Gross IRR: {result.gross_irr:.1%}")
    lines.append(f"LP MOIC:    {result.lp_moic:.2f}x  |  "
                 f"LP IRR:    {result.lp_irr:.1%}")
    return "\n".join(lines)
