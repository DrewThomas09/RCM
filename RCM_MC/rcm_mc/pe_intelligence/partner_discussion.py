"""Partner discussion — autogen partner-voice Q&A from a review.

Takes a :class:`PartnerReview` and generates a list of
question-and-answer pairs in the partner's voice. The pattern
mirrors the kind of back-and-forth an associate has with a partner
before IC: "what's the answer if they ask X?" The partner writes the
answer first, then asks the next question.

This is NOT a chatbot; it's a deterministic mapping of findings to
known partner questions + partner-voice responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import HeuristicHit
from .partner_review import PartnerReview
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
)


@dataclass
class DiscussionItem:
    question: str                    # how a partner asks
    answer: str                      # how the partner would answer
    context: str = ""                # why this Q surfaced
    source_id: str = ""              # heuristic id / band metric

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "context": self.context,
            "source_id": self.source_id,
        }


# ── Mapping heuristic hits → Q&A ────────────────────────────────────

_HIT_QA = {
    "medicare_heavy_multiple_ceiling": (
        "What comp clears Medicare-heavy at this multiple?",
        "I don't have one yet. Either the exit multiple resets to 9x or "
        "the deal doesn't clear the hurdle. We'll know after we pull "
        "comparable closed transactions from the 2022-2024 window.",
    ),
    "aggressive_denial_improvement": (
        "Do you believe 300+ bps of denial improvement in 12 months?",
        "Not for year 1. The first 200 bps are credible from front-end "
        "edits; beyond that requires a platform change. We'd discount "
        "years 2+ by 40% in the base case.",
    ),
    "capitation_vbc_uses_ffs_growth": (
        "Is this growth volume-driven or lives-driven?",
        "If it's capitated, it's lives × PMPM and we've modeled it "
        "wrong. Need to rebuild the revenue stack before we bid.",
    ),
    "multiple_expansion_carrying_return": (
        "What does the return look like at a flat multiple?",
        "Meaningfully worse. That's the right sensitivity to run — if "
        "it still clears at flat, we have a deal; if not, we're "
        "betting on the market.",
    ),
    "leverage_too_high_govt_mix": (
        "If CMS cuts 100 bps, do covenants hold?",
        "At this leverage level, no. Either we lower debt at close or "
        "negotiate covenant-lite terms before we sign.",
    ),
    "covenant_headroom_tight": (
        "How tight is the headroom, and what's the single-quarter miss?",
        "Below 20% means one bad quarter triggers a lender conversation. "
        "Budget for a waiver possibility and build the rainy-day buffer.",
    ),
    "insufficient_data_coverage": (
        "What data do we still need from the seller?",
        "Payer mix detail, denial ledger, two years of AR aging. We "
        "should escalate the request before we finalize the bid.",
    ),
    "ar_days_above_peer": (
        "Is the AR a billing or a payer problem?",
        "Diagnose by aging bucket. If it concentrates in 90+ days with "
        "specific payers, that's a payer dispute. If it spreads across "
        "buckets, it's billing operations.",
    ),
    "denial_rate_elevated": (
        "Is there reason-code concentration?",
        "If top-10 codes are ≥60% of denied volume, we have a focused "
        "fix. If they're spread, it's systemic and the lever program "
        "gets harder.",
    ),
    "small_deal_mega_irr": (
        "How does the dispersion look at +1 turn on entry?",
        "Small-deal IRRs are wide. At +1 turn, I'd expect the median "
        "IRR to compress 600-800 bps. Still fundable? Maybe. Still "
        "a standout? Probably not.",
    ),
    "moic_cagr_too_high": (
        "What's the MOIC at a 15% shock to any leg?",
        "If it drops below 2.0x, the story is too fragile. The peer "
        "median on top-quartile healthcare is 25-30% CAGR; we should "
        "stay inside that band.",
    ),
    "covid_relief_unwind": (
        "What's the ex-COVID baseline EBITDA?",
        "Strip PRF, ERC, temporary rate add-ons. That's the number "
        "the exit multiple should be applied to.",
    ),
    "340b_margin_dependency": (
        "If 340B goes away in year 3, what's the bridge?",
        "Rebuild the cashflow with 340B cut in half at year 3. "
        "If the deal breaks, we're not confident in the thesis.",
    ),
    "ehr_migration_planned": (
        "What's the cutover quarter look like?",
        "Every EHR conversion I've watched produced claims lag and "
        "DSO extension. Pre-negotiate covenant relief for the cutover "
        "quarter and model a 9-12 month drag period.",
    ),
}


def _hit_to_qa(hit: HeuristicHit) -> Optional[DiscussionItem]:
    pair = _HIT_QA.get(hit.id)
    if not pair:
        return None
    q, a = pair
    return DiscussionItem(
        question=q, answer=a,
        context=hit.finding, source_id=hit.id,
    )


def _band_to_qa(b: BandCheck) -> Optional[DiscussionItem]:
    if b.verdict not in (VERDICT_STRETCH, VERDICT_OUT_OF_BAND,
                         VERDICT_IMPLAUSIBLE):
        return None
    if b.metric == "irr":
        return DiscussionItem(
            question=f"How do you defend a {b.observed*100:.1f}% IRR?",
            answer=b.partner_note or b.rationale,
            context=b.rationale, source_id=f"band:{b.metric}",
        )
    if b.metric == "exit_multiple":
        return DiscussionItem(
            question=f"Which comp supports a {b.observed:.2f}x exit?",
            answer=b.partner_note or "Reset to the peer ceiling if no comp holds.",
            context=b.rationale, source_id=f"band:{b.metric}",
        )
    if b.metric == "ebitda_margin":
        return DiscussionItem(
            question=f"What explains the {b.observed*100:.1f}% margin?",
            answer=b.partner_note or b.rationale,
            context=b.rationale, source_id=f"band:{b.metric}",
        )
    if b.metric.startswith("lever:"):
        return DiscussionItem(
            question=f"Who owns the {b.metric.split(':',1)[1]} program?",
            answer=b.partner_note or "A named owner with milestones and capex is required.",
            context=b.rationale, source_id=f"band:{b.metric}",
        )
    return None


# ── Orchestrator ────────────────────────────────────────────────────

def build_discussion(review: PartnerReview) -> List[DiscussionItem]:
    """Build partner-voice Q&A from a review.

    Returns questions from heuristic hits + band checks, deduped by
    source id.
    """
    items: List[DiscussionItem] = []
    seen: set = set()
    for hit in review.heuristic_hits:
        qa = _hit_to_qa(hit)
        if qa is not None and qa.source_id not in seen:
            items.append(qa)
            seen.add(qa.source_id)
    for band in review.reasonableness_checks:
        qa = _band_to_qa(band)
        if qa is not None and qa.source_id not in seen:
            items.append(qa)
            seen.add(qa.source_id)
    return items


def render_discussion_markdown(items: List[DiscussionItem]) -> str:
    """Render a discussion as partner-voice Markdown Q&A."""
    if not items:
        return "_No discussion items — nothing in the review triggered a partner Q&A._"
    parts: List[str] = ["# Partner Discussion Q&A", ""]
    for item in items:
        parts.append(f"**Q:** {item.question}")
        parts.append("")
        parts.append(f"**A:** {item.answer}")
        if item.context:
            parts.append("")
            parts.append(f"_Context:_ {item.context}")
        parts.append("")
        parts.append("---")
        parts.append("")
    return "\n".join(parts)
