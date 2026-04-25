"""Top-level entry: run_exit_readiness_packet.

Runs every archetype valuator + every equity-story score + the
readiness-gap analysis, returning a single result dict the
partner pastes into the IC binder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .target import ExitTarget, ExitArchetype, ArchetypeResult
from .valuators import (
    simulate_strategic_exit, simulate_secondary_pe,
    simulate_sponsor_to_sponsor, simulate_take_private,
    simulate_continuation_vehicle, simulate_ipo,
    simulate_dividend_recap,
)
from .equity_story import score_equity_story, EquityStoryScore
from .readiness import identify_readiness_gaps, ReadinessGap


_VALUATORS = {
    ExitArchetype.STRATEGIC: simulate_strategic_exit,
    ExitArchetype.SECONDARY_PE: simulate_secondary_pe,
    ExitArchetype.SPONSOR_TO_SPONSOR: simulate_sponsor_to_sponsor,
    ExitArchetype.TAKE_PRIVATE: simulate_take_private,
    ExitArchetype.CONTINUATION: simulate_continuation_vehicle,
    ExitArchetype.IPO: simulate_ipo,
    ExitArchetype.DIVIDEND_RECAP: simulate_dividend_recap,
}


@dataclass
class ExitReadinessResult:
    target_name: str
    valuations: List[ArchetypeResult] = field(default_factory=list)
    story_scores: List[EquityStoryScore] = field(default_factory=list)
    readiness_gaps: List[ReadinessGap] = field(default_factory=list)
    recommended_archetype: ExitArchetype = ExitArchetype.SECONDARY_PE
    recommended_ev_mm: float = 0.0


def run_exit_readiness_packet(target: ExitTarget) -> ExitReadinessResult:
    valuations: List[ArchetypeResult] = []
    story_scores: List[EquityStoryScore] = []

    for arch, fn in _VALUATORS.items():
        valuations.append(fn(target))
        story_scores.append(score_equity_story(target, arch))

    # Recommended archetype = highest (EV × story_fit × confidence)
    # excluding dividend recap (not an exit).
    by_archetype = {v.archetype: v for v in valuations}
    by_arch_story = {s.archetype: s for s in story_scores}

    best_archetype = ExitArchetype.SECONDARY_PE
    best_score = -1.0
    for arch, val in by_archetype.items():
        if arch == ExitArchetype.DIVIDEND_RECAP:
            continue
        story = by_arch_story.get(arch)
        if not story:
            continue
        composite = (val.enterprise_value_mm * story.fit_score
                     * val.confidence)
        if composite > best_score:
            best_score = composite
            best_archetype = arch

    rec_val = by_archetype[best_archetype]
    return ExitReadinessResult(
        target_name=target.target_name,
        valuations=valuations,
        story_scores=story_scores,
        readiness_gaps=identify_readiness_gaps(target),
        recommended_archetype=best_archetype,
        recommended_ev_mm=rec_val.enterprise_value_mm,
    )
