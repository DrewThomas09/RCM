"""Exit channel selector — rank exit paths for a deal.

Four primary channels:

- **Strategic** — sold to a corporate buyer. Typically highest
  multiple because of synergies, but slowest close and more
  regulatory review.
- **Financial sponsor** — sold to another PE firm. Fastest close,
  good multiples at the top of cycle, limited structural risk.
- **IPO** — public listing. Best outcome when comparable peers
  trade well; worst when market is closed.
- **Continuation vehicle** — GP-led secondary; LPs can roll or
  cash out. Useful when premium asset + more runway needed.

This module scores each channel based on deal size, sector heat,
rate environment, and operating maturity, then returns a ranked
recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CHANNELS = ("strategic", "sponsor", "ipo", "continuation")


@dataclass
class ExitChannelInputs:
    ebitda_m: float
    revenue_m: float
    sector_heat: str = "warm"             # "hot" / "warm" / "cool"
    ipo_window_status: str = "open"       # "open" / "cautious" / "closed"
    rate_environment: str = "flat"        # "easing" / "flat" / "tightening"
    has_strategic_buyers_interested: bool = False
    years_held: int = 5
    has_material_runway_thesis: bool = False
    preferred_irr: float = 0.20


@dataclass
class ChannelRank:
    channel: str
    score_0_100: int
    expected_multiple: float              # EV/EBITDA
    timing_months: int
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "score_0_100": self.score_0_100,
            "expected_multiple": self.expected_multiple,
            "timing_months": self.timing_months,
            "rationale": self.rationale,
        }


@dataclass
class ExitChannelRecommendation:
    best_channel: str
    ranks: List[ChannelRank] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_channel": self.best_channel,
            "ranks": [r.to_dict() for r in self.ranks],
            "partner_note": self.partner_note,
        }


def _score_strategic(inputs: ExitChannelInputs) -> ChannelRank:
    score = 40
    mult = 11.0
    if inputs.has_strategic_buyers_interested:
        score += 25
    if inputs.sector_heat == "hot":
        score += 15
        mult += 2.0
    elif inputs.sector_heat == "cool":
        score -= 15
        mult -= 1.0
    if inputs.ebitda_m >= 50:
        score += 10
    months = 9
    rationale = ("Strategic premium typical when synergies are real; "
                 "regulatory review lengthens timeline.")
    return ChannelRank("strategic", max(0, min(100, score)),
                        mult, months, rationale)


def _score_sponsor(inputs: ExitChannelInputs) -> ChannelRank:
    score = 55
    mult = 10.0
    if inputs.sector_heat == "hot":
        score += 15
        mult += 1.0
    elif inputs.sector_heat == "cool":
        score -= 10
        mult -= 1.0
    if inputs.rate_environment == "easing":
        score += 10
        mult += 0.5
    elif inputs.rate_environment == "tightening":
        score -= 10
        mult -= 0.5
    if inputs.ebitda_m >= 25:
        score += 10
    months = 6
    rationale = ("Sponsor-to-sponsor trades close faster; pricing "
                 "tracks credit-market conditions.")
    return ChannelRank("sponsor", max(0, min(100, score)),
                        mult, months, rationale)


def _score_ipo(inputs: ExitChannelInputs) -> ChannelRank:
    score = 25
    mult = 12.0
    if inputs.revenue_m >= 300 and inputs.ebitda_m >= 75:
        score += 20
    else:
        score -= 15
    if inputs.ipo_window_status == "open":
        score += 25
        mult += 1.0
    elif inputs.ipo_window_status == "closed":
        score -= 30
        mult -= 2.0
    months = 12
    rationale = ("IPO needs scale (rev ≥ $300M typical) plus an open "
                 "market window.")
    return ChannelRank("ipo", max(0, min(100, score)),
                        mult, months, rationale)


def _score_continuation(inputs: ExitChannelInputs) -> ChannelRank:
    score = 30
    mult = 10.5
    if inputs.has_material_runway_thesis:
        score += 25
    if inputs.years_held >= 5:
        score += 10
    if inputs.ipo_window_status == "closed" and inputs.sector_heat != "hot":
        # Continuation becomes more attractive when other channels close.
        score += 15
    months = 6
    rationale = ("Continuation vehicles work when there's a clear runway "
                 "thesis and LP appetite for a roll.")
    return ChannelRank("continuation", max(0, min(100, score)),
                        mult, months, rationale)


def rank_exit_channels(inputs: ExitChannelInputs) -> ExitChannelRecommendation:
    ranks = [
        _score_strategic(inputs),
        _score_sponsor(inputs),
        _score_ipo(inputs),
        _score_continuation(inputs),
    ]
    ranks.sort(key=lambda r: r.score_0_100, reverse=True)
    best = ranks[0]

    note = (f"Best channel: **{best.channel}** "
            f"(score {best.score_0_100}/100, expected "
            f"{best.expected_multiple:.1f}x, timing {best.timing_months}mo). "
            f"Runner up: {ranks[1].channel} "
            f"({ranks[1].score_0_100}/100).")

    return ExitChannelRecommendation(
        best_channel=best.channel,
        ranks=ranks,
        partner_note=note,
    )


def render_exit_channel_markdown(r: ExitChannelRecommendation) -> str:
    lines = [
        "# Exit channel selector",
        "",
        f"_{r.partner_note}_",
        "",
        "| Channel | Score | Multiple | Timing (mo) |",
        "|---|---:|---:|---:|",
    ]
    for c in r.ranks:
        lines.append(
            f"| {c.channel} | {c.score_0_100} | "
            f"{c.expected_multiple:.1f}x | {c.timing_months} |"
        )
    lines.extend(["", "## Rationale", ""])
    for c in r.ranks:
        lines.append(f"- **{c.channel}**: {c.rationale}")
    return "\n".join(lines)
