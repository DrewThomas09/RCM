"""360-feedback aggregation with rater-weighted means.

Each executive receives feedback from multiple raters (boss,
peers, direct reports, self, external). Different rater types
have different reliability for different traits — boss feedback
weights more for strategic clarity; direct-report feedback
weights more for operational execution + people leadership.

This module aggregates per-trait scores across raters using
calibrated weights, then surfaces:

  rater_consistency      across-rater standard deviation per
                         trait (high = "raters disagree" = yellow
                         flag for the partner)
  blind_spot_score       absolute difference between the
                         executive's self-rating and the
                         non-self mean (the bigger the gap, the
                         more the executive is mis-calibrated)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Dict, Iterable, List

from .executive import RaterRole


@dataclass
class RaterFeedback:
    """One rater × one executive × N traits."""
    rater_id: str
    rater_role: RaterRole
    person_id: str
    trait_scores: Dict[str, float] = field(default_factory=dict)


# Calibrated weights per rater role.
_RATER_WEIGHTS: Dict[RaterRole, float] = {
    RaterRole.BOSS: 0.35,
    RaterRole.PEER: 0.25,
    RaterRole.DIRECT_REPORT: 0.25,
    RaterRole.SELF: 0.05,
    RaterRole.EXTERNAL: 0.10,
}


@dataclass
class FeedbackAggregate:
    """Per-executive aggregated feedback."""
    person_id: str
    n_raters: int
    weighted_trait_scores: Dict[str, float] = field(
        default_factory=dict)
    rater_consistency: Dict[str, float] = field(default_factory=dict)
    blind_spot_score: float = 0.0
    yellow_flags: List[str] = field(default_factory=list)


def aggregate_360_feedback(
    person_id: str,
    feedback: Iterable[RaterFeedback],
) -> FeedbackAggregate:
    """Aggregate 360 feedback for one executive.

    Computes:
      • Per-trait weighted mean (rater-role-weighted).
      • Per-trait across-rater standard deviation.
      • Blind-spot score: |self_rating − non_self_mean| averaged
        across traits.
    """
    feedback_list = [f for f in feedback
                     if f.person_id == person_id]
    if not feedback_list:
        return FeedbackAggregate(person_id=person_id, n_raters=0)

    # Collect per-trait raw values
    by_trait: Dict[str, List[tuple]] = {}
    self_scores: Dict[str, float] = {}
    for f in feedback_list:
        weight = _RATER_WEIGHTS.get(f.rater_role, 0.10)
        for trait, val in f.trait_scores.items():
            by_trait.setdefault(trait, []).append(
                (weight, val, f.rater_role))
            if f.rater_role == RaterRole.SELF:
                self_scores[trait] = val

    weighted_means: Dict[str, float] = {}
    consistency: Dict[str, float] = {}
    non_self_means: Dict[str, float] = {}
    for trait, entries in by_trait.items():
        # Weighted mean
        total_w = sum(e[0] for e in entries)
        if total_w > 0:
            weighted_means[trait] = round(
                sum(e[0] * e[1] for e in entries) / total_w, 3)
        # Across-rater stdev (unweighted)
        vals = [e[1] for e in entries]
        if len(vals) > 1:
            consistency[trait] = round(stdev(vals), 3)
        else:
            consistency[trait] = 0.0
        # Non-self mean
        non_self_vals = [e[1] for e in entries
                         if e[2] != RaterRole.SELF]
        if non_self_vals:
            non_self_means[trait] = mean(non_self_vals)

    # Blind-spot score
    if self_scores and non_self_means:
        blind_spots = [
            abs(self_scores[t] - non_self_means[t])
            for t in self_scores
            if t in non_self_means
        ]
        blind_spot = mean(blind_spots) if blind_spots else 0.0
    else:
        blind_spot = 0.0

    # Yellow flags
    flags: List[str] = []
    for trait, std in consistency.items():
        if std >= 1.0:
            flags.append(
                f"Wide rater disagreement on {trait} "
                f"(std {std:.2f}) — partner should triangulate.")
    if blind_spot >= 1.0:
        flags.append(
            f"Self-perception gap of {blind_spot:.2f} pts vs "
            f"non-self raters — partner should explore.")

    return FeedbackAggregate(
        person_id=person_id,
        n_raters=len(feedback_list),
        weighted_trait_scores=weighted_means,
        rater_consistency=consistency,
        blind_spot_score=round(blind_spot, 3),
        yellow_flags=flags,
    )
