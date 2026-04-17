"""Automated "does this data make sense?" checks (Prompt 28).

Three strategies, stacked:

1. **Statistical**: |z-score| vs the comparable cohort > 2.5.
   Catches implausibly low (2% denial rate) or implausibly high
   (90-day AR). Severity bands on the z magnitude.
2. **Causal consistency**: uses the economic ontology. If the parent
   and child metrics on a causal edge move in *opposite* directions
   vs their cohort — e.g., denial_rate unusually low but days_in_ar
   unusually high — flag it. The edges say they should co-move.
3. **Temporal discontinuity**: a >30% YoY change in a metric that
   normally moves <10%/year suggests a methodology change, not a
   real improvement.

These checks run in :func:`detect_anomalies`, which the packet
builder calls from the completeness step. Anomalies of severity
HIGH+ demote the completeness grade by one letter (trust penalty).
Each anomaly also materializes as a ``DATA_ANOMALY`` risk flag with
a targeted diligence question.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ── Enum + dataclass ──────────────────────────────────────────────

class AnomalyType(str, Enum):
    """Category of anomaly — UI renders each with a distinct icon."""
    IMPLAUSIBLY_LOW = "IMPLAUSIBLY_LOW"
    IMPLAUSIBLY_HIGH = "IMPLAUSIBLY_HIGH"
    INCONSISTENT_WITH_RELATED = "INCONSISTENT_WITH_RELATED"
    TEMPORAL_DISCONTINUITY = "TEMPORAL_DISCONTINUITY"


@dataclass
class AnomalyResult:
    """One detected anomaly.

    ``severity`` is a string (``CRITICAL`` / ``HIGH`` / ``MEDIUM``)
    so callers don't have to import ``RiskSeverity`` just to consume
    the result. The builder translates to the enum when it creates
    a risk flag.
    """
    metric_key: str
    value: float
    anomaly_type: AnomalyType
    severity: str = "MEDIUM"
    z_score: float = 0.0
    percentile_rank: float = 0.5
    cohort_mean: float = 0.0
    cohort_std: float = 0.0
    explanation: str = ""
    related_metrics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "value": float(self.value),
            "anomaly_type": self.anomaly_type.value
            if isinstance(self.anomaly_type, AnomalyType)
            else str(self.anomaly_type),
            "severity": self.severity,
            "z_score": float(self.z_score),
            "percentile_rank": float(self.percentile_rank),
            "cohort_mean": float(self.cohort_mean),
            "cohort_std": float(self.cohort_std),
            "explanation": self.explanation,
            "related_metrics": list(self.related_metrics),
        }


# ── Helpers ────────────────────────────────────────────────────────

def _z_severity(z: float) -> str:
    """Map z magnitude to a severity label.

    |z| > 3.5 → CRITICAL. > 3.0 → HIGH. > 2.5 → MEDIUM. Otherwise
    the caller should skip the anomaly entirely (magnitude-below-bar
    is not an anomaly).
    """
    z = abs(z)
    if z > 3.5:
        return "CRITICAL"
    if z > 3.0:
        return "HIGH"
    return "MEDIUM"


def _cohort_stats(comparables: Any, metric_key: str) -> Optional[Dict[str, float]]:
    """Return ``{"mean", "std", "values"}`` for one metric across the
    comparable cohort, or ``None`` when there aren't enough peers.

    Accepts either a :class:`ComparableSet` or a raw list of peer
    dicts. Peers without the metric are silently skipped.
    """
    peers: List[Any] = []
    # Try ``comparables.peers`` first (ComparableSet); fall back to
    # a raw list.
    if hasattr(comparables, "peers"):
        peers = list(comparables.peers or [])
    elif isinstance(comparables, (list, tuple)):
        peers = list(comparables)
    values: List[float] = []
    for p in peers:
        fields_dict = (
            getattr(p, "fields", None)
            if hasattr(p, "fields")
            else (p.get("fields") if isinstance(p, dict) else p)
        )
        if not fields_dict or metric_key not in fields_dict:
            continue
        try:
            v = float(fields_dict[metric_key])
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        values.append(v)
    if len(values) < 4:
        return None   # too few peers for a meaningful z
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return {"mean": mean, "std": math.sqrt(var), "values": values}


def _percentile_rank(value: float, values: Sequence[float]) -> float:
    """Share of cohort strictly less than ``value``. Used for the
    "ranks at Nth percentile" explanation string."""
    if not values:
        return 0.5
    below = sum(1 for v in values if v < value)
    return below / len(values)


# ── Statistical anomaly detector ──────────────────────────────────

def _detect_statistical(
    metric_key: str, value: float, stats: Dict[str, float],
) -> Optional[AnomalyResult]:
    mean = stats["mean"]
    std = stats["std"]
    if std <= 1e-12:
        return None
    z = (value - mean) / std
    if abs(z) <= 2.5:
        return None
    severity = _z_severity(z)
    pct = _percentile_rank(value, stats["values"])
    atype = (
        AnomalyType.IMPLAUSIBLY_LOW if z < 0
        else AnomalyType.IMPLAUSIBLY_HIGH
    )
    direction = "low" if z < 0 else "high"
    explanation = (
        f"The reported {metric_key} of {value:.2f} is unusually {direction} — "
        f"ranks at the {pct * 100:.0f}th percentile of "
        f"{len(stats['values'])} comparable hospitals "
        f"(cohort mean {mean:.2f}, σ {std:.2f}, z={z:+.2f})."
    )
    return AnomalyResult(
        metric_key=metric_key,
        value=float(value),
        anomaly_type=atype,
        severity=severity,
        z_score=float(z),
        percentile_rank=float(pct),
        cohort_mean=float(mean),
        cohort_std=float(std),
        explanation=explanation,
    )


# ── Causal consistency ────────────────────────────────────────────

def _z_for(metric: str, value: Optional[float],
           comparables: Any) -> Optional[float]:
    if value is None:
        return None
    stats = _cohort_stats(comparables, metric)
    if stats is None or stats["std"] <= 1e-12:
        return None
    return (value - stats["mean"]) / stats["std"]


def _detect_causal_inconsistencies(
    observed_metrics: Dict[str, float],
    comparables: Any,
    causal_graph: Any,
) -> List[AnomalyResult]:
    """Walk the causal edges. If a parent is z < -2 and the child is
    z > +2 (or vice versa) on a ``+`` edge, the two metrics are
    moving opposite to how the ontology says they should. Same logic
    mirrored for ``-`` edges.

    Only fires when both endpoints have cohort data — avoids noisy
    alerts on thin peer sets.
    """
    if causal_graph is None or not hasattr(causal_graph, "edges"):
        return []
    out: List[AnomalyResult] = []
    seen_pairs: set = set()
    for edge in causal_graph.edges:
        if edge.parent not in observed_metrics or edge.child not in observed_metrics:
            continue
        key = (edge.parent, edge.child)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        z_p = _z_for(edge.parent, observed_metrics.get(edge.parent),
                     comparables)
        z_c = _z_for(edge.child, observed_metrics.get(edge.child),
                     comparables)
        if z_p is None or z_c is None:
            continue
        # Only flag when both endpoints are themselves meaningfully
        # away from cohort median — small z's are noise.
        if abs(z_p) < 2.0 or abs(z_c) < 2.0:
            continue
        expected_sign = 1.0 if edge.effect_direction == "+" else -1.0
        if (z_p * z_c) * expected_sign >= 0:
            continue   # signs agree with expectation — no anomaly
        severity = "HIGH" if min(abs(z_p), abs(z_c)) >= 2.5 else "MEDIUM"
        out.append(AnomalyResult(
            metric_key=edge.child,
            value=float(observed_metrics[edge.child]),
            anomaly_type=AnomalyType.INCONSISTENT_WITH_RELATED,
            severity=severity,
            z_score=float(z_c),
            explanation=(
                f"{edge.child} (z={z_c:+.2f}) and {edge.parent} "
                f"(z={z_p:+.2f}) are moving opposite to their expected "
                f"causal relationship ('{edge.effect_direction}' edge, "
                f"{edge.mechanism or 'mechanism per ontology'})."
            ),
            related_metrics=[edge.parent],
        ))
    return out


# ── Temporal discontinuity ────────────────────────────────────────

# Metrics that typically drift <10%/year in real operations. A >30%
# jump on one of these is more often a methodology change (vendor
# swap, numerator/denominator redefinition) than a real improvement.
_STABLE_METRICS = frozenset({
    "denial_rate", "final_denial_rate", "net_collection_rate",
    "clean_claim_rate", "days_in_ar", "cost_to_collect",
    "case_mix_index", "bad_debt",
})


def _detect_temporal_discontinuities(
    observed_metrics: Dict[str, float],
    historical_values: Dict[str, Sequence[Any]],
) -> List[AnomalyResult]:
    """A >30% YoY change on a stable metric → ``TEMPORAL_DISCONTINUITY``.

    ``historical_values`` mirrors the
    :func:`rcm_mc.ml.temporal_forecaster.forecast_all` signature —
    metric_key → sequence of ``(period, value)`` tuples.
    """
    out: List[AnomalyResult] = []
    for metric, series in (historical_values or {}).items():
        if metric not in _STABLE_METRICS:
            continue
        if not series:
            continue
        # Extract floats only, in chronological order.
        pts: List[float] = []
        for row in series:
            try:
                pts.append(float(row[1]))
            except (TypeError, ValueError, IndexError):
                continue
        if len(pts) < 2:
            continue
        # Compare the most recent value to the prior.
        latest, prior = pts[-1], pts[-2]
        if prior == 0:
            continue
        pct_change = (latest - prior) / abs(prior)
        if abs(pct_change) < 0.30:
            continue
        severity = "HIGH" if abs(pct_change) >= 0.50 else "MEDIUM"
        out.append(AnomalyResult(
            metric_key=metric,
            value=float(latest),
            anomaly_type=AnomalyType.TEMPORAL_DISCONTINUITY,
            severity=severity,
            z_score=float(pct_change),
            explanation=(
                f"{metric} moved {pct_change * 100:+.1f}% between the last "
                f"two reporting periods ({prior:.2f} → {latest:.2f}). "
                f"This metric typically drifts <10%/year — large jumps "
                f"often indicate a methodology change (vendor swap, "
                f"numerator/denominator redefinition) rather than a real "
                f"operational shift."
            ),
        ))
    return out


# ── Public entry ──────────────────────────────────────────────────

def detect_anomalies(
    observed_metrics: Dict[str, Any],
    comparables: Any = None,
    *,
    causal_graph: Any = None,
    historical_values: Optional[Dict[str, Sequence[Any]]] = None,
) -> List[AnomalyResult]:
    """Full anomaly sweep across all three strategies.

    Returns a severity-sorted list (CRITICAL → HIGH → MEDIUM). Empty
    when there are no comparables and no history — the checks have
    nothing to ground themselves against.

    ``observed_metrics`` accepts either a ``{metric: float}`` dict or
    the packet's ``{metric: ObservedMetric}``. Non-numeric entries
    are silently skipped.
    """
    numeric: Dict[str, float] = {}
    for k, v in (observed_metrics or {}).items():
        if hasattr(v, "value"):
            try:
                numeric[k] = float(v.value)
            except (TypeError, ValueError):
                continue
        else:
            try:
                numeric[k] = float(v)
            except (TypeError, ValueError):
                continue

    anomalies: List[AnomalyResult] = []

    # 1. Statistical — one metric at a time.
    if comparables is not None:
        for metric, value in numeric.items():
            stats = _cohort_stats(comparables, metric)
            if stats is None:
                continue
            result = _detect_statistical(metric, value, stats)
            if result is not None:
                anomalies.append(result)

    # 2. Causal consistency.
    if causal_graph is not None and comparables is not None:
        anomalies.extend(_detect_causal_inconsistencies(
            numeric, comparables, causal_graph,
        ))

    # 3. Temporal discontinuity.
    if historical_values:
        anomalies.extend(_detect_temporal_discontinuities(
            numeric, historical_values,
        ))

    _SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    anomalies.sort(
        key=lambda a: (_SEVERITY_RANK.get(a.severity, 9), a.metric_key),
    )
    return anomalies
