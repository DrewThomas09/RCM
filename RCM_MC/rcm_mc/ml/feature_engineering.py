"""Feature engineering for the RCM predictor.

Three pure-function operations:

- :func:`derive_features` — compute interaction terms & ratios that
  empirically lift Ridge R² on held-out hospitals.
- :func:`normalize_metrics` — z-score against peer medians so metrics
  on different scales (percentages vs. days) are comparable.
- :func:`detect_outliers` — flag metrics >2.5 σ from the comparable
  cohort mean, so partners see data-quality flags before the number
  gets cited.

All three are NaN-safe: missing inputs produce missing outputs; we
never propagate NaN or raise on partial data.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


def _safe_float(v: Any) -> Optional[float]:
    """Convert to float; return None on missing / non-numeric / NaN."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None:
        return None
    if abs(den) < 1e-12:
        return None
    return num / den


def derive_interaction_features(known_metrics: Dict[str, Any]) -> Dict[str, float]:
    """Full-spec interaction / ratio features for the ridge predictor.

    Superset of :func:`derive_features`. The ridge predictor prefers
    this one because it includes the payer-complexity score (weighted
    by typical denial difficulty) and ``revenue_per_bed`` (a decent
    proxy for acuity that the cross-hospital regressions pick up).

    Missing inputs yield missing outputs (key omitted from the returned
    dict). Never raises on partial data.
    """
    m = {k: _safe_float(v) if not isinstance(v, dict) else v
         for k, v in (known_metrics or {}).items()}
    out: Dict[str, float] = {}

    r1 = _safe_div(m.get("denial_rate"), m.get("net_collection_rate"))
    if r1 is not None:
        out["denial_to_collection_ratio"] = r1

    r2 = _safe_div(m.get("net_collection_rate"), m.get("days_in_ar"))
    if r2 is not None:
        out["ar_efficiency"] = r2

    if (m.get("clean_claim_rate") is not None
            and m.get("first_pass_resolution_rate") is not None):
        out["first_pass_gap"] = (
            float(m["clean_claim_rate"]) - float(m["first_pass_resolution_rate"])
        )

    if (m.get("avoidable_denial_pct") is not None
            and m.get("denial_rate") is not None):
        out["avoidable_denial_burden"] = (
            float(m["avoidable_denial_pct"]) * float(m["denial_rate"])
        )

    # Payer complexity: weighted by typical payer-level denial difficulty.
    # Medicaid > commercial > Medicare Advantage; Medicare FFS is the
    # baseline (coefficient ~0). Accepts either ``payer_mix_*_pct``
    # (percentage-point scale) or ``payer_mix`` dict (fractions).
    commercial = _safe_float(m.get("payer_mix_commercial_pct"))
    medicaid = _safe_float(m.get("payer_mix_medicaid_pct"))
    ma = _safe_float(m.get("payer_mix_medicare_advantage_pct"))
    if isinstance(m.get("payer_mix"), dict):
        pm = m["payer_mix"]
        if commercial is None:
            commercial = _safe_float(pm.get("commercial"))
            # Fractions → pct; we keep units consistent.
            if commercial is not None and commercial <= 1.0:
                commercial *= 100.0
        if medicaid is None:
            medicaid = _safe_float(pm.get("medicaid"))
            if medicaid is not None and medicaid <= 1.0:
                medicaid *= 100.0
        if ma is None:
            ma = _safe_float(pm.get("medicare_advantage"))
            if ma is not None and ma <= 1.0:
                ma *= 100.0
    if commercial is not None or medicaid is not None or ma is not None:
        out["payer_complexity_score"] = (
            0.4 * (commercial or 0.0)
            + 0.35 * (medicaid or 0.0)
            + 0.25 * (ma or 0.0)
        )

    rpb = _safe_div(_safe_float(m.get("net_revenue")),
                    _safe_float(m.get("bed_count")))
    if rpb is not None:
        out["revenue_per_bed"] = rpb

    return out


