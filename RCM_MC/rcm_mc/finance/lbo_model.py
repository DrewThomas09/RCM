"""Leveraged Buyout model for hospital PE transactions.

Projects returns (MOIC, IRR) under a given capital structure with
debt paydown, EBITDA growth, and multiple expansion/compression.
Outputs a formatted sources & uses, annual P&L, debt schedule,
and returns waterfall.

Built for associates preparing IC decks.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class LBOAssumptions:
    """Everything driving the LBO returns."""
    # Entry
    entry_ebitda: float = 50_000_000
    entry_multiple: float = 10.0
    revenue_base: float = 400_000_000
    # Capital structure
    senior_debt_turns: float = 4.0
    senior_rate: float = 0.065
    sub_debt_turns: float = 1.0
    sub_rate: float = 0.10
    # Growth
    revenue_growth: float = 0.04
    ebitda_margin_base: float = 0.125
    margin_improvement_annual_bps: float = 50
    # Exit
    hold_years: int = 5
    exit_multiple: float = 10.5
    # Other
    capex_pct_revenue: float = 0.035
    nwc_pct_revenue: float = 0.08
    tax_rate: float = 0.25
    cash_sweep_pct: float = 0.50
    management_fee_pct: float = 0.02
    transaction_fees_pct: float = 0.03

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourcesAndUses:
    """Transaction sources and uses."""
    # Sources
    senior_debt: float = 0.0
    sub_debt: float = 0.0
    equity: float = 0.0
    total_sources: float = 0.0
    # Uses
    enterprise_value: float = 0.0
    transaction_fees: float = 0.0
    total_uses: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) for k, v in asdict(self).items()}


@dataclass
class LBOYear:
    """One year of the hold period."""
    year: int
    revenue: float
    ebitda: float
    ebitda_margin: float
    interest_senior: float
    interest_sub: float
    ebt: float
    taxes: float
    net_income: float
    capex: float
    delta_nwc: float
    free_cash_flow: float
    mandatory_repayment: float
    optional_sweep: float
    senior_debt_balance: float
    sub_debt_balance: float
    total_debt: float
    net_debt: float
    leverage_turns: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) if isinstance(v, float) else v
                for k, v in asdict(self).items()}


@dataclass
class LBOReturns:
    """Exit returns."""
    exit_ebitda: float
    exit_ev: float
    net_debt_at_exit: float
    equity_at_exit: float
    equity_invested: float
    moic: float
    irr: float
    total_value_created: float
    value_from_growth: float
    value_from_multiple: float
    value_from_deleveraging: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 4) if k in ("moic", "irr") else round(v, 2)
                for k, v in asdict(self).items()}


@dataclass
class LBOResult:
    """Full LBO output."""
    assumptions: LBOAssumptions
    sources_and_uses: SourcesAndUses
    projections: List[LBOYear]
    returns: LBOReturns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumptions": self.assumptions.to_dict(),
            "sources_and_uses": self.sources_and_uses.to_dict(),
            "projections": [y.to_dict() for y in self.projections],
            "returns": self.returns.to_dict(),
        }


def build_lbo(
    assumptions: Optional[LBOAssumptions] = None,
    **overrides: Any,
) -> LBOResult:
    """Build a full LBO model."""
    a = assumptions or LBOAssumptions()
    for k, v in overrides.items():
        if hasattr(a, k):
            setattr(a, k, v)

    # Sources & Uses
    ev = a.entry_ebitda * a.entry_multiple
    fees = ev * a.transaction_fees_pct
    total_uses = ev + fees
    senior = a.entry_ebitda * a.senior_debt_turns
    sub = a.entry_ebitda * a.sub_debt_turns
    equity = total_uses - senior - sub

    su = SourcesAndUses(
        senior_debt=senior, sub_debt=sub, equity=equity,
        total_sources=total_uses,
        enterprise_value=ev, transaction_fees=fees,
        total_uses=total_uses,
    )

    # Projections
    projections: List[LBOYear] = []
    sr_bal = senior
    sub_bal = sub
    prev_revenue = a.revenue_base
    prev_nwc = a.revenue_base * a.nwc_pct_revenue
    margin = a.ebitda_margin_base
    da_pct = 0.025

    for yr in range(1, a.hold_years + 1):
        revenue = prev_revenue * (1 + a.revenue_growth)
        margin = margin + a.margin_improvement_annual_bps / 10000
        ebitda = revenue * margin
        da = revenue * da_pct
        int_sr = sr_bal * a.senior_rate
        int_sub = sub_bal * a.sub_rate
        ebt = ebitda - da - int_sr - int_sub - (ev * a.management_fee_pct / a.hold_years)
        taxes = max(ebt * a.tax_rate, 0)
        ni = ebt - taxes
        capex = revenue * a.capex_pct_revenue
        nwc = revenue * a.nwc_pct_revenue
        d_nwc = nwc - prev_nwc
        fcf = ni + da - capex - d_nwc

        mandatory = 0.0
        sweep = max(fcf * a.cash_sweep_pct, 0)
        total_repay = mandatory + sweep

        if total_repay > sr_bal:
            sub_repay = min(total_repay - sr_bal, sub_bal)
            sr_bal = 0
            sub_bal -= sub_repay
        else:
            sr_bal -= total_repay

        total_debt = sr_bal + sub_bal
        leverage = total_debt / ebitda if ebitda > 0 else 0

        projections.append(LBOYear(
            year=yr, revenue=revenue, ebitda=ebitda,
            ebitda_margin=margin,
            interest_senior=int_sr, interest_sub=int_sub,
            ebt=ebt, taxes=taxes, net_income=ni,
            capex=capex, delta_nwc=d_nwc,
            free_cash_flow=fcf,
            mandatory_repayment=mandatory,
            optional_sweep=sweep,
            senior_debt_balance=sr_bal,
            sub_debt_balance=sub_bal,
            total_debt=total_debt,
            net_debt=total_debt,
            leverage_turns=leverage,
        ))
        prev_revenue = revenue
        prev_nwc = nwc

    # Returns
    exit_ebitda = projections[-1].ebitda
    exit_ev = exit_ebitda * a.exit_multiple
    net_debt = projections[-1].total_debt
    equity_exit = exit_ev - net_debt
    moic = equity_exit / equity if equity > 0 else 0
    irr = moic ** (1 / a.hold_years) - 1 if moic > 0 else 0

    entry_equity_ebitda = a.entry_ebitda * (a.exit_multiple - a.entry_multiple)
    growth_value = (exit_ebitda - a.entry_ebitda) * a.exit_multiple
    multiple_value = entry_equity_ebitda
    delev_value = (senior + sub) - net_debt

    returns = LBOReturns(
        exit_ebitda=exit_ebitda, exit_ev=exit_ev,
        net_debt_at_exit=net_debt, equity_at_exit=equity_exit,
        equity_invested=equity, moic=moic, irr=irr,
        total_value_created=equity_exit - equity,
        value_from_growth=growth_value,
        value_from_multiple=multiple_value,
        value_from_deleveraging=delev_value,
    )

    return LBOResult(
        assumptions=a, sources_and_uses=su,
        projections=projections, returns=returns,
    )


def build_lbo_from_deal(profile: Dict[str, Any]) -> LBOResult:
    """Convenience: build LBO from deal profile.

    Precedence for margin: current_ebitda/revenue > ebitda_margin field >
    12% default. Revenue must be present; callers upstream should guard
    against running the LBO on empty profiles.
    """
    revenue = float(profile.get("net_revenue") or profile.get("revenue") or 400e6)

    # Resolve margin
    ebitda_raw = profile.get("current_ebitda")
    if ebitda_raw not in (None, ""):
        ebitda = float(ebitda_raw)
        margin = ebitda / revenue if revenue > 0 else 0.12
    elif profile.get("ebitda_margin") not in (None, ""):
        try:
            margin = float(profile["ebitda_margin"])
        except (TypeError, ValueError):
            margin = 0.12
        ebitda = revenue * margin
    else:
        margin = 0.12
        ebitda = revenue * margin

    # Clamp to plausible LBO-target range. Sub-zero EBITDA can't be
    # financed with traditional senior debt turns, so we floor at 2%.
    margin = max(0.02, min(0.40, margin))
    ebitda = revenue * margin

    return build_lbo(
        entry_ebitda=ebitda,
        revenue_base=revenue,
        ebitda_margin_base=margin,
    )
