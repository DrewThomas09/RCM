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

THESIS_LIBRARY: Dict[str, InvestmentThesis] = {
    "denial_turnaround": InvestmentThesis(
        name="Denial turnaround",
        criteria=[
            ThesisCriterion("denial_rate", ">", 10.0, weight=2.0),
        ],
    ),
    "ar_optimization": InvestmentThesis(
        name="AR optimization",
        criteria=[
            ThesisCriterion("days_in_ar", ">", 50.0, weight=2.0),
        ],
    ),
    "rural_consolidation": InvestmentThesis(
        name="Rural consolidation",
        # Multi-criterion thesis: small / distressed / cash-constrained /
        # Medicare-heavy. The original single-criterion form
        # (bed_count < 200, weight=1.5) collapsed thousands of rural
        # hospitals onto identical scores; the stable sort then
        # alphabetised by CCN, surfacing only Alabama in the top 50
        # because AL CCNs (010xxx) lead the dataset. Adding distress
        # and payer-mix criteria gives every hospital a continuous
        # score and makes ties rare across states.
        criteria=[
            ThesisCriterion("bed_count", "<", 200, weight=1.0),
            ThesisCriterion("operating_margin", "<", 0.0, weight=1.5),
            ThesisCriterion("days_cash_on_hand", "<", 60.0, weight=1.0),
            ThesisCriterion("medicare_day_pct", ">", 0.45, weight=1.0),
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
    thesis: InvestmentThesis,
    *,
    limit: int = 50,
    max_per_state: Optional[int] = None,
) -> List[ThesisMatch]:
    """Scan HCRIS, score every hospital, return top matches.

    Iterates the full HCRIS dataset (~6,000 hospitals) once. Hospital
    metrics that aren't surfaced as raw HCRIS columns (operating
    margin, days cash on hand, payer mix percentages) are derived
    here so every thesis criterion can be evaluated regardless of
    which underlying field was the source.

    ``max_per_state`` caps the number of hospitals returned per state
    so the top-N list is geographically diverse. The original
    implementation had no per-state cap — combined with stable-sort
    behaviour on tied scores, this surfaced only Alabama in the
    rural-consolidation thesis (because AL CCNs lead the dataset
    alphabetically). When ``max_per_state`` is None the cap is
    auto-computed as max(2, limit / 10), giving roughly even coverage
    across the 50 states + DC.
    """
    try:
        from ..data.hcris import _get_latest_per_ccn, _row_to_dict
    except Exception:  # noqa: BLE001
        return []
    df = _get_latest_per_ccn()
    if df.empty:
        return []

    # Derive any missing scoring fields once at the dataframe level.
    df = _ensure_scoring_features(df)

    state_cap = (
        max(2, int(limit / 10)) if max_per_state is None
        else max(1, int(max_per_state))
    )
    per_state_count: Dict[str, int] = {}

    candidates: List[ThesisMatch] = []
    for _, row in df.iterrows():
        rec = _row_to_dict(row)
        score, per_crit = score_hospital_against_thesis(rec, thesis)
        if score <= 0:
            continue
        candidates.append(ThesisMatch(
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

    # Sort highest-score-first, then admit per-state up to the cap.
    # This preserves the "best deal first" ranking across the result
    # set while preventing any one state from dominating the top-N.
    candidates.sort(key=lambda m: m.score, reverse=True)
    matches: List[ThesisMatch] = []
    overflow: List[ThesisMatch] = []
    for m in candidates:
        if per_state_count.get(m.state, 0) < state_cap:
            matches.append(m)
            per_state_count[m.state] = per_state_count.get(m.state, 0) + 1
            if len(matches) >= int(limit):
                break
        else:
            overflow.append(m)
    # If the per-state cap left us short of the limit (unusual — only
    # happens when the dataset has fewer-than-50 distinct states with
    # qualifying hospitals), backfill from the overflow tier so we
    # still return ``limit`` results.
    if len(matches) < int(limit):
        for m in overflow:
            matches.append(m)
            if len(matches) >= int(limit):
                break
    return matches[:int(limit)]


def _ensure_scoring_features(df):
    """Derive the columns the rural_consolidation thesis scores against.

    HCRIS ships raw revenue/expense/payer-day fields; the multi-
    criterion theses expect derived features (operating_margin,
    days_cash_on_hand, medicare_day_pct). When a dataframe is loaded
    from a slim HCRIS extract that doesn't carry these, compute them
    once here so the per-row scorer never returns 0 just because the
    column is missing.
    """
    import pandas as _pd

    if df is None or df.empty:
        return df
    out = df.copy()
    # Legacy thesis criteria reference ``bed_count``; HCRIS exposes
    # ``beds``. Alias so older theses keep scoring when run through
    # the new multi-state-cap path.
    if "bed_count" not in out.columns and "beds" in out.columns:
        out["bed_count"] = out["beds"]
    rev = _pd.to_numeric(out.get("net_patient_revenue"), errors="coerce")
    opex = _pd.to_numeric(out.get("operating_expenses"), errors="coerce")
    if "operating_margin" not in out.columns:
        import numpy as _np
        margin = (rev - opex) / rev.where(rev > 1e5)
        margin = margin.replace([_np.inf, -_np.inf], _np.nan)
        out["operating_margin"] = margin.where(margin.between(-1.0, 1.0))
    if "medicare_day_pct" not in out.columns:
        med = _pd.to_numeric(out.get("medicare_days"), errors="coerce")
        tot = _pd.to_numeric(out.get("total_patient_days"), errors="coerce")
        out["medicare_day_pct"] = (med / tot.where(tot > 0)).clip(0, 1)
    if "days_cash_on_hand" not in out.columns:
        # HCRIS doesn't carry days-cash-on-hand directly. Use a rough
        # liquidity proxy: hospitals with negative net income relative
        # to opex are likely cash-constrained. Maps NI/opex into a
        # 0–120 days-cash-on-hand band so the criterion scorer can
        # still produce a continuous signal. This is explicitly a
        # diligence proxy, not a precise figure — the data source
        # admin module flags any row that hits the proxy fallback.
        ni = _pd.to_numeric(out.get("net_income"), errors="coerce")
        ratio = (ni / opex.where(opex > 0)).clip(-0.5, 0.5)
        out["days_cash_on_hand"] = (60 + ratio * 120).clip(0, 365)
    return out
