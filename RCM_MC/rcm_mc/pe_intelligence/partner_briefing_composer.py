"""Partner briefing composer — cross-module unified brief.

Partner statement: "I don't read ten separate reports.
I read one page that pulls from all of them. If the
brain is smart, it can synthesize across what it already
knows."

Distinct from:
- `deal_one_liner` — one sentence.
- `pre_ic_chair_brief` — 4 bullets for IC chair.
- `ic_memo` / `ic_decision_synthesizer` — full IC deck.

This module is the **one-page partner briefing** that
composes outputs from multiple judgment layers into a
single synthesized document:

- **Verdict line** (from deal one-liner precedence).
- **Subsector lens summary** (one line).
- **Thesis chain health** (confirmed / open / contradicted
  count).
- **Pattern stack** (compound risks named).
- **Pre-mortem strength** (thin / moderate / strong +
  exit outcome narrative).
- **Seller motivation** (if decoded).
- **Negotiation posture** (concession ladder summary).
- **Recommendation** (invest / pass / diligence_more /
  reprice).

The compose function is **opinionated**: it picks the
dominant signal and surfaces it first. It is not a
concatenation — it's a partner-voice synthesis.

### Why this matters

Partners don't consume module output in isolation. A
senior partner reading a failure archetype also wants
to know whether the subsector lens agrees, whether the
thesis chain is broken, and what the pre-mortem reads
like. This module does that stitch-together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BriefingInputs:
    deal_name: str = ""
    subsector: str = ""

    # From deal_one_liner synthesis (recommendation + one-liner).
    recommendation: str = ""
    one_liner: str = ""

    # From subsector_partner_lens.
    subsector_summary: str = ""

    # From thesis_implications_chain.
    thesis: str = ""
    thesis_confirmed: int = 0
    thesis_not_addressed: int = 0
    thesis_contradicted: int = 0

    # From cross_pattern_digest.
    compound_risks: List[str] = field(default_factory=list)
    total_pattern_severity: float = 0.0

    # From pre_mortem_simulator.
    pre_mortem_strength: str = "thin"       # thin/moderate/strong
    pre_mortem_exit_outcome: str = ""

    # From seller_motivation_decoder.
    seller_motivation: str = ""

    # From pricing_concession_ladder.
    walk_away_price_m: Optional[float] = None
    current_seller_ask_m: Optional[float] = None
    concession_ladder_gap_m: Optional[float] = None

    # From failure_archetype_library.
    failure_archetype_matches: List[str] = field(default_factory=list)


@dataclass
class BriefingSection:
    heading: str
    content: str


@dataclass
class PartnerBriefing:
    deal_name: str
    recommendation: str
    one_liner: str
    headline_verdict: str
    sections: List[BriefingSection] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "recommendation": self.recommendation,
            "one_liner": self.one_liner,
            "headline_verdict": self.headline_verdict,
            "sections": [
                {"heading": s.heading, "content": s.content}
                for s in self.sections
            ],
            "partner_note": self.partner_note,
        }


def _format_thesis_health(inputs: BriefingInputs) -> str:
    if not inputs.thesis:
        return "No explicit thesis provided."
    total = (inputs.thesis_confirmed
             + inputs.thesis_not_addressed
             + inputs.thesis_contradicted)
    if total == 0:
        return f"Thesis '{inputs.thesis}': chain not walked."
    parts = [
        f"{inputs.thesis_confirmed} confirmed",
        f"{inputs.thesis_not_addressed} not-addressed",
        f"{inputs.thesis_contradicted} contradicted",
    ]
    return f"Thesis '{inputs.thesis}': {', '.join(parts)}."


def _format_pattern_stack(inputs: BriefingInputs) -> str:
    if not inputs.compound_risks:
        return (
            f"No compound risks; cumulative pattern "
            f"severity {inputs.total_pattern_severity:.2f}."
        )
    return (
        f"Compound risks firing: "
        f"{', '.join(inputs.compound_risks[:3])}. "
        f"Severity {inputs.total_pattern_severity:.2f}."
    )


def _format_pre_mortem(inputs: BriefingInputs) -> str:
    body = f"Pre-mortem strength: {inputs.pre_mortem_strength}."
    if inputs.pre_mortem_exit_outcome:
        body += f" Exit: {inputs.pre_mortem_exit_outcome}"
    return body


def _format_negotiation(inputs: BriefingInputs) -> str:
    if inputs.walk_away_price_m is None \
            or inputs.current_seller_ask_m is None:
        return "Negotiation posture not provided."
    gap = inputs.current_seller_ask_m - inputs.walk_away_price_m
    if gap > 0:
        return (
            f"Seller ask ${inputs.current_seller_ask_m:,.0f}M "
            f"is ${gap:,.0f}M above walk-away. Concession "
            "ladder required or walk."
        )
    if gap < 0:
        return (
            f"Seller at/below walk-away "
            f"${inputs.walk_away_price_m:,.0f}M. Tighten "
            "structure; no price concession needed."
        )
    return "Seller at walk-away. Close on structure."


def _format_archetypes(inputs: BriefingInputs) -> str:
    if not inputs.failure_archetype_matches:
        return "No failure archetype matches."
    return (
        f"Failure archetypes firing: "
        f"{', '.join(inputs.failure_archetype_matches[:3])}."
    )


def _derive_headline_verdict(
    inputs: BriefingInputs,
) -> str:
    rec = (inputs.recommendation or "").lower()
    if rec == "pass":
        return ("PASS — the math doesn't work or the thesis "
                "chain is broken. Walk.")
    if rec == "reprice":
        return ("REPRICE — deal survives only with price or "
                "structural relief. Counter at walk-away "
                "minus.")
    if rec == "diligence_more":
        return ("DILIGENCE MORE — named open items that, if "
                "resolved, flip the verdict. Do not advance "
                "to IC without them.")
    if rec == "invest":
        return ("INVEST — thesis chain tight, patterns "
                "contained, archetype matches explained. "
                "This is the deal we want.")
    if rec == "proceed_with_mitigants":
        return ("PROCEED WITH MITIGANTS — named mitigation "
                "required, but the shape of the deal is "
                "acceptable.")
    return ("Verdict not provided — complete judgment-layer "
            "runs before assembling briefing.")


def compose_partner_briefing(
    inputs: BriefingInputs,
) -> PartnerBriefing:
    sections: List[BriefingSection] = []

    if inputs.subsector and inputs.subsector_summary:
        sections.append(BriefingSection(
            heading=f"Subsector lens — {inputs.subsector}",
            content=inputs.subsector_summary,
        ))

    sections.append(BriefingSection(
        heading="Thesis chain health",
        content=_format_thesis_health(inputs),
    ))

    sections.append(BriefingSection(
        heading="Pattern stack",
        content=_format_pattern_stack(inputs),
    ))

    sections.append(BriefingSection(
        heading="Failure archetypes",
        content=_format_archetypes(inputs),
    ))

    sections.append(BriefingSection(
        heading="Pre-mortem read",
        content=_format_pre_mortem(inputs),
    ))

    if inputs.seller_motivation:
        sections.append(BriefingSection(
            heading="Seller motivation",
            content=(
                f"Dominant: {inputs.seller_motivation} "
                "(see seller_motivation_decoder)."
            ),
        ))

    sections.append(BriefingSection(
        heading="Negotiation posture",
        content=_format_negotiation(inputs),
    ))

    headline = _derive_headline_verdict(inputs)

    # Partner note — pulls the dominant signal.
    if inputs.thesis_contradicted >= 1:
        partner_note = (
            "Briefing reads: thesis chain is broken at a "
            "named link. That is the fact that dominates "
            "all other sections."
        )
    elif inputs.pre_mortem_strength == "strong":
        partner_note = (
            "Briefing reads: pre-mortem constructs a plausible "
            "Y1-Y5 failure narrative. Do not close without "
            "explicit mitigation on each year's root-cause "
            "signal."
        )
    elif len(inputs.compound_risks) >= 2:
        partner_note = (
            "Briefing reads: ≥ 2 compound pattern risks. "
            "Re-price or structural protection required — "
            "do not proceed on merits alone."
        )
    elif inputs.recommendation == "invest":
        partner_note = (
            "Briefing reads: all judgment layers green. "
            "This is the best deal in the pipeline — "
            "advance to IC."
        )
    else:
        partner_note = (
            "Briefing reads: mixed signals. Use the "
            "concession ladder and chair brief to structure "
            "the next round."
        )

    return PartnerBriefing(
        deal_name=inputs.deal_name or "(unnamed deal)",
        recommendation=inputs.recommendation,
        one_liner=inputs.one_liner,
        headline_verdict=headline,
        sections=sections,
        partner_note=partner_note,
    )


def render_partner_briefing_markdown(
    b: PartnerBriefing,
) -> str:
    lines = [
        f"# {b.deal_name} — Partner briefing",
        "",
        f"**Verdict:** {b.headline_verdict}",
        "",
        f"> {b.one_liner}" if b.one_liner else "",
        "",
        f"_{b.partner_note}_",
        "",
    ]
    for s in b.sections:
        lines.append(f"## {s.heading}")
        lines.append("")
        lines.append(s.content)
        lines.append("")
    return "\n".join(lines)
