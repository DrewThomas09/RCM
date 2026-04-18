"""IC memo header — the first page partner reads.

Partner statement: "Every IC memo has the same first
page. Recommendation up top, thesis in one sentence,
three things that work, three things that don't, three
things that would change my mind. I should be able to
pick up that page and know the deal in 60 seconds."

Distinct from:
- `ic_memo` — full IC deck.
- `ic_decision_synthesizer` — decision-bundle with flip
  signals embedded.
- `deal_one_liner` — single-sentence margin verdict.
- `pre_ic_chair_brief` — 4-bullet chair briefing.

This module produces the **standardized IC-memo header**
— the first page a reader sees. Five blocks in a fixed
order:

1. **Recommendation** — one word (invest / pass /
   diligence-more / reprice / proceed_with_mitigants).
2. **One-sentence thesis** — the deal in one clause.
3. **What works** — top 3 things that support the
   recommendation.
4. **What doesn't** — top 3 risks / breaks.
5. **What would change my mind** — top 3 signals that
   would flip the verdict.

Each list is capped at 3. Partners complain when they
get more; more = fuzzy thinking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VALID_RECS = (
    "invest", "pass", "diligence_more",
    "reprice", "proceed_with_mitigants",
)


@dataclass
class ICHeaderInputs:
    deal_name: str
    recommendation: str = ""
    thesis_one_sentence: str = ""
    what_works_candidates: List[str] = field(default_factory=list)
    what_breaks_candidates: List[str] = field(default_factory=list)
    would_change_my_mind_candidates: List[str] = field(
        default_factory=list
    )


@dataclass
class ICMemoHeader:
    deal_name: str
    recommendation: str
    recommendation_rationale: str
    thesis_one_sentence: str
    what_works: List[str] = field(default_factory=list)
    what_breaks: List[str] = field(default_factory=list)
    would_change_my_mind: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "recommendation": self.recommendation,
            "recommendation_rationale":
                self.recommendation_rationale,
            "thesis_one_sentence":
                self.thesis_one_sentence,
            "what_works": list(self.what_works),
            "what_breaks": list(self.what_breaks),
            "would_change_my_mind":
                list(self.would_change_my_mind),
        }


def _rationale_for(rec: str) -> str:
    return {
        "invest": (
            "Thesis tight, patterns contained, chain "
            "closed — this is the deal we want."
        ),
        "pass": (
            "The math doesn't work or the thesis chain "
            "is broken. Walk."
        ),
        "diligence_more": (
            "Named open items that, if resolved, would "
            "flip the verdict. Advance only with them "
            "closed."
        ),
        "reprice": (
            "Deal survives only with price or structural "
            "relief. Counter at walk-away."
        ),
        "proceed_with_mitigants": (
            "Named mitigation required but the shape of "
            "the deal is acceptable."
        ),
    }.get(rec, "Recommendation not classified.")


def synthesize_ic_memo_header(
    inputs: ICHeaderInputs,
) -> ICMemoHeader:
    rec = inputs.recommendation or "diligence_more"
    if rec not in VALID_RECS:
        rec = "diligence_more"

    # Cap each list to 3 items. Partners complain above 3.
    works = list(inputs.what_works_candidates[:3])
    breaks = list(inputs.what_breaks_candidates[:3])
    flip = list(inputs.would_change_my_mind_candidates[:3])

    # If candidates missing, supply partner-voice placeholders.
    if not works:
        if rec == "invest":
            works = [
                "Operating thesis; partner controls outcome.",
                "Pattern libraries clean.",
                "Management bench adequate or deep.",
            ]
        elif rec == "pass":
            works = [
                "(No material support — recommendation "
                "dominates.)",
            ]
        else:
            works = ["(Populate from packet diligence.)"]
    if not breaks:
        if rec == "pass":
            breaks = [
                "Thesis chain broken at named link.",
                "Compound-pattern risk across libraries.",
                "Pre-mortem reads strong.",
            ]
        elif rec == "invest":
            breaks = ["Execution slippage; multiple compression."]
        else:
            breaks = ["(Populate from pattern scan.)"]
    if not flip:
        flip = [
            "Resolution of the named open items in 'what "
            "doesn't work'.",
            "Seller indemnity or escrow that covers top "
            "bear case.",
            "Re-price to walk-away or seller-structural "
            "concession.",
        ]

    thesis = inputs.thesis_one_sentence or (
        f"{inputs.deal_name} — thesis not yet captured in "
        "one sentence. Partner: write it before IC."
    )

    return ICMemoHeader(
        deal_name=inputs.deal_name,
        recommendation=rec,
        recommendation_rationale=_rationale_for(rec),
        thesis_one_sentence=thesis,
        what_works=works,
        what_breaks=breaks,
        would_change_my_mind=flip,
    )


def render_ic_memo_header_markdown(
    h: ICMemoHeader,
) -> str:
    lines = [
        f"# {h.deal_name} — IC memo header",
        "",
        f"## Recommendation",
        f"**{h.recommendation.upper()}** — "
        f"{h.recommendation_rationale}",
        "",
        f"## Thesis",
        h.thesis_one_sentence,
        "",
        "## What works",
        "",
    ]
    for i, item in enumerate(h.what_works, 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append("## What doesn't")
    lines.append("")
    for i, item in enumerate(h.what_breaks, 1):
        lines.append(f"{i}. {item}")
    lines.append("")
    lines.append("## What would change my mind")
    lines.append("")
    for i, item in enumerate(h.would_change_my_mind, 1):
        lines.append(f"{i}. {item}")
    return "\n".join(lines)


def render_ic_memo_header_text(h: ICMemoHeader) -> str:
    """Plain-text 1-page print format."""
    parts: List[str] = [
        f"{h.deal_name} — IC MEMO",
        f"Recommendation: {h.recommendation.upper()}",
        f"Rationale: {h.recommendation_rationale}",
        f"Thesis: {h.thesis_one_sentence}",
        "",
        "What works:",
    ]
    parts.extend(f"  {i}. {x}"
                 for i, x in enumerate(h.what_works, 1))
    parts.append("")
    parts.append("What doesn't:")
    parts.extend(f"  {i}. {x}"
                 for i, x in enumerate(h.what_breaks, 1))
    parts.append("")
    parts.append("What would change my mind:")
    parts.extend(f"  {i}. {x}"
                 for i, x in enumerate(h.would_change_my_mind, 1))
    return "\n".join(parts)
