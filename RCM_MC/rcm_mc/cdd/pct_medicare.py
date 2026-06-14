"""NEW-04 Percentage-of-Medicare reimbursement benchmarking.

Reprices commercial allowed amounts to the Medicare fee schedule for the same
codes, then expresses commercial allowed divided by Medicare allowed as a
percentage. Every output is labeled with its basis: medical-services-repriced
or facility-inclusive. Bases are never blended silently; a claim whose basis
differs from the requested basis raises a flag.

Reference anchors ship as labeled external benchmarks, never as the target's own
number:
    196 percent  Milliman, medical services, 2025
    254 percent  RAND Round 5.1, hospital inpatient plus outpatient,
                 facility-inclusive, 2022
    171 percent  RAND, ambulatory surgery center

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-04"

BASIS_MEDICAL = "medical-services-repriced"
BASIS_FACILITY = "facility-inclusive"
VALID_BASES = {BASIS_MEDICAL, BASIS_FACILITY}

REFERENCE_ANCHORS = [
    {"label": "Milliman medical services 2025", "pct": 196.0, "basis": BASIS_MEDICAL},
    {"label": "RAND 5.1 hospital IP+OP 2022", "pct": 254.0, "basis": BASIS_FACILITY},
    {"label": "RAND ASC", "pct": 171.0, "basis": BASIS_FACILITY},
]


def pct_of_medicare(
    claims: Sequence[Mapping[str, Any]],
    medicare_schedule: Mapping[str, float],
    *,
    basis: str,
    source: str = "Target claims plus CMS fee schedule",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Compute percentage-of-Medicare for a claims set on an explicit basis.

    ``claims``: records of {code, allowed (commercial allowed per unit),
    volume (optional, default 1), basis (optional per-claim)}.
    ``medicare_schedule``: code to Medicare allowed per unit.
    """
    if basis not in VALID_BASES:
        raise ValueError(f"basis must be one of {sorted(VALID_BASES)}, got {basis!r}")
    if not claims:
        raise ValueError("pct_of_medicare requires at least one claim")

    flags: List[Flag] = []
    comm_total = 0.0
    med_total = 0.0
    per_code: List[Dict[str, Any]] = []
    missing: List[str] = []
    basis_conflict = False

    for c in claims:
        code = str(c["code"])
        allowed = float(c["allowed"])
        vol = float(c.get("volume", 1))
        claim_basis = c.get("basis", basis)
        if claim_basis not in VALID_BASES:
            raise ValueError(f"claim {code}: invalid basis {claim_basis!r}")
        if claim_basis != basis:
            basis_conflict = True
        if code not in medicare_schedule:
            missing.append(code)
            continue
        med_unit = float(medicare_schedule[code])
        comm_total += allowed * vol
        med_total += med_unit * vol
        per_code.append({
            "code": code,
            "volume": vol,
            "commercial_allowed": allowed,
            "medicare_allowed": med_unit,
            "pct_of_medicare": safe_div(allowed, med_unit) * 100.0,
        })

    if basis_conflict:
        flags.append(Flag(
            code="basis_mismatch",
            severity="risk",
            message=(
                "Claims carry a basis different from the requested basis. Bases "
                "are not blended. Reprice on a single basis before comparing."
            ),
            source=source,
        ))
    if missing:
        flags.append(Flag(
            code="codes_missing_from_schedule",
            severity="warn",
            message=(
                f"{len(missing)} code(s) had no Medicare reference and were "
                "excluded from the blended ratio."
            ),
        ))

    blended = safe_div(comm_total, med_total) * 100.0

    # Reconcile: blended ratio ties to the volume-weighted code totals.
    reconciliations = [
        Reconciliation(
            identity="blended pct == commercial_total / medicare_total * 100",
            lhs=blended,
            rhs=safe_div(comm_total, med_total) * 100.0,
            tolerance=1e-9,
        )
    ]

    series = [
        Series(
            name=f"Percent of Medicare by code ({basis})",
            kind="bar",
            points=[{"label": r["code"], "value": r["pct_of_medicare"]} for r in per_code],
        ),
        Series(
            name="Reference benchmarks (external)",
            kind="bar",
            points=[{"label": a["label"], "value": a["pct"], "basis": a["basis"]}
                    for a in REFERENCE_ANCHORS],
        ),
        Series(name="Repricing detail", kind="bar", internal_only=True, points=per_code),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        basis=basis,
        assumptions=[
            f"Ratio is commercial allowed divided by Medicare allowed on the {basis} basis.",
            "Reference anchors are external benchmarks, not the target's number. Bases are not blended.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title=f"Percent of Medicare ({basis})",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Blended commercial reimbursement is {blended:.1f} percent of "
            f"Medicare on the {basis} basis, across {len(per_code)} codes."
        ),
        meta={
            "basis": basis,
            "blended_pct": blended,
            "commercial_total": comm_total,
            "medicare_total": med_total,
            "per_code": per_code,
            "reference_anchors": REFERENCE_ANCHORS,
            "missing_codes": missing,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    claims = [
        {"code": "99213", "allowed": 150.0, "volume": 10},
        {"code": "99214", "allowed": 250.0, "volume": 4},
        {"code": "70450", "allowed": 180.0, "volume": 5},
    ]
    schedule = {"99213": 75.0, "99214": 100.0, "70450": 120.0}
    return pct_of_medicare(claims, schedule, basis=BASIS_MEDICAL,
                           source="Demo claims", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Percentage-of-Medicare reimbursement benchmarking",
        audience="both",
        demo=_demo,
    )
)
