"""Unified feature importance protocol + adapters for non-Ridge models.

Trained Ridge predictors (denial / days_AR / collection / distress)
already expose ``.feature_importance()`` and ``.explain()`` from the
shared scaffold. The trained-Ridge primitive returns
(name, std_coefficient, relative_importance) tuples — clean
interpretation: |β| on standardized features.

Non-Ridge models (regime detection, volume forecaster, contract
strength, service-line profitability) need adapters because their
'feature importance' lives in different shapes:

  • Regime detection: which metric *drove* the overall regime
    label? Magnitude proportional to that metric's |slope_relative|
    in the current segment.
  • Volume forecaster: which service line drove hospital-wide
    trajectory? Magnitude = volume_share × |projected_cagr|.
  • Contract strength: which (payer × code) most pulls the
    overall log-ratio? Magnitude = |log(rate_ratio)| × weight.
  • Service-line profitability: which service line contributes
    most to profit / drag? Magnitude = |contribution_margin|.

This module ships those adapters as a uniform
``FeatureImportance`` shape so the visualization layer can render
any model with one renderer.

Public API::

    from rcm_mc.ml.feature_importance import (
        FeatureImportance,
        importance_from_trained_ridge,
        importance_from_regime,
        importance_from_volume_report,
        importance_from_contract_strength,
        importance_from_service_lines,
    )
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class FeatureImportance:
    """One uniform feature-importance row for any model."""
    feature: str
    raw_value: float            # signed: positive = increase target
    relative: float             # 0..1, share of total |raw_value|
    direction: str              # 'positive' | 'negative' | 'neutral'

    @classmethod
    def from_pairs(
        cls, pairs: List[Tuple[str, float]],
    ) -> List["FeatureImportance"]:
        """Build a list from (name, signed_value) pairs."""
        if not pairs:
            return []
        total_abs = sum(abs(v) for _, v in pairs)
        out: List["FeatureImportance"] = []
        for name, val in pairs:
            rel = (abs(val) / total_abs
                   if total_abs > 0 else 0.0)
            if val > 1e-9:
                direction = "positive"
            elif val < -1e-9:
                direction = "negative"
            else:
                direction = "neutral"
            out.append(cls(
                feature=str(name),
                raw_value=float(val),
                relative=round(rel, 4),
                direction=direction,
            ))
        out.sort(key=lambda r: -abs(r.raw_value))
        return out


# ── Adapters ─────────────────────────────────────────────────

def importance_from_trained_ridge(
    predictor: Any,
) -> List[FeatureImportance]:
    """Adapter for TrainedRCMPredictor.feature_importance().

    feature_importance() returns (name, std_coef, rel) — we
    repackage as the uniform shape.
    """
    raw = predictor.feature_importance()
    pairs = [(name, float(coef))
             for name, coef, _rel in raw]
    return FeatureImportance.from_pairs(pairs)


def importance_from_regime(
    report: Any,
) -> List[FeatureImportance]:
    """Adapter for HospitalRegimeReport.

    Each metric's 'importance' to the overall regime is
    proportional to its current segment's |slope_relative|. Sign
    follows slope direction: positive slope = positive driver
    when the overall regime is growth, negative driver when
    distress.
    """
    out: List[Tuple[str, float]] = []
    for metric, analysis in report.per_metric.items():
        if not analysis.segments:
            continue
        last = analysis.segments[-1]
        # Sign: align with the slope direction (so positive trend
        # in revenue is a 'positive driver' whatever the regime)
        out.append((metric, float(last.slope_relative)))
    return FeatureImportance.from_pairs(out)


def importance_from_volume_report(
    report: Any,
) -> List[FeatureImportance]:
    """Adapter for HospitalTrajectoryReport.

    Each service line's importance = volume_share × signed CAGR.
    Lines with bigger volumes and stronger growth/decline pull
    harder on the hospital-wide trajectory.
    """
    if not report.per_line:
        return []
    # Compute volume share from last historical period
    last_volumes: Dict[str, float] = {}
    for f in report.per_line:
        if f.historical:
            last_volumes[f.service_line] = float(
                f.historical[-1][1])
    total = sum(last_volumes.values())
    if total <= 0:
        return []
    out: List[Tuple[str, float]] = []
    for f in report.per_line:
        share = last_volumes.get(f.service_line, 0) / total
        cagr = f.projected_cagr or 0.0
        # importance = share × cagr (signed)
        out.append((f.service_line, share * cagr))
    return FeatureImportance.from_pairs(out)


def importance_from_contract_strength(
    score: Any,
) -> List[FeatureImportance]:
    """Adapter for ContractStrengthScore.

    Each (payer × code) in the top-above + top-below variances
    becomes a feature; importance is signed log-ratio. Surfaces
    the codes that most pull the overall strength score above /
    below market.
    """
    out: List[Tuple[str, float]] = []
    for c in score.top_above_market:
        # Above-market = positive driver of strength
        log_ratio = (math.log(c.rate_ratio)
                     if c.rate_ratio > 0 else 0.0)
        out.append(
            (f"{c.payer_name} · {c.code}", log_ratio))
    for c in score.top_below_market:
        log_ratio = (math.log(c.rate_ratio)
                     if c.rate_ratio > 0 else 0.0)
        out.append(
            (f"{c.payer_name} · {c.code}", log_ratio))
    return FeatureImportance.from_pairs(out)


def importance_from_service_lines(
    margins: List[Any],
) -> List[FeatureImportance]:
    """Adapter for [ServiceLineMargin].

    Each line's importance = signed contribution_margin.
    Profitable lines are positive drivers; subsidized lines are
    negative drivers.
    """
    pairs = [
        (m.service_line, float(m.contribution_margin))
        for m in margins
    ]
    return FeatureImportance.from_pairs(pairs)


def importance_from_explain_pairs(
    pairs: List[Tuple[str, float]],
) -> List[FeatureImportance]:
    """Adapter for any explain() output already in
    (name, signed_value) shape."""
    return FeatureImportance.from_pairs(pairs)


# ── Permutation-importance-style summary ─────────────────────

def aggregate_importance_by_category(
    importances: List[FeatureImportance],
    category_map: Dict[str, str],
) -> Dict[str, float]:
    """Group features into higher-level categories and sum their
    relative importance.

    category_map: feature_name → category. Features not in the
    map go into 'other'.
    """
    out: Dict[str, float] = {}
    for imp in importances:
        cat = category_map.get(imp.feature, "other")
        out[cat] = out.get(cat, 0.0) + imp.relative
    return {k: round(v, 4) for k, v in out.items()}
