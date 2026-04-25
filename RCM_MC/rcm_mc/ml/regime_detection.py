"""Regime detection on hospital financial time series.

The partner-relevant question this module answers: *looking at
this hospital's 5-year financial history, when did its trajectory
change, and what regime is it in now?* — Growth, Stable, or
Distress.

This is meaningfully different from the volume_trend_forecaster
(short-horizon trajectory per service line) and the forward_
distress_predictor (probability that future margin crosses a
threshold). Regime detection is a **structural-break** analysis
of the past — it tells you when the hospital's trajectory changed,
which is the question that drives 'has the thesis already played
out?' calls in IC discussions.

Approach:

  1. **PELT** (Pruned Exact Linear Time) changepoint detection on
     each financial metric series. PELT is the canonical optimal-
     segmentation algorithm — pure numpy, O(n) under the linear-
     cost assumption.
  2. Per-segment regime classification: a segment's slope sign +
     magnitude + level vs historical mean labels it as growth /
     stable / distress / recovery.
  3. Multi-metric fusion: revenue, EBITDA margin, and volume
     each get their own regime label. The hospital's overall
     regime is the modal label across the three, with conflict
     flags when they disagree (a common partner red flag —
     revenue growing but margin shrinking = unit-economics
     deteriorating).

Public API::

    from rcm_mc.ml.regime_detection import (
        ChangePoint,
        RegimeSegment,
        HospitalRegimeReport,
        detect_changepoints,
        classify_regime,
        analyze_hospital_regime,
    )
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# Regime band cutoffs on segment slope (in std-dev units per
# period — slope normalized by series std). Tuned for hospital
# annual financials where 5-year histories are typical.
_SLOPE_BANDS_REL: List[Tuple[float, str]] = [
    (-0.20, "distress"),
    (-0.05, "decline"),
    (0.05, "stable"),
    (0.20, "growth"),
    (1e9, "rapid_growth"),
]


@dataclass
class ChangePoint:
    """One detected structural break."""
    index: int                # position in the time series
    timestamp: Optional[str]  # period label if available
    pre_mean: float
    post_mean: float
    magnitude: float          # |post_mean - pre_mean| / series_std


@dataclass
class RegimeSegment:
    """One regime segment between changepoints (or boundaries)."""
    start_index: int
    end_index: int
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]
    n_periods: int
    mean_value: float
    slope_per_period: float
    slope_relative: float     # slope / series_std
    volatility: float
    regime: str               # 'growth' / 'stable' / 'distress' / ...


@dataclass
class MetricRegimeAnalysis:
    """Full regime analysis for one metric."""
    metric: str
    n_periods: int
    series_mean: float
    series_std: float
    changepoints: List[ChangePoint]
    segments: List[RegimeSegment]
    current_regime: str
    current_segment_periods: int
    notes: List[str] = field(default_factory=list)


@dataclass
class HospitalRegimeReport:
    """Multi-metric fusion."""
    ccn: Optional[str]
    per_metric: Dict[str, MetricRegimeAnalysis]
    overall_regime: str
    confidence: str           # 'high' / 'mixed' / 'conflicted'
    conflict_flags: List[str]
    notes: List[str] = field(default_factory=list)


# ── PELT changepoint detection ───────────────────────────────

def _segment_cost(
    cum_sum: np.ndarray, cum_sum_sq: np.ndarray,
    start: int, end: int,
) -> float:
    """L2 cost of fitting a constant mean to data[start:end+1].

    Computes RSS = Σ(x - mean)² in O(1) using cumulative sums:
        RSS = Σx² - (Σx)² / n
    """
    n = end - start + 1
    if n <= 0:
        return 0.0
    s = cum_sum[end + 1] - cum_sum[start]
    s2 = cum_sum_sq[end + 1] - cum_sum_sq[start]
    return float(s2 - (s * s) / n)


def detect_changepoints(
    values: Sequence[float],
    *,
    min_segment_length: int = 2,
    penalty: Optional[float] = None,
) -> List[int]:
    """PELT changepoint detection. Pure numpy.

    Args:
      values: 1-D series. NaN values rejected (caller pre-cleans).
      min_segment_length: minimum periods per segment. 2 is a
        sensible default for annual data — anything shorter isn't
        a real regime, just noise.
      penalty: additive cost per changepoint (BIC-style:
        σ²·log(n) by default).

    Returns: list of changepoint indices (the *first* index of each
    new segment, excluding 0). Empty list = no breaks detected.
    """
    arr = np.asarray(values, dtype=float)
    if np.isnan(arr).any():
        raise ValueError(
            "Series contains NaN; clean before calling")
    n = len(arr)
    if n < 2 * min_segment_length:
        return []

    # BIC-style penalty: σ² · log(n)
    if penalty is None:
        sigma2 = float(np.var(arr))
        if sigma2 <= 1e-12:
            return []  # constant series → no changepoints
        penalty = sigma2 * math.log(n)

    # Cumulative sums for O(1) segment cost
    cum_sum = np.zeros(n + 1)
    cum_sum_sq = np.zeros(n + 1)
    cum_sum[1:] = np.cumsum(arr)
    cum_sum_sq[1:] = np.cumsum(arr * arr)

    # PELT recursion: F[t] = min over s < t of
    #   [F[s] + cost(s+1, t) + β]
    F = np.full(n + 1, np.inf)
    F[0] = -penalty
    cps: List[List[int]] = [[] for _ in range(n + 1)]
    for t in range(1, n + 1):
        best_cost = np.inf
        best_s = 0
        end = t - 1
        # min_segment_length on both sides
        s_max = end - min_segment_length + 1
        for s in range(0, s_max + 1):
            # New segment is [s, end]; need s ≥ 0 + the previous
            # segment must also be ≥ min_segment_length
            if s > 0 and s < min_segment_length:
                continue
            seg = _segment_cost(
                cum_sum, cum_sum_sq, s, end)
            cost = F[s] + seg + penalty
            if cost < best_cost:
                best_cost = cost
                best_s = s
        F[t] = best_cost
        if best_s == 0:
            cps[t] = []
        else:
            cps[t] = cps[best_s] + [best_s]
    return cps[n]


# ── Regime classification ────────────────────────────────────

def _slope(values: np.ndarray) -> float:
    """OLS slope of values vs time index."""
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = values.mean()
    num = float(np.sum((x - x_mean) * (values - y_mean)))
    den = float(np.sum((x - x_mean) ** 2))
    return num / den if den > 0 else 0.0


def _classify_regime(slope_rel: float) -> str:
    for thresh, label in _SLOPE_BANDS_REL:
        if slope_rel < thresh:
            return label
    return _SLOPE_BANDS_REL[-1][1]


def classify_regime(
    values: Sequence[float],
    series_std: float,
) -> str:
    """Classify a segment based on slope + level.

    series_std is the global series standard deviation used to
    normalize slope to scale-free 'std-devs per period'."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0 or series_std <= 0:
        return "stable"
    slope = _slope(arr)
    slope_rel = slope / series_std if series_std > 0 else 0
    return _classify_regime(slope_rel)


