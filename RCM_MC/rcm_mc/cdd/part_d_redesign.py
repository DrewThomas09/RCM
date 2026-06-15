"""NEW-29 Part D IRA redesign payer-share allocation.

The Inflation Reduction Act collapsed Part D into three phases and capped
enrollee out-of-pocket spend. For a brand drug the 2025 structure is: the
enrollee pays 100 percent through the deductible, then 25 percent in the initial
phase while the plan pays 65 percent and the manufacturer 10 percent, until
enrollee out-of-pocket reaches the cap (2,000 in 2025, 2,100 in 2026). Above the
cap the enrollee pays nothing; the plan pays 60 percent, the manufacturer 20
percent, and Medicare reinsurance 20 percent, a sharp cut from the pre-IRA 80
percent reinsurance share.

This exhibit allocates a member's annual gross drug cost across the three phases
and four payers, proves the allocation ties to gross spend, and flags when the
enrollee reaches the out-of-pocket cap. The catastrophic reinsurance share is
surfaced because it moved most of the tail risk from Medicare onto plans.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-29"

# Year parameters: deductible and enrollee out-of-pocket cap.
YEAR_PARAMS = {
    2025: {"deductible": 590.0, "oop_cap": 2000.0},
    2026: {"deductible": 615.0, "oop_cap": 2100.0},
}

# Initial-phase brand cost split (enrollee / plan / manufacturer).
INITIAL_ENROLLEE = 0.25
INITIAL_PLAN = 0.65
INITIAL_MANUFACTURER = 0.10

# Catastrophic-phase brand cost split (enrollee / plan / manufacturer / Medicare).
CATA_ENROLLEE = 0.0
CATA_PLAN = 0.60
CATA_MANUFACTURER = 0.20
CATA_MEDICARE = 0.20


def allocate_part_d(
    gross_cost: float,
    *,
    year: int = 2025,
    deductible: float | None = None,
    oop_cap: float | None = None,
) -> Dict[str, Any]:
    """Allocate one member's annual brand drug cost across phases and payers."""
    if gross_cost < 0:
        raise ValueError("gross_cost must be non-negative")
    if year not in YEAR_PARAMS and (deductible is None or oop_cap is None):
        raise ValueError(f"year must be one of {sorted(YEAR_PARAMS)} or pass deductible and oop_cap")
    params = YEAR_PARAMS.get(year, {})
    d = deductible if deductible is not None else params["deductible"]
    cap = oop_cap if oop_cap is not None else params["oop_cap"]

    # Deductible phase: enrollee pays 100 percent up to the deductible.
    deductible_gross = min(gross_cost, d)
    enrollee = deductible_gross
    plan = 0.0
    manufacturer = 0.0
    medicare = 0.0
    remaining = gross_cost - deductible_gross

    # Initial phase: enrollee pays 25 percent until out-of-pocket reaches the cap.
    # Gross needed in the initial phase to take enrollee OOP from the deductible to
    # the cap is (cap - deductible) / 0.25.
    initial_cap_gross = safe_div(cap - d, INITIAL_ENROLLEE, default=0.0)
    initial_gross = min(remaining, initial_cap_gross)
    enrollee += INITIAL_ENROLLEE * initial_gross
    plan += INITIAL_PLAN * initial_gross
    manufacturer += INITIAL_MANUFACTURER * initial_gross
    remaining -= initial_gross

    # Catastrophic phase: enrollee pays nothing; plan / manufacturer / Medicare split.
    cata_gross = remaining
    enrollee += CATA_ENROLLEE * cata_gross
    plan += CATA_PLAN * cata_gross
    manufacturer += CATA_MANUFACTURER * cata_gross
    medicare += CATA_MEDICARE * cata_gross

    cap_reached = gross_cost >= deductible_gross + initial_cap_gross - 1e-9 and initial_cap_gross > 0
    return {
        "year": year,
        "deductible": d,
        "oop_cap": cap,
        "gross_cost": gross_cost,
        "phases": {
            "deductible": {"gross": deductible_gross},
            "initial": {"gross": initial_gross},
            "catastrophic": {"gross": cata_gross},
        },
        "payers": {
            "enrollee": enrollee,
            "plan": plan,
            "manufacturer": manufacturer,
            "medicare": medicare,
        },
        "enrollee_oop": enrollee,
        "cap_reached": cap_reached,
    }


