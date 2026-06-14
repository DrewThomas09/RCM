"""HEDIS/CQM-style quality-measure gap analysis + composite scorecard.

Scores quality measures against national benchmarks and a peer cohort,
sizes the patient care-gap to the next threshold, and rolls a weighted
composite into a star-equivalent. Native reimplementation of the slice
of the Tuva quality mart diligence needs.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .measures import (
    QUALITY_MEASURES,
    MeasureResult,
    MeasureVerdict,
    QualityMeasure,
    QualityScorecard,
    evaluate_measure,
    get_measure,
    score_quality,
)

__all__ = [
    "QUALITY_MEASURES",
    "MeasureResult",
    "MeasureVerdict",
    "QualityMeasure",
    "QualityScorecard",
    "evaluate_measure",
    "get_measure",
    "score_quality",
]
