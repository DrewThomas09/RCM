"""Same-specialty / same-region / same-landlord bankruptcy
contagion detector.

Given a target's specialty, region, and landlord, check against
the known-bankruptcy corpus. Historical cluster patterns:
    - ER/Anesthesia (Envision + APP)
    - MA-risk primary care (Cano + others)
    - REIT-backed hospital (Steward + Prospect)

The corpus here is seeded — a production engine would pull from
the public-deals corpus referenced elsewhere in the platform.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


_BANKRUPTCY_CORPUS = [
    {"name": "Steward Health Care", "year": 2024,
     "specialty": "HOSPITAL", "region": "Northeast + Gulf Coast",
     "landlord": "Medical Properties Trust"},
    {"name": "Prospect Medical", "year": 2025,
     "specialty": "HOSPITAL", "region": "Northeast + West",
     "landlord": "Medical Properties Trust"},
    {"name": "Envision Healthcare", "year": 2023,
     "specialty": "EMERGENCY_MEDICINE", "region": "National",
     "landlord": None},
    {"name": "American Physician Partners", "year": 2023,
     "specialty": "EMERGENCY_MEDICINE", "region": "Southeast",
     "landlord": None},
    {"name": "Cano Health", "year": 2024,
     "specialty": "FAMILY_MEDICINE", "region": "Florida + Southeast",
     "landlord": None},
    {"name": "Wellpath", "year": 2024,
     "specialty": "CORRECTIONAL_HEALTH", "region": "National",
     "landlord": None},
]


@dataclass
class BankruptcyContagionResult:
    target_specialty: str
    target_region: Optional[str]
    target_landlord: Optional[str]
    specialty_matches: List[str] = field(default_factory=list)
    landlord_matches: List[str] = field(default_factory=list)
    region_matches: List[str] = field(default_factory=list)
    severity: str = "LOW"
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def detect_bankruptcy_contagion(
    *,
    target_specialty: str,
    target_region: Optional[str] = None,
    target_landlord: Optional[str] = None,
) -> BankruptcyContagionResult:
    sp = target_specialty.strip().upper().replace(" ", "_")
    sp_matches: List[str] = []
    reg_matches: List[str] = []
    ll_matches: List[str] = []
    for case in _BANKRUPTCY_CORPUS:
        if case["specialty"] == sp:
            sp_matches.append(case["name"])
        if target_region and case.get("region"):
            if _norm(target_region) in _norm(case["region"]) or \
               _norm(case["region"]) in _norm(target_region):
                reg_matches.append(case["name"])
        if target_landlord and case.get("landlord"):
            if _norm(target_landlord) in _norm(case["landlord"]) or \
               _norm(case["landlord"]) in _norm(target_landlord):
                ll_matches.append(case["name"])
    total_hits = (
        len(sp_matches) + len(reg_matches) + len(ll_matches)
    )
    if ll_matches and sp_matches:
        sev = "CRITICAL"
    elif sp_matches:
        sev = "HIGH"
    elif ll_matches or reg_matches:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    narrative_parts: List[str] = []
    if sp_matches:
        narrative_parts.append(
            f"Specialty cluster: {', '.join(sp_matches)}"
        )
    if ll_matches:
        narrative_parts.append(
            f"Same-landlord match: {', '.join(ll_matches)}"
        )
    if reg_matches:
        narrative_parts.append(
            f"Same-region match: {', '.join(reg_matches)}"
        )
    narrative = "; ".join(narrative_parts) or "No corpus match."
    return BankruptcyContagionResult(
        target_specialty=sp,
        target_region=target_region,
        target_landlord=target_landlord,
        specialty_matches=sp_matches,
        landlord_matches=ll_matches,
        region_matches=reg_matches,
        severity=sev,
        narrative=narrative,
    )