def _build_segment(
    arr: np.ndarray,
    start: int,
    end: int,
    timestamps: Optional[List[str]],
    series_std: float,
) -> RegimeSegment:
    """Build a RegimeSegment from raw indices."""
    seg_vals = arr[start:end + 1]
    slope = _slope(seg_vals)
    slope_rel = slope / series_std if series_std > 0 else 0.0
    return RegimeSegment(
        start_index=start,
        end_index=end,
        start_timestamp=(timestamps[start]
                         if timestamps else None),
        end_timestamp=(timestamps[end]
                       if timestamps else None),
        n_periods=end - start + 1,
        mean_value=round(float(seg_vals.mean()), 4),
        slope_per_period=round(slope, 4),
        slope_relative=round(slope_rel, 4),
        volatility=round(float(np.std(seg_vals)), 4),
        regime=_classify_regime(slope_rel),
    )


def _changepoint_to_struct(
    arr: np.ndarray,
    cp_index: int,
    timestamps: Optional[List[str]],
    series_std: float,
) -> ChangePoint:
    pre = arr[:cp_index]
    post = arr[cp_index:]
    pre_mean = float(pre.mean()) if len(pre) > 0 else 0.0
    post_mean = float(post.mean()) if len(post) > 0 else 0.0
    mag = (abs(post_mean - pre_mean) / series_std
           if series_std > 0 else 0.0)
    return ChangePoint(
        index=cp_index,
        timestamp=(timestamps[cp_index]
                   if timestamps else None),
        pre_mean=round(pre_mean, 4),
        post_mean=round(post_mean, 4),
        magnitude=round(mag, 4),
    )


