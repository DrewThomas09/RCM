"""Corporate Practice of Medicine exposure engine.

Given a target's legal structure + state footprint, compute
per-state exposure against the CPOM lattice in
``content/cpom_states.yaml``.

Banding:
  RED     — target's structure appears in a state's
            ``structure_bans`` list (void-ab-initio risk)
  YELLOW  — target's structure appears in
            ``structure_restrictions``, or the state has any
            ``voided_contracts`` entries and an effective date
            has passed
  GREEN   — state on the lattice but no restrictions hit
  UNKNOWN — state not on the lattice

The engine is read-only against the YAML; content freshness is
enforced by a separate test.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from .packet import (
    CONTENT_DIR, CPOMExposure, CPOMReport, RegulatoryBand, load_yaml,
)


# The legal structures the engine understands. Callers pass one as
# ``target_structure`` when computing exposure.
VALID_STRUCTURES = {
    "FRIENDLY_PC_PASS_THROUGH",
    "MSO_PC_MANAGEMENT_FEE",
    "DIRECT_EMPLOYMENT",
    "PROFESSIONAL_LLC",
}


def _days_until(iso: Optional[str], today: Optional[date] = None) -> Optional[int]:
    if not iso:
        return None
    today = today or date.today()
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return None
    return (d - today).days


def _content_is_stale(
    content: Dict[str, Any], max_age_days: int = 60,
    today: Optional[date] = None,
) -> bool:
    today = today or date.today()
    lr = content.get("last_reviewed")
    if not lr:
        return True
    try:
        d = date.fromisoformat(str(lr))
    except ValueError:
        return True
    return (today - d).days > max_age_days


def compute_cpom_exposure(
    *,
    target_structure: str,
    footprint_states: Iterable[str],
    today: Optional[date] = None,
) -> CPOMReport:
    """Walk the state lattice for every state in ``footprint_states``
    and return the :class:`CPOMReport`."""
    structure = target_structure.upper().replace(" ", "_")
    if structure not in VALID_STRUCTURES:
        raise ValueError(
            f"unknown target_structure {target_structure!r}; "
            f"expected one of {sorted(VALID_STRUCTURES)}"
        )
    content = load_yaml("cpom_states")
    lattice = {s["code"]: s for s in content.get("states") or ()}

    per_state: List[CPOMExposure] = []
    for code_raw in footprint_states:
        code = (code_raw or "").strip().upper()
        if not code:
            continue
        entry = lattice.get(code)
        if entry is None:
            per_state.append(CPOMExposure(
                state_code=code, state_name=code,
                statute="(not on lattice)",
                band=RegulatoryBand.UNKNOWN,
            ))
            continue
        bans = set(entry.get("structure_bans") or ())
        restrictions = set(entry.get("structure_restrictions") or ())
        voided = list(entry.get("voided_contracts") or ())
        effective_date = entry.get("effective_date")
        deadline = entry.get("compliance_deadline")
        has_effective = (
            effective_date is not None
            and (today or date.today()) >= date.fromisoformat(str(effective_date))
        )
        if structure in bans:
            band = RegulatoryBand.RED
        elif structure in restrictions and has_effective:
            band = RegulatoryBand.YELLOW
        elif voided and has_effective:
            band = RegulatoryBand.YELLOW
        else:
            band = RegulatoryBand.GREEN
        per_state.append(CPOMExposure(
            state_code=code,
            state_name=str(entry.get("name", code)),
            statute=str(entry.get("statute", "")),
            effective_date=str(effective_date) if effective_date else None,
            compliance_deadline=str(deadline) if deadline else None,
            band=band,
            voided_contracts=voided,
            remediation_cost_usd=float(
                entry.get("remediation_cost_usd", 0) or 0
            ),
            days_to_deadline=_days_until(
                str(deadline) if deadline else None, today,
            ),
        ))

    bands = [s.band for s in per_state]
    if RegulatoryBand.RED in bands:
        overall = RegulatoryBand.RED
    elif RegulatoryBand.YELLOW in bands:
        overall = RegulatoryBand.YELLOW
    elif bands and all(b == RegulatoryBand.UNKNOWN for b in bands):
        overall = RegulatoryBand.UNKNOWN
    else:
        overall = RegulatoryBand.GREEN

    total_rem = sum(
        s.remediation_cost_usd for s in per_state
        if s.band in (RegulatoryBand.RED, RegulatoryBand.YELLOW)
    )
    return CPOMReport(
        target_structure=structure,
        footprint_states=sorted({(s or "").upper() for s in footprint_states}),
        per_state=per_state,
        overall_band=overall,
        total_remediation_usd=total_rem,
        maintenance_required=_content_is_stale(content, today=today),
        content_last_reviewed=str(content.get("last_reviewed") or ""),
    )
