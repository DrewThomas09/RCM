"""Leverage structure analysis for hospital M&A deals.

Models debt capacity, coverage ratios, covenant headroom, and amortisation
schedules for a deal given entry assumptions.  Designed for PE diligence:
"Can this capital structure survive a Medicare rate cut year-two?"

Key concepts:
    - Entry leverage: Total Debt / EBITDA at close
    - Interest coverage: EBITDA / Interest Expense
    - Fixed-charge coverage: (EBITDA - CapEx) / (Interest + Required Amort)
    - Covenant headroom: distance from current ratio to covenant trigger
    - Debt capacity: max debt sustainable at a given coverage floor

Default assumptions (can be overridden per-deal):
    - Interest rate: 7.5% (average HY + TL spread, 2023-2024 env)
    - Required amort: 1% / year of original term loan principal
    - CapEx: 4.5% of revenue (typical hospital maintenance CapEx)
    - Revenue = EBITDA / 0.10 (assumes 10% EBITDA margin if not provided)
    - EBITDA growth: 3% / year (conservative organic)
    - Covenant trigger: Net Leverage > 6.5x (typical TL covenant)

Public API:
    LeverageProfile  dataclass
    DebtScenario     dataclass
    model_leverage(deal, assumptions)       -> LeverageProfile
    debt_capacity(ebitda_mm, assumptions)   -> float  (max debt $M)
    coverage_ratio(ebitda, interest, capex, amort) -> dict
    covenant_headroom(profile)              -> dict
    stress_leverage(profile, ebitda_shock)  -> LeverageProfile
    leverage_table(profile)                 -> str  (ASCII)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULTS: Dict[str, float] = {
    "interest_rate":         0.075,   # 7.5% blended
    "required_amort_pct":    0.010,   # 1% / yr on TL principal
    "capex_pct_revenue":     0.045,   # 4.5% revenue
    "ebitda_margin":         0.100,   # 10% — used to back-calculate revenue
    "ebitda_growth_annual":  0.030,   # 3% organic
    "covenant_leverage_max": 6.50,    # Net Debt / EBITDA trigger
    "equity_pct":            0.40,    # 40% equity / 60% debt default
    "hold_years":            5.0,
    "exit_multiple":         8.0,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AnnualDebtMetrics:
    year: int                          # 0 = entry, 1 = year 1, …
    ebitda: float
    revenue: float
    debt_balance: float
    interest_expense: float
    required_amort: float
    capex: float
    interest_coverage: float           # EBITDA / Interest
    fixed_charge_coverage: float       # (EBITDA - CapEx) / (Int + Amort)
    net_leverage: float                # Debt / EBITDA
    covenant_headroom_turns: float     # covenant_max - net_leverage

    def as_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "ebitda_mm": round(self.ebitda, 2),
            "revenue_mm": round(self.revenue, 2),
            "debt_balance_mm": round(self.debt_balance, 2),
            "interest_expense_mm": round(self.interest_expense, 2),
            "required_amort_mm": round(self.required_amort, 2),
            "capex_mm": round(self.capex, 2),
            "interest_coverage": round(self.interest_coverage, 2),
            "fixed_charge_coverage": round(self.fixed_charge_coverage, 2),
            "net_leverage": round(self.net_leverage, 2),
            "covenant_headroom_turns": round(self.covenant_headroom_turns, 2),
        }


@dataclass
class LeverageProfile:
    deal_name: str
    entry_ev_mm: float
    entry_ebitda_mm: float
    entry_debt_mm: float
    equity_mm: float
    entry_leverage: float               # Entry Debt / EBITDA
    entry_interest_coverage: float
    entry_fixed_charge_coverage: float
    assumptions: Dict[str, float]
    annual_metrics: List[AnnualDebtMetrics] = field(default_factory=list)
    covenant_at_risk: bool = False      # True if leverage ever breaches covenant
    covenant_breach_year: Optional[int] = None
    min_coverage_year: Optional[int] = None   # year of worst interest coverage
    min_coverage_ratio: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "entry_ev_mm": self.entry_ev_mm,
            "entry_ebitda_mm": self.entry_ebitda_mm,
            "entry_debt_mm": self.entry_debt_mm,
            "equity_mm": self.equity_mm,
            "entry_leverage": round(self.entry_leverage, 2),
            "entry_interest_coverage": round(self.entry_interest_coverage, 2),
            "entry_fixed_charge_coverage": round(self.entry_fixed_charge_coverage, 2),
            "covenant_at_risk": self.covenant_at_risk,
            "covenant_breach_year": self.covenant_breach_year,
            "min_coverage_year": self.min_coverage_year,
            "min_coverage_ratio": round(self.min_coverage_ratio, 2) if self.min_coverage_ratio else None,
            "annual_metrics": [m.as_dict() for m in self.annual_metrics],
            "assumptions": {k: round(v, 4) for k, v in self.assumptions.items()},
        }


# ---------------------------------------------------------------------------
# Core modelling
# ---------------------------------------------------------------------------

def _resolve_assumptions(overrides: Optional[Dict[str, float]]) -> Dict[str, float]:
    assumptions = dict(_DEFAULTS)
    if overrides:
        assumptions.update(overrides)
    return assumptions


def model_leverage(
    deal: Dict[str, Any],
    assumptions: Optional[Dict[str, float]] = None,
) -> LeverageProfile:
    """Model the leverage profile of a deal over the hold period.

    Args:
        deal:        deal dict (needs ev_mm, ebitda_at_entry_mm at minimum)
        assumptions: override any default assumption (see _DEFAULTS)

    Returns:
        LeverageProfile with annual debt metrics for each year 0 → hold_years.
    """
    a = _resolve_assumptions(assumptions)

    ev = float(deal.get("ev_mm") or 0)
    ebitda = float(deal.get("ebitda_at_entry_mm") or 0)
    hold = float(deal.get("hold_years") or a["hold_years"])

    if ev <= 0:
        raise ValueError("ev_mm must be positive")
    if ebitda <= 0:
        raise ValueError("ebitda_at_entry_mm must be positive")

    # Debt structure
    entry_debt = a.get("entry_debt_mm") or ev * (1 - a["equity_pct"])
    equity = ev - entry_debt
    interest_rate = a["interest_rate"]
    amort_pct = a["required_amort_pct"]
    capex_pct = a["capex_pct_revenue"]
    margin = a["ebitda_margin"]
    growth = a["ebitda_growth_annual"]
    cov_max = a["covenant_leverage_max"]

    # Revenue implied if not supplied
    revenue_entry = float(deal.get("revenue_mm") or ebitda / margin)

    # Entry metrics
    entry_interest = entry_debt * interest_rate
    entry_amort = entry_debt * amort_pct
    entry_capex = revenue_entry * capex_pct
    entry_leverage = entry_debt / ebitda
    entry_ic = ebitda / entry_interest if entry_interest > 0 else 999.0
    entry_fc_numer = ebitda - entry_capex
    entry_fc_denom = entry_interest + entry_amort
    entry_fcc = entry_fc_numer / entry_fc_denom if entry_fc_denom > 0 else 999.0

    # Annual projection
    annual: List[AnnualDebtMetrics] = []
    debt = entry_debt
    cur_ebitda = ebitda
    cur_revenue = revenue_entry
    covenant_at_risk = False
    covenant_breach_year: Optional[int] = None
    min_ic = entry_ic
    min_ic_year = 0

    for yr in range(int(hold) + 1):
        if yr > 0:
            cur_ebitda *= (1 + growth)
            cur_revenue *= (1 + growth)
            amort_payment = entry_debt * amort_pct      # % of original principal
            debt = max(0.0, debt - amort_payment)

        interest = debt * interest_rate
        amort = entry_debt * amort_pct
        capex = cur_revenue * capex_pct
        ic = cur_ebitda / interest if interest > 0 else 999.0
        fc_numer = cur_ebitda - capex
        fc_denom = interest + amort
        fcc = fc_numer / fc_denom if fc_denom > 0 else 999.0
        net_lev = debt / cur_ebitda if cur_ebitda > 0 else 999.0
        headroom = cov_max - net_lev

        if net_lev > cov_max and not covenant_at_risk:
            covenant_at_risk = True
            covenant_breach_year = yr

        if ic < min_ic:
            min_ic = ic
            min_ic_year = yr

        annual.append(AnnualDebtMetrics(
            year=yr,
            ebitda=cur_ebitda,
            revenue=cur_revenue,
            debt_balance=debt,
            interest_expense=interest,
            required_amort=amort,
            capex=capex,
            interest_coverage=ic,
            fixed_charge_coverage=fcc,
            net_leverage=net_lev,
            covenant_headroom_turns=headroom,
        ))

    return LeverageProfile(
        deal_name=str(deal.get("deal_name", "")),
        entry_ev_mm=ev,
        entry_ebitda_mm=ebitda,
        entry_debt_mm=entry_debt,
        equity_mm=equity,
        entry_leverage=entry_leverage,
        entry_interest_coverage=entry_ic,
        entry_fixed_charge_coverage=entry_fcc,
        assumptions=a,
        annual_metrics=annual,
        covenant_at_risk=covenant_at_risk,
        covenant_breach_year=covenant_breach_year,
        min_coverage_year=min_ic_year,
        min_coverage_ratio=min_ic,
    )


def debt_capacity(
    ebitda_mm: float,
    assumptions: Optional[Dict[str, float]] = None,
    coverage_floor: float = 1.5,
) -> float:
    """Max debt $M sustainable at the given interest coverage floor.

    Args:
        ebitda_mm:       EBITDA at entry ($M)
        coverage_floor:  minimum acceptable Interest Coverage Ratio
        assumptions:     override interest_rate etc.

    Returns:
        Maximum supportable debt ($M).
    """
    a = _resolve_assumptions(assumptions)
    rate = a["interest_rate"]
    if rate <= 0 or coverage_floor <= 0:
        raise ValueError("interest_rate and coverage_floor must be positive")
    max_interest = ebitda_mm / coverage_floor
    return max_interest / rate


def coverage_ratio(
    ebitda: float,
    interest: float,
    capex: float = 0.0,
    amort: float = 0.0,
) -> Dict[str, float]:
    """Compute interest and fixed-charge coverage ratios."""
    ic = ebitda / interest if interest > 0 else 999.0
    fcc_denom = interest + amort
    fcc = (ebitda - capex) / fcc_denom if fcc_denom > 0 else 999.0
    return {
        "interest_coverage": round(ic, 2),
        "fixed_charge_coverage": round(fcc, 2),
    }


def covenant_headroom(profile: LeverageProfile) -> Dict[str, Any]:
    """Summary of covenant headroom across the hold period."""
    cov_max = profile.assumptions["covenant_leverage_max"]
    metrics = profile.annual_metrics

    headrooms = [m.covenant_headroom_turns for m in metrics]
    min_headroom = min(headrooms) if headrooms else None
    min_headroom_year = headrooms.index(min_headroom) if headrooms else None
    worst_leverage = max(m.net_leverage for m in metrics) if metrics else None

    return {
        "covenant_leverage_trigger": cov_max,
        "entry_leverage": round(profile.entry_leverage, 2),
        "worst_leverage": round(worst_leverage, 2) if worst_leverage else None,
        "min_headroom_turns": round(min_headroom, 2) if min_headroom is not None else None,
        "min_headroom_year": min_headroom_year,
        "covenant_at_risk": profile.covenant_at_risk,
        "covenant_breach_year": profile.covenant_breach_year,
    }


def stress_leverage(
    profile: LeverageProfile,
    ebitda_shock: float,
    shock_year: int = 1,
) -> LeverageProfile:
    """Re-model leverage with an EBITDA shock (e.g. -0.10 = 10% decline in year 1).

    Args:
        profile:     base LeverageProfile from model_leverage()
        ebitda_shock: fractional change to EBITDA (e.g. -0.10 for -10%)
        shock_year:  year in which shock occurs (1-indexed; 0 = entry year)

    Returns:
        New LeverageProfile with stressed EBITDA path.
    """
    deal = {
        "deal_name": f"{profile.deal_name} [stressed {ebitda_shock:+.0%}]",
        "ev_mm": profile.entry_ev_mm,
        "ebitda_at_entry_mm": profile.entry_ebitda_mm * (1 + ebitda_shock) if shock_year == 0
                              else profile.entry_ebitda_mm,
        "hold_years": len(profile.annual_metrics) - 1,
    }
    assumptions = dict(profile.assumptions)
    if shock_year > 0:
        # Reduce growth in shock year only; model will compound from there
        # We proxy by reducing entry ebitda if shock_year == 1
        if shock_year == 1:
            deal["ebitda_at_entry_mm"] = profile.entry_ebitda_mm
            assumptions["ebitda_growth_annual"] = (
                (1 + profile.assumptions["ebitda_growth_annual"]) * (1 + ebitda_shock) - 1
            )
    return model_leverage(deal, assumptions)


def leverage_table(profile: LeverageProfile) -> str:
    """ASCII table of annual leverage metrics."""
    lines = [
        f"Leverage Profile: {profile.deal_name}",
        f"  Entry EV: ${profile.entry_ev_mm:,.0f}M  |  Entry Debt: ${profile.entry_debt_mm:,.0f}M  "
        f"|  Equity: ${profile.equity_mm:,.0f}M  |  Entry Lev: {profile.entry_leverage:.1f}x",
        "-" * 90,
        f"{'Yr':>2}  {'EBITDA':>8} {'Debt':>8} {'Int Cov':>7} {'FCC':>6} "
        f"{'Net Lev':>7} {'Headroom':>8}",
        "-" * 90,
    ]
    for m in profile.annual_metrics:
        breach = " ← BREACH" if m.net_leverage > profile.assumptions["covenant_leverage_max"] else ""
        lines.append(
            f"{m.year:>2}  ${m.ebitda:>6,.0f}M  ${m.debt_balance:>6,.0f}M  "
            f"{m.interest_coverage:>6.2f}x  {m.fixed_charge_coverage:>5.2f}x  "
            f"{m.net_leverage:>6.2f}x  {m.covenant_headroom_turns:>7.2f}x{breach}"
        )
    if profile.covenant_at_risk:
        lines.append(f"\n  *** COVENANT BREACH in Year {profile.covenant_breach_year} ***")
    return "\n".join(lines)
