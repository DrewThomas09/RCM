"""State-by-state sale-leaseback feasibility.

Given a target's state(s), return the per-state feasibility of a
sale-leaseback exit structure. Seeded from
``content/sale_leaseback_blockers.yaml``.

State statuses:
    IN_EFFECT — statute enacted and in force (e.g., MA H.5159).
                Sale-leasebacks restricted or prohibited.
    PHASED    — phased-in ban (CT HB 5316: REIT control bans
                2026-10-01, sale-leaseback bans 2027-10-01).
    PENDING   — proposed legislation, not yet law.
    NONE      — state not on the lattice, no blocker known.
"""
from __future__ import annotations

from typing import Iterable, List

from .types import SaleLeasebackBlocker, load_content


def sale_leaseback_feasibility(
    state_codes: Iterable[str],
) -> List[SaleLeasebackBlocker]:
    """Return one :class:`SaleLeasebackBlocker` per input state.

    Always returns a row for every requested state (NONE status
    when the state isn't on the lattice) so the UI can render a
    uniform matrix."""
    content = load_content("sale_leaseback_blockers")
    lattice = {s["code"]: s for s in content.get("states") or ()}

    out: List[SaleLeasebackBlocker] = []
    for raw in state_codes:
        code = (raw or "").strip().upper()
        if not code:
            continue
        entry = lattice.get(code)
        if entry is None:
            out.append(SaleLeasebackBlocker(
                state_code=code, statute="(not on lattice)",
                status="NONE", feasible=True,
                caveats=["State not on the blocker lattice — no "
                         "known restriction. Verify with counsel."],
            ))
            continue
        status = str(entry.get("status", "NONE"))
        feasible = status not in ("IN_EFFECT", "PHASED")
        caveats: List[str] = []
        if entry.get("impact"):
            caveats.append(str(entry["impact"]))
        if status == "PHASED":
            caveats.append(
                f"Phased — effective {entry.get('effective_date')}, "
                f"second-phase {entry.get('second_phase_date')}. "
                f"Deals must close before the applicable phase date."
            )
            # Still feasible during the window.
            feasible = True
        out.append(SaleLeasebackBlocker(
            state_code=code,
            statute=str(entry.get("statute", "")),
            status=status,
            feasible=feasible,
            caveats=caveats,
        ))
    return out
