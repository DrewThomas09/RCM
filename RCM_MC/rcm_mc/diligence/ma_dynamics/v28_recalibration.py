"""V28 recalibration engine — the deepest analytic moat.

Given a member roster with diagnosis codes + attributed revenue,
compute per-member and aggregate revenue impact of the V24→V28
transition.

The 837 ingest already carries the diagnosis codes; this module
joins them against the V24/V28 HCC mapping and produces:

    - per-member risk score under V24
    - per-member risk score under V28
    - delta
    - revenue impact (delta × benchmark_per_risk_unit_usd)

Benchmark revenue per risk unit depends on the plan's MA
capitation — typical CMS benchmark is ~$11,000/year/member × the
risk score. Callers pass this; defaults are indicative only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class V28CodeMapping:
    icd10: str
    description: str
    v24_hcc: Optional[int]
    v28_hcc: Optional[int]
    v24_weight: float
    v28_weight: float

    @property
    def weight_delta(self) -> float:
        return self.v28_weight - self.v24_weight


def load_code_map() -> Dict[str, V28CodeMapping]:
    """Load and index the representative V28 code map."""
    data = yaml.safe_load(
        (CONTENT_DIR / "v28_hcc_deltas.yaml").read_text("utf-8")
    )
    out: Dict[str, V28CodeMapping] = {}
    for row in data.get("code_map") or ():
        m = V28CodeMapping(
            icd10=str(row.get("icd10")),
            description=str(row.get("description") or ""),
            v24_hcc=row.get("v24_hcc"),
            v28_hcc=row.get("v28_hcc"),
            v24_weight=float(row.get("v24_weight", 0.0) or 0.0),
            v28_weight=float(row.get("v28_weight", 0.0) or 0.0),
        )
        out[m.icd10.upper()] = m
    return out


@dataclass
class V28MemberImpact:
    member_id: str
    v24_risk_score: float
    v28_risk_score: float
    revenue_impact_usd: float
    removed_code_count: int


@dataclass
class V28Result:
    members_scored: int
    members_missing_codes: int
    aggregate_v24_score: float
    aggregate_v28_score: float
    aggregate_risk_score_reduction_pct: float
    aggregate_revenue_impact_usd: float
    per_member: List[V28MemberImpact] = field(default_factory=list)
    removed_codes_observed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "members_scored": self.members_scored,
            "members_missing_codes": self.members_missing_codes,
            "aggregate_v24_score": self.aggregate_v24_score,
            "aggregate_v28_score": self.aggregate_v28_score,
            "aggregate_risk_score_reduction_pct":
                self.aggregate_risk_score_reduction_pct,
            "aggregate_revenue_impact_usd":
                self.aggregate_revenue_impact_usd,
            "removed_codes_observed":
                list(self.removed_codes_observed),
        }


def compute_v28_recalibration(
    members: Iterable[Dict[str, Any]],
    *,
    benchmark_per_risk_unit_usd: float = 11_000.0,
) -> V28Result:
    """Compute V28 impact for a member roster.

    Each ``member`` dict: {member_id, diagnosis_codes: List[str]}.
    Risk scores are summed HCC weights (capped category; simplified
    version of the CMS risk model that's sufficient for diligence-
    level scenario projection).
    """
    code_map = load_code_map()
    per_member: List[V28MemberImpact] = []
    total_v24 = 0.0
    total_v28 = 0.0
    missing = 0
    removed_observed: set = set()

    for m in members:
        codes = [
            str(c).upper() for c in (m.get("diagnosis_codes") or ())
        ]
        if not codes:
            missing += 1
            continue
        # V24: sum of weights for each HCC hit (one weight per HCC
        # bucket — multiple codes mapping to the same V24 HCC count
        # once).
        v24_hccs: Dict[int, float] = {}
        v28_hccs: Dict[int, float] = {}
        removed_count = 0
        for code in codes:
            mapping = code_map.get(code)
            if mapping is None:
                continue
            if mapping.v24_hcc is not None:
                v24_hccs[mapping.v24_hcc] = max(
                    v24_hccs.get(mapping.v24_hcc, 0.0),
                    mapping.v24_weight,
                )
            if mapping.v28_hcc is not None:
                v28_hccs[mapping.v28_hcc] = max(
                    v28_hccs.get(mapping.v28_hcc, 0.0),
                    mapping.v28_weight,
                )
            elif mapping.v24_hcc is not None:
                # Code lost HCC status under V28.
                removed_count += 1
                removed_observed.add(code)
        v24_score = sum(v24_hccs.values())
        v28_score = sum(v28_hccs.values())
        revenue_impact = (
            (v28_score - v24_score) * benchmark_per_risk_unit_usd
        )
        per_member.append(V28MemberImpact(
            member_id=str(m.get("member_id")),
            v24_risk_score=v24_score,
            v28_risk_score=v28_score,
            revenue_impact_usd=revenue_impact,
            removed_code_count=removed_count,
        ))
        total_v24 += v24_score
        total_v28 += v28_score

    members_scored = len(per_member)
    reduction_pct = (
        (total_v24 - total_v28) / total_v24 if total_v24 > 0 else 0.0
    )
    aggregate_revenue = (
        sum(pm.revenue_impact_usd for pm in per_member)
    )
    return V28Result(
        members_scored=members_scored,
        members_missing_codes=missing,
        aggregate_v24_score=total_v24,
        aggregate_v28_score=total_v28,
        aggregate_risk_score_reduction_pct=reduction_pct,
        aggregate_revenue_impact_usd=aggregate_revenue,
        per_member=per_member,
        removed_codes_observed=sorted(removed_observed),
    )
