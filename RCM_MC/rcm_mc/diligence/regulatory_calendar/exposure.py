"""Facility → applicable-rule exposure join (P8b).

Maps a provider type (+ state, for state-scoped rules) onto the curated
REGULATORY_EVENTS library so a facility page can answer the first IC-memo
question — "which rulemaking touches this asset's revenue?" — with dated,
sourced events rather than generalities.

Honesty contract: the join is tag-based against the curated library (11
events, refreshed quarterly, each with a Federal Register / agency source
URL). It is a CURATED COVERAGE list, not an exhaustive regulatory inventory
— the panel must say so. State-scoped events (e.g. CT sale-leaseback
phase-out) only fire for facilities in that state, with the scope named in
the match reason.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .calendar import REGULATORY_EVENTS, RegulatoryEvent

# Which specialty tags in the curated library mean "this is about the
# facility type itself" (vs a physician-specialty event).
_PROVIDER_TAGS = {
    "hospital": {"HOSPITAL", "ACUTE_HOSPITAL", "HOPD"},
    "dialysis": {"DIALYSIS"},
}

# Events whose applicability is limited to one state. Encoded here (not in
# the event dataclass) so the curated library stays a plain catalog; the
# join layer owns scoping semantics.
_STATE_SCOPED = {
    "ct_hb_5316_sale_leaseback_phaseout": "CT",
}


@dataclass(frozen=True)
class ExposureMatch:
    event: RegulatoryEvent
    reason: str          # why this event applies to this facility


def applicable_events(provider_type: str = "hospital",
                      state: Optional[str] = None) -> List[ExposureMatch]:
    """Events from the curated library that touch this provider type in this
    state. Sorted soonest-effective first (undated last)."""
    tags = _PROVIDER_TAGS.get(provider_type, set())
    out: List[ExposureMatch] = []
    for e in REGULATORY_EVENTS:
        hit = tags & set(e.affected_specialties)
        if not hit:
            continue
        scope_state = _STATE_SCOPED.get(e.event_id)
        if scope_state:
            if not state or state.upper() != scope_state:
                continue
            reason = (f"{scope_state}-scoped rule; facility is in "
                      f"{scope_state} and is a {provider_type}")
        else:
            reason = f"applies to {provider_type} providers ({'/'.join(sorted(hit))})"
        out.append(ExposureMatch(event=e, reason=reason))
    out.sort(key=lambda m: (m.event.effective_date is None,
                            m.event.effective_date or m.event.publish_date))
    return out


def exposure_summary(matches: List[ExposureMatch]) -> Tuple[float, float]:
    """Σ expected revenue impact %, Σ expected margin impact pp across the
    matched events — a coarse curated-library reading, for the panel header."""
    rev = sum(m.event.expected_revenue_impact_pct for m in matches)
    mgn = sum(m.event.expected_margin_impact_pp for m in matches)
    return rev, mgn
