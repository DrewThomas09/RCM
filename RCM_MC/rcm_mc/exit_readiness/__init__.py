"""Exit readiness packet — sell-side simulation across 7 archetypes.

2025 healthcare PE exit value reached $156B; the spread between
exit archetypes was 2-3 turns of EBITDA. The partner who matched
the right archetype to the right asset captured the spread; the
one who defaulted to "secondary PE" left value on the table.

This module simulates sell-side outcomes across all seven viable
exit archetypes, scoring each on:

  • Archetype-specific valuation (DCF, LBO model, MOIC-targeted)
  • Equity-story fit — does the asset's story map to what this
    buyer type pays for?
  • Readiness gap — what's missing today that would let the
    partner run this archetype with credibility?

Output is partner-ready: per-archetype valuation + equity-story
score + readiness-gap roadmap.

The seven archetypes:

  1. Strategic corporate — pays revenue/strategic synergy premium
  2. Secondary PE — pays the LBO model price
  3. Sponsor-to-sponsor — secondary PE plus relationship premium
  4. Take-private — public-comp DCF with control premium
  5. Continuation vehicle — NAV-anchored
  6. IPO — public market multiples × float-discount
  7. Dividend recap — debt-funded distribution, no exit

Public API::

    from rcm_mc.exit_readiness import (
        ExitTarget, ExitArchetype,
        simulate_strategic_exit, simulate_secondary_pe,
        simulate_sponsor_to_sponsor, simulate_take_private,
        simulate_continuation_vehicle, simulate_ipo,
        simulate_dividend_recap,
        score_equity_story, identify_readiness_gaps,
        run_exit_readiness_packet,
    )
"""
from .target import ExitTarget, ExitArchetype, ArchetypeResult
from .valuators import (
    simulate_strategic_exit,
    simulate_secondary_pe,
    simulate_sponsor_to_sponsor,
    simulate_take_private,
    simulate_continuation_vehicle,
    simulate_ipo,
    simulate_dividend_recap,
)
from .equity_story import score_equity_story, EquityStoryScore
from .readiness import identify_readiness_gaps, ReadinessGap
from .packet import run_exit_readiness_packet, ExitReadinessResult

__all__ = [
    "ExitTarget", "ExitArchetype", "ArchetypeResult",
    "simulate_strategic_exit", "simulate_secondary_pe",
    "simulate_sponsor_to_sponsor", "simulate_take_private",
    "simulate_continuation_vehicle", "simulate_ipo",
    "simulate_dividend_recap",
    "score_equity_story", "EquityStoryScore",
    "identify_readiness_gaps", "ReadinessGap",
    "run_exit_readiness_packet", "ExitReadinessResult",
]
