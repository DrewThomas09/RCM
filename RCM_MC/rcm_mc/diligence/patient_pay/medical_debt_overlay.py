"""State-level medical-debt credit-reporting overlay.

State laws restricting or banning medical debt on consumer credit
reports compress the tools available to collect patient balances,
pushing bad-debt reserves higher.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


# State restrictions as of 2026-04. Update quarterly.
_STATE_RESTRICTIONS = {
    "CO": {"status": "BANNED", "effective_year": 2024,
           "description": "Ban on reporting medical debt to consumer CRAs."},
    "IL": {"status": "BANNED", "effective_year": 2024,
           "description": "Banned medical debt on consumer credit reports."},
    "MN": {"status": "RESTRICTED", "effective_year": 2024,
           "description": "Restrictions on medical debt reporting + 180-day delay."},
    "NY": {"status": "BANNED", "effective_year": 2023,
           "description": "Ban on medical debt on credit reports."},
    "NJ": {"status": "BANNED", "effective_year": 2024},
    "VA": {"status": "RESTRICTED", "effective_year": 2024,
           "description": "Restrictions + caps on interest rates."},
}


@dataclass
class MedicalDebtExposure:
    state_code: str
    status: str                 # BANNED | RESTRICTED | NONE
    effective_year: Optional[int]
    bad_debt_uplift_pct: float   # incremental reserve vs. baseline
    severity: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def compute_medical_debt_overlay(
    state_codes: Iterable[str],
) -> List[MedicalDebtExposure]:
    out: List[MedicalDebtExposure] = []
    for raw in state_codes:
        code = (raw or "").strip().upper()
        entry = _STATE_RESTRICTIONS.get(code)
        if entry is None:
            out.append(MedicalDebtExposure(
                state_code=code, status="NONE", effective_year=None,
                bad_debt_uplift_pct=0.0, severity="LOW",
            ))
            continue
        status = entry.get("status", "NONE")
        if status == "BANNED":
            uplift = 0.03     # +3% bad-debt reserve vs. baseline
            sev = "HIGH"
        elif status == "RESTRICTED":
            uplift = 0.015
            sev = "MEDIUM"
        else:
            uplift = 0.0
            sev = "LOW"
        out.append(MedicalDebtExposure(
            state_code=code, status=status,
            effective_year=entry.get("effective_year"),
            bad_debt_uplift_pct=uplift,
            severity=sev,
        ))
    return out
