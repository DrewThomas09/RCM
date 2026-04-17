"""Deal Analysis Packet — canonical dataclass for one deal's full analysis.

The packet is the spine of the product. UI routes, API endpoints, and
exports render from *this* object — nothing renders independently. If a
number shows up on a page, it came from here.

Why one object instead of twelve:
- Partners expect the variance drill, the bridge, and the risk flags to
  tell the same story. If each is computed ad-hoc per-route, numbers
  drift — we spent two quarters chasing reconciliations like that.
- Single object = single snapshot. A cached packet is a frozen picture
  of "what we knew about this deal at time T". Partners can diff two
  runs cleanly.
- Serializability is load-bearing: every nested section is
  JSON-round-trippable so the SQLite cache can hold a compressed blob
  instead of re-computing.

Numeric formatting conventions follow CLAUDE.md: dollars 2dp, pct 1dp,
ratios 4dp. We don't round inside the dataclass (storage keeps full
precision) — formatting is the renderer's job. But ``to_json`` collapses
``float('nan')`` / ``float('inf')`` to ``None`` so JSON is valid.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, asdict, fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Enums ─────────────────────────────────────────────────────────────

class SectionStatus(str, Enum):
    """Per-section completion signal. A packet is still valid when a
    section is INCOMPLETE or FAILED — downstream renderers check
    ``status`` before reading content.
    """
    OK = "OK"
    INCOMPLETE = "INCOMPLETE"  # partial data, useable with caveats
    FAILED = "FAILED"           # could not compute at all
    SKIPPED = "SKIPPED"         # deliberately not computed (e.g. skip_simulation)


class MetricSource(str, Enum):
    """Provenance source for a single metric value in the merged profile.

    Ordering (high → low confidence):
      OBSERVED > EXTRACTED > AUTO_POPULATED > PREDICTED > BENCHMARK.

    - ``OBSERVED``: analyst entered directly, or Phase-2 actuals import.
    - ``EXTRACTED``: parsed from a seller file via the document reader
      (Prompt 25). Roughly partner-tier because they came out of the
      seller's own system, but column-mapping can misfire — the
      reader attaches a ``confidence`` and a source cell reference.
    - ``AUTO_POPULATED``: pulled from a public source (HCRIS, Care
      Compare, IRS 990) via :func:`rcm_mc.data.auto_populate.auto_populate`
      (Prompt 23). Public data is reliable but lagged + not deal-specific.
    - ``PREDICTED``: ridge-predictor inference from the comparable set.
    - ``BENCHMARK``: fell back to the registry P50 with no
      hospital-specific signal.
    """
    OBSERVED = "OBSERVED"
    EXTRACTED = "EXTRACTED"
    AUTO_POPULATED = "AUTO_POPULATED"
    PREDICTED = "PREDICTED"
    BENCHMARK = "BENCHMARK"
    UNKNOWN = "UNKNOWN"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DiligencePriority(str, Enum):
    P0 = "P0"  # IC blocker
    P1 = "P1"  # confirm before signing
    P2 = "P2"  # nice-to-have


# ── Serialization helpers ─────────────────────────────────────────────

def _json_safe(v: Any) -> Any:
    """Recursively coerce a value into JSON-serializable primitives.

    NaN and infinity → None (JSON spec rejects them). Dates → ISO.
    Enums → their value. Dataclasses → their dict form.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int,)):
        return int(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return float(v)
    if isinstance(v, str):
        return v
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, (datetime,)):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _json_safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_json_safe(x) for x in v]
    if is_dataclass(v):
        if hasattr(v, "to_dict"):
            return v.to_dict()
        return _json_safe(asdict(v))
    # numpy scalars, Decimal, etc.
    try:
        import numpy as _np  # optional
        if isinstance(v, _np.integer):
            return int(v)
        if isinstance(v, _np.floating):
            f = float(v)
            return None if math.isnan(f) or math.isinf(f) else f
        if isinstance(v, _np.bool_):
            return bool(v)
    except ImportError:  # pragma: no cover
        pass
    # Last resort: str() so JSON at least succeeds.
    return str(v)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or s == "":
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _parse_datetime(s: Optional[str]) -> Optional[datetime]:
    if s is None or s == "":
        return None
    try:
        return datetime.fromisoformat(str(s))
    except ValueError:
        return None


# ── Section 1: Hospital profile ───────────────────────────────────────

@dataclass
class HospitalProfile:
    bed_count: Optional[int] = None
    region: Optional[str] = None
    state: Optional[str] = None
    payer_mix: Dict[str, float] = field(default_factory=dict)
    teaching_status: Optional[str] = None
    urban_rural: Optional[str] = None
    system_affiliation: Optional[str] = None
    cms_provider_id: Optional[str] = None   # a.k.a. CCN
    ein: Optional[str] = None
    npi: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HospitalProfile":
        d = dict(d or {})
        bc = d.get("bed_count")
        return cls(
            bed_count=int(bc) if bc not in (None, "") else None,
            region=d.get("region"),
            state=d.get("state"),
            payer_mix={str(k): float(v) for k, v in (d.get("payer_mix") or {}).items()},
            teaching_status=d.get("teaching_status"),
            urban_rural=d.get("urban_rural"),
            system_affiliation=d.get("system_affiliation"),
            cms_provider_id=d.get("cms_provider_id"),
            ein=d.get("ein"),
            npi=d.get("npi"),
            name=d.get("name"),
        )


# ── Section 2: Observed inputs ────────────────────────────────────────

