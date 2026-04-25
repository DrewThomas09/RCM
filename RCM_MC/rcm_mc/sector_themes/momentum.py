"""Theme momentum scoring — emerging vs saturated vs declining.

The heatmap in heatmap.py shows raw theme density per period.
But density alone doesn't tell the partner what's INTERESTING.
A theme stable at 8% for three years is mature. A theme that
went 0% → 1% → 5% in three years is the actual investable
emerging theme.

This module fits a linear trend per theme across periods and
emits four metrics:

  current_density       latest period's score
  slope                 linear-fit slope across periods
  acceleration          change in slope across the last two
                        period pairs (positive = picking up)
  momentum_score        composite ranking weight
  band                  emerging / stable / saturated / declining

Plus a ranked list helper ``top_emerging_themes`` that combines
the heatmap + momentum + a top-N filter so the partner gets one
output: the themes a fund should bias its target sourcing toward.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from .corpus import Document
from .heatmap import emerging_theme_heatmap
from .themes import THEME_ANCHORS, ThemeAnchor


@dataclass
class ThemeMomentum:
    """Per-theme momentum summary."""
    theme_id: str
    label: str
    n_periods: int
    current_density: float
    slope: float
    acceleration: float
    momentum_score: float
    band: str             # emerging / rising / stable /
                          # saturated / declining


def _band_for(slope: float, current: float, n_periods: int) -> str:
    """Classify a theme into one of the five bands."""
    if n_periods < 2:
        return "stable"
    if slope > 0.05 and current < 0.20:
        # Steep upward trend, still small density
        return "emerging"
    if slope > 0.02:
        return "rising"
    if slope < -0.02:
        return "declining"
    if current >= 0.20:
        return "saturated"
    return "stable"


def compute_theme_momentum(
    heatmap: Dict[str, Dict[str, float]],
    *,
    custom_anchors: Optional[Dict[str, ThemeAnchor]] = None,
) -> List[ThemeMomentum]:
    """Compute per-theme momentum from a heatmap dict.

    The heatmap is shaped {theme_id → {period → density}}; period
    keys are sortable strings (e.g. "2024", "2025" or "2024Q1",
    "2024Q2").

    Returns a list of ThemeMomentum, sorted by momentum_score
    descending. momentum_score = current_density × (1 + slope) +
    acceleration × 0.5 — biased toward themes with both
    momentum AND meaningful current density.
    """
    out: List[ThemeMomentum] = []
    anchors = dict(THEME_ANCHORS)
    if custom_anchors:
        anchors.update(custom_anchors)

    for theme_id, periods in heatmap.items():
        if not periods:
            continue
        # Sort periods chronologically by their string key
        sorted_periods = sorted(periods.keys())
        densities = [periods[p] for p in sorted_periods]
        n = len(densities)

        # Linear-fit slope (numpy polyfit)
        if n >= 2:
            x = np.arange(n, dtype=float)
            y = np.array(densities, dtype=float)
            try:
                coef = np.polyfit(x, y, 1)
                slope = float(coef[0])
            except (np.linalg.LinAlgError, ValueError):
                slope = 0.0
        else:
            slope = 0.0

        # Acceleration: difference between the last two pair-wise
        # slopes. Requires ≥3 periods.
        if n >= 3:
            recent_slope = densities[-1] - densities[-2]
            prior_slope = densities[-2] - densities[-3]
            acceleration = recent_slope - prior_slope
        else:
            acceleration = 0.0

        current = densities[-1]
        momentum = (current * (1.0 + slope)
                    + 0.5 * acceleration)

        anchor = anchors.get(theme_id)
        label = (anchor.label if anchor else theme_id)
        out.append(ThemeMomentum(
            theme_id=theme_id, label=label,
            n_periods=n,
            current_density=round(current, 4),
            slope=round(slope, 4),
            acceleration=round(acceleration, 4),
            momentum_score=round(momentum, 4),
            band=_band_for(slope, current, n),
        ))

    out.sort(key=lambda m: m.momentum_score, reverse=True)
    return out


def top_emerging_themes(
    documents: Iterable[Document],
    *,
    top_n: int = 5,
    granularity: str = "year",
    custom_anchors: Optional[Dict[str, ThemeAnchor]] = None,
) -> List[ThemeMomentum]:
    """End-to-end pipeline: heatmap → momentum → top-N emerging.

    "Emerging" filter: returns only themes in the EMERGING or
    RISING band (slope > 0). Sorts by momentum_score descending.
    Caps at ``top_n``.
    """
    heatmap = emerging_theme_heatmap(
        documents, granularity=granularity,
        custom_anchors=custom_anchors,
    )
    all_momentum = compute_theme_momentum(
        heatmap, custom_anchors=custom_anchors)
    rising = [m for m in all_momentum
              if m.band in ("emerging", "rising")]
    return rising[:top_n]
