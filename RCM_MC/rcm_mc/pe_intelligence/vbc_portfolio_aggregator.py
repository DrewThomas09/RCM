"""VBC portfolio aggregator — concentration and total EBITDA across contracts.

Partner statement: "A single VBC contract is one
risk. A portfolio of VBC contracts can either be
diversified — population variability evens out across
contracts — or concentrated. If 60% of VBC EBITDA
comes from one contract, you don't have a VBC
portfolio, you have one bet. I want the portfolio
view: what's the total EBITDA contribution from VBC,
which contract drives the most, and what's the
volatility band when bear scenarios hit multiple
contracts simultaneously."

Distinct from:
- `vbc_risk_share_underwriter` — single contract.
- `payer_mix_risk` — payer concentration generally.

This module aggregates the per-contract reports into
a portfolio view.

### Output

- total VBC revenue, expected EBITDA, bear EBITDA
- per-contract EBITDA contribution (descending)
- top-1 / top-3 concentration of VBC EBITDA
- correlated-bear scenario: all contracts +5pp MLR
  simultaneously
- partner verdict: diversified / concentrated /
  single-bet
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .vbc_risk_share_underwriter import (
    VBCContractInputs,
    VBCRiskShareReport,
    underwrite_vbc_contract,
)


@dataclass
class VBCPortfolioInputs:
    contracts: List[VBCContractInputs] = field(
        default_factory=list)


@dataclass
class ContractContribution:
    name: str
    expected_ebitda_m: float
    contribution_share: float
    bear_ebitda_m: float
    verdict: str


@dataclass
class VBCPortfolioReport:
    contracts: List[ContractContribution] = field(
        default_factory=list)
    total_revenue_m: float = 0.0
    total_expected_ebitda_m: float = 0.0
    total_bear_ebitda_m: float = 0.0
    total_bull_ebitda_m: float = 0.0
    top1_concentration_pct: float = 0.0
    top3_concentration_pct: float = 0.0
    portfolio_verdict: str = "diversified"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contracts": [
                {"name": c.name,
                 "expected_ebitda_m": c.expected_ebitda_m,
                 "contribution_share":
                     c.contribution_share,
                 "bear_ebitda_m": c.bear_ebitda_m,
                 "verdict": c.verdict}
                for c in self.contracts
            ],
            "total_revenue_m": self.total_revenue_m,
            "total_expected_ebitda_m":
                self.total_expected_ebitda_m,
            "total_bear_ebitda_m":
                self.total_bear_ebitda_m,
            "total_bull_ebitda_m":
                self.total_bull_ebitda_m,
            "top1_concentration_pct":
                self.top1_concentration_pct,
            "top3_concentration_pct":
                self.top3_concentration_pct,
            "portfolio_verdict":
                self.portfolio_verdict,
            "partner_note": self.partner_note,
        }


def aggregate_vbc_portfolio(
    inputs: VBCPortfolioInputs,
) -> VBCPortfolioReport:
    if not inputs.contracts:
        return VBCPortfolioReport(
            partner_note=(
                "No VBC contracts in portfolio — "
                "nothing to aggregate."),
        )

    per_contract: List[VBCRiskShareReport] = [
        underwrite_vbc_contract(c)
        for c in inputs.contracts
    ]

    total_revenue = sum(
        r.revenue_m for r in per_contract)
    total_expected = sum(
        r.expected_result.ebitda_m
        for r in per_contract
        if r.expected_result is not None
    )
    total_bear = sum(
        r.bear_result.ebitda_m
        for r in per_contract
        if r.bear_result is not None
    )
    total_bull = sum(
        r.bull_result.ebitda_m
        for r in per_contract
        if r.bull_result is not None
    )

    # Per-contract contributions (only count
    # positive-EBITDA contracts in concentration since
    # negative ones drag, not concentrate).
    contributions: List[ContractContribution] = []
    positive_total = sum(
        max(0.0, r.expected_result.ebitda_m
            if r.expected_result else 0.0)
        for r in per_contract
    )
    for r in per_contract:
        exp = (
            r.expected_result.ebitda_m
            if r.expected_result else 0.0
        )
        bear = (
            r.bear_result.ebitda_m
            if r.bear_result else 0.0
        )
        share = (
            max(0.0, exp) / positive_total
            if positive_total > 0 else 0.0
        )
        contributions.append(ContractContribution(
            name=r.contract_name,
            expected_ebitda_m=exp,
            contribution_share=round(share, 4),
            bear_ebitda_m=bear,
            verdict=r.verdict,
        ))

    contributions.sort(
        key=lambda c: c.expected_ebitda_m, reverse=True)

    top1 = (
        contributions[0].contribution_share
        if contributions else 0.0
    )
    top3 = sum(
        c.contribution_share for c in contributions[:3]
    )

    if top1 >= 0.50:
        verdict = "single_bet"
        note = (
            f"Top contract = {top1:.0%} of VBC EBITDA. "
            f"This is not a portfolio — it's one bet "
            "with backup contracts. Renegotiate the top "
            "contract's corridor or expand other "
            "contracts before treating VBC as "
            "diversified."
        )
    elif top1 >= 0.30 or top3 >= 0.75:
        verdict = "concentrated"
        note = (
            f"Top-1 {top1:.0%}, top-3 {top3:.0%} of "
            "VBC EBITDA — concentrated. Stress-test "
            "the top contracts harder; their bear cases "
            "drive the portfolio bear."
        )
    else:
        verdict = "diversified"
        note = (
            f"Top-1 {top1:.0%}, top-3 {top3:.0%} of "
            "VBC EBITDA — diversified portfolio. "
            "Population variability across contracts "
            "should mute single-contract MLR shocks."
        )

    if total_bear < 0:
        note += (
            f" Correlated bear (all contracts +5pp MLR) "
            f"= ${total_bear:.1f}M EBITDA. VBC portfolio "
            "becomes a drag in bear, not a contributor."
        )

    return VBCPortfolioReport(
        contracts=contributions,
        total_revenue_m=round(total_revenue, 2),
        total_expected_ebitda_m=round(
            total_expected, 2),
        total_bear_ebitda_m=round(total_bear, 2),
        total_bull_ebitda_m=round(total_bull, 2),
        top1_concentration_pct=round(top1, 4),
        top3_concentration_pct=round(top3, 4),
        portfolio_verdict=verdict,
        partner_note=note,
    )


def render_vbc_portfolio_markdown(
    r: VBCPortfolioReport,
) -> str:
    lines = [
        "# VBC portfolio",
        "",
        f"_Verdict: **{r.portfolio_verdict}**_ — "
        f"{r.partner_note}",
        "",
        f"- Total VBC revenue: ${r.total_revenue_m:.1f}M",
        f"- Expected EBITDA: "
        f"${r.total_expected_ebitda_m:+.1f}M",
        f"- Bear EBITDA (all +5pp MLR): "
        f"${r.total_bear_ebitda_m:+.1f}M",
        f"- Bull EBITDA (all -5pp MLR): "
        f"${r.total_bull_ebitda_m:+.1f}M",
        f"- Top-1 concentration: "
        f"{r.top1_concentration_pct:.0%}",
        f"- Top-3 concentration: "
        f"{r.top3_concentration_pct:.0%}",
        "",
        "| Contract | Expected | Share | Bear | Verdict |",
        "|---|---|---|---|---|",
    ]
    for c in r.contracts:
        lines.append(
            f"| {c.name} | "
            f"${c.expected_ebitda_m:+.2f}M | "
            f"{c.contribution_share:.0%} | "
            f"${c.bear_ebitda_m:+.2f}M | "
            f"{c.verdict} |"
        )
    return "\n".join(lines)