@dataclass
class ObservedMetric:
    value: float
    source: str = "USER_INPUT"   # USER_INPUT | HCRIS | IRS990 | ...
    source_detail: str = ""
    as_of_date: Optional[date] = None
    quality_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": _json_safe(self.value),
            "source": self.source,
            "source_detail": self.source_detail,
            "as_of_date": self.as_of_date.isoformat() if self.as_of_date else None,
            "quality_flags": list(self.quality_flags),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ObservedMetric":
        return cls(
            value=float(d.get("value") or 0.0),
            source=str(d.get("source") or "USER_INPUT"),
            source_detail=str(d.get("source_detail") or ""),
            as_of_date=_parse_date(d.get("as_of_date")),
            quality_flags=list(d.get("quality_flags") or []),
        )


# ── Section 3: Completeness assessment ────────────────────────────────

@dataclass
class MissingField:
    metric_key: str
    display_name: str = ""
    category: str = ""
    ebitda_sensitivity_rank: int = 999

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    @classmethod
    def from_dict(cls, d: Any) -> "MissingField":
        # Tolerate legacy string rows (`missing_fields=["days_in_ar", ...]`).
        if isinstance(d, str):
            return cls(metric_key=d)
        d = d or {}
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            display_name=str(d.get("display_name") or ""),
            category=str(d.get("category") or ""),
            ebitda_sensitivity_rank=int(d.get("ebitda_sensitivity_rank") or 999),
        )


@dataclass
class StaleField:
    metric_key: str
    observed_date: Optional[date] = None
    days_stale: int = 0
    stale_threshold: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "observed_date": self.observed_date.isoformat() if self.observed_date else None,
            "days_stale": int(self.days_stale),
            "stale_threshold": int(self.stale_threshold),
        }

    @classmethod
    def from_dict(cls, d: Any) -> "StaleField":
        if isinstance(d, str):
            return cls(metric_key=d)
        d = d or {}
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            observed_date=_parse_date(d.get("observed_date")),
            days_stale=int(d.get("days_stale") or 0),
            stale_threshold=int(d.get("stale_threshold") or 0),
        )


@dataclass
class ConflictField:
    metric_key: str
    values: List[Dict[str, Any]] = field(default_factory=list)   # [{source, value, as_of}]
    chosen_source: str = ""
    chosen_value: Optional[float] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "values": _json_safe(self.values),
            "chosen_source": self.chosen_source,
            "chosen_value": _json_safe(self.chosen_value),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Any) -> "ConflictField":
        if isinstance(d, str):
            return cls(metric_key=d)
        d = d or {}
        cv = d.get("chosen_value")
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            values=list(d.get("values") or []),
            chosen_source=str(d.get("chosen_source") or ""),
            chosen_value=float(cv) if cv is not None else None,
            reason=str(d.get("reason") or ""),
        )


@dataclass
class QualityFlag:
    metric_key: str
    flag_type: str = ""   # OUT_OF_RANGE | SUSPICIOUS_CHANGE | MISSING_BREAKDOWN | STALE | BENCHMARK_OUTLIER | PAYER_MIX_INCOMPLETE
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""
    value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "flag_type": self.flag_type,
            "severity": self.severity.value,
            "detail": self.detail,
            "value": _json_safe(self.value),
        }

    @classmethod
    def from_dict(cls, d: Any) -> "QualityFlag":
        d = d or {}
        v = d.get("value")
        sev = d.get("severity") or "LOW"
        try:
            severity = RiskSeverity(sev)
        except ValueError:
            severity = RiskSeverity.LOW
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            flag_type=str(d.get("flag_type") or ""),
            severity=severity,
            detail=str(d.get("detail") or ""),
            value=float(v) if v is not None else None,
        )