def normalize_features(
    features: Dict[str, Any],
    benchmark_stats: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    """Z-score against ``benchmark_stats = {metric: {"mean": m, "std": s}}``.

    Differs from :func:`normalize_metrics` in two ways:
    1. Takes pre-computed mean/std rather than medians / a comparable
       cohort to derive them from.
    2. Pre-computed stats are what a production ridge pipeline caches
       to disk; this lets prediction-time feature normalization use
       those exact stats without recomputing from scratch.

    Features with no matching benchmark row are returned raw — never
    dropped, so the feature vector keeps its shape.
    """
    out: Dict[str, float] = {}
    for k, v in (features or {}).items():
        f = _safe_float(v)
        if f is None:
            continue
        stats = (benchmark_stats or {}).get(k) or {}
        mean = _safe_float(stats.get("mean"))
        sd = _safe_float(stats.get("std"))
        if mean is None or sd is None or sd <= 0:
            out[k] = f
            continue
        out[k] = (f - mean) / sd
    return out


def derive_features(raw_metrics: Dict[str, Any]) -> Dict[str, float]:
    """Return the interaction/ratio features derived from ``raw_metrics``.

    Missing inputs yield missing outputs (key omitted from the returned
    dict). Caller merges the derived features onto the raw metrics if
    they want the full feature set.
    """
    m = {k: _safe_float(v) for k, v in (raw_metrics or {}).items()}
    out: Dict[str, float] = {}

    r1 = _safe_div(m.get("denial_rate"), m.get("net_collection_rate"))
    if r1 is not None:
        out["denial_to_collection_ratio"] = r1

    r2 = _safe_div(m.get("net_collection_rate"), m.get("days_in_ar"))
    if r2 is not None:
        out["ar_efficiency"] = r2

    if (m.get("clean_claim_rate") is not None
            and m.get("first_pass_resolution_rate") is not None):
        out["first_pass_gap"] = (
            m["clean_claim_rate"] - m["first_pass_resolution_rate"]
        )

    if (m.get("avoidable_denial_pct") is not None
            and m.get("denial_rate") is not None):
        out["avoidable_denial_burden"] = (
            m["avoidable_denial_pct"] * m["denial_rate"]
        )

    return out


def _metric_median_map(
    comparables: Iterable[Dict[str, Any]],
) -> Dict[str, float]:
    """Per-metric median across the comparable cohort. Skips NaN values."""
    pool: Dict[str, List[float]] = {}
    for peer in comparables or []:
        for k, v in (peer or {}).items():
            f = _safe_float(v)
            if f is None:
                continue
            pool.setdefault(k, []).append(f)
    return {k: median(vs) for k, vs in pool.items() if vs}


def _metric_std_map(
    comparables: Iterable[Dict[str, Any]],
) -> Dict[str, float]:
    """Per-metric population stddev across comparables. Zero if <2 samples."""
    pool: Dict[str, List[float]] = {}
    for peer in comparables or []:
        for k, v in (peer or {}).items():
            f = _safe_float(v)
            if f is None:
                continue
            pool.setdefault(k, []).append(f)
    out: Dict[str, float] = {}
    for k, vs in pool.items():
        if len(vs) < 2:
            out[k] = 0.0
            continue
        mean = sum(vs) / len(vs)
        var = sum((x - mean) ** 2 for x in vs) / len(vs)
        out[k] = math.sqrt(var)
    return out


def normalize_metrics(
    metrics: Dict[str, Any],
    *,
    benchmark_medians: Optional[Dict[str, float]] = None,
    benchmark_stds: Optional[Dict[str, float]] = None,
    comparables: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, float]:
    """Z-score every numeric metric against benchmarks.

    Either pass pre-computed ``benchmark_medians`` + ``benchmark_stds``,
    OR pass ``comparables`` and we'll compute them. If neither is
    provided, returns the raw values (no normalization) — caller is
    responsible for deciding what to do with that.
    """
    if benchmark_medians is None or benchmark_stds is None:
        if comparables is None:
            # No reference population to normalize against; return raw.
            return {k: f for k, v in (metrics or {}).items()
                    if (f := _safe_float(v)) is not None}
        benchmark_medians = _metric_median_map(comparables)
        benchmark_stds = _metric_std_map(comparables)

    out: Dict[str, float] = {}
    for k, v in (metrics or {}).items():
        f = _safe_float(v)
        if f is None:
            continue
        med = benchmark_medians.get(k)
        sd = benchmark_stds.get(k)
        if med is None or sd is None or sd <= 0:
            # Can't normalize — emit raw value as fallback. A sd of 0
            # means the peer group is a point mass; any deviation is
            # ±∞ in true z-score terms.
            out[k] = 0.0 if med is not None and f == med else f
            continue
        out[k] = (f - med) / sd
    return out


def detect_outliers(
    metrics: Dict[str, Any],
    comparables: Iterable[Dict[str, Any]],
    *,
    threshold_sd: float = 2.5,
) -> List[str]:
    """Return metric names where the target is >``threshold_sd`` standard
    deviations from the comparable cohort mean.

    Empty list if no comparables or if every metric is within tolerance.
    """
    comparables = list(comparables or [])
    if not comparables:
        return []
    means: Dict[str, float] = {}
    stds = _metric_std_map(comparables)
    # Means separately — _metric_std_map already walked the pool but
    # returns stddev not mean; compute means here to avoid scope leaks.
    pool: Dict[str, List[float]] = {}
    for peer in comparables:
        for k, v in (peer or {}).items():
            f = _safe_float(v)
            if f is None:
                continue
            pool.setdefault(k, []).append(f)
    for k, vs in pool.items():
        if vs:
            means[k] = sum(vs) / len(vs)

    flags: List[str] = []
    for k, v in (metrics or {}).items():
        f = _safe_float(v)
        if f is None:
            continue
        mu = means.get(k)
        sd = stds.get(k, 0.0)
        if mu is None or sd <= 0:
            continue
        if abs(f - mu) / sd > threshold_sd:
            flags.append(k)
    return flags
