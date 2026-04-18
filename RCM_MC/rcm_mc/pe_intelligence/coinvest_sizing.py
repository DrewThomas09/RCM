"""Co-invest sizing — how much of a deal to offer LPs.

Large deals are commonly syndicated to LPs via co-investment.
Partners size the co-invest based on:

- Fund concentration limits (single-deal cap typically 10-15%
  of fund).
- LP demand signal (which LPs asked, how much).
- Deal size vs fund size.
- Residual equity need.

This module takes fund + deal inputs and returns a partner-prudent
co-invest sizing + LP-letter outline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CoInvestInputs:
    fund_size_m: float
    total_equity_m: float                # total equity check for this deal
    fund_concentration_cap_pct: float = 0.15    # max single-deal fraction
    lp_signaled_demand_m: Optional[float] = None
    expected_deals_in_fund: int = 15
    preserve_buffer_pct: float = 0.20    # reserve for reserves/follow-ons


@dataclass
class CoInvestSizing:
    fund_capacity_m: float
    concentration_cap_m: float
    fund_commitment_m: float
    coinvest_offered_m: float
    lp_demand_coverage_ratio: Optional[float]
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_capacity_m": self.fund_capacity_m,
            "concentration_cap_m": self.concentration_cap_m,
            "fund_commitment_m": self.fund_commitment_m,
            "coinvest_offered_m": self.coinvest_offered_m,
            "lp_demand_coverage_ratio": self.lp_demand_coverage_ratio,
            "partner_note": self.partner_note,
        }


def size_coinvest(inputs: CoInvestInputs) -> CoInvestSizing:
    """Size fund commitment vs co-invest offering."""
    # Fund's available deployable capacity: fund_size × (1 - reserve buffer).
    capacity = inputs.fund_size_m * (1 - inputs.preserve_buffer_pct)
    # Single-deal cap.
    conc_cap = inputs.fund_size_m * inputs.fund_concentration_cap_pct
    # Fund commitment = min of equity, cap, and per-deal share of capacity.
    per_deal_budget = capacity / max(inputs.expected_deals_in_fund, 1)
    fund_commitment = min(inputs.total_equity_m, conc_cap, per_deal_budget)
    coinvest = max(0.0, inputs.total_equity_m - fund_commitment)
    demand_coverage = None
    if inputs.lp_signaled_demand_m is not None and coinvest > 0:
        demand_coverage = min(inputs.lp_signaled_demand_m / coinvest, 5.0)
    if coinvest == 0:
        note = ("Fund covers the whole check — no co-invest needed.")
    elif demand_coverage is not None and demand_coverage >= 1.5:
        note = (f"Co-invest ${coinvest:,.1f}M — LP demand ~"
                f"{demand_coverage:.1f}x covered. Allocation "
                "decisions required.")
    elif demand_coverage is not None and demand_coverage < 1.0:
        note = (f"Co-invest ${coinvest:,.1f}M — LP demand under-covers. "
                "Widen the invitation list or reduce syndication.")
    else:
        note = (f"Co-invest ${coinvest:,.1f}M at standard allocation.")
    return CoInvestSizing(
        fund_capacity_m=round(capacity, 2),
        concentration_cap_m=round(conc_cap, 2),
        fund_commitment_m=round(fund_commitment, 2),
        coinvest_offered_m=round(coinvest, 2),
        lp_demand_coverage_ratio=(round(demand_coverage, 4)
                                   if demand_coverage is not None else None),
        partner_note=note,
    )


def render_coinvest_markdown(sizing: CoInvestSizing) -> str:
    lines = [
        "# Co-invest sizing",
        "",
        f"- Fund capacity: ${sizing.fund_capacity_m:,.1f}M",
        f"- Concentration cap: ${sizing.concentration_cap_m:,.1f}M",
        f"- Fund commitment: ${sizing.fund_commitment_m:,.1f}M",
        f"- Co-invest offered: ${sizing.coinvest_offered_m:,.1f}M",
    ]
    if sizing.lp_demand_coverage_ratio is not None:
        lines.append(
            f"- LP demand coverage: {sizing.lp_demand_coverage_ratio:.2f}x"
        )
    lines.extend(["", f"_{sizing.partner_note}_"])
    return "\n".join(lines)