@dataclass
class CompletenessAssessment:
    """Answers "what do we know, what's missing, can we trust it?"

    Field shape: ``missing_fields``/``stale_fields``/``conflicting_fields``
    hold structured dataclasses (``MissingField``, etc.). For backward
    compatibility, constructors tolerate plain strings — they coerce to
    the structured form with just ``metric_key`` populated.
    """
    coverage_pct: float = 0.0               # [0,1]
    total_metrics: int = 0
    observed_count: int = 0
    missing_fields: List[MissingField] = field(default_factory=list)
    stale_fields: List[StaleField] = field(default_factory=list)
    conflicting_fields: List[ConflictField] = field(default_factory=list)
    quality_flags: List[QualityFlag] = field(default_factory=list)
    #: Ranked by EBITDA sensitivity (most impactful missing field first).
    missing_ranked_by_sensitivity: List[str] = field(default_factory=list)
    #: Same as ``missing_ranked_by_sensitivity``; retained for v1 callers.
    missing_fields_ranked: List[str] = field(default_factory=list)
    grade: str = ""                          # A / B / C / D
    status: SectionStatus = SectionStatus.OK
    reason: str = ""
    #: Prompt 28 — :class:`AnomalyResult` dicts surfaced alongside the
    #: completeness assessment. Anomalies of severity HIGH+ demote the
    #: grade by one letter. Stored as dicts for cheap JSON round-trip.
    anomalies: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Coerce legacy string inputs ([`"denial_rate"`, ...]) to structured form.
        self.missing_fields = [
            v if isinstance(v, MissingField) else MissingField.from_dict(v)
            for v in self.missing_fields
        ]
        self.stale_fields = [
            v if isinstance(v, StaleField) else StaleField.from_dict(v)
            for v in self.stale_fields
        ]
        self.conflicting_fields = [
            v if isinstance(v, ConflictField) else ConflictField.from_dict(v)
            for v in self.conflicting_fields
        ]
        self.quality_flags = [
            v if isinstance(v, QualityFlag) else QualityFlag.from_dict(v)
            for v in self.quality_flags
        ]
        # Keep the two "ranked" fields in sync so old callers still work.
        if self.missing_ranked_by_sensitivity and not self.missing_fields_ranked:
            self.missing_fields_ranked = list(self.missing_ranked_by_sensitivity)
        elif self.missing_fields_ranked and not self.missing_ranked_by_sensitivity:
            self.missing_ranked_by_sensitivity = list(self.missing_fields_ranked)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_pct": _json_safe(self.coverage_pct),
            "total_metrics": int(self.total_metrics),
            "observed_count": int(self.observed_count),
            "missing_fields": [m.to_dict() for m in self.missing_fields],
            "stale_fields": [s.to_dict() for s in self.stale_fields],
            "conflicting_fields": [c.to_dict() for c in self.conflicting_fields],
            "quality_flags": [q.to_dict() for q in self.quality_flags],
            "missing_ranked_by_sensitivity": list(self.missing_ranked_by_sensitivity),
            "missing_fields_ranked": list(self.missing_fields_ranked),
            "grade": self.grade,
            "status": self.status.value,
            "reason": self.reason,
            "anomalies": [dict(a) for a in (self.anomalies or [])],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompletenessAssessment":
        return cls(
            coverage_pct=float(d.get("coverage_pct") or 0.0),
            total_metrics=int(d.get("total_metrics") or 0),
            observed_count=int(d.get("observed_count") or 0),
            missing_fields=[MissingField.from_dict(m) for m in (d.get("missing_fields") or [])],
            stale_fields=[StaleField.from_dict(s) for s in (d.get("stale_fields") or [])],
            conflicting_fields=[ConflictField.from_dict(c) for c in (d.get("conflicting_fields") or [])],
            quality_flags=[QualityFlag.from_dict(q) for q in (d.get("quality_flags") or [])],
            missing_ranked_by_sensitivity=list(d.get("missing_ranked_by_sensitivity") or []),
            missing_fields_ranked=list(d.get("missing_fields_ranked") or []),
            grade=str(d.get("grade") or ""),
            status=SectionStatus(d.get("status") or "OK"),
            reason=str(d.get("reason") or ""),
            anomalies=[dict(a) for a in (d.get("anomalies") or [])],
        )


# ── Section 4: Comparable set ─────────────────────────────────────────

@dataclass
class ComparableHospital:
    id: str
    similarity_score: float
    similarity_components: Dict[str, float] = field(default_factory=dict)
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "similarity_score": _json_safe(self.similarity_score),
            "similarity_components": {k: _json_safe(v) for k, v in self.similarity_components.items()},
            "fields": _json_safe(self.fields),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComparableHospital":
        return cls(
            id=str(d.get("id") or ""),
            similarity_score=float(d.get("similarity_score") or 0.0),
            similarity_components={k: float(v) for k, v in (d.get("similarity_components") or {}).items()},
            fields=dict(d.get("fields") or {}),
        )


@dataclass
class ComparableSet:
    peers: List[ComparableHospital] = field(default_factory=list)
    features_used: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    robustness_check: Dict[str, Any] = field(default_factory=dict)
    status: SectionStatus = SectionStatus.OK
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peers": [p.to_dict() for p in self.peers],
            "features_used": list(self.features_used),
            "weights": {k: _json_safe(v) for k, v in self.weights.items()},
            "robustness_check": _json_safe(self.robustness_check),
            "status": self.status.value,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComparableSet":
        return cls(
            peers=[ComparableHospital.from_dict(p) for p in (d.get("peers") or [])],
            features_used=list(d.get("features_used") or []),
            weights={k: float(v) for k, v in (d.get("weights") or {}).items()},
            robustness_check=dict(d.get("robustness_check") or {}),
            status=SectionStatus(d.get("status") or "OK"),
            reason=str(d.get("reason") or ""),
        )


# ── Section 5: Predicted metrics ──────────────────────────────────────

@dataclass
class PredictedMetric:
    value: float
    ci_low: float
    ci_high: float
    method: str = "ridge"
    r_squared: float = 0.0
    n_comparables_used: int = 0
    feature_importances: Dict[str, float] = field(default_factory=dict)
    provenance_chain: List[str] = field(default_factory=list)
    #: Conformal / bootstrap coverage target (e.g. 0.90). Older packets
    #: saved before conformal prediction won't have this — defaults to
    #: 0.0 so their roundtrip produces the same value.
    coverage_target: float = 0.0
    #: A/B/C/D grade combining method, cohort size, and fit quality.
    reliability_grade: str = ""
    #: Prompt 29 — which base model the ensemble picked. One of
    #: ``ridge_regression`` / ``knn`` / ``weighted_median``. Empty
    #: string on older packets (back-compat).
    model_selection: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": _json_safe(self.value),
            "ci_low": _json_safe(self.ci_low),
            "ci_high": _json_safe(self.ci_high),
            "method": self.method,
            "r_squared": _json_safe(self.r_squared),
            "n_comparables_used": int(self.n_comparables_used),
            "feature_importances": {k: _json_safe(v) for k, v in self.feature_importances.items()},
            "provenance_chain": list(self.provenance_chain),
            "coverage_target": _json_safe(self.coverage_target),
            "reliability_grade": self.reliability_grade,
            "model_selection": self.model_selection,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PredictedMetric":
        return cls(
            value=float(d.get("value") or 0.0),
            ci_low=float(d.get("ci_low") or 0.0),
            ci_high=float(d.get("ci_high") or 0.0),
            method=str(d.get("method") or "ridge"),
            r_squared=float(d.get("r_squared") or 0.0),
            n_comparables_used=int(d.get("n_comparables_used") or 0),
            feature_importances={k: float(v) for k, v in (d.get("feature_importances") or {}).items()},
            provenance_chain=list(d.get("provenance_chain") or []),
            coverage_target=float(d.get("coverage_target") or 0.0),
            reliability_grade=str(d.get("reliability_grade") or ""),
            model_selection=str(d.get("model_selection") or ""),
        )


