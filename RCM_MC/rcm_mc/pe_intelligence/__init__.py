"""PE Intelligence Brain — senior-partner judgment layer over a packet.

This package does not modify any existing calculation. It consumes a
``DealAnalysisPacket`` and emits a ``PartnerReview`` with three kinds
of findings:

1. **Reasonableness bands** — sanity-check IRRs, EBITDA margins, and
   lever realizability against size / payer-mix peer ranges. Flags when
   a model output drifts outside the band a senior partner would
   accept without a very good story.
2. **Heuristics** — codified PE rules of thumb. Medicare-heavy payer
   mix caps exit multiples. Denial improvements above 200 bps/yr are
   aggressive. Capitation plays need different math than FFS. These
   rules live in :mod:`heuristics` and are mirrored in
   ``docs/PE_HEURISTICS.md`` as a living doc.
3. **Narrative commentary** — short paragraphs in the voice a senior
   partner would write in an IC memo: direct, opinionated, with the
   bear case explicit.

The entry point is :func:`partner_review.partner_review`. It is called
from OUTSIDE ``packet_builder`` — the packet stays pure; judgment is
applied downstream. This preserves the "one packet, rendered by many
consumers" invariant.
"""
from __future__ import annotations

from .reasonableness import (
    Band,
    BandCheck,
    check_ebitda_margin,
    check_irr,
    check_lever_realizability,
    check_multiple_ceiling,
    run_reasonableness_checks,
)
from .heuristics import (
    Heuristic,
    HeuristicHit,
    all_heuristics,
    run_heuristics,
)
from .narrative import (
    NarrativeBlock,
    compose_narrative,
)
from .partner_review import (
    PartnerReview,
    partner_review,
)

__all__ = [
    "Band",
    "BandCheck",
    "Heuristic",
    "HeuristicHit",
    "NarrativeBlock",
    "PartnerReview",
    "all_heuristics",
    "check_ebitda_margin",
    "check_irr",
    "check_lever_realizability",
    "check_multiple_ceiling",
    "compose_narrative",
    "partner_review",
    "run_heuristics",
    "run_reasonableness_checks",
]
