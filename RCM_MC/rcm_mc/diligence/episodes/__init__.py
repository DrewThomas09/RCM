"""Episode-of-care grouping + service-line P&L.

Rolls raw claim lines up into anchor-triggered episodes (CMS-BPCI
shape: trigger + pre/post window, overlapping windows merged), then
produces cost-per-episode distributions and a service-line P&L — the
unit PE actually underwrites on. Native reimplementation of the slice
of the Tuva episode mart diligence needs.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .grouper import (
    ClaimLine,
    Episode,
    EpisodeDefinition,
    EpisodeGroupingResult,
    ServiceLinePnL,
    group_episodes,
)

__all__ = [
    "ClaimLine",
    "Episode",
    "EpisodeDefinition",
    "EpisodeGroupingResult",
    "ServiceLinePnL",
    "group_episodes",
]