# ── Section 6: Merged RCM profile ─────────────────────────────────────

@dataclass
class ProfileMetric:
    value: float
    source: MetricSource = MetricSource.UNKNOWN
    benchmark_percentile: Optional[float] = None
    trend: Optional[str] = None         # "improving" | "flat" | "degrading"
    quality: Optional[str] = None       # "high" | "medium" | "low"
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    #: Ontology metadata. Populated by the builder from
    #: :mod:`rcm_mc.domain.econ_ontology` when the metric is in the
    #: registry; left as ``None`` / empty for unclassified metrics.
    #: Additive so older serialized packets still deserialize.
    domain: Optional[str] = None
    financial_pathway: Optional[str] = None
    causal_path_summary: Optional[str] = None
    mechanism_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": _json_safe(self.value),
            "source": self.source.value,
            "benchmark_percentile": _json_safe(self.benchmark_percentile),
            "trend": self.trend,
            "quality": self.quality,
            "ci_low": _json_safe(self.ci_low),
            "ci_high": _json_safe(self.ci_high),
            "domain": self.domain,
            "financial_pathway": self.financial_pathway,
            "causal_path_summary": self.causal_path_summary,
            "mechanism_tags": list(self.mechanism_tags),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProfileMetric":
        return cls(
            value=float(d.get("value") or 0.0),
            source=MetricSource(d.get("source") or "UNKNOWN"),
            benchmark_percentile=(float(d["benchmark_percentile"])
                                  if d.get("benchmark_percentile") is not None else None),
            trend=d.get("trend"),
            quality=d.get("quality"),
            ci_low=(float(d["ci_low"]) if d.get("ci_low") is not None else None),
            ci_high=(float(d["ci_high"]) if d.get("ci_high") is not None else None),
            domain=d.get("domain"),
            financial_pathway=d.get("financial_pathway"),
            causal_path_summary=d.get("causal_path_summary"),
            mechanism_tags=list(d.get("mechanism_tags") or []),
        )


# ── Section 7: EBITDA bridge ──────────────────────────────────────────

@dataclass
class MetricImpact:
    metric_key: str
    current_value: float
    target_value: float
    revenue_impact: float = 0.0
    cost_impact: float = 0.0
    ebitda_impact: float = 0.0
    margin_impact_bps: float = 0.0
    #: Cash released (or tied up) from a working-capital lever such as
    #: days_in_ar. One-time, not recurring — separate from EBITDA.
    working_capital_impact: float = 0.0
    #: Which input metric(s) drove this impact. Used by the provenance
    #: graph to chain dollar amounts back to their observed / predicted
    #: source. Empty for dataclasses loaded from pre-bridge packets.
    upstream_metrics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MetricImpact":
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            current_value=float(d.get("current_value") or 0.0),
            target_value=float(d.get("target_value") or 0.0),
            revenue_impact=float(d.get("revenue_impact") or 0.0),
            cost_impact=float(d.get("cost_impact") or 0.0),
            ebitda_impact=float(d.get("ebitda_impact") or 0.0),
            margin_impact_bps=float(d.get("margin_impact_bps") or 0.0),
            working_capital_impact=float(d.get("working_capital_impact") or 0.0),
            upstream_metrics=list(d.get("upstream_metrics") or []),
        )


@dataclass
class EBITDABridgeResult:
    current_ebitda: float = 0.0
    target_ebitda: float = 0.0
    total_ebitda_impact: float = 0.0
    new_ebitda_margin: float = 0.0
    ebitda_delta_pct: float = 0.0
    per_metric_impacts: List[MetricImpact] = field(default_factory=list)
    waterfall_data: List[Tuple[str, float]] = field(default_factory=list)
    sensitivity_tornado: List[Dict[str, Any]] = field(default_factory=list)
    #: One-time working-capital released from lever improvements (e.g.
    #: AR days reduction). Reported separately from EBITDA so partners
    #: don't double-count the cash.
    working_capital_released: float = 0.0
    #: Integer margin delta in basis points (target - current).
    margin_improvement_bps: int = 0
    #: EV lift at a few common multiples, e.g. ``{"10x": ..., "12x": ..., "15x": ...}``.
    ev_impact_at_multiple: Dict[str, float] = field(default_factory=dict)
    status: SectionStatus = SectionStatus.OK
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_ebitda": _json_safe(self.current_ebitda),
            "target_ebitda": _json_safe(self.target_ebitda),
            "total_ebitda_impact": _json_safe(self.total_ebitda_impact),
            "new_ebitda_margin": _json_safe(self.new_ebitda_margin),
            "ebitda_delta_pct": _json_safe(self.ebitda_delta_pct),
            "per_metric_impacts": [m.to_dict() for m in self.per_metric_impacts],
            # tuples → list of length-2 for JSON roundtrip.
            "waterfall_data": [[str(lbl), _json_safe(val)] for lbl, val in self.waterfall_data],
            "sensitivity_tornado": _json_safe(self.sensitivity_tornado),
            "working_capital_released": _json_safe(self.working_capital_released),
            "margin_improvement_bps": int(self.margin_improvement_bps),
            "ev_impact_at_multiple": {k: _json_safe(v) for k, v in self.ev_impact_at_multiple.items()},
            "status": self.status.value,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EBITDABridgeResult":
        return cls(
            current_ebitda=float(d.get("current_ebitda") or 0.0),
            target_ebitda=float(d.get("target_ebitda") or 0.0),
            total_ebitda_impact=float(d.get("total_ebitda_impact") or 0.0),
            new_ebitda_margin=float(d.get("new_ebitda_margin") or 0.0),
            ebitda_delta_pct=float(d.get("ebitda_delta_pct") or 0.0),
            per_metric_impacts=[MetricImpact.from_dict(m) for m in (d.get("per_metric_impacts") or [])],
            waterfall_data=[(str(row[0]), float(row[1])) for row in (d.get("waterfall_data") or [])],
            sensitivity_tornado=list(d.get("sensitivity_tornado") or []),
            working_capital_released=float(d.get("working_capital_released") or 0.0),
            margin_improvement_bps=int(d.get("margin_improvement_bps") or 0),
            ev_impact_at_multiple={k: float(v) for k, v in (d.get("ev_impact_at_multiple") or {}).items()},
            status=SectionStatus(d.get("status") or "OK"),
            reason=str(d.get("reason") or ""),
        )


