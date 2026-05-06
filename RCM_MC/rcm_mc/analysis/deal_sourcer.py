"""Predictive deal sourcing: hospitals that fit your thesis (Prompt 61).

The fund defines an investment thesis (metric criteria + geography +
size range). The platform scores every hospital in HCRIS against that
thesis and returns the top matches ranked by fit score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ThesisCriterion:
    metric_key: str
    operator: str        # ">" | "<" | ">=" | "<=" | "between"
    value: Any           # float or (low, high) tuple for "between"
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "operator": self.operator,
            "value": self.value,
            "weight": float(self.weight),
        }


@dataclass
class InvestmentThesis:
    name: str
    criteria: List[ThesisCriterion] = field(default_factory=list)
    deal_size_range: Optional[Tuple[float, float]] = None
    preferred_regions: List[str] = field(default_factory=list)
    excluded_systems: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "criteria": [c.to_dict() for c in self.criteria],
            "deal_size_range": self.deal_size_range,
            "preferred_regions": list(self.preferred_regions),
            "excluded_systems": list(self.excluded_systems),
        }


@dataclass
class ThesisMatch:
    ccn: str = ""
    name: str = ""
    state: str = ""
    bed_count: int = 0
    score: float = 0.0
    criterion_scores: Dict[str, float] = field(default_factory=dict)
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn, "name": self.name, "state": self.state,
            "bed_count": int(self.bed_count),
            "score": float(self.score),
            "criterion_scores": {k: float(v) for k, v in self.criterion_scores.items()},
            "narrative": self.narrative,
        }


# ── Predefined theses ─────────────────────────────────────────────

# Theses are scored against the HCRIS hospital corpus, so every
# metric_key here MUST resolve to a column emitted by
# ``rcm_mc.data.hcris._row_to_dict`` (or a derived field added by
# ``find_thesis_matches`` below — currently ``commercial_payer_pct``
# computed as 1 - medicare_day_pct - medicaid_day_pct, and
# ``operating_margin_pct`` computed from net_income / net_patient_revenue).
# Reaching for RCM-style metrics like ``denial_rate`` produces a
# zero-match scoreboard because HCRIS doesn't carry those fields.
THESIS_LIBRARY: Dict[str, InvestmentThesis] = {
    "rural_consolidation": InvestmentThesis(
        name="Rural consolidation",
        criteria=[
            # Small-bed independent hospitals are the standard target
            # for roll-up plays.
            ThesisCriterion("beds", "between", (25, 200), weight=2.0),
        ],
    ),
    "regional_platform": InvestmentThesis(
        name="Regional platform",
        criteria=[
            # Mid-size hospitals (200-500 beds) with meaningful
            # commercial mix that anchor a regional roll-up.
            ThesisCriterion("beds", "between", (200, 500), weight=1.5),
            ThesisCriterion("commercial_payer_pct", ">", 0.30, weight=2.0),
        ],
    ),
    "margin_turnaround": InvestmentThesis(
        name="Margin turnaround",
        criteria=[
            # Hospitals running negative operating margins — typical
            # turnaround / value-creation sourcing target.
            ThesisCriterion("operating_margin_pct", "<", 0.0, weight=2.5),
            ThesisCriterion("beds", ">", 100, weight=1.0),
        ],
    ),
    "commercial_payer_mix": InvestmentThesis(
        name="High commercial payer mix",
        criteria=[
            # Hospitals with strong commercial mix — premium asset for
            # PE buyers given commercial-rate uplift potential.
            ThesisCriterion("commercial_payer_pct", ">", 0.50, weight=2.0),
            ThesisCriterion("beds", ">", 150, weight=1.0),
        ],
    ),
    "high_revenue_target": InvestmentThesis(
        name="Large revenue target",
        criteria=[
            # Top-tier revenue scale — often ~$500M+ NPR — for
            # platform-defining acquisitions.
            ThesisCriterion("net_patient_revenue", ">", 500_000_000, weight=2.0),
        ],
    ),
}


# ── Scoring ────────────────────────────────────────────────────────

def _evaluate_criterion(
    criterion: ThesisCriterion, value: Optional[float],
) -> float:
    """Return 0.0–1.0 score for one criterion on one hospital."""
    if value is None:
        return 0.0
    op = criterion.operator
    target = criterion.value
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if op == ">" and isinstance(target, (int, float)):
        return min(1.0, max(0.0, (v - float(target)) / max(abs(float(target)), 1.0)))
    if op == "<" and isinstance(target, (int, float)):
        return min(1.0, max(0.0, (float(target) - v) / max(abs(float(target)), 1.0)))
    if op == "between" and isinstance(target, (list, tuple)) and len(target) == 2:
        lo, hi = float(target[0]), float(target[1])
        if lo <= v <= hi:
            return 1.0
        return 0.0
    return 0.0


def score_hospital_against_thesis(
    hospital_metrics: Dict[str, Any],
    thesis: InvestmentThesis,
) -> Tuple[float, Dict[str, float]]:
    """Return ``(composite_score_0_100, per_criterion_scores)``."""
    total_weight = sum(c.weight for c in thesis.criteria) or 1.0
    per_criterion: Dict[str, float] = {}
    weighted_sum = 0.0
    for c in thesis.criteria:
        val = hospital_metrics.get(c.metric_key)
        if val is None:
            val = hospital_metrics.get("fields", {}).get(c.metric_key)
        s = _evaluate_criterion(c, val)
        per_criterion[c.metric_key] = s
        weighted_sum += s * c.weight
    composite = (weighted_sum / total_weight) * 100.0

    # Region bonus / penalty.
    state = str(hospital_metrics.get("state") or "").upper()
    if thesis.preferred_regions and state:
        if state in [r.upper() for r in thesis.preferred_regions]:
            composite = min(100.0, composite + 10.0)

    # System exclusion.
    system = str(hospital_metrics.get("system_affiliation") or "")
    if thesis.excluded_systems and system:
        if any(ex.lower() in system.lower() for ex in thesis.excluded_systems):
            composite = 0.0

    return float(composite), per_criterion


def find_thesis_matches(
    thesis: InvestmentThesis, *, limit: int = 50,
) -> List[ThesisMatch]:
    """Scan HCRIS, score every hospital, return top matches."""
    try:
        from ..data.hcris import _get_latest_per_ccn, _row_to_dict
    except Exception:  # noqa: BLE001
        return []
    df = _get_latest_per_ccn()
    if df.empty:
        return []
    matches: List[ThesisMatch] = []
    for _, row in df.iterrows():
        rec = _row_to_dict(row)
        # Derived fields that THESIS_LIBRARY criteria reference but
        # HCRIS doesn't ship directly. Computed once per row so the
        # scorer can match on them like any other metric.
        try:
            mc = float(rec.get("medicare_day_pct") or 0)
            md = float(rec.get("medicaid_day_pct") or 0)
            rec["commercial_payer_pct"] = max(0.0, 1.0 - mc - md)
        except (TypeError, ValueError):
            rec["commercial_payer_pct"] = None
        try:
            npr = float(rec.get("net_patient_revenue") or 0)
            ni = float(rec.get("net_income") or 0)
            rec["operating_margin_pct"] = ni / npr if npr > 0 else None
        except (TypeError, ValueError):
            rec["operating_margin_pct"] = None
        score, per_crit = score_hospital_against_thesis(rec, thesis)
        if score <= 0:
            continue
        matches.append(ThesisMatch(
            ccn=str(rec.get("ccn") or ""),
            name=str(rec.get("name") or ""),
            state=str(rec.get("state") or ""),
            bed_count=int(rec.get("beds") or 0),
            score=score,
            criterion_scores=per_crit,
            narrative=(
                f"{rec.get('name') or '?'} scores {score:.0f}/100 "
                f"on '{thesis.name}' thesis."
            ),
        ))
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:int(limit)]
