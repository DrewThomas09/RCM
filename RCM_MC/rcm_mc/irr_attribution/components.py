"""DealCashflows + AttributionComponents + AttributionResult dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DealCashflows:
    """All inputs the attribution math needs.

    Entry / exit:
      ev_at_entry, ebitda_at_entry, revenue_at_entry,
      ev_at_exit, ebitda_at_exit, revenue_at_exit
      net_debt_at_entry, net_debt_at_exit

    Add-on contribution (for organic vs M&A split):
      addon_revenue_contribution_mm: total revenue added by
        bolt-on M&A during the hold

    LP cash-flow trail (for IRR):
      cashflows: list of (period_years_from_close, amount_mm)
        where negative = LP capital call, positive = distribution
        to LP. Includes dividend recaps + final exit proceeds.

    Optional:
      fx_translation_loss_mm: cumulative FX impact on USD-reported
        equity value (negative if USD strengthened vs deal currency)
      sub_line_credit_savings_mm: total interest savings from using
        a credit line vs calling LP capital earlier
    """
    deal_name: str = ""
    entry_year: int = 0
    exit_year: int = 0

    ev_at_entry_mm: float = 0.0
    ev_at_exit_mm: float = 0.0
    ebitda_at_entry_mm: float = 0.0
    ebitda_at_exit_mm: float = 0.0
    revenue_at_entry_mm: float = 0.0
    revenue_at_exit_mm: float = 0.0
    net_debt_at_entry_mm: float = 0.0
    net_debt_at_exit_mm: float = 0.0

    addon_revenue_contribution_mm: float = 0.0

    cashflows: List = field(default_factory=list)
    # cashflows: List[Tuple[float, float]] of (year, amount_mm)

    fx_translation_loss_mm: float = 0.0
    sub_line_credit_savings_mm: float = 0.0


@dataclass
class AttributionComponents:
    """The orthogonal decomposition of value creation."""
    revenue_growth_organic_mm: float = 0.0
    revenue_growth_ma_mm: float = 0.0
    margin_expansion_mm: float = 0.0
    multiple_expansion_mm: float = 0.0
    leverage_mm: float = 0.0
    fx_mm: float = 0.0
    dividend_recap_mm: float = 0.0
    sub_line_credit_mm: float = 0.0
    cross_terms_mm: float = 0.0
    total_value_created_mm: float = 0.0


@dataclass
class AttributionResult:
    """Top-level result the partner reads."""
    deal_name: str
    entry_equity_mm: float
    exit_equity_mm: float
    irr: float                    # decimal (0.20 = 20%)
    moic: float                   # multiple of invested capital
    components: AttributionComponents
    component_share: Dict[str, float] = field(default_factory=dict)
        # share of total value creation, signed
