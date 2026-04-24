"""Point-of-service collection rate benchmarks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


_POS_COLLECTION_BENCHMARKS = {
    "HOSPITAL":  {"p25": 0.08, "p50": 0.15, "p75": 0.25},
    "ASC":       {"p25": 0.40, "p50": 0.60, "p75": 0.75},
    "PHYSICIAN_OFFICE": {"p25": 0.30, "p50": 0.45, "p75": 0.60},
    "MOB":       {"p25": 0.25, "p50": 0.40, "p75": 0.55},
}


@dataclass
class POSCollectionResult:
    specialty: str
    pos_collection_rate: float
    placement: str
    benchmark: Dict[str, float]
    severity: str          # LOW | MEDIUM | HIGH (understaffed RCM)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def benchmark_pos_collection(
    *,
    specialty: str,
    pos_collection_rate: float,
) -> Optional[POSCollectionResult]:
    bench = _POS_COLLECTION_BENCHMARKS.get(specialty.upper())
    if not bench:
        return None
    if pos_collection_rate < bench["p25"]:
        placement = "below_p25"
    elif pos_collection_rate < bench["p50"]:
        placement = "p25_to_p50"
    elif pos_collection_rate < bench["p75"]:
        placement = "p50_to_p75"
    else:
        placement = "above_p75"
    sev = "HIGH" if placement == "below_p25" else (
        "MEDIUM" if placement == "p25_to_p50" else "LOW"
    )
    return POSCollectionResult(
        specialty=specialty.upper(),
        pos_collection_rate=float(pos_collection_rate),
        placement=placement,
        benchmark=bench,
        severity=sev,
    )
