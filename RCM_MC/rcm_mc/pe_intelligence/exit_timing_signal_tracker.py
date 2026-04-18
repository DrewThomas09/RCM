"""Exit timing signal tracker — when do we start exit prep?

Partner reflex: exit readiness is not a year-5 question. Multiple
signals align in the 18-24 months before an optimal exit:

- EBITDA trajectory stable or improving in the last 6 months.
- Thesis pillars substantially executed.
- Credit markets open (easing or stable).
- Peer transaction comps at attractive multiples.
- Management team stable and sellable.
- 2+ years of clean QofE history.
- CEO willing to remain or clean succession.

This module takes a signal bundle and returns:

- Ready-to-start count (signals flashing green).
- Blockers (signals that must flip before prep).
- Recommended next-step (start banker-RFP / wait / dry-run sale).
- Partner note on timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExitTimingContext:
    hold_quarter: int = 4
    ebitda_6mo_trend: str = "stable"          # stable/up/down
    thesis_lever_completion_pct: float = 0.40
    credit_markets: str = "stable"             # easing/stable/tightening
    peer_multiples_vs_entry: float = 0.0       # +/- vs entry pct
    management_team_stable: bool = True
    qofe_clean_quarters: int = 4
    ceo_willing_to_stay: bool = True
    current_nav_above_cost: bool = True
    recent_write_downs: bool = False


@dataclass
class ExitSignal:
    name: str
    status: str                                # "green" / "yellow" / "red"
    detail: str


@dataclass
class ExitTimingReport:
    green_count: int
    yellow_count: int
    red_count: int
    recommended_action: str                    # start_prep / dry_run / wait
    blockers: List[str]
    signals: List[ExitSignal]
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "green_count": self.green_count,
            "yellow_count": self.yellow_count,
            "red_count": self.red_count,
            "recommended_action": self.recommended_action,
            "blockers": list(self.blockers),
            "signals": [
                {"name": s.name, "status": s.status, "detail": s.detail}
                for s in self.signals
            ],
            "partner_note": self.partner_note,
        }


def track_exit_timing(ctx: ExitTimingContext) -> ExitTimingReport:
    signals: List[ExitSignal] = []

    # 1. EBITDA trend.
    if ctx.ebitda_6mo_trend == "up":
        signals.append(ExitSignal(
            "ebitda_trend", "green",
            "EBITDA trending up — strongest sales moment."))
    elif ctx.ebitda_6mo_trend == "stable":
        signals.append(ExitSignal(
            "ebitda_trend", "yellow",
            "EBITDA flat — workable but less leverage with buyers."))
    else:
        signals.append(ExitSignal(
            "ebitda_trend", "red",
            "EBITDA declining — buyers catch this in QofE."))

    # 2. Thesis execution.
    if ctx.thesis_lever_completion_pct >= 0.70:
        signals.append(ExitSignal(
            "thesis_executed", "green",
            f"{ctx.thesis_lever_completion_pct*100:.0f}% of thesis "
            "levers executed — story is concrete."))
    elif ctx.thesis_lever_completion_pct >= 0.40:
        signals.append(ExitSignal(
            "thesis_executed", "yellow",
            f"{ctx.thesis_lever_completion_pct*100:.0f}% of levers "
            "executed — story still has 'we're working on it.'"))
    else:
        signals.append(ExitSignal(
            "thesis_executed", "red",
            "Less than 40% of thesis levers executed — too early."))

    # 3. Credit markets.
    if ctx.credit_markets == "easing":
        signals.append(ExitSignal(
            "credit_markets", "green",
            "Credit easing — sponsor-to-sponsor window open."))
    elif ctx.credit_markets == "stable":
        signals.append(ExitSignal(
            "credit_markets", "yellow",
            "Credit stable — workable; monitor."))
    else:
        signals.append(ExitSignal(
            "credit_markets", "red",
            "Credit tightening — buyers haircut bids; wait."))

    # 4. Peer multiples.
    if ctx.peer_multiples_vs_entry >= 0.05:
        signals.append(ExitSignal(
            "peer_multiples", "green",
            f"Peer comps {ctx.peer_multiples_vs_entry*100:.0f}% "
            "above entry — comp-supported premium."))
    elif ctx.peer_multiples_vs_entry >= -0.05:
        signals.append(ExitSignal(
            "peer_multiples", "yellow",
            "Peer multiples flat to entry — no tailwind."))
    else:
        signals.append(ExitSignal(
            "peer_multiples", "red",
            f"Peer multiples {ctx.peer_multiples_vs_entry*100:.0f}% "
            "below entry — multiple-compression headwind."))

    # 5. Management stability.
    if ctx.management_team_stable and ctx.ceo_willing_to_stay:
        signals.append(ExitSignal(
            "management", "green",
            "Team stable and CEO committed — sellable."))
    elif ctx.management_team_stable or ctx.ceo_willing_to_stay:
        signals.append(ExitSignal(
            "management", "yellow",
            "Team stable OR CEO committed but not both."))
    else:
        signals.append(ExitSignal(
            "management", "red",
            "Team unstable + CEO not committed — stabilize first."))

    # 6. QofE history.
    if ctx.qofe_clean_quarters >= 8:
        signals.append(ExitSignal(
            "qofe_history", "green",
            f"{ctx.qofe_clean_quarters} clean quarters — buyer "
            "diligence fast."))
    elif ctx.qofe_clean_quarters >= 4:
        signals.append(ExitSignal(
            "qofe_history", "yellow",
            f"{ctx.qofe_clean_quarters} clean quarters — minimum; "
            "buyer will want more."))
    else:
        signals.append(ExitSignal(
            "qofe_history", "red",
            f"Only {ctx.qofe_clean_quarters} clean quarters — buyers "
            "walk or haircut."))

    # 7. NAV vs cost.
    if ctx.current_nav_above_cost and not ctx.recent_write_downs:
        signals.append(ExitSignal(
            "nav_posture", "green",
            "NAV above cost with no recent write-downs."))
    elif ctx.current_nav_above_cost:
        signals.append(ExitSignal(
            "nav_posture", "yellow",
            "NAV above cost but recent write-downs muddy the story."))
    else:
        signals.append(ExitSignal(
            "nav_posture", "red",
            "NAV below cost — don't sell at a loss unless forced."))

    green = sum(1 for s in signals if s.status == "green")
    yellow = sum(1 for s in signals if s.status == "yellow")
    red = sum(1 for s in signals if s.status == "red")

    blockers = [s.detail for s in signals if s.status == "red"]

    if green >= 5 and red == 0:
        action = "start_banker_rfp"
        note = (f"{green} green signals, no reds — initiate banker "
                "RFP this quarter. Sell into strength, not because "
                "the clock says hold year 5.")
    elif green >= 3 and red == 0:
        action = "dry_run_sale"
        note = (f"{green} greens, no reds — run a dry-run sale with "
                "2-3 banker pitches to calibrate market view. Full "
                "RFP in 6-9 months if signals hold.")
    elif red >= 2:
        action = "wait"
        note = (f"{red} red signals — wait. Exit while these are red "
                "prices to the worst data point. Fix the reds first.")
    elif red == 1:
        action = "wait"
        note = (f"One blocker: '{blockers[0]}'. Address before "
                "engaging bankers.")
    else:
        action = "wait"
        note = ("Too few green signals to justify exit prep. Keep "
                "executing; reassess in 2 quarters.")

    return ExitTimingReport(
        green_count=green,
        yellow_count=yellow,
        red_count=red,
        recommended_action=action,
        blockers=blockers,
        signals=signals,
        partner_note=note,
    )


def render_exit_timing_markdown(r: ExitTimingReport) -> str:
    lines = [
        "# Exit timing signal tracker",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Recommended action: **{r.recommended_action}**",
        f"- Green signals: {r.green_count}",
        f"- Yellow: {r.yellow_count}",
        f"- Red: {r.red_count}",
        "",
        "| Signal | Status | Detail |",
        "|---|---|---|",
    ]
    for s in r.signals:
        lines.append(f"| {s.name} | {s.status} | {s.detail} |")
    if r.blockers:
        lines.extend(["", "## Blockers", ""])
        for b in r.blockers:
            lines.append(f"- {b}")
    return "\n".join(lines)