def part_d_redesign(
    gross_cost: float,
    *,
    year: int = 2025,
    deductible: float | None = None,
    oop_cap: float | None = None,
    source: str = "CMS Part D Redesign Program Instructions",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Build the Part D IRA redesign payer-share exhibit for one member."""
    a = allocate_part_d(gross_cost, year=year, deductible=deductible, oop_cap=oop_cap)
    payers = a["payers"]
    phases = a["phases"]

    flags = []
    if a["cap_reached"]:
        flags.append(Flag(
            code="oop_cap_reached",
            severity="info",
            message=(
                f"Enrollee out-of-pocket reaches the {a['oop_cap']:,.0f} cap; spend "
                f"above the cap costs the enrollee nothing."
            ),
            source=source,
        ))
    if phases["catastrophic"]["gross"] > 0:
        cata_medicare = CATA_MEDICARE * phases["catastrophic"]["gross"]
        flags.append(Flag(
            code="catastrophic_reinsurance_shift",
            severity="warn",
            message=(
                f"Catastrophic spend of {phases['catastrophic']['gross']:,.2f} now carries "
                f"only 20 percent Medicare reinsurance ({cata_medicare:,.2f}); plans hold 60 percent."
            ),
            source=source,
        ))

    payer_share = Series(name="Payer share of gross drug cost", kind="bar", points=[
        {"label": "Enrollee", "value": payers["enrollee"]},
        {"label": "Plan", "value": payers["plan"]},
        {"label": "Manufacturer", "value": payers["manufacturer"]},
        {"label": "Medicare reinsurance", "value": payers["medicare"]},
    ])
    by_phase = Series(name="Gross cost by phase", kind="bar", points=[
        {"label": "Deductible", "value": phases["deductible"]["gross"]},
        {"label": "Initial coverage", "value": phases["initial"]["gross"]},
        {"label": "Catastrophic", "value": phases["catastrophic"]["gross"]},
    ])
    oop_detail = Series(name="Enrollee out-of-pocket vs cap", kind="bar", internal_only=True, points=[
        {"label": "Enrollee OOP", "value": a["enrollee_oop"]},
        {"label": "OOP cap", "value": a["oop_cap"]},
    ])

    total_paid = sum(payers.values())
    total_phase = sum(p["gross"] for p in phases.values())
    reconciliations = [
        Reconciliation(
            identity="payer shares sum to gross cost",
            lhs=total_paid,
            rhs=a["gross_cost"],
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="phase gross sums to gross cost",
            lhs=total_phase,
            rhs=a["gross_cost"],
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="enrollee out-of-pocket does not exceed cap",
            lhs=min(a["enrollee_oop"], a["oop_cap"]),
            rhs=a["enrollee_oop"],
            tolerance=1e-6,
        ),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Brand drug. Deductible phase enrollee pays 100 percent; initial phase 25 / 65 / 10 enrollee / plan / manufacturer.",
            "Catastrophic phase 0 / 60 / 20 / 20 enrollee / plan / manufacturer / Medicare reinsurance.",
            "Enrollee out-of-pocket cap is 2,000 in 2025 and 2,100 in 2026; deductible is 590 then 615.",
            "Initial-phase gross to reach the cap is the remaining cap divided by the 25 percent enrollee coinsurance.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Part D IRA redesign payer shares",
        audience=audience,
        series=[payer_share, by_phase, oop_detail],
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"On {a['gross_cost']:,.2f} gross drug cost in {a['year']}, the enrollee pays "
            f"{payers['enrollee']:,.2f}, the plan {payers['plan']:,.2f}, and Medicare "
            f"{payers['medicare']:,.2f}."
        ),
        meta=a,
    )
    return ex.validate()


def _demo() -> Exhibit:
    # 10,000 brand drug cost in 2025: enrollee hits the 2,000 cap, the plan carries
    # the bulk, and Medicare reinsurance is only 20 percent of the catastrophic tail.
    return part_d_redesign(
        10000.0, year=2025,
        source="Demo Part D member shaped to the 2025 redesign",
        vintage="2025",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Part D IRA redesign payer shares",
        audience="both",
        demo=_demo,
    )
)
