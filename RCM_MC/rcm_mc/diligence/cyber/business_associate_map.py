"""Business Associate cascade risk.

Given the target's disclosed BA list (clearinghouse, billing, RCM
BPO, telehealth vendor, PACS vendor), cross-reference against the
known-catastrophic BA catalogue in the YAML. Change Healthcare is
the anchor case.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class BACascadeFinding:
    ba_name: str
    matched_catastrophe: Optional[str]
    cascade_risk_multiplier: float
    typical_downtime_days: int
    severity: str = "LOW"
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _normalize(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


def assess_business_associates(
    bas: Iterable[str],
) -> List[BACascadeFinding]:
    """Return one finding per BA. LOW when no match; HIGH or
    CRITICAL when matched to a known catastrophe."""
    data = yaml.safe_load(
        (CONTENT_DIR / "ehr_vendor_risk.yaml").read_text("utf-8")
    )
    catastrophes = data.get("ba_catastrophes") or []
    out: List[BACascadeFinding] = []
    for raw in bas:
        name = (raw or "").strip()
        if not name:
            continue
        n = _normalize(name)
        matched = None
        multiplier = 1.0
        downtime = 2
        for c in catastrophes:
            aliases = [c["name"]] + list(c.get("aka") or [])
            for alias in aliases:
                if _normalize(alias) in n or n in _normalize(alias):
                    matched = c["name"]
                    multiplier = float(c.get(
                        "cascade_risk_multiplier", 1.0,
                    ))
                    downtime = int(c.get("typical_downtime_days", 5))
                    break
            if matched:
                break
        if matched == "Change Healthcare":
            severity = "CRITICAL"
            narrative = (
                f"{name} is identified as Change Healthcare / Optum — "
                f"the 2024 ransomware attack affected ~190M individuals "
                f"and disrupted 94% of US hospitals. Single point of "
                f"cascade risk for this target."
            )
        elif matched:
            severity = "HIGH"
            narrative = (
                f"{name} matches the {matched} BA catastrophe on the "
                f"lattice ({multiplier}x cascade risk multiplier)."
            )
        else:
            severity = "LOW"
            narrative = f"{name} not on the known-catastrophe list."
        out.append(BACascadeFinding(
            ba_name=name,
            matched_catastrophe=matched,
            cascade_risk_multiplier=multiplier,
            typical_downtime_days=downtime,
            severity=severity,
            narrative=narrative,
        ))
    return out
