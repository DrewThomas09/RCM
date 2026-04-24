"""EHR migration cost library + integration-velocity estimator.

Seed benchmarks from published case studies: Epic migration is
18-36 months and roughly $100k-$200k per provider + $500k-$1.5M
per bed at the system level.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# Per-provider + per-bed migration cost bands (public aggregates).
_EHR_COST_BANDS = {
    "EPIC":           {"per_provider_usd": 150_000, "per_bed_usd": 800_000,
                       "duration_months": (18, 36)},
    "ORACLE_CERNER":  {"per_provider_usd": 120_000, "per_bed_usd": 650_000,
                       "duration_months": (18, 30)},
    "ATHENAHEALTH":   {"per_provider_usd": 60_000,  "per_bed_usd": 300_000,
                       "duration_months": (12, 18)},
    "ECLINICALWORKS": {"per_provider_usd": 50_000,  "per_bed_usd": 250_000,
                       "duration_months": (10, 18)},
    "MEDITECH":       {"per_provider_usd": 90_000,  "per_bed_usd": 450_000,
                       "duration_months": (15, 24)},
}


@dataclass
class IntegrationVelocity:
    target_ehr: str
    provider_count: int
    bed_count: int
    estimated_cost_usd: float
    estimated_duration_months_low: int
    estimated_duration_months_high: int
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def estimate_ehr_migration(
    *,
    target_ehr: str,
    provider_count: int = 0,
    bed_count: int = 0,
) -> IntegrationVelocity:
    """Estimate the migration cost + duration window for a target
    consolidating onto the named EHR."""
    bands = _EHR_COST_BANDS.get(target_ehr.upper())
    if not bands:
        return IntegrationVelocity(
            target_ehr=target_ehr.upper(),
            provider_count=provider_count, bed_count=bed_count,
            estimated_cost_usd=0.0,
            estimated_duration_months_low=0,
            estimated_duration_months_high=0,
            notes=f"Unknown EHR {target_ehr!r} — no cost band.",
        )
    per_prov = bands["per_provider_usd"] * provider_count
    per_bed = bands["per_bed_usd"] * bed_count
    total = per_prov + per_bed
    low, high = bands["duration_months"]
    return IntegrationVelocity(
        target_ehr=target_ehr.upper(),
        provider_count=provider_count,
        bed_count=bed_count,
        estimated_cost_usd=total,
        estimated_duration_months_low=low,
        estimated_duration_months_high=high,
        notes=(
            f"Public-aggregate anchors: ${bands['per_provider_usd']:,.0f}/"
            f"provider + ${bands['per_bed_usd']:,.0f}/bed. Range "
            f"{low}-{high} months."
        ),
    )
