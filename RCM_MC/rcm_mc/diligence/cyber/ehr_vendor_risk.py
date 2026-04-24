"""EHR vendor risk score lookups."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "ehr_vendor_risk.yaml").read_text("utf-8")
    )


def list_ehr_vendors() -> List[str]:
    return list((_load().get("vendors") or {}).keys())


def ehr_vendor_risk_score(vendor: str) -> Optional[int]:
    """Return the 0-100 systemic risk score for the named EHR
    vendor (EPIC, ORACLE_CERNER, ATHENAHEALTH, ECLINICALWORKS,
    NEXTGEN, MEDITECH). Returns None when the vendor isn't on the
    lattice. Lower = safer."""
    entry = (_load().get("vendors") or {}).get(vendor.upper())
    if not entry:
        return None
    return int(entry.get("systemic_risk_score", 50))


def get_vendor_profile(vendor: str) -> Optional[Dict[str, Any]]:
    """Full vendor record (breach count, concentration multiplier,
    notes). Used by the cyber-score composite."""
    return (_load().get("vendors") or {}).get(vendor.upper())
