from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Initiative:
    code: str
    title: str
    description: str
    primary_root_causes: List[str]
    typical_levers: List[str]  # which model parameters it tends to move
    typical_time_to_impact_months: int


ROOT_CAUSE_DESCRIPTIONS: Dict[str, str] = {
    "authorization": "Prior authorization / medical management friction (missing auth, auth mismatch, OON).",
    "eligibility": "Eligibility, coverage, COB, member ID, benefit mismatch.",
    "coding": "Coding, documentation, charge capture, modifier/DRG/APC issues.",
    "medical_necessity": "Medical necessity, level of care, clinical validation disputes.",
    "timely_filing": "Filing/appeal timeliness, late submission, appeal deadline misses.",
    "other_admin": "Other administrative denials (format, bundling, duplicate, missing info).",
    "other": "Unclassified / other.",
}

INITIATIVE_LIBRARY: Dict[str, Initiative] = {
    "PA_AUTOMATION": Initiative(
        code="PA_AUTOMATION",
        title="Prior authorization automation + front-end controls",
        description="Automate auth checks, order workflows, and eligibility/benefit verification pre-service.",
        primary_root_causes=["authorization", "eligibility"],
        typical_levers=["idr (Commercial)", "stage_mix (less L2/L3)", "rework cost", "days in A/R"],
        typical_time_to_impact_months=6,
    ),
    "CDI_CODING": Initiative(
        code="CDI_CODING",
        title="CDI / coding quality + charge capture",
        description="Improve documentation, coding edits, and clinical validation response playbooks.",
        primary_root_causes=["coding", "medical_necessity"],
        typical_levers=["idr", "fwr", "stage_mix", "rework cost"],
        typical_time_to_impact_months=9,
    ),
    "WORKQUEUE_RPA": Initiative(
        code="WORKQUEUE_RPA",
        title="Denial workqueue redesign + RPA",
        description="Standardize workqueues, automate low-value touches, and balance capacity to reduce backlog aging.",
        primary_root_causes=["timely_filing", "other_admin", "authorization", "eligibility", "coding"],
        typical_levers=["capacity", "queue_wait_days", "fwr (aging penalty)", "economic drag"],
        typical_time_to_impact_months=4,
    ),
    "CONTRACT_RECOVERY": Initiative(
        code="CONTRACT_RECOVERY",
        title="Contract underpayment recovery program",
        description="Systematic identification and follow-up of contract underpayments; payer escalation paths.",
        primary_root_causes=["other_admin"],
        typical_levers=["underpay recovery", "underpay leakage", "underpay rework cost"],
        typical_time_to_impact_months=6,
    ),
}


def infer_root_cause(denial_type: str) -> str:
    """Heuristic mapping from denial type keys to standardized root cause buckets."""
    t = str(denial_type or "").strip().lower()
    if any(k in t for k in ("auth", "prior", "oonauth", "out-of-network", "oon")):
        return "authorization"
    if any(k in t for k in ("elig", "coverage", "cob", "benefit", "member")):
        return "eligibility"
    if any(k in t for k in ("code", "coding", "modifier", "drg", "apc", "charge")):
        return "coding"
    if any(k in t for k in ("clinical", "med", "necessity", "loc", "validation")):
        return "medical_necessity"
    if any(k in t for k in ("timely", "late", "deadline")):
        return "timely_filing"
    if any(k in t for k in ("admin", "format", "duplicate", "missing")):
        return "other_admin"
    return "other"


def recommended_initiatives_for_root_cause(root_cause: str) -> List[Initiative]:
    rc = str(root_cause or "other").strip().lower()
    out = []
    for init in INITIATIVE_LIBRARY.values():
        if rc in [r.lower() for r in init.primary_root_causes]:
            out.append(init)
    # If no direct match, suggest workqueue/RPA as a universal
    if not out:
        out = [INITIATIVE_LIBRARY["WORKQUEUE_RPA"]]
    return out
