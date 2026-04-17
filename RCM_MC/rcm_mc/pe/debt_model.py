"""Debt trajectory projections for leveraged buyouts (Prompt 45).

Models a multi-tranche debt structure through a hold period, projecting
year-by-year balances with mandatory amortisation, optional excess-cash
sweeps, leverage ratios, and covenant compliance. PE sponsors use this
to size financing, stress-test covenants, and time refinancing windows.

Public API:
    project_debt_trajectory(debt, ebitda_trajectory)
        -> DebtTrajectory

Design principle: all math is deterministic and audit-friendly. Each
year's projection reconciles: ending_balance == beginning_balance
- mandatory_amort - cash_sweep. No stochastic elements — feed in
different EBITDA trajectories for scenario analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ── Data types ──────────────────────────────────────────────────────────


@dataclass
class DebtTranche:
    """A single layer in the capital structure.

    Parameters
    ----------
    name : str
        Human label (e.g., "Term Loan A", "Second Lien").
    principal : float
        Outstanding balance at close ($).
    rate : float
        Annual interest rate (decimal, e.g. 0.05 for 5%).
    amort_pct : float
        Annual mandatory amortisation as a fraction of *original*
        principal (e.g. 0.05 for 5%/yr). Set 0 for bullet.
    sweep_pct : float
        Fraction of excess free cash flow swept to repay this tranche
        (e.g. 0.50 for 50% ECF sweep). Applies in waterfall order.
    priority : int
        Repayment priority — lower is more senior (swept first).
    """
    name: str
    principal: float
    rate: float = 0.05
    amort_pct: float = 0.0
    sweep_pct: float = 0.0
    priority: int = 1


@dataclass
class DebtStructure:
    """Full debt package at close.

    Parameters
    ----------
    tranches : list[DebtTranche]
        All debt layers, ordered by priority (senior first).
    max_leverage : float
        Total debt / EBITDA covenant ceiling (e.g. 6.0x).
    min_coverage : float
        EBITDA / total interest floor (e.g. 2.0x).
    capex_pct : float
        Maintenance capex as % of EBITDA — subtracted before computing
        excess cash available for sweeps.
    tax_rate : float
        Effective tax rate applied to pre-tax income for cash-flow calc.
    """
    tranches: List[DebtTranche] = field(default_factory=list)
    max_leverage: float = 6.0
    min_coverage: float = 2.0
    capex_pct: float = 0.10
    tax_rate: float = 0.25


@dataclass
class YearProjection:
    """Single-year debt projection for the full structure."""
    year: int
    beginning_balance: float
    interest_expense: float
    mandatory_amort: float
    cash_sweep: float
    ending_balance: float
    ebitda: float
    leverage: float          # ending_balance / ebitda
    coverage: float          # ebitda / interest_expense
    covenant_ok: bool        # True if both leverage and coverage pass
    free_cash_flow: float    # post-interest, post-tax, post-capex
    tranche_details: List[dict] = field(default_factory=list)


@dataclass
class DebtTrajectory:
    """Full hold-period debt projection."""
    years: List[YearProjection] = field(default_factory=list)
    first_breach_year: Optional[int] = None
    entry_leverage: float = 0.0
    exit_leverage: float = 0.0
    total_debt_repaid: float = 0.0
    total_interest_paid: float = 0.0


# ── Validation ──────────────────────────────────────────────────────────


def _validate_inputs(debt: DebtStructure, ebitda_trajectory: List[float]) -> None:
    """Raise ValueError on bad inputs — fail fast, fail clearly."""
    if not debt.tranches:
        raise ValueError("debt structure must have at least one tranche")
    if not ebitda_trajectory:
        raise ValueError("ebitda_trajectory must have at least one year")
    for i, e in enumerate(ebitda_trajectory):
        if e <= 0:
            raise ValueError(
                f"ebitda_trajectory[{i}] must be positive (got {e})"
            )
    for t in debt.tranches:
        if t.principal < 0:
            raise ValueError(f"tranche '{t.name}' principal must be >= 0")
        if t.rate < 0:
            raise ValueError(f"tranche '{t.name}' rate must be >= 0")
        if not (0 <= t.amort_pct <= 1):
            raise ValueError(
                f"tranche '{t.name}' amort_pct must be in [0, 1]"
            )
        if not (0 <= t.sweep_pct <= 1):
            raise ValueError(
                f"tranche '{t.name}' sweep_pct must be in [0, 1]"
            )


# ── Projection engine ──────────────────────────────────────────────────


def _compute_year(
    year: int,
    balances: List[float],
    originals: List[float],
    debt: DebtStructure,
    ebitda: float,
) -> tuple:
    """Project one year and return (YearProjection, updated balances)."""
    tranches = debt.tranches
    new_balances = list(balances)
    tranche_details = []

    # Step 1: interest on beginning balances
    total_interest = 0.0
    for i, t in enumerate(tranches):
        interest_i = new_balances[i] * t.rate
        total_interest += interest_i

    # Step 2: mandatory amort (fraction of original principal, capped at
    # remaining balance)
    total_amort = 0.0
    for i, t in enumerate(tranches):
        amort_i = min(originals[i] * t.amort_pct, new_balances[i])
        new_balances[i] -= amort_i
        total_amort += amort_i

    # Step 3: free cash flow available for sweeps
    capex = ebitda * debt.capex_pct
    pre_tax_income = ebitda - total_interest - capex
    taxes = max(0.0, pre_tax_income * debt.tax_rate)
    fcf = pre_tax_income - taxes - total_amort
    free_cash = max(0.0, fcf)

    # Step 4: excess cash sweep — apply in priority order
    total_sweep = 0.0
    sorted_indices = sorted(range(len(tranches)),
                            key=lambda j: tranches[j].priority)
    remaining_cash = free_cash
    for idx in sorted_indices:
        t = tranches[idx]
        if t.sweep_pct <= 0 or remaining_cash <= 0 or new_balances[idx] <= 0:
            continue
        sweep_amount = min(remaining_cash * t.sweep_pct, new_balances[idx])
        new_balances[idx] -= sweep_amount
        total_sweep += sweep_amount
        remaining_cash -= sweep_amount

    # Build tranche details
    beginning_total = sum(balances)
    ending_total = sum(new_balances)
    for i, t in enumerate(tranches):
        tranche_details.append({
            "name": t.name,
            "beginning": balances[i],
            "ending": new_balances[i],
            "interest": balances[i] * t.rate,
        })

    # Ratios
    leverage = ending_total / ebitda if ebitda > 0 else float("inf")
    coverage = ebitda / total_interest if total_interest > 0 else float("inf")
    covenant_ok = (leverage <= debt.max_leverage
                   and coverage >= debt.min_coverage)

    proj = YearProjection(
        year=year,
        beginning_balance=beginning_total,
        interest_expense=total_interest,
        mandatory_amort=total_amort,
        cash_sweep=total_sweep,
        ending_balance=ending_total,
        ebitda=ebitda,
        leverage=round(leverage, 4),
        coverage=round(coverage, 4),
        covenant_ok=covenant_ok,
        free_cash_flow=round(free_cash, 2),
        tranche_details=tranche_details,
    )
    return proj, new_balances


def project_debt_trajectory(
    debt: DebtStructure,
    ebitda_trajectory: List[float],
) -> DebtTrajectory:
    """Project year-by-year debt paydown through the hold period.

    Parameters
    ----------
    debt : DebtStructure
        The closing debt package with tranches, covenants, and
        assumptions.
    ebitda_trajectory : list[float]
        Projected annual EBITDA for each year of the hold (Year 1
        is index 0). Length determines the projection horizon.

    Returns
    -------
    DebtTrajectory
        Full projection with per-year detail, first-breach detection,
        and summary statistics.
    """
    _validate_inputs(debt, ebitda_trajectory)

    balances = [t.principal for t in debt.tranches]
    originals = list(balances)
    entry_balance = sum(balances)
    entry_leverage = entry_balance / ebitda_trajectory[0]

    years: List[YearProjection] = []
    first_breach: Optional[int] = None
    total_interest = 0.0

    for yr_idx, ebitda in enumerate(ebitda_trajectory):
        proj, balances = _compute_year(
            year=yr_idx + 1, balances=balances, originals=originals,
            debt=debt, ebitda=ebitda,
        )
        years.append(proj)
        total_interest += proj.interest_expense
        if not proj.covenant_ok and first_breach is None:
            first_breach = proj.year

    exit_balance = sum(balances)
    exit_leverage = exit_balance / ebitda_trajectory[-1]

    return DebtTrajectory(
        years=years,
        first_breach_year=first_breach,
        entry_leverage=round(entry_leverage, 4),
        exit_leverage=round(exit_leverage, 4),
        total_debt_repaid=round(entry_balance - exit_balance, 2),
        total_interest_paid=round(total_interest, 2),
    )


# ── Convenience helpers ─────────────────────────────────────────────────


def quick_leverage_check(
    total_debt: float,
    ebitda: float,
    max_leverage: float = 6.0,
) -> dict:
    """One-shot leverage check — returns dict with ratio + pass/fail."""
    if ebitda <= 0:
        return {"leverage": float("inf"), "ok": False,
                "max_leverage": max_leverage}
    lev = total_debt / ebitda
    return {"leverage": round(lev, 4), "ok": lev <= max_leverage,
            "max_leverage": max_leverage}


def format_trajectory_summary(traj: DebtTrajectory) -> str:
    """Terminal-friendly summary of a debt trajectory."""
    lines = [
        f"Entry leverage: {traj.entry_leverage:.2f}x",
        f"Exit leverage:  {traj.exit_leverage:.2f}x",
        f"Total repaid:   ${traj.total_debt_repaid:,.0f}",
        f"Total interest: ${traj.total_interest_paid:,.0f}",
    ]
    if traj.first_breach_year is not None:
        lines.append(f"FIRST BREACH:   Year {traj.first_breach_year}")
    else:
        lines.append("Covenants:      All clear")
    lines.append("")
    lines.append(f"{'Year':>4}  {'Beg Bal':>12}  {'Amort':>10}  "
                 f"{'Sweep':>10}  {'End Bal':>12}  {'Lev':>6}  {'Cov':>6}  OK")
    for y in traj.years:
        lines.append(
            f"{y.year:>4}  {y.beginning_balance:>12,.0f}  "
            f"{y.mandatory_amort:>10,.0f}  {y.cash_sweep:>10,.0f}  "
            f"{y.ending_balance:>12,.0f}  {y.leverage:>6.2f}  "
            f"{y.coverage:>6.2f}  {'✓' if y.covenant_ok else '✗'}"
        )
    return "\n".join(lines)
