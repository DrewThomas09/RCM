"""IC voting aggregator — combine partner votes into a decision.

Investment Committees don't operate by pure majority; they operate by
*weighted*, *qualified* votes. A managing partner's vote counts more
than a principal's. A hard "no" with stated reasoning has veto power
in many firms. Abstentions are real signals, not noise.

This module models an IC vote as:

- A set of :class:`Voter` objects (role-weighted).
- A set of :class:`Vote` objects (per voter, with optional dissent).
- A :class:`VoteOutcome` aggregating the decision.

It is not a full IC workflow tool (no persistence, no governance) —
it's a helper for offline what-if analysis and for wiring into the
PartnerReview → decision pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Vote types ──────────────────────────────────────────────────────

VOTE_YES = "yes"
VOTE_NO = "no"
VOTE_ABSTAIN = "abstain"
VOTE_YES_CAVEATS = "yes_with_caveats"

ALL_VOTES = (VOTE_YES, VOTE_NO, VOTE_ABSTAIN, VOTE_YES_CAVEATS)


# ── Roles & weights ─────────────────────────────────────────────────

# Default weights for common IC roles. Firms override per their
# governance; these are starting points.
ROLE_WEIGHTS: Dict[str, float] = {
    "managing_partner": 2.0,
    "partner": 1.5,
    "principal": 1.0,
    "vp": 0.5,
    "observer": 0.0,
}


# ── Dataclasses ─────────────────────────────────────────────────────

@dataclass
class Voter:
    name: str
    role: str = "partner"
    weight: Optional[float] = None         # overrides ROLE_WEIGHTS
    has_veto: bool = False                 # if True, NO vote triggers veto
    recused: bool = False                  # recused from this vote

    def effective_weight(self) -> float:
        if self.recused:
            return 0.0
        if self.weight is not None:
            return float(self.weight)
        return ROLE_WEIGHTS.get(self.role, 1.0)


@dataclass
class Vote:
    voter: str                             # voter name
    vote: str                              # one of ALL_VOTES
    rationale: str = ""                    # required for NO / YES_CAVEATS
    conditions: List[str] = field(default_factory=list)   # for yes_with_caveats


@dataclass
class VoteOutcome:
    decision: str                          # "APPROVED" | "REJECTED" | "TABLED" | "APPROVED_WITH_CONDITIONS"
    yes_weight: float = 0.0
    no_weight: float = 0.0
    abstain_weight: float = 0.0
    caveat_weight: float = 0.0
    total_weight: float = 0.0
    approval_pct: float = 0.0
    veto_triggered: bool = False
    conditions: List[str] = field(default_factory=list)
    dissent_rationales: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "yes_weight": self.yes_weight,
            "no_weight": self.no_weight,
            "abstain_weight": self.abstain_weight,
            "caveat_weight": self.caveat_weight,
            "total_weight": self.total_weight,
            "approval_pct": self.approval_pct,
            "veto_triggered": self.veto_triggered,
            "conditions": list(self.conditions),
            "dissent_rationales": list(self.dissent_rationales),
            "summary": self.summary,
        }


# ── Aggregator ──────────────────────────────────────────────────────

def aggregate_vote(
    voters: List[Voter],
    votes: List[Vote],
    *,
    approval_threshold: float = 0.60,
) -> VoteOutcome:
    """Aggregate a list of votes into a single IC decision.

    Rules:
    - Each voter has a weight. Missing votes from a non-recused voter
      are counted as abstentions (non-counting).
    - A voter with ``has_veto=True`` voting NO triggers ``veto_triggered``
      regardless of percentage.
    - ``yes_with_caveats`` counts as a yes for tally but requires
      all conditions to be incorporated before finalizing.
    - Approval needs approval_pct >= approval_threshold AND no veto.
    - Otherwise: if any NO weight exists with rationale, REJECTED; else
      TABLED (not enough voters / insufficient info).
    """
    by_name = {v.name: v for v in voters}
    outcome = VoteOutcome(decision="TABLED")

    for vote in votes:
        voter = by_name.get(vote.voter)
        if voter is None or voter.recused:
            continue
        w = voter.effective_weight()
        if w == 0.0:
            continue
        outcome.total_weight += w
        if vote.vote == VOTE_YES:
            outcome.yes_weight += w
        elif vote.vote == VOTE_NO:
            outcome.no_weight += w
            if voter.has_veto:
                outcome.veto_triggered = True
            if vote.rationale:
                outcome.dissent_rationales.append(
                    f"{voter.name} ({voter.role}): {vote.rationale}"
                )
        elif vote.vote == VOTE_YES_CAVEATS:
            outcome.caveat_weight += w
            outcome.conditions.extend(vote.conditions)
        elif vote.vote == VOTE_ABSTAIN:
            outcome.abstain_weight += w
        else:
            # Unknown vote — treat as abstain.
            outcome.abstain_weight += w

    # Compute approval percentage on the weighted yes + yes_with_caveats
    # out of non-abstain weight.
    effective_total = (outcome.yes_weight + outcome.no_weight +
                       outcome.caveat_weight)
    if effective_total > 0:
        outcome.approval_pct = (
            (outcome.yes_weight + outcome.caveat_weight) / effective_total
        )

    if outcome.veto_triggered:
        outcome.decision = "REJECTED"
    elif outcome.approval_pct >= approval_threshold and effective_total > 0:
        if outcome.caveat_weight > 0:
            outcome.decision = "APPROVED_WITH_CONDITIONS"
        else:
            outcome.decision = "APPROVED"
    elif outcome.no_weight > 0:
        outcome.decision = "REJECTED"
    else:
        outcome.decision = "TABLED"

    outcome.summary = _summarize(outcome)
    return outcome


def _summarize(outcome: VoteOutcome) -> str:
    lines: List[str] = [
        f"Decision: {outcome.decision}",
        f"Approval: {outcome.approval_pct*100:.1f}%",
        f"Weights — YES: {outcome.yes_weight:.1f}, NO: {outcome.no_weight:.1f}, "
        f"CAVEATS: {outcome.caveat_weight:.1f}, ABSTAIN: {outcome.abstain_weight:.1f}",
    ]
    if outcome.veto_triggered:
        lines.append("Veto-holder voted NO; decision is REJECTED regardless of tally.")
    if outcome.dissent_rationales:
        lines.append("Dissent:")
        for r in outcome.dissent_rationales:
            lines.append(f"  - {r}")
    if outcome.conditions:
        lines.append("Conditions to close:")
        for c in outcome.conditions:
            lines.append(f"  - {c}")
    return "\n".join(lines)


# ── Default IC from a review ────────────────────────────────────────

def default_committee() -> List[Voter]:
    """A sensible default committee for testing / demos."""
    return [
        Voter(name="MP1", role="managing_partner", has_veto=True),
        Voter(name="MP2", role="managing_partner", has_veto=True),
        Voter(name="P1", role="partner"),
        Voter(name="P2", role="partner"),
        Voter(name="PR1", role="principal"),
        Voter(name="VP1", role="vp"),
    ]


def auto_vote_from_review(
    review_recommendation: str,
    voters: List[Voter],
) -> List[Vote]:
    """Produce a synthetic vote list from a PartnerReview recommendation.

    Useful for sensitivity analysis: "if IC votes per the review's
    recommendation, what's the outcome?" Not a substitute for actual
    IC decisions.
    """
    mapping = {
        "PASS": VOTE_NO,
        "PROCEED_WITH_CAVEATS": VOTE_YES_CAVEATS,
        "PROCEED": VOTE_YES,
        "STRONG_PROCEED": VOTE_YES,
    }
    vote_type = mapping.get(review_recommendation, VOTE_ABSTAIN)
    rationale = {
        "PASS": "Model recommends declining.",
        "PROCEED_WITH_CAVEATS": "Model recommends advancing with conditions.",
        "PROCEED": "Model recommends advancing.",
        "STRONG_PROCEED": "Model recommends prioritizing.",
    }.get(review_recommendation, "")
    conditions = (["Address named diligence workstreams"]
                  if vote_type == VOTE_YES_CAVEATS else [])
    return [
        Vote(voter=v.name, vote=vote_type, rationale=rationale,
             conditions=list(conditions))
        for v in voters
    ]
