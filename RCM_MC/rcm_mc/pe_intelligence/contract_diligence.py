"""Contract diligence — payer-contract portfolio risk scorer.

Payer contracts are the single largest revenue-risk item on most
healthcare deals. This module takes a list of payer contracts (each
with expiry date, revenue share, termination clauses, rate-reset
mechanics) and produces:

- Per-contract risk score (0..1).
- Portfolio-level concentration + maturity wall.
- Action list (which contracts to re-negotiate pre-close, which to
  monitor).

A contract is "risky" when:
- It expires inside the hold window.
- It represents a top-3 revenue share.
- It has an adverse termination clause (at-will, anti-assignment).
- Its rate-reset mechanic is payer-favorable (annual CPI-only).
- Government contract with recent state-level rate pressure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class PayerContract:
    payer_name: str
    revenue_share: float              # fraction 0..1
    expiry_years: Optional[float] = None    # years until expiry
    termination_mechanic: str = "standard"   # "at_will" | "anti_assignment" | "standard"
    rate_reset_mechanic: str = "market"      # "cpi_only" | "market" | "negotiated" | "formula"
    is_government: bool = False
    state: Optional[str] = None
    is_top3: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_name": self.payer_name,
            "revenue_share": self.revenue_share,
            "expiry_years": self.expiry_years,
            "termination_mechanic": self.termination_mechanic,
            "rate_reset_mechanic": self.rate_reset_mechanic,
            "is_government": self.is_government,
            "state": self.state,
            "is_top3": self.is_top3,
        }


@dataclass
class ContractRisk:
    contract: PayerContract
    score: float                       # 0..1
    flags: List[str] = field(default_factory=list)
    action: str = ""                   # "renegotiate_pre_close" | "monitor" | "note"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract.to_dict(),
            "score": self.score,
            "flags": list(self.flags),
            "action": self.action,
        }


@dataclass
class ContractPortfolio:
    per_contract: List[ContractRisk] = field(default_factory=list)
    portfolio_concentration: float = 0.0         # top-3 share
    maturity_wall_pct: float = 0.0               # % of revenue from contracts expiring in hold
    high_risk_count: int = 0
    partner_note: str = ""
    actions_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_contract": [c.to_dict() for c in self.per_contract],
            "portfolio_concentration": self.portfolio_concentration,
            "maturity_wall_pct": self.maturity_wall_pct,
            "high_risk_count": self.high_risk_count,
            "partner_note": self.partner_note,
            "actions_needed": list(self.actions_needed),
        }


# ── Scorer ──────────────────────────────────────────────────────────

_VOLATILE_GOVT_STATES = {"IL", "NY", "CA", "LA", "OK", "MS", "AR"}


def _score_contract(
    contract: PayerContract,
    *,
    hold_years: Optional[float],
) -> ContractRisk:
    score = 0.0
    flags: List[str] = []

    # 1. Expiry inside hold
    if (contract.expiry_years is not None and hold_years is not None
            and contract.expiry_years <= hold_years + 0.25):
        score += 0.35
        flags.append(f"Expires in {contract.expiry_years:.1f}yr (hold {hold_years:.1f}yr).")
    elif (contract.expiry_years is not None and contract.expiry_years <= 1.0):
        score += 0.20
        flags.append("Near-term expiry — pre-close renegotiation window open.")

    # 2. Revenue concentration
    if contract.revenue_share >= 0.25:
        score += 0.30
        flags.append(f"Top-1 revenue share {contract.revenue_share*100:.0f}%.")
    elif contract.is_top3 or contract.revenue_share >= 0.15:
        score += 0.15
        flags.append("Top-3 revenue share.")

    # 3. Termination mechanic
    if contract.termination_mechanic == "at_will":
        score += 0.25
        flags.append("At-will termination clause.")
    elif contract.termination_mechanic == "anti_assignment":
        score += 0.20
        flags.append("Anti-assignment clause — change-of-control risk.")

    # 4. Rate-reset mechanic
    if contract.rate_reset_mechanic == "cpi_only":
        score += 0.10
        flags.append("CPI-only reset — payer-favorable.")
    elif contract.rate_reset_mechanic == "formula":
        score += 0.05
        flags.append("Formula-based reset — limits negotiation room.")

    # 5. Government + volatile state
    if contract.is_government and contract.state in _VOLATILE_GOVT_STATES:
        score += 0.15
        flags.append(f"Government contract in rate-volatile state ({contract.state}).")
    elif contract.is_government:
        score += 0.05
        flags.append("Government contract — rate-cycle exposure.")

    score = min(score, 1.0)

    # Action recommendation
    if score >= 0.60:
        action = "renegotiate_pre_close"
    elif score >= 0.35:
        action = "monitor"
    else:
        action = "note"

    return ContractRisk(
        contract=contract,
        score=round(score, 4),
        flags=flags,
        action=action,
    )


# ── Portfolio orchestrator ─────────────────────────────────────────

def analyze_contract_portfolio(
    contracts: List[PayerContract],
    *,
    hold_years: Optional[float] = None,
) -> ContractPortfolio:
    """Score each contract and aggregate into portfolio metrics."""
    per_contract = [_score_contract(c, hold_years=hold_years) for c in contracts]

    # Portfolio concentration: sum of top-3 revenue shares.
    sorted_shares = sorted((c.revenue_share for c in contracts), reverse=True)
    portfolio_concentration = sum(sorted_shares[:3]) if sorted_shares else 0.0

    # Maturity wall: revenue share from contracts expiring inside hold.
    if hold_years is None:
        maturity_wall = 0.0
    else:
        maturity_wall = sum(
            c.revenue_share for c in contracts
            if c.expiry_years is not None
            and c.expiry_years <= hold_years + 0.25
        )

    high_risk = sum(1 for r in per_contract if r.score >= 0.60)

    actions: List[str] = []
    if maturity_wall >= 0.40:
        actions.append(
            f"{maturity_wall*100:.0f}% of revenue expires in hold — "
            "stagger renewals pre-close.")
    if portfolio_concentration >= 0.70:
        actions.append(
            f"Top-3 payer concentration {portfolio_concentration*100:.0f}% — "
            "diversify or price in single-payer risk.")
    high_risk_actions = [
        f"Renegotiate {r.contract.payer_name} pre-close."
        for r in per_contract if r.score >= 0.60
    ]
    actions.extend(high_risk_actions[:5])

    if high_risk == 0 and maturity_wall < 0.25:
        note = "Payer portfolio is quiet — no material contract risk."
    elif high_risk >= 3:
        note = (f"{high_risk} high-risk contract(s) + "
                f"{maturity_wall*100:.0f}% maturity wall — pre-close "
                "renegotiation required.")
    else:
        note = (f"{high_risk} high-risk contract(s); maturity wall "
                f"{maturity_wall*100:.0f}% of revenue.")

    return ContractPortfolio(
        per_contract=per_contract,
        portfolio_concentration=round(portfolio_concentration, 4),
        maturity_wall_pct=round(maturity_wall, 4),
        high_risk_count=high_risk,
        partner_note=note,
        actions_needed=actions,
    )


def render_contract_diligence_markdown(portfolio: ContractPortfolio) -> str:
    lines = [
        "# Payer contract diligence",
        "",
        f"**Partner note:** {portfolio.partner_note}",
        "",
        f"- Top-3 concentration: {portfolio.portfolio_concentration*100:.0f}%",
        f"- Maturity wall (in hold): {portfolio.maturity_wall_pct*100:.0f}%",
        f"- High-risk contracts: {portfolio.high_risk_count}",
        "",
        "## Per-contract detail",
        "",
        "| Payer | Share | Expiry | Score | Action |",
        "|---|---:|---:|---:|---|",
    ]
    for r in portfolio.per_contract:
        c = r.contract
        expiry = f"{c.expiry_years:.1f}yr" if c.expiry_years is not None else "n/a"
        lines.append(
            f"| {c.payer_name} | {c.revenue_share*100:.0f}% | "
            f"{expiry} | {r.score:.2f} | {r.action} |"
        )
    if portfolio.actions_needed:
        lines.extend(["", "## Actions needed", ""])
        for i, a in enumerate(portfolio.actions_needed, 1):
            lines.append(f"{i}. {a}")
    return "\n".join(lines)
