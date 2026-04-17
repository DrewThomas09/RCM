"""Management first sit-down — post-LOI agenda generator.

Different from `first_thirty_minutes` (which is for a screen MI).
This is the FIRST post-LOI working session with the CEO + C-suite,
typically 90 minutes, agenda-driven. A partner does not ask "tell
me about yourself" — they go in with a prepared agenda calibrated
to what the packet already told them.

The agenda has three blocks:

- **Confirm the thesis** — "walk me through the three pillars as
  you see them." Tests whether management owns the thesis or is
  reciting it.
- **Name the risks** — "what keeps you up at night?" A CEO who
  cannot name a risk is selling; a CEO who names three real ones
  is underwritten.
- **Sign up for measurable outcomes** — "by when, by whom, by
  how much?" This is where MIP grants and KPI instrumentation
  get committed.

This module generates a custom agenda per deal based on which
packet signals deserve attention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SitdownContext:
    deal_name: str = "Deal"
    subsector: str = ""
    # Thesis pillars mentioned in the CIM:
    thesis_pillars: List[str] = field(default_factory=list)
    # Packet signals:
    current_denial_rate: float = 0.08
    top_payer_share: float = 0.25
    integration_pct: float = 1.0
    management_score_0_100: int = 70
    commercial_payer_pct: float = 0.50
    historical_failure_matches: List[str] = field(default_factory=list)
    has_pending_fca: bool = False
    has_covenant_lite: bool = False
    leverage: float = 5.5
    claimed_year_1_synergies_m: float = 0.0


@dataclass
class AgendaItem:
    block: str                             # "thesis"/"risks"/"outcomes"
    minutes: int
    topic: str
    question: str
    probe: str                             # what to push on if canned

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block": self.block,
            "minutes": self.minutes,
            "topic": self.topic,
            "question": self.question,
            "probe": self.probe,
        }


@dataclass
class SitdownAgenda:
    deal_name: str
    total_minutes: int
    items: List[AgendaItem] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "total_minutes": self.total_minutes,
            "items": [i.to_dict() for i in self.items],
            "partner_note": self.partner_note,
        }


def _confirm_thesis(ctx: SitdownContext) -> List[AgendaItem]:
    items: List[AgendaItem] = []
    pillars = ctx.thesis_pillars or ["growth", "operational lift",
                                        "M&A"]
    items.append(AgendaItem(
        block="thesis", minutes=15,
        topic=f"Thesis pillars — {', '.join(pillars[:3])}",
        question=("Walk me through your top-three value-creation "
                  "pillars AS YOU SEE THEM. Not the banker's version."),
        probe=("If management recites the CIM verbatim, they do not "
               "own the thesis. Push for 'what would you do first' "
               "and how it differs from the slides."),
    ))
    if ctx.claimed_year_1_synergies_m >= 5:
        items.append(AgendaItem(
            block="thesis", minutes=10,
            topic=(f"Year-1 synergies "
                   f"${ctx.claimed_year_1_synergies_m:.1f}M"),
            question=("Which specific year-1 synergies do YOU commit "
                      "to executing, with named owners and months?"),
            probe=("If they can only speak in totals and not by month "
                   "× owner, the synergies are pro-forma fiction."),
        ))
    return items


def _name_risks(ctx: SitdownContext) -> List[AgendaItem]:
    items: List[AgendaItem] = []
    items.append(AgendaItem(
        block="risks", minutes=10,
        topic="What keeps you up at night",
        question=("What are the three things that could derail this "
                  "business over the next 5 years? Be specific."),
        probe=("A CEO who can't name three real risks is selling. A "
               "CEO who names three you hadn't thought of is "
               "underwritten."),
    ))
    if ctx.current_denial_rate >= 0.10:
        items.append(AgendaItem(
            block="risks", minutes=5,
            topic=(f"Denial rate "
                   f"{ctx.current_denial_rate*100:.1f}%"),
            question=("Top-3 denial reasons by payer, and which ones "
                      "are structural vs fixable in 2026."),
            probe=("If they say 'all of it is fixable,' push for the "
                   "payer-specific reason codes."),
        ))
    if ctx.top_payer_share >= 0.35:
        items.append(AgendaItem(
            block="risks", minutes=5,
            topic=(f"Top payer concentration "
                   f"{ctx.top_payer_share*100:.0f}%"),
            question=("If your top payer walked, what is the 12-month "
                      "plan?"),
            probe=("No answer = they haven't considered it. Partners "
                   "don't accept 'we have a great relationship.'"),
        ))
    if ctx.has_pending_fca:
        items.append(AgendaItem(
            block="risks", minutes=10,
            topic="FCA / regulatory exposure",
            question=("Walk me through every open FCA or CID. Named "
                      "counsel, exposure, timeline."),
            probe=("If they don't have this on a page, they are not "
                   "managing it. Escalate."),
        ))
    if ctx.historical_failure_matches:
        pattern = ctx.historical_failure_matches[0]
        items.append(AgendaItem(
            block="risks", minutes=8,
            topic=f"Historical pattern: {pattern}",
            question=(f"This deal profile pattern-matches {pattern}. "
                      "What makes this different? Specifically."),
            probe=("Three structural mitigations, not three paragraphs "
                   "of differentiation talk."),
        ))
    return items


def _sign_up_outcomes(ctx: SitdownContext) -> List[AgendaItem]:
    items: List[AgendaItem] = []
    items.append(AgendaItem(
        block="outcomes", minutes=10,
        topic="12-month operating plan",
        question=("Name the 5 metrics I should hold you to in the "
                  "first 12 months. With numbers."),
        probe=("If they can't name 5 with specific targets, they're "
               "not ready for a sponsor-owned operating rhythm."),
    ))
    if ctx.management_score_0_100 < 65:
        items.append(AgendaItem(
            block="outcomes", minutes=8,
            topic="Team gaps + hiring plan",
            question=("Which C-suite seats need to be filled or "
                      "upgraded in the next 6 months?"),
            probe=("Founder-CEO defensiveness here is normal. Push "
                   "past it — the ask is about fit-to-scale, not "
                   "about them."),
        ))
    items.append(AgendaItem(
        block="outcomes", minutes=8,
        topic="MIP structure + commitments",
        question=("What MIP structure would make YOU commit through "
                  "exit, and what accelerator do you want?"),
        probe=("Answers that duck the numbers are a red flag for "
               "retention risk."),
    ))
    return items


def build_agenda(ctx: SitdownContext,
                 total_minutes: int = 90) -> SitdownAgenda:
    items = (
        _confirm_thesis(ctx)
        + _name_risks(ctx)
        + _sign_up_outcomes(ctx)
    )
    # Trim to fit total_minutes.
    running = 0
    kept: List[AgendaItem] = []
    for i in items:
        if running + i.minutes > total_minutes:
            break
        kept.append(i)
        running += i.minutes

    by_block = {"thesis": 0, "risks": 0, "outcomes": 0}
    for i in kept:
        by_block[i.block] = by_block.get(i.block, 0) + 1

    if by_block["thesis"] == 0 or by_block["risks"] == 0 \
            or by_block["outcomes"] == 0:
        note = ("Sit-down is incomplete — a partner covers thesis + "
                "risks + outcomes in every first session. Extend the "
                "meeting.")
    else:
        note = (f"{running}-minute agenda: "
                f"{by_block['thesis']} thesis, "
                f"{by_block['risks']} risk, "
                f"{by_block['outcomes']} outcome items. "
                "Partner discipline: do not skip the outcomes block; "
                "that is where you learn whether they can be "
                "sponsor-managed.")

    return SitdownAgenda(
        deal_name=ctx.deal_name,
        total_minutes=running,
        items=kept,
        partner_note=note,
    )


def render_agenda_markdown(a: SitdownAgenda) -> str:
    lines = [
        f"# {a.deal_name} — Management first sit-down",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Total: {a.total_minutes} minutes",
        "",
    ]
    current_block = None
    for i in a.items:
        if i.block != current_block:
            current_block = i.block
            lines.append(f"## Block: {current_block.title()}")
            lines.append("")
        lines.append(f"### ({i.minutes}min) {i.topic}")
        lines.append(f"- **Question:** {i.question}")
        lines.append(f"- **Probe if canned:** {i.probe}")
        lines.append("")
    return "\n".join(lines)
