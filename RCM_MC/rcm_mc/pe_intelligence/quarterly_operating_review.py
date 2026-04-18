"""Quarterly operating review — the post-close QoR agenda.

Partners run QoRs quarterly with portfolio CEOs. Generic "how are
things going" is a waste. A disciplined QoR is:

1. **Numbers** — the KPI cascade vs plan (15 minutes).
2. **Thesis progress** — value-creation lever by lever (15 min).
3. **People + operating rhythm** — team, hires, departures, cash
   (15 min).
4. **Forward-look + asks** — next 90 days + what the CEO needs
   from the board (15 min).

This module generates a QoR agenda tailored to the current signals:
if denial rate is trending up, the numbers block drills down on
it; if a lever is behind schedule, thesis block spends more time
there.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QoRContext:
    deal_name: str = "Portco"
    hold_quarter: int = 4                   # which quarter in hold
    ebitda_vs_plan_pct: float = 0.0         # +/- % vs plan
    revenue_vs_plan_pct: float = 0.0
    denial_rate_trend: str = "flat"         # rising/falling/flat
    dar_vs_plan_days: float = 0.0           # current - plan
    thesis_levers: List[str] = field(default_factory=list)
    lever_on_track_count: int = 0
    lever_behind_count: int = 0
    has_open_ceo_hire: bool = False
    cash_runway_months: float = 18.0
    covenant_headroom_pct: float = 0.25
    new_bolt_on_closed_this_quarter: bool = False


@dataclass
class QoRBlock:
    title: str
    minutes: int
    bullets: List[str]
    partner_focus: str                      # where partner pushes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "minutes": self.minutes,
            "bullets": list(self.bullets),
            "partner_focus": self.partner_focus,
        }


@dataclass
class QoRAgenda:
    deal_name: str
    hold_quarter: int
    total_minutes: int
    blocks: List[QoRBlock] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "hold_quarter": self.hold_quarter,
            "total_minutes": self.total_minutes,
            "blocks": [b.to_dict() for b in self.blocks],
            "partner_note": self.partner_note,
        }


def _numbers_block(ctx: QoRContext) -> QoRBlock:
    bullets: List[str] = []
    bullets.append(
        f"EBITDA vs plan: {ctx.ebitda_vs_plan_pct*100:+.1f}%")
    bullets.append(
        f"Revenue vs plan: {ctx.revenue_vs_plan_pct*100:+.1f}%")
    if ctx.denial_rate_trend == "rising":
        bullets.append("Denial rate is RISING — 15-minute deep-dive "
                        "on top-3 reasons by payer.")
    if abs(ctx.dar_vs_plan_days) >= 5:
        bullets.append(
            f"DAR vs plan: {ctx.dar_vs_plan_days:+.0f} days — "
            "billing cadence review.")
    bullets.append(f"Cash runway: {ctx.cash_runway_months:.0f} months")
    bullets.append(
        f"Covenant headroom: {ctx.covenant_headroom_pct*100:.0f}%")
    if ctx.ebitda_vs_plan_pct < -0.05:
        focus = ("Partner pushes HARD on the EBITDA miss — specific "
                 "named driver, not 'timing issues.'")
    elif ctx.denial_rate_trend == "rising":
        focus = ("Partner focus: denial-rate inflection. RCM "
                 "leadership explains.")
    elif ctx.covenant_headroom_pct < 0.15:
        focus = ("Partner focus: covenant headroom tight; 13-week "
                 "cash owner walks scenarios.")
    else:
        focus = ("Partner focus: lowest-performing KPI gets drilled.")
    return QoRBlock(
        title="Numbers",
        minutes=15,
        bullets=bullets,
        partner_focus=focus,
    )


def _thesis_block(ctx: QoRContext) -> QoRBlock:
    bullets: List[str] = []
    bullets.append(
        f"Levers on track: {ctx.lever_on_track_count}")
    bullets.append(
        f"Levers behind: {ctx.lever_behind_count}")
    if ctx.thesis_levers:
        bullets.append("Review: " + "; ".join(ctx.thesis_levers[:3]))
    if ctx.new_bolt_on_closed_this_quarter:
        bullets.append("New bolt-on closed — integration status.")
    if ctx.lever_behind_count >= 2:
        focus = ("Two+ levers behind — partner asks for named "
                 "recovery plan with owner and date. No general "
                 "'we'll get there.'")
    elif ctx.new_bolt_on_closed_this_quarter:
        focus = ("Integration is the #1 execution risk for new "
                 "bolt-ons — 30/60/90-day milestones.")
    else:
        focus = ("Partner focus: lever pacing vs hold-year "
                 "expectations.")
    return QoRBlock(
        title="Thesis Progress",
        minutes=15,
        bullets=bullets,
        partner_focus=focus,
    )


def _people_block(ctx: QoRContext) -> QoRBlock:
    bullets: List[str] = []
    if ctx.has_open_ceo_hire:
        bullets.append("**CEO search open** — named firm, candidate "
                        "stage, expected close.")
    bullets.append("Named departures this quarter + retention plan.")
    bullets.append("Top-5 clinician / operator retention tracker.")
    bullets.append("MIP vesting status + at-risk grants.")
    if ctx.has_open_ceo_hire:
        focus = ("Partner focus: CEO search is the #1 operating "
                 "risk in this period; weekly updates from search "
                 "chair.")
    else:
        focus = ("Partner focus: retention in key clinical + "
                 "operating roles.")
    return QoRBlock(
        title="People + Operating Rhythm",
        minutes=15,
        bullets=bullets,
        partner_focus=focus,
    )


def _forward_block(ctx: QoRContext) -> QoRBlock:
    bullets: List[str] = []
    bullets.append("Next-90-day top-3 operating priorities.")
    bullets.append("CEO's asks of the board (specific, time-bound).")
    bullets.append("Next-quarter KPI targets reaffirmed or revised.")
    if ctx.hold_quarter >= 8:
        bullets.append("Exit-readiness status + banker-prep items "
                        "(applicable in hold year 3+).")
    focus = ("Partner focus: extract CEO's asks explicitly. A CEO "
             "with no asks is either perfectly resourced (rare) or "
             "not thinking strategically.")
    return QoRBlock(
        title="Forward-look + Asks",
        minutes=15,
        bullets=bullets,
        partner_focus=focus,
    )


def build_qor_agenda(ctx: QoRContext) -> QoRAgenda:
    blocks = [
        _numbers_block(ctx),
        _thesis_block(ctx),
        _people_block(ctx),
        _forward_block(ctx),
    ]
    total = sum(b.minutes for b in blocks)

    if ctx.ebitda_vs_plan_pct < -0.10:
        note = (f"Q{ctx.hold_quarter}: EBITDA "
                f"{ctx.ebitda_vs_plan_pct*100:.0f}% below plan. This "
                "QoR is an intervention, not a review. Extend "
                "numbers block if needed.")
    elif ctx.lever_behind_count >= 2 or ctx.has_open_ceo_hire:
        note = (f"Q{ctx.hold_quarter}: multiple execution items need "
                "partner attention. Drive specifics in every block.")
    elif ctx.ebitda_vs_plan_pct >= 0.05:
        note = (f"Q{ctx.hold_quarter}: outperforming. Use the time "
                "to pull forward value-creation levers or assess "
                "early exit readiness.")
    else:
        note = (f"Q{ctx.hold_quarter}: standard QoR. Hit the four "
                "blocks; don't let any drift.")

    return QoRAgenda(
        deal_name=ctx.deal_name,
        hold_quarter=ctx.hold_quarter,
        total_minutes=total,
        blocks=blocks,
        partner_note=note,
    )


def render_qor_agenda_markdown(a: QoRAgenda) -> str:
    lines = [
        f"# {a.deal_name} — QoR Q{a.hold_quarter}",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Total: {a.total_minutes} minutes",
        "",
    ]
    for b in a.blocks:
        lines.append(f"## ({b.minutes}min) {b.title}")
        for bullet in b.bullets:
            lines.append(f"- {bullet}")
        lines.append(f"- **Partner focus:** {b.partner_focus}")
        lines.append("")
    return "\n".join(lines)