# ── Section 8: Monte Carlo simulation ─────────────────────────────────

@dataclass
class PercentileSet:
    p10: float = 0.0
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    p90: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PercentileSet":
        d = d or {}
        return cls(
            p10=float(d.get("p10") or 0.0),
            p25=float(d.get("p25") or 0.0),
            p50=float(d.get("p50") or 0.0),
            p75=float(d.get("p75") or 0.0),
            p90=float(d.get("p90") or 0.0),
        )


@dataclass
class SimulationSummary:
    n_sims: int = 0
    seed: int = 0
    ebitda_uplift: PercentileSet = field(default_factory=PercentileSet)
    moic: PercentileSet = field(default_factory=PercentileSet)
    irr: PercentileSet = field(default_factory=PercentileSet)
    probability_of_covenant_breach: float = 0.0
    variance_contribution_by_metric: Dict[str, float] = field(default_factory=dict)
    convergence_check: Dict[str, Any] = field(default_factory=dict)
    status: SectionStatus = SectionStatus.OK
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_sims": int(self.n_sims),
            "seed": int(self.seed),
            "ebitda_uplift": self.ebitda_uplift.to_dict(),
            "moic": self.moic.to_dict(),
            "irr": self.irr.to_dict(),
            "probability_of_covenant_breach": _json_safe(self.probability_of_covenant_breach),
            "variance_contribution_by_metric": {k: _json_safe(v) for k, v in self.variance_contribution_by_metric.items()},
            "convergence_check": _json_safe(self.convergence_check),
            "status": self.status.value,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimulationSummary":
        return cls(
            n_sims=int(d.get("n_sims") or 0),
            seed=int(d.get("seed") or 0),
            ebitda_uplift=PercentileSet.from_dict(d.get("ebitda_uplift")),
            moic=PercentileSet.from_dict(d.get("moic")),
            irr=PercentileSet.from_dict(d.get("irr")),
            probability_of_covenant_breach=float(d.get("probability_of_covenant_breach") or 0.0),
            variance_contribution_by_metric={k: float(v) for k, v in (d.get("variance_contribution_by_metric") or {}).items()},
            convergence_check=dict(d.get("convergence_check") or {}),
            status=SectionStatus(d.get("status") or "OK"),
            reason=str(d.get("reason") or ""),
        )


# ── Section 9: Risk flags ─────────────────────────────────────────────

