"""State AG enforcement heatmap.

State AGs with active PE-healthcare review regimes + recent
enforcement. Refresh quarterly against state AG press releases.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


_STATE_AG_TIERS = {
    # Aggressive — active PE review regime, recent enforcement
    "CA": {"tier": "HIGH",
           "recent_enforcement_count": 6,
           "notes": "HCCOA-style review + aggressive AG office."},
    "OR": {"tier": "HIGH",
           "recent_enforcement_count": 4,
           "notes": "CPOM + sale-leaseback attention."},
    "MA": {"tier": "HIGH",
           "recent_enforcement_count": 7,
           "notes": "Steward-era enforcement backlog."},
    "CO": {"tier": "HIGH",
           "recent_enforcement_count": 3,
           "notes": "Anesthesia consolidation enforcement."},
    "IN": {"tier": "MEDIUM",
           "recent_enforcement_count": 2,
           "notes": "HB 1666 enforcement ramping."},
    "WA": {"tier": "MEDIUM",
           "recent_enforcement_count": 2,
           "notes": "AG transaction review regime."},
    "NM": {"tier": "MEDIUM",
           "recent_enforcement_count": 2,
           "notes": "HCCOA enforcement."},
    "NY": {"tier": "MEDIUM",
           "recent_enforcement_count": 3,
           "notes": "Pending legislation; AG office active."},
    "CT": {"tier": "MEDIUM",
           "recent_enforcement_count": 1,
           "notes": "HB 5316 rollout."},
}


@dataclass
class StateAGExposure:
    state_code: str
    tier: str                          # HIGH | MEDIUM | LOW
    recent_enforcement_count: int
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def state_ag_enforcement_heatmap(
    states: Iterable[str],
) -> List[StateAGExposure]:
    out: List[StateAGExposure] = []
    for raw in states:
        code = (raw or "").strip().upper()
        entry = _STATE_AG_TIERS.get(code)
        if entry is None:
            out.append(StateAGExposure(
                state_code=code, tier="LOW",
                recent_enforcement_count=0,
                notes="Not on active-enforcement list.",
            ))
            continue
        out.append(StateAGExposure(
            state_code=code,
            tier=entry["tier"],
            recent_enforcement_count=entry["recent_enforcement_count"],
            notes=entry.get("notes", ""),
        ))
    return out