def analyze_metric_regime(
    metric: str,
    values: Sequence[float],
    *,
    timestamps: Optional[Sequence[str]] = None,
    min_segment_length: int = 2,
    penalty: Optional[float] = None,
) -> MetricRegimeAnalysis:
    """Run PELT + segment classification on one metric series."""
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]  # drop NaN
    n = len(arr)
    ts: Optional[List[str]] = (
        list(timestamps[:n]) if timestamps else None)
    if n == 0:
        return MetricRegimeAnalysis(
            metric=metric, n_periods=0,
            series_mean=0.0, series_std=0.0,
            changepoints=[], segments=[],
            current_regime="stable",
            current_segment_periods=0,
            notes=["No data."])

    series_std = float(np.std(arr))
    series_mean = float(np.mean(arr))

    if n < 2 * min_segment_length:
        # Single segment over the whole history
        seg = _build_segment(arr, 0, n - 1, ts, series_std)
        notes = []
        if n < 4:
            notes.append(
                f"Only {n} periods of history — regime "
                f"label is best-current-estimate, not a "
                f"structural-break analysis.")
        return MetricRegimeAnalysis(
            metric=metric, n_periods=n,
            series_mean=round(series_mean, 4),
            series_std=round(series_std, 4),
            changepoints=[], segments=[seg],
            current_regime=seg.regime,
            current_segment_periods=seg.n_periods,
            notes=notes)

    cp_indices = detect_changepoints(
        arr, min_segment_length=min_segment_length,
        penalty=penalty)

    # Build segments between [0, cp1, cp2, ..., n-1]
    boundaries = [0] + cp_indices + [n]
    segments: List[RegimeSegment] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1] - 1
        if end < start:
            continue
        segments.append(
            _build_segment(arr, start, end, ts, series_std))

    changepoints = [
        _changepoint_to_struct(arr, cp, ts, series_std)
        for cp in cp_indices
    ]

    current = segments[-1] if segments else None
    current_regime = current.regime if current else "stable"
    current_periods = (current.n_periods
                       if current else 0)

    notes: List[str] = []
    if changepoints:
        notes.append(
            f"{len(changepoints)} structural break"
            f"{'s' if len(changepoints) != 1 else ''} "
            f"detected.")
    if current_regime in ("distress", "decline"):
        notes.append(
            f"Currently in {current_regime} regime "
            f"({current_periods} periods).")
    if current_regime == "rapid_growth":
        notes.append(
            f"Currently in rapid-growth regime "
            f"({current_periods} periods).")

    return MetricRegimeAnalysis(
        metric=metric, n_periods=n,
        series_mean=round(series_mean, 4),
        series_std=round(series_std, 4),
        changepoints=changepoints,
        segments=segments,
        current_regime=current_regime,
        current_segment_periods=current_periods,
        notes=notes)


# ── Multi-metric fusion ──────────────────────────────────────

