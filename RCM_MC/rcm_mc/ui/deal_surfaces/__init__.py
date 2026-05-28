"""Deal-lens analysis surfaces — the /deals/<ccn>/* family.

Implements the 18-surface analysis handoff (Diligence / Models / Market & risk
/ Value creation / Diagnostics) on top of the existing real services
(HCRIS, caduceus score, comparable finder, ebitda bridge, lbo / dcf models,
ml predictors, …). Surfaces ship one at a time; unbuilt surfaces render an
honest "under construction" page rather than fabricating data.
"""
from __future__ import annotations

from ._shell import (
    DealSurface,
    SURFACES,
    SURFACE_BY_PATH,
    SURFACE_GROUPS,
    deal_shell,
    fetch_hospital,
)
from ._stub import render_surface_stub
from .bridge import render_deal_bridge
from .lbo import render_deal_lbo
from .profile import render_deal_profile

__all__ = [
    "DealSurface",
    "SURFACES",
    "SURFACE_BY_PATH",
    "SURFACE_GROUPS",
    "deal_shell",
    "fetch_hospital",
    "render_surface_stub",
    "render_deal_profile",
    "render_deal_bridge",
    "render_deal_lbo",
]
