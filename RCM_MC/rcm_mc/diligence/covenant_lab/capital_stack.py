"""Capital-stack model for the Covenant Stress Lab.

A capital stack is a list of ``DebtTranche`` records, each of which
describes one instrument (revolver, senior TLB, unitranche, mezz,
seller note) with:

    * rate (floating with a SOFR + spread, or a fixed rate)
    * amortization schedule (percent of principal paid back per year)
    * bullet / cash-sweep behavior
    * interest-only period (months)
    * commitment fee on unused revolver capacity

The module provides:

    * ``build_debt_schedule(stack, rate_path, quarters)`` which
      produces per-quarter scheduled amortization, interest, and
      ending balance for every tranche.
    * ``total_debt_service(per_tranche_quarters)`` which rolls up
      to a single Σ interest + Σ principal + Σ commitment fee row
      consumed by the covenant evaluator.

Why the module exists: Deal MC already produces EBITDA bands, but
the stress lab needs the *other* side of the covenant equation —
what the target actually owes in cash debt service each quarter.
Partners care because a 7.2× leverage ratio headline hides
quarterly amortization cliffs and revolver draw dynamics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class TrancheKind(str, Enum):
    REVOLVER = "REVOLVER"
    TLA = "TLA"                  # Term Loan A — bank-style amort
    TLB = "TLB"                  # Term Loan B — 1% / 99% bullet
    UNITRANCHE = "UNITRANCHE"
    MEZZANINE = "MEZZANINE"
    SELLER_NOTE = "SELLER_NOTE"
    SUBORDINATED = "SUBORDINATED"


@dataclass(frozen=True)
class DebtTranche:
    """One instrument in the capital stack.

    ``principal_usd`` is the drawn balance at close.  For a revolver,
    it's the *commitment size* — drawn balance is tracked per-quarter
    by the schedule builder.

    ``rate_floating`` true means the tranche's rate = rate_path[q] +
    ``spread_bps``; false means flat ``fixed_rate``.

    ``amortization_schedule`` is a list of per-year amort percentages
    of the *original* principal; missing years default to zero.  For
    a TLB the classic pattern is ``[0.01] * (term_years - 1) +
    [1.0 - 0.01 * (term_years - 1)]`` (1 % / year + bullet).

    ``cash_sweep_pct`` applies excess cash flow to paydown — 0.50
    means 50 % of post-debt-service cash flow amortizes the tranche.
    """
    name: str
    kind: TrancheKind
    principal_usd: float
    term_years: int = 6
    spread_bps: float = 500.0                # 5.00 %
    fixed_rate: Optional[float] = None       # if set, used instead
    rate_floating: bool = True
    amortization_schedule: Tuple[float, ...] = ()
    interest_only_months: int = 0
    cash_sweep_pct: float = 0.0              # 0.5 = 50 % sweep
    commitment_fee_bps: float = 50.0         # on undrawn revolver
    initial_draw_pct: float = 0.0            # revolver draw at close
    lien_priority: int = 1                    # 1 = senior
    is_secured: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "principal_usd": self.principal_usd,
            "term_years": self.term_years,
            "spread_bps": self.spread_bps,
            "fixed_rate": self.fixed_rate,
            "rate_floating": self.rate_floating,
            "amortization_schedule":
                list(self.amortization_schedule),
            "interest_only_months": self.interest_only_months,
            "cash_sweep_pct": self.cash_sweep_pct,
            "commitment_fee_bps": self.commitment_fee_bps,
            "initial_draw_pct": self.initial_draw_pct,
            "lien_priority": self.lien_priority,
            "is_secured": self.is_secured,
        }


@dataclass
class CapitalStack:
    """A priority-ordered list of tranches, senior-first."""
    tranches: List[DebtTranche] = field(default_factory=list)

    @property
    def total_funded_usd(self) -> float:
        """Funded principal at close (excludes undrawn revolver
        capacity)."""
        total = 0.0
        for t in self.tranches:
            if t.kind == TrancheKind.REVOLVER:
                total += t.principal_usd * t.initial_draw_pct
            else:
                total += t.principal_usd
        return total

    @property
    def total_committed_usd(self) -> float:
        return sum(t.principal_usd for t in self.tranches)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tranches": [t.to_dict() for t in self.tranches],
            "total_funded_usd": self.total_funded_usd,
            "total_committed_usd": self.total_committed_usd,
        }


# ────────────────────────────────────────────────────────────────────
# Schedule builder
# ────────────────────────────────────────────────────────────────────

@dataclass
class TrancheQuarter:
    """One quarter of scheduled debt-service for one tranche."""
    tranche_name: str
    quarter_idx: int                 # 0-indexed quarter from close
    year: int
    quarter_in_year: int             # 1-4
    beginning_balance: float
    scheduled_amortization: float
    interest_expense: float
    commitment_fee: float
    ending_balance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tranche_name": self.tranche_name,
            "quarter_idx": self.quarter_idx,
            "year": self.year,
            "quarter_in_year": self.quarter_in_year,
            "beginning_balance": self.beginning_balance,
            "scheduled_amortization": self.scheduled_amortization,
            "interest_expense": self.interest_expense,
            "commitment_fee": self.commitment_fee,
            "ending_balance": self.ending_balance,
        }


@dataclass
class QuarterlyDebtService:
    """Roll-up of all tranches in one quarter."""
    quarter_idx: int
    year: int
    quarter_in_year: int
    total_interest: float
    total_scheduled_amort: float
    total_commitment_fee: float
    total_debt_balance: float
    senior_debt_balance: float       # lien_priority == 1 subset
    per_tranche: List[TrancheQuarter] = field(default_factory=list)

    @property
    def total_debt_service(self) -> float:
        return (
            self.total_interest
            + self.total_scheduled_amort
            + self.total_commitment_fee
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarter_idx": self.quarter_idx,
            "year": self.year,
            "quarter_in_year": self.quarter_in_year,
            "total_interest": self.total_interest,
            "total_scheduled_amort": self.total_scheduled_amort,
            "total_commitment_fee": self.total_commitment_fee,
            "total_debt_balance": self.total_debt_balance,
            "senior_debt_balance": self.senior_debt_balance,
            "total_debt_service": self.total_debt_service,
            "per_tranche":
                [t.to_dict() for t in self.per_tranche],
        }


def _effective_rate(
    tranche: DebtTranche,
    base_rate: float,
) -> float:
    """Resolve the effective annual rate for a tranche given a
    base (SOFR/LIBOR-proxy) for the quarter.  The base rate is
    annualized and applied on a simple-interest basis over the
    quarter — a reasonable approximation for PE debt underwriting.
    """
    if not tranche.rate_floating and tranche.fixed_rate is not None:
        return float(tranche.fixed_rate)
    return float(base_rate) + (tranche.spread_bps / 10_000.0)


def _quarterly_amort_fraction(
    tranche: DebtTranche,
    year_idx: int,
) -> float:
    """Fraction of the tranche's *original* principal amortized in
    the current quarter, drawn from the per-year schedule spread
    evenly across the four quarters of that year."""
    if year_idx >= len(tranche.amortization_schedule):
        return 0.0
    return tranche.amortization_schedule[year_idx] / 4.0


def build_debt_schedule(
    stack: CapitalStack,
    rate_path_annual: Sequence[float],
    quarters: int = 20,
) -> List[QuarterlyDebtService]:
    """Compute a quarter-by-quarter debt-service schedule for every
    tranche in the stack over ``quarters`` quarters.

    ``rate_path_annual`` is a per-quarter base rate (annualized
    SOFR/LIBOR-proxy).  If shorter than ``quarters`` the last value
    is carried forward.  This deliberately matches how PE desks
    underwrite floating-rate facilities against a forward curve.
    """
    if not stack.tranches:
        return []

    # Normalize rate path
    rate_path = list(rate_path_annual) or [0.05]
    while len(rate_path) < quarters:
        rate_path.append(rate_path[-1])

    # Per-tranche running balance
    running: Dict[str, float] = {}
    for t in stack.tranches:
        if t.kind == TrancheKind.REVOLVER:
            running[t.name] = t.principal_usd * t.initial_draw_pct
        else:
            running[t.name] = t.principal_usd

    out: List[QuarterlyDebtService] = []
    for q in range(quarters):
        year_idx = q // 4
        quarter_in_year = q % 4 + 1
        base = rate_path[q]
        per: List[TrancheQuarter] = []
        senior_bal = 0.0
        for t in stack.tranches:
            beg = running[t.name]
            # Interest on beginning balance
            rate = _effective_rate(t, base)
            interest = beg * (rate / 4.0)
            # Scheduled amortization
            io_quarters = t.interest_only_months // 3
            if q < io_quarters:
                amort = 0.0
            elif t.kind == TrancheKind.REVOLVER:
                # Revolvers don't amortize on a schedule
                amort = 0.0
            else:
                frac = _quarterly_amort_fraction(t, year_idx)
                amort = min(beg, t.principal_usd * frac)
            # Commitment fee on undrawn revolver
            if t.kind == TrancheKind.REVOLVER:
                undrawn = max(0.0, t.principal_usd - beg)
                comm_fee = undrawn * (t.commitment_fee_bps / 10_000.0) / 4.0
            else:
                comm_fee = 0.0
            end = max(0.0, beg - amort)
            running[t.name] = end
            per.append(TrancheQuarter(
                tranche_name=t.name,
                quarter_idx=q,
                year=year_idx + 1,
                quarter_in_year=quarter_in_year,
                beginning_balance=beg,
                scheduled_amortization=amort,
                interest_expense=interest,
                commitment_fee=comm_fee,
                ending_balance=end,
            ))
            if t.lien_priority == 1:
                senior_bal += end
        out.append(QuarterlyDebtService(
            quarter_idx=q,
            year=year_idx + 1,
            quarter_in_year=quarter_in_year,
            total_interest=sum(p.interest_expense for p in per),
            total_scheduled_amort=sum(
                p.scheduled_amortization for p in per
            ),
            total_commitment_fee=sum(p.commitment_fee for p in per),
            total_debt_balance=sum(p.ending_balance for p in per),
            senior_debt_balance=senior_bal,
            per_tranche=per,
        ))
    return out


# ────────────────────────────────────────────────────────────────────
# Default stack helper — for PE LBO underwriting
# ────────────────────────────────────────────────────────────────────

def default_lbo_stack(
    total_debt_usd: float,
    *,
    revolver_usd: float = 0.0,
    revolver_draw_pct: float = 0.0,
    tlb_share: float = 0.65,
    unitranche_share: float = 0.25,
    mezz_share: float = 0.10,
    term_years: int = 6,
    senior_spread_bps: float = 450.0,
    mezz_spread_bps: float = 950.0,
) -> CapitalStack:
    """Assemble a conventional LBO capital stack."""
    tranches: List[DebtTranche] = []
    if revolver_usd > 0:
        tranches.append(DebtTranche(
            name="Revolver",
            kind=TrancheKind.REVOLVER,
            principal_usd=revolver_usd,
            term_years=term_years,
            spread_bps=senior_spread_bps - 50.0,
            commitment_fee_bps=50.0,
            initial_draw_pct=revolver_draw_pct,
            lien_priority=1,
        ))
    # Amort schedule for a 6-year TLB: 1 % / year for 5 years, bullet
    tlb_amort = (
        tuple([0.01] * max(term_years - 1, 0))
        + (max(0.0, 1.0 - 0.01 * max(term_years - 1, 0)),)
    )
    if tlb_share > 0:
        tranches.append(DebtTranche(
            name="TLB",
            kind=TrancheKind.TLB,
            principal_usd=total_debt_usd * tlb_share,
            term_years=term_years,
            spread_bps=senior_spread_bps,
            amortization_schedule=tlb_amort,
            lien_priority=1,
        ))
    if unitranche_share > 0:
        tranches.append(DebtTranche(
            name="Unitranche",
            kind=TrancheKind.UNITRANCHE,
            principal_usd=total_debt_usd * unitranche_share,
            term_years=term_years,
            spread_bps=senior_spread_bps + 150.0,
            amortization_schedule=tlb_amort,
            lien_priority=1,
        ))
    if mezz_share > 0:
        # Mezz is bullet + PIK, but for covenant-lab purposes we
        # model it as interest-only for the full term + bullet in
        # the final year.
        mezz_amort = tuple([0.0] * (term_years - 1) + [1.0])
        tranches.append(DebtTranche(
            name="Mezzanine",
            kind=TrancheKind.MEZZANINE,
            principal_usd=total_debt_usd * mezz_share,
            term_years=term_years,
            spread_bps=mezz_spread_bps,
            amortization_schedule=mezz_amort,
            lien_priority=2,
            is_secured=False,
        ))
    return CapitalStack(tranches=tranches)