# Map fine-grained per-metric regime → coarse hospital regime
_OVERALL_MAP = {
    "rapid_growth": "growth",
    "growth": "growth",
    "stable": "stable",
    "decline": "distress",
    "distress": "distress",
}


def analyze_hospital_regime(
    metric_series: Dict[
        str, Sequence[float]],
    *,
    ccn: Optional[str] = None,
    timestamps: Optional[Sequence[str]] = None,
    min_segment_length: int = 2,
    penalty: Optional[float] = None,
) -> HospitalRegimeReport:
    """Run regime analysis on multiple metrics + fuse to a single
    hospital regime label.

    Args:
      metric_series: dict of metric name → time series. Typical
        partner-relevant set: revenue, ebitda_margin, volume,
        days_cash_on_hand.
      ccn: optional hospital identifier.
      timestamps: optional shared period labels.
      min_segment_length: PELT minimum segment length.
      penalty: PELT penalty.

    Returns: HospitalRegimeReport with per-metric analysis + fused
    overall regime.
    """
    per_metric: Dict[str, MetricRegimeAnalysis] = {}
    for metric, values in metric_series.items():
        per_metric[metric] = analyze_metric_regime(
            metric, values, timestamps=timestamps,
            min_segment_length=min_segment_length,
            penalty=penalty)

    # Map per-metric regimes to coarse labels
    coarse_labels = [
        _OVERALL_MAP.get(m.current_regime, "stable")
        for m in per_metric.values()
    ]
    if not coarse_labels:
        return HospitalRegimeReport(
            ccn=ccn, per_metric={},
            overall_regime="stable",
            confidence="mixed",
            conflict_flags=[],
            notes=["No metric data."])

    counter = Counter(coarse_labels)
    most_common, count = counter.most_common(1)[0]
    overall = most_common

    if len(set(coarse_labels)) == 1:
        confidence = "high"
    elif count >= len(coarse_labels) * 0.6:
        confidence = "mixed"
    else:
        confidence = "conflicted"

    # Conflict flags — partners care most about revenue-margin
    # divergence (unit-economics deterioration).
    conflict_flags: List[str] = []
    if ("revenue" in per_metric
            and "ebitda_margin" in per_metric):
        rev_regime = _OVERALL_MAP.get(
            per_metric["revenue"].current_regime, "stable")
        marg_regime = _OVERALL_MAP.get(
            per_metric["ebitda_margin"].current_regime,
            "stable")
        if (rev_regime == "growth"
                and marg_regime == "distress"):
            conflict_flags.append(
                "Revenue growing but margin distressed — "
                "unit-economics deteriorating. Likely the "
                "growth is being purchased with discounts "
                "or labor, not earned.")
        if (rev_regime == "distress"
                and marg_regime == "growth"):
            conflict_flags.append(
                "Revenue declining but margin improving — "
                "shrinking-to-profitability. Sustainable only "
                "if the bottom has been found.")
    if ("volume" in per_metric
            and "revenue" in per_metric):
        vol_regime = _OVERALL_MAP.get(
            per_metric["volume"].current_regime, "stable")
        rev_regime = _OVERALL_MAP.get(
            per_metric["revenue"].current_regime, "stable")
        if (vol_regime == "distress"
                and rev_regime == "growth"):
            conflict_flags.append(
                "Volume declining but revenue growing — "
                "rate-driven growth. Sustainable only as long "
                "as payer mix or rate gains continue.")

    notes: List[str] = []
    if confidence == "conflicted":
        notes.append(
            "Metrics disagree on hospital regime — review "
            "per-metric breakdown before relying on overall "
            "label.")
    if overall == "distress":
        notes.append(
            "Hospital is in distress regime — restructuring/"
            "turnaround thesis territory.")

    return HospitalRegimeReport(
        ccn=ccn, per_metric=per_metric,
        overall_regime=overall,
        confidence=confidence,
        conflict_flags=conflict_flags,
        notes=notes)