@dataclass
class RiskFlag:
    """Automated risk signal surfaced from data patterns.

    ``explanation`` / ``trigger_metric`` are v1 fields kept so packets
    saved before the risk-flags v2 refresh still round-trip. New code
    prefers ``detail`` + ``trigger_metrics`` (plural): ``detail`` is the
    2-3-sentence human-readable explanation that shows up in the UI;
    ``trigger_metrics`` carries the full list of metric keys that drove
    the flag so the provenance UI can chain dollars back to source data.
    """
    category: str       # OPERATIONAL | REGULATORY | PAYER | CODING | DATA_QUALITY | FINANCIAL
    severity: RiskSeverity = RiskSeverity.LOW
    explanation: str = ""
    trigger_metric: Optional[str] = None
    trigger_value: Optional[float] = None
    title: str = ""
    detail: str = ""
    trigger_metrics: List[str] = field(default_factory=list)
    ebitda_at_risk: Optional[float] = None

    def __post_init__(self) -> None:
        # Back-compat: if caller provided ``explanation`` but not ``detail``
        # (old code path), use explanation as detail. Same for plural
        # trigger_metrics derived from the singular field.
        if not self.detail and self.explanation:
            self.detail = self.explanation
        if not self.explanation and self.detail:
            self.explanation = self.detail
        if not self.trigger_metrics and self.trigger_metric:
            self.trigger_metrics = [self.trigger_metric]
        if self.trigger_metric is None and self.trigger_metrics:
            self.trigger_metric = self.trigger_metrics[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "explanation": self.explanation,
            "trigger_metric": self.trigger_metric,
            "trigger_value": _json_safe(self.trigger_value),
            "title": self.title,
            "detail": self.detail,
            "trigger_metrics": list(self.trigger_metrics),
            "ebitda_at_risk": _json_safe(self.ebitda_at_risk),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RiskFlag":
        tv = d.get("trigger_value")
        ear = d.get("ebitda_at_risk")
        return cls(
            category=str(d.get("category") or ""),
            severity=RiskSeverity(d.get("severity") or "LOW"),
            explanation=str(d.get("explanation") or ""),
            trigger_metric=d.get("trigger_metric"),
            trigger_value=float(tv) if tv is not None else None,
            title=str(d.get("title") or ""),
            detail=str(d.get("detail") or ""),
            trigger_metrics=list(d.get("trigger_metrics") or []),
            ebitda_at_risk=float(ear) if ear is not None else None,
        )


# ── Section 10: Provenance graph ──────────────────────────────────────

@dataclass
class DataNode:
    metric: str
    value: float
    source: str
    source_detail: str = ""
    confidence: float = 1.0
    upstream: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value": _json_safe(self.value),
            "source": self.source,
            "source_detail": self.source_detail,
            "confidence": _json_safe(self.confidence),
            "upstream": list(self.upstream),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataNode":
        return cls(
            metric=str(d.get("metric") or ""),
            value=float(d.get("value") or 0.0),
            source=str(d.get("source") or "UNKNOWN"),
            source_detail=str(d.get("source_detail") or ""),
            confidence=float(d.get("confidence") or 1.0),
            upstream=list(d.get("upstream") or []),
        )


@dataclass
class ProvenanceSnapshot:
    """Flat, JSON-roundtrippable snapshot of the provenance DAG.

    Stored on the packet and survives the ``analysis_runs`` SQLite
    cache. Contrast with
    :class:`rcm_mc.provenance.graph.ProvenanceGraph`, which is the
    rich explorable DAG with typed edges + cycle detection —
    rebuilt on demand from a packet rather than persisted.

    Two classes, same concept at different granularity. Use
    fully-qualified imports when both are in scope.
    """
    nodes: Dict[str, DataNode] = field(default_factory=dict)

    def add(self, node: DataNode) -> None:
        self.nodes[node.metric] = node

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": {k: v.to_dict() for k, v in self.nodes.items()}}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceSnapshot":
        raw = (d or {}).get("nodes") or {}
        return cls(nodes={k: DataNode.from_dict(v) for k, v in raw.items()})


# Back-compat alias. The old name is still imported by tests and a
# handful of internal call sites; new code should use
# :class:`ProvenanceSnapshot`. Slated for removal once every import
# has been migrated.
ProvenanceGraph = ProvenanceSnapshot


# ── Section 11: Diligence questions ───────────────────────────────────

@dataclass
class DiligenceQuestion:
    question: str
    trigger_metric: Optional[str] = None
    trigger_reason: str = ""
    priority: DiligencePriority = DiligencePriority.P2
    category: str = ""              # OPERATIONAL | REGULATORY | ... (matches RiskFlag categories)
    #: Machine-readable data pattern that fired the question — e.g.
    #: ``"denial_rate=14.5%"`` or ``"missing:case_mix_index"``. Read by
    #: the UI tooltip; kept distinct from ``trigger_reason`` which is
    #: the human narrative ("above partner comfort line").
    trigger: str = ""
    context: str = ""               # why this matters for valuation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "trigger_metric": self.trigger_metric,
            "trigger_reason": self.trigger_reason,
            "priority": self.priority.value,
            "category": self.category,
            "trigger": self.trigger,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DiligenceQuestion":
        return cls(
            question=str(d.get("question") or ""),
            trigger_metric=d.get("trigger_metric"),
            trigger_reason=str(d.get("trigger_reason") or ""),
            priority=DiligencePriority(d.get("priority") or "P2"),
            category=str(d.get("category") or ""),
            trigger=str(d.get("trigger") or ""),
            context=str(d.get("context") or ""),
        )


# ── The packet ────────────────────────────────────────────────────────

PACKET_SCHEMA_VERSION = "1.0"

SECTION_NAMES = (
    "profile",
    "observed_metrics",
    "completeness",
    "comparables",
    "predicted_metrics",
    "rcm_profile",
    "ebitda_bridge",
    "simulation",
    "risk_flags",
    "provenance",
    "diligence_questions",
    "exports",
    "v2_simulation",
)


@dataclass
class DealAnalysisPacket:
    """The canonical per-deal analysis object. See module docstring for
    the contract."""

    # Identity
    deal_id: str
    deal_name: str = ""
    run_id: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str = PACKET_SCHEMA_VERSION
    scenario_id: Optional[str] = None
    as_of: Optional[date] = None

    # Sections 1-12
    profile: HospitalProfile = field(default_factory=HospitalProfile)
    observed_metrics: Dict[str, ObservedMetric] = field(default_factory=dict)
    completeness: CompletenessAssessment = field(default_factory=CompletenessAssessment)
    comparables: ComparableSet = field(default_factory=ComparableSet)
    predicted_metrics: Dict[str, PredictedMetric] = field(default_factory=dict)
    rcm_profile: Dict[str, ProfileMetric] = field(default_factory=dict)
    ebitda_bridge: EBITDABridgeResult = field(default_factory=EBITDABridgeResult)
    simulation: Optional[SimulationSummary] = None
    risk_flags: List[RiskFlag] = field(default_factory=list)
    provenance: ProvenanceSnapshot = field(default_factory=ProvenanceSnapshot)
    diligence_questions: List[DiligenceQuestion] = field(default_factory=list)
    exports: Dict[str, str] = field(default_factory=dict)

    # ── Phase-4 additive sections (Prompt 2) ────────────────────────
    # Each is optional so packets serialized before these fields
    # existed still deserialize. Wired by ``packet_builder`` after
    # ontology + completeness are populated.
    reimbursement_profile: Optional[Dict[str, Any]] = None
    revenue_realization: Optional[Dict[str, Any]] = None
    metric_sensitivity_map: Optional[Dict[str, Dict[str, Any]]] = None

    # ── Phase-4 additive sections (Prompt 3) ────────────────────────
    # Value bridge v2 outputs. The v1 bridge (``ebitda_bridge``)
    # remains authoritative for the Prompt 1 research-band calibration;
    # v2 is surfaced alongside so partners can compare deterministic
    # unit-economics math against the top-down coefficients.
    value_bridge_result: Optional[Dict[str, Any]] = None
    leverage_table: Optional[List[Dict[str, Any]]] = None
    recurring_vs_one_time_summary: Optional[Dict[str, Any]] = None
    enterprise_value_summary: Optional[Dict[str, Any]] = None

    # ── Phase-4 additive sections (Prompt 16) ──────────────────────
    # Output of the v2 Monte Carlo simulator. Separate from
    # ``simulation`` (which is the v1 simulator's output) so both can
    # coexist on a packet for side-by-side comparison. Stored as a
    # plain dict via ``V2MonteCarloResult.to_dict()``.
    v2_simulation: Optional[Dict[str, Any]] = None

    # ── Phase-4 additive sections (Prompt 18) ──────────────────────
    # Analyst overrides applied during this packet build. Flat
    # ``{override_key: value}`` shape — matches the on-disk
    # ``deal_overrides`` table. ``None`` means "no overrides stored for
    # this deal at build time". Renderers that chain dollars back to
    # provenance should emit ``ProvenanceTag.ANALYST_OVERRIDE`` on any
    # metric whose key appears here.
    analyst_overrides: Optional[Dict[str, Any]] = None

    # ── Phase-4 additive sections (Prompt 20) ──────────────────────
    # Output of ``mc.scenario_comparison.compare_scenarios``. Populated
    # on-demand by the workbench's Scenarios tab (via POST to
    # ``/api/analysis/<id>/simulate/compare``) — the builder does not
    # auto-run comparison because each scenario costs a full MC. Flat
    # dict shape matches ``ScenarioComparison.to_dict()``.
    scenario_comparison: Optional[Dict[str, Any]] = None

    # ── Phase-4 additive sections (Prompt 24) ──────────────────────
    # Static state-level regulatory + payer context from
    # :mod:`rcm_mc.data.state_regulatory`. ``None`` means "no
    # assessment run" (e.g., the deal profile has no state). Shape
    # matches ``RegulatoryAssessment.to_dict()``.
    regulatory_context: Optional[Dict[str, Any]] = None

    # ── Phase-4 additive sections (Prompt 27) ──────────────────────
    # Per-metric temporal forecasts from
    # :mod:`rcm_mc.ml.temporal_forecaster`. Keyed by metric_key;
    # each value is a ``TemporalForecast.to_dict()``. Empty dict when
    # the analyst didn't upload multi-period history.
    metric_forecasts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── Helpers ──

    def section(self, name: str) -> Any:
        """Fetch one section by name. Used by ``/api/analysis/<id>/section/<name>``
        so the server doesn't grow a dispatch switch for every field."""
        if name not in SECTION_NAMES and name not in ("deal_id", "deal_name",
                                                      "run_id", "generated_at",
                                                      "model_version", "scenario_id",
                                                      "as_of"):
            raise KeyError(f"Unknown section: {name!r}")
        return getattr(self, name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "run_id": self.run_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "model_version": self.model_version,
            "scenario_id": self.scenario_id,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "profile": self.profile.to_dict(),
            "observed_metrics": {k: v.to_dict() for k, v in self.observed_metrics.items()},
            "completeness": self.completeness.to_dict(),
            "comparables": self.comparables.to_dict(),
            "predicted_metrics": {k: v.to_dict() for k, v in self.predicted_metrics.items()},
            "rcm_profile": {k: v.to_dict() for k, v in self.rcm_profile.items()},
            "ebitda_bridge": self.ebitda_bridge.to_dict(),
            "simulation": self.simulation.to_dict() if self.simulation is not None else None,
            "risk_flags": [r.to_dict() for r in self.risk_flags],
            "provenance": self.provenance.to_dict(),
            "diligence_questions": [q.to_dict() for q in self.diligence_questions],
            "exports": dict(self.exports),
            "reimbursement_profile": (dict(self.reimbursement_profile)
                                       if self.reimbursement_profile else None),
            "revenue_realization": (dict(self.revenue_realization)
                                     if self.revenue_realization else None),
            "metric_sensitivity_map": (
                {k: dict(v) for k, v in self.metric_sensitivity_map.items()}
                if self.metric_sensitivity_map else None
            ),
            "value_bridge_result": (dict(self.value_bridge_result)
                                     if self.value_bridge_result else None),
            "leverage_table": (
                [dict(row) for row in self.leverage_table]
                if self.leverage_table else None
            ),
            "recurring_vs_one_time_summary": (
                dict(self.recurring_vs_one_time_summary)
                if self.recurring_vs_one_time_summary else None
            ),
            "enterprise_value_summary": (
                dict(self.enterprise_value_summary)
                if self.enterprise_value_summary else None
            ),
            "v2_simulation": (dict(self.v2_simulation)
                               if self.v2_simulation else None),
            "analyst_overrides": (dict(self.analyst_overrides)
                                   if self.analyst_overrides else None),
            "scenario_comparison": (dict(self.scenario_comparison)
                                     if self.scenario_comparison else None),
            "regulatory_context": (dict(self.regulatory_context)
                                    if self.regulatory_context else None),
            "metric_forecasts": (
                {k: dict(v) for k, v in self.metric_forecasts.items()}
                if self.metric_forecasts else {}
            ),
        }

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        """JSON with NaN/Inf coerced to null."""
        return json.dumps(self.to_dict(), indent=indent, default=_json_safe)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DealAnalysisPacket":
        sim_raw = d.get("simulation")
        simulation = SimulationSummary.from_dict(sim_raw) if sim_raw else None
        gen_at = _parse_datetime(d.get("generated_at")) or datetime.now(timezone.utc)
        return cls(
            deal_id=str(d.get("deal_id") or ""),
            deal_name=str(d.get("deal_name") or ""),
            run_id=str(d.get("run_id") or ""),
            generated_at=gen_at,
            model_version=str(d.get("model_version") or PACKET_SCHEMA_VERSION),
            scenario_id=d.get("scenario_id"),
            as_of=_parse_date(d.get("as_of")),
            profile=HospitalProfile.from_dict(d.get("profile") or {}),
            observed_metrics={k: ObservedMetric.from_dict(v)
                              for k, v in (d.get("observed_metrics") or {}).items()},
            completeness=CompletenessAssessment.from_dict(d.get("completeness") or {}),
            comparables=ComparableSet.from_dict(d.get("comparables") or {}),
            predicted_metrics={k: PredictedMetric.from_dict(v)
                               for k, v in (d.get("predicted_metrics") or {}).items()},
            rcm_profile={k: ProfileMetric.from_dict(v)
                         for k, v in (d.get("rcm_profile") or {}).items()},
            ebitda_bridge=EBITDABridgeResult.from_dict(d.get("ebitda_bridge") or {}),
            simulation=simulation,
            risk_flags=[RiskFlag.from_dict(r) for r in (d.get("risk_flags") or [])],
            provenance=ProvenanceSnapshot.from_dict(d.get("provenance") or {}),
            diligence_questions=[DiligenceQuestion.from_dict(q)
                                 for q in (d.get("diligence_questions") or [])],
            exports=dict(d.get("exports") or {}),
            reimbursement_profile=(dict(d["reimbursement_profile"])
                                    if d.get("reimbursement_profile") else None),
            revenue_realization=(dict(d["revenue_realization"])
                                  if d.get("revenue_realization") else None),
            metric_sensitivity_map=(
                {k: dict(v) for k, v in d["metric_sensitivity_map"].items()}
                if d.get("metric_sensitivity_map") else None
            ),
            value_bridge_result=(dict(d["value_bridge_result"])
                                  if d.get("value_bridge_result") else None),
            leverage_table=(
                [dict(row) for row in d["leverage_table"]]
                if d.get("leverage_table") else None
            ),
            recurring_vs_one_time_summary=(
                dict(d["recurring_vs_one_time_summary"])
                if d.get("recurring_vs_one_time_summary") else None
            ),
            enterprise_value_summary=(
                dict(d["enterprise_value_summary"])
                if d.get("enterprise_value_summary") else None
            ),
            v2_simulation=(dict(d["v2_simulation"])
                            if d.get("v2_simulation") else None),
            analyst_overrides=(dict(d["analyst_overrides"])
                                if d.get("analyst_overrides") else None),
            scenario_comparison=(dict(d["scenario_comparison"])
                                  if d.get("scenario_comparison") else None),
            regulatory_context=(dict(d["regulatory_context"])
                                 if d.get("regulatory_context") else None),
            metric_forecasts={
                str(k): dict(v) for k, v in
                (d.get("metric_forecasts") or {}).items()
            },
        )

    @classmethod
    def from_json(cls, s: str) -> "DealAnalysisPacket":
        return cls.from_dict(json.loads(s))


# ── Input hashing ─────────────────────────────────────────────────────

def hash_inputs(
    *,
    deal_id: str,
    observed_metrics: Dict[str, Any],
    scenario_id: Optional[str] = None,
    as_of: Optional[date] = None,
    profile: Optional[Dict[str, Any]] = None,
    analyst_overrides: Optional[Dict[str, Any]] = None,
) -> str:
    """Deterministic SHA256 over canonical input JSON.

    Used for dedup in the analysis_runs cache: if the same (deal,
    scenario, as_of, observed metrics, profile, analyst overrides)
    combination has been seen before, reuse the stored packet instead
    of rebuilding. ``analyst_overrides`` (Prompt 18) is included so a
    newly-written override correctly forces a cache miss on the next
    build.

    Critical: uses ``sort_keys=True`` so dict ordering doesn't produce
    spurious misses.
    """
    def _clean(x: Any) -> Any:
        if isinstance(x, ObservedMetric):
            return x.to_dict()
        if isinstance(x, HospitalProfile):
            return x.to_dict()
        return _json_safe(x)

    payload = {
        "deal_id": str(deal_id),
        "scenario_id": scenario_id,
        "as_of": as_of.isoformat() if as_of else None,
        "observed_metrics": {k: _clean(v) for k, v in (observed_metrics or {}).items()},
        "profile": _clean(profile or {}),
        "analyst_overrides": {
            str(k): _clean(v)
            for k, v in (analyst_overrides or {}).items()
        },
    }
    s = json.dumps(payload, sort_keys=True, default=_json_safe)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
