"""Management rollover equity — how much should management roll?

Partner reflex: "How much of the proceeds is management rolling?"
Rollover equity is the clearest signal of seller conviction. A
founder-CEO rolling 25% of proceeds into newco is betting their
net worth on the thesis; rolling 2% means they're taking the
money and running.

Partner-approximated target rollover by situation:

- Founder-CEO under 55, growth thesis: 20-30%.
- Founder-CEO at 55-65, turnaround or mature business: 10-20%.
- Founder-CEO over 65 or retiring: 5-10% (respect the exit).
- Sponsor-backed CEO, joining newco: 15-25% (less than founder
  but material).
- Turnaround / distressed: minimum rollover, cash retention
  focus.

Below target → flag management-alignment risk. Above → signals
confidence. The module recommends a target and flags deviation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RolloverContext:
    ceo_name: str = "CEO"
    ceo_is_founder: bool = False
    ceo_age: int = 50
    ceo_planning_to_stay: bool = True
    ceo_gross_proceeds_m: float = 0.0
    proposed_rollover_pct: float = 0.0
    deal_type: str = "platform"                # platform / turnaround /
                                               # late_cycle / distressed
    business_maturity: str = "growth"          # growth / mature / decline


@dataclass
class RolloverRecommendation:
    target_rollover_pct_low: float
    target_rollover_pct_high: float
    target_rollover_m: float                   # midpoint $
    proposed_rollover_m: float
    gap_vs_target_pct: float                   # proposed - midpoint
    alignment_grade: str                       # strong / adequate / thin
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_rollover_pct_low":
                self.target_rollover_pct_low,
            "target_rollover_pct_high":
                self.target_rollover_pct_high,
            "target_rollover_m": self.target_rollover_m,
            "proposed_rollover_m": self.proposed_rollover_m,
            "gap_vs_target_pct": self.gap_vs_target_pct,
            "alignment_grade": self.alignment_grade,
            "partner_note": self.partner_note,
        }


def _target_range(ctx: RolloverContext) -> tuple:
    # Default platform ranges.
    if ctx.deal_type == "distressed":
        return (0.03, 0.08)
    if ctx.deal_type == "turnaround":
        return (0.05, 0.15)

    # Founder paths.
    if ctx.ceo_is_founder:
        if ctx.ceo_age >= 65 or not ctx.ceo_planning_to_stay:
            return (0.05, 0.10)
        if ctx.ceo_age >= 55:
            return (0.10, 0.20)
        # Younger founder, growth thesis.
        if ctx.business_maturity == "growth":
            return (0.20, 0.30)
        return (0.15, 0.25)

    # Sponsor-backed CEO joining newco.
    if ctx.ceo_planning_to_stay:
        return (0.15, 0.25)
    return (0.05, 0.15)


def design_rollover(
    ctx: RolloverContext,
) -> RolloverRecommendation:
    low, high = _target_range(ctx)
    mid = (low + high) / 2.0
    target_m = ctx.ceo_gross_proceeds_m * mid
    proposed_m = ctx.ceo_gross_proceeds_m * ctx.proposed_rollover_pct
    gap = ctx.proposed_rollover_pct - mid

    # Grade alignment.
    if ctx.proposed_rollover_pct >= low:
        if ctx.proposed_rollover_pct >= high:
            grade = "strong"
        else:
            grade = "adequate"
    else:
        grade = "thin"

    if grade == "strong":
        note = (f"Strong alignment — {ctx.ceo_name} rolling "
                f"{ctx.proposed_rollover_pct*100:.0f}%, above "
                f"the {high*100:.0f}% upper target. Clear conviction "
                "signal.")
    elif grade == "adequate":
        note = (f"Adequate rollover at "
                f"{ctx.proposed_rollover_pct*100:.0f}% (target "
                f"{low*100:.0f}-{high*100:.0f}%). Aligned enough "
                "for partner comfort.")
    else:
        note = (f"Thin rollover — {ctx.proposed_rollover_pct*100:.1f}% "
                f"vs target {low*100:.0f}-{high*100:.0f}%. "
                f"{ctx.ceo_name} is taking proceeds and reducing "
                "skin-in-game. Negotiate up or lean on MIP to fill "
                "the alignment gap.")

    if ctx.deal_type == "distressed" and grade == "thin":
        note = (f"Distressed deal — thin rollover is expected here. "
                "Focus alignment on cash retention + MIP, not "
                "rollover.")

    return RolloverRecommendation(
        target_rollover_pct_low=low,
        target_rollover_pct_high=high,
        target_rollover_m=round(target_m, 2),
        proposed_rollover_m=round(proposed_m, 2),
        gap_vs_target_pct=round(gap, 4),
        alignment_grade=grade,
        partner_note=note,
    )


def render_rollover_markdown(
    r: RolloverRecommendation,
) -> str:
    lines = [
        "# Management rollover equity",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Target range: "
        f"{r.target_rollover_pct_low*100:.0f}%-"
        f"{r.target_rollover_pct_high*100:.0f}%",
        f"- Target rollover (midpoint): "
        f"${r.target_rollover_m:,.2f}M",
        f"- Proposed rollover: ${r.proposed_rollover_m:,.2f}M",
        f"- Gap vs midpoint: {r.gap_vs_target_pct*100:+.1f}pp",
        f"- Alignment grade: **{r.alignment_grade}**",
    ]
    return "\n".join(lines)
