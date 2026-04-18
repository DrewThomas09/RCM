"""Refinancing window — when to refi portfolio debt.

Portfolio companies carry floating-rate + covenanted debt. Partners
need to know:

- When is the next maturity wall?
- Is the current rate environment friendly enough to refi early?
- Are covenants loose enough that lenders will re-underwrite?
- What's the partner-preferred window?

This module takes a debt stack + rate context and returns a
recommended refinance window + partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DebtTranche:
    name: str                             # "TLB", "Revolver", "Mezz", "PIK"
    principal_m: float
    maturity_year: int                    # year matures (absolute year)
    rate: float                           # current all-in rate
    covenant_headroom_pct: float = 0.30   # EBITDA cushion vs covenant

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "principal_m": self.principal_m,
            "maturity_year": self.maturity_year,
            "rate": self.rate,
            "covenant_headroom_pct": self.covenant_headroom_pct,
        }


@dataclass
class RefiContext:
    current_year: int
    current_market_rate: float            # prevailing all-in for new issues
    rate_trend: str = "flat"              # "down", "flat", "up"
    credit_spread_bps: int = 500          # spread to base


@dataclass
class RefiRecommendation:
    tranche_name: str
    action: str                           # "refi_now", "refi_in_1_year",
                                          # "wait", "hold_to_maturity"
    rationale: str
    years_to_maturity: int
    rate_delta_bps: int                   # current_rate - market_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tranche_name": self.tranche_name,
            "action": self.action,
            "rationale": self.rationale,
            "years_to_maturity": self.years_to_maturity,
            "rate_delta_bps": self.rate_delta_bps,
        }


@dataclass
class RefiPlan:
    recommendations: List[RefiRecommendation] = field(default_factory=list)
    total_maturity_wall_m: float = 0.0    # principal due in next 24 months
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_maturity_wall_m": self.total_maturity_wall_m,
            "partner_note": self.partner_note,
        }


def _decide_action(tranche: DebtTranche, ctx: RefiContext) -> RefiRecommendation:
    years_to_mat = tranche.maturity_year - ctx.current_year
    rate_delta_bps = int(round((tranche.rate - ctx.current_market_rate) * 10000))

    # Imminent maturity → must refi.
    if years_to_mat <= 1:
        return RefiRecommendation(
            tranche_name=tranche.name, action="refi_now",
            rationale=(f"Matures in {years_to_mat} year(s) — must be "
                       "refinanced or paid down."),
            years_to_maturity=max(years_to_mat, 0),
            rate_delta_bps=rate_delta_bps,
        )

    # Refi opportunity: current rate much higher than market, and
    # covenants have room.
    if (rate_delta_bps >= 100
            and tranche.covenant_headroom_pct >= 0.20
            and ctx.rate_trend != "down"):
        # Rates are flat/up — lock in savings now.
        return RefiRecommendation(
            tranche_name=tranche.name, action="refi_now",
            rationale=(f"Current rate {tranche.rate*100:.2f}% is "
                       f"{rate_delta_bps} bps above market and covenant "
                       "headroom is healthy — refi now."),
            years_to_maturity=years_to_mat, rate_delta_bps=rate_delta_bps,
        )

    # Rates falling + a few years to maturity → wait.
    if ctx.rate_trend == "down" and years_to_mat >= 2:
        return RefiRecommendation(
            tranche_name=tranche.name, action="wait",
            rationale="Rates trending down — wait for better pricing.",
            years_to_maturity=years_to_mat, rate_delta_bps=rate_delta_bps,
        )

    # Rates rising + maturity within 2-3 years → refi in 1 year.
    if ctx.rate_trend == "up" and years_to_mat <= 3:
        return RefiRecommendation(
            tranche_name=tranche.name, action="refi_in_1_year",
            rationale=(f"Rates rising — lock in within 12 months before "
                       "maturity squeeze."),
            years_to_maturity=years_to_mat, rate_delta_bps=rate_delta_bps,
        )

    # Covenant tightness → cannot refi without cushion.
    if tranche.covenant_headroom_pct < 0.15:
        return RefiRecommendation(
            tranche_name=tranche.name, action="wait",
            rationale=(f"Covenant headroom {tranche.covenant_headroom_pct*100:.0f}% "
                       "too thin — build EBITDA cushion before approaching lenders."),
            years_to_maturity=years_to_mat, rate_delta_bps=rate_delta_bps,
        )

    return RefiRecommendation(
        tranche_name=tranche.name, action="hold_to_maturity",
        rationale=("No refi edge currently — hold."),
        years_to_maturity=years_to_mat, rate_delta_bps=rate_delta_bps,
    )


def plan_refinance(tranches: List[DebtTranche],
                    ctx: RefiContext) -> RefiPlan:
    """Produce refi recommendations for a debt stack."""
    recs = [_decide_action(t, ctx) for t in tranches]
    wall = sum(t.principal_m for t in tranches
               if t.maturity_year - ctx.current_year <= 2)

    now_actions = [r for r in recs if r.action == "refi_now"]
    if now_actions:
        note = (
            f"{len(now_actions)} tranche(s) flagged for refi now. "
            f"Next-24-month maturity wall: ${wall:,.0f}M."
        )
    elif any(r.action == "refi_in_1_year" for r in recs):
        note = "Refi window opening in 12 months — start banker RFP."
    elif all(r.action == "wait" for r in recs):
        note = "All tranches in wait mode — monitor rate environment."
    else:
        note = "Mixed book — selective refi + hold posture."
    return RefiPlan(
        recommendations=recs,
        total_maturity_wall_m=round(wall, 2),
        partner_note=note,
    )


def render_refi_plan_markdown(plan: RefiPlan) -> str:
    lines = [
        "# Refinancing plan",
        "",
        f"_{plan.partner_note}_",
        "",
        f"- 24-month maturity wall: ${plan.total_maturity_wall_m:,.0f}M",
        "",
        "| Tranche | Action | Years | Rate Δ bps |",
        "|---|---|---:|---:|",
    ]
    for r in plan.recommendations:
        lines.append(
            f"| {r.tranche_name} | {r.action} | {r.years_to_maturity} | "
            f"{r.rate_delta_bps:+d} |"
        )
    lines.extend(["", "## Rationale", ""])
    for r in plan.recommendations:
        lines.append(f"- **{r.tranche_name}**: {r.rationale}")
    return "\n".join(lines)
