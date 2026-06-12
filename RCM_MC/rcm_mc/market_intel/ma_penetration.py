"""Medicare Advantage penetration intelligence — by state.

The payer-intel gap this closes: the desk modeled payer-mix *regimes*
(commercial vs government share) but had no geographic read on the MA
shift — and MA penetration is the geography-level variable that
decides whether a Medicare book behaves like fee-for-service or like
managed care (rate pressure, prior auth, narrow networks, downcoding
risk). This module loads the curated KFF/CMS state penetration cut
(``content/ma_penetration.yaml``) and bands states into the exposure
tiers a deal team actually reasons in.

Band thresholds: SATURATED ≥ 55% (MA plans set the terms), HIGH 45-54%
(at/near the national norm), MODERATE 30-44%, LOW < 30% (traditional
Medicare still dominates). Cut points follow the national average
(~54%) so "HIGH" reads as "normal for 2025", not as an outlier label.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONTENT_DIR = Path(__file__).parent / "content"

_BANDS = [
    ("SATURATED", 55.0),
    ("HIGH", 45.0),
    ("MODERATE", 30.0),
    ("LOW", float("-inf")),
]


@dataclass
class StatePenetration:
    state: str
    penetration_pct: float
    band: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _band(pct: float) -> str:
    for name, floor in _BANDS:
        if pct >= floor:
            return name
    return "LOW"


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "ma_penetration.yaml").read_text("utf-8"))


def national_penetration_pct() -> float:
    return float(_load().get("national_penetration_pct", 0.0))


def list_state_penetration() -> List[StatePenetration]:
    """All states, penetration-descending — the order the exposure
    table reads in."""
    out = [
        StatePenetration(
            state=str(row["state"]).upper(),
            penetration_pct=float(row["penetration_pct"]),
            band=_band(float(row["penetration_pct"])),
        )
        for row in _load().get("states") or ()
    ]
    out.sort(key=lambda s: -s.penetration_pct)
    return out


def get_state(state: str) -> Optional[StatePenetration]:
    key = (state or "").strip().upper()
    for s in list_state_penetration():
        if s.state == key:
            return s
    return None


def band_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {name: 0 for name, _ in _BANDS}
    for s in list_state_penetration():
        counts[s.band] += 1
    return counts


def footprint_exposure(states: List[str]) -> Dict[str, Any]:
    """Average MA penetration across a target's state footprint —
    the one-number geographic MA-exposure read for a deal.

    Unknown state codes are dropped (query-string input; a typo
    shouldn't 500 the page)."""
    rows = [s for s in (get_state(st) for st in states) if s is not None]
    if not rows:
        return {"states": [], "avg_penetration_pct": 0.0, "band": "LOW",
                "vs_national_pp": 0.0}
    avg = sum(s.penetration_pct for s in rows) / len(rows)
    return {
        "states": [s.to_dict() for s in rows],
        "avg_penetration_pct": round(avg, 1),
        "band": _band(avg),
        "vs_national_pp": round(avg - national_penetration_pct(), 1),
    }
