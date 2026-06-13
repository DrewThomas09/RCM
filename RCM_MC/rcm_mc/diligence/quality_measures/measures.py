"""HEDIS/CQM-style quality-measure gap analysis — numpy + stdlib.

Quality performance is a value driver and a downside risk: MA Stars
bonuses, ACO shared-savings gates, and VBC contract withholds all hinge
on measure rates. This mart scores a target's quality measures against
national benchmarks and (when available) a peer cohort, sizes the
**care gap** (patients you'd have to close to clear the next threshold),
and rolls a weighted composite into a star-equivalent.

Why gap-count, not just rate: a partner can't act on "82% on HbA1c
control." They can act on "47 diabetic patients are one A1c draw away
from clearing the 4-star cut." The gap-count is the operating lever.

Native reimplementation of the slice of the Tuva quality mart diligence
needs; runs on aggregate numerator/denominator counts, not claim lines.
The curated measure library follows the ``payer_library`` pattern — one
editable table with a documented benchmark and direction per measure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

CITATION_KEY = "QM1"
SOURCE_MODULE = "diligence.quality_measures"


class MeasureVerdict(str, Enum):
    ABOVE_BENCHMARK = "ABOVE_BENCHMARK"
    AT_BENCHMARK = "AT_BENCHMARK"
    BELOW_BENCHMARK = "BELOW_BENCHMARK"


@dataclass(frozen=True)
class QualityMeasure:
    """One measure definition + its national benchmark."""
    measure_id: str
    name: str
    higher_is_better: bool
    national_benchmark: float       # 0..1 rate
    domain: str                     # e.g. "Diabetes", "Prevention"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measure_id": self.measure_id, "name": self.name,
            "higher_is_better": self.higher_is_better,
            "national_benchmark": self.national_benchmark,
            "domain": self.domain, "notes": self.notes,
        }


# Curated library. Benchmarks are representative national rates for the
# 2026 diligence cycle — refresh from the HEDIS/CMS Stars technical
# specs annually. Rates are directional defaults, not contract values.
QUALITY_MEASURES: Tuple[QualityMeasure, ...] = (
    QualityMeasure("HBA1C_CONTROL", "Hemoglobin A1c control (<8%)",
                   True, 0.72, "Diabetes"),
    QualityMeasure("BP_CONTROL", "Controlling high blood pressure",
                   True, 0.66, "Cardiovascular"),
    QualityMeasure("STATIN_THERAPY", "Statin therapy for cardiovascular disease",
                   True, 0.83, "Cardiovascular"),
    QualityMeasure("BREAST_SCREEN", "Breast cancer screening",
                   True, 0.74, "Prevention"),
    QualityMeasure("COLORECTAL_SCREEN", "Colorectal cancer screening",
                   True, 0.71, "Prevention"),
    QualityMeasure("MED_ADHERENCE_DIABETES", "Medication adherence — diabetes",
                   True, 0.84, "Adherence"),
    QualityMeasure("MED_ADHERENCE_STATINS", "Medication adherence — statins",
                   True, 0.82, "Adherence"),
    QualityMeasure("FLU_VACCINE", "Annual flu vaccination",
                   True, 0.70, "Prevention"),
    QualityMeasure("PLAN_ALL_READMIT", "Plan all-cause readmissions",
                   False, 0.14, "Utilization",
                   notes="Lower is better — a rate, not a gap-close."),
    QualityMeasure("ED_UTILIZATION", "Avoidable ED utilization (per 1k)",
                   False, 0.18, "Utilization",
                   notes="Lower is better; expressed as a rate proxy."),
)

_BY_ID: Dict[str, QualityMeasure] = {m.measure_id: m for m in QUALITY_MEASURES}


def get_measure(measure_id: str) -> Optional[QualityMeasure]:
    return _BY_ID.get(measure_id)


@dataclass
class MeasureResult:
    measure_id: str
    name: str
    higher_is_better: bool
    numerator: int
    denominator: int
    rate: float
    benchmark: float
    gap_to_benchmark: float          # signed, in rate points (toward "good")
    gap_count: int                   # patients to close to reach benchmark
    percentile_vs_peers: Optional[float]
    verdict: MeasureVerdict
    performance_score: float         # 0..1, normalized "goodness"
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measure_id": self.measure_id, "name": self.name,
            "higher_is_better": self.higher_is_better,
            "numerator": self.numerator, "denominator": self.denominator,
            "rate": round(self.rate, 4), "benchmark": round(self.benchmark, 4),
            "gap_to_benchmark": round(self.gap_to_benchmark, 4),
            "gap_count": self.gap_count,
            "percentile_vs_peers": (
                None if self.percentile_vs_peers is None
                else round(self.percentile_vs_peers, 4)
            ),
            "verdict": self.verdict.value,
            "performance_score": round(self.performance_score, 4),
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


_AT_BAND = 0.02      # within 2 rate points of benchmark = "at"


def evaluate_measure(
    measure: QualityMeasure,
    numerator: int,
    denominator: int,
    peer_rates: Optional[Sequence[float]] = None,
) -> MeasureResult:
    """Score one measure: rate, signed gap to benchmark, the patient
    gap-count to reach it, peer percentile, and a normalized 0-1
    performance score (always oriented so higher = better, regardless
    of measure polarity)."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    rate = numerator / denominator
    bench = measure.national_benchmark

    if measure.higher_is_better:
        gap = bench - rate                          # >0 means below benchmark
        gap_count = max(0, math.ceil(gap * denominator)) if gap > 0 else 0
        if rate >= bench - _AT_BAND and rate <= bench + _AT_BAND:
            verdict = MeasureVerdict.AT_BENCHMARK
        elif rate > bench:
            verdict = MeasureVerdict.ABOVE_BENCHMARK
        else:
            verdict = MeasureVerdict.BELOW_BENCHMARK
        score = rate            # already 0..1, higher better
        gap_signed = bench - rate
    else:
        gap = rate - bench                          # >0 means worse (too high)
        gap_count = max(0, math.ceil(gap * denominator)) if gap > 0 else 0
        if abs(rate - bench) <= _AT_BAND:
            verdict = MeasureVerdict.AT_BENCHMARK
        elif rate < bench:
            verdict = MeasureVerdict.ABOVE_BENCHMARK   # below = better here
        else:
            verdict = MeasureVerdict.BELOW_BENCHMARK
        score = max(0.0, 1.0 - rate)   # lower rate → higher score
        gap_signed = bench - rate      # toward "good" (negative if worse)

    pct: Optional[float] = None
    if peer_rates:
        peers = list(peer_rates)
        below = sum(1 for p in peers if p < rate)
        raw_pct = below / len(peers)
        # For lower-is-better, invert so high percentile = good.
        pct = raw_pct if measure.higher_is_better else (1.0 - raw_pct)

    return MeasureResult(
        measure_id=measure.measure_id, name=measure.name,
        higher_is_better=measure.higher_is_better,
        numerator=numerator, denominator=denominator, rate=rate,
        benchmark=bench, gap_to_benchmark=gap_signed, gap_count=gap_count,
        percentile_vs_peers=pct, verdict=verdict,
        performance_score=score,
    )


@dataclass
class QualityScorecard:
    composite_score: float           # 0..100
    star_equivalent: float           # 1..5
    n_measures: int
    total_gap_patients: int
    weakest_measures: List[str]
    results: List[MeasureResult] = field(default_factory=list)
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 2),
            "star_equivalent": round(self.star_equivalent, 2),
            "n_measures": self.n_measures,
            "total_gap_patients": self.total_gap_patients,
            "weakest_measures": list(self.weakest_measures),
            "results": [r.to_dict() for r in self.results],
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def score_quality(
    results: Sequence[MeasureResult],
    weights: Optional[Dict[str, float]] = None,
) -> QualityScorecard:
    """Roll measure results into a weighted composite (0-100) and a
    star-equivalent (1-5). Weights default to equal. ``total_gap_patients``
    is the sum of gap-counts — the addressable book of work; the three
    lowest-scoring measures are surfaced as the priorities."""
    results = list(results)
    if not results:
        return QualityScorecard(0.0, 1.0, 0, 0, [], [], "No measures scored.")
    w = weights or {}
    tot_w = 0.0
    acc = 0.0
    for r in results:
        wi = w.get(r.measure_id, 1.0)
        acc += wi * r.performance_score
        tot_w += wi
    composite01 = acc / tot_w if tot_w else 0.0
    composite = composite01 * 100
    star = 1.0 + 4.0 * composite01
    total_gap = sum(r.gap_count for r in results)
    weakest = [
        r.measure_id for r in sorted(results, key=lambda r: r.performance_score)
    ][:3]
    sc = QualityScorecard(
        composite_score=composite, star_equivalent=star,
        n_measures=len(results), total_gap_patients=total_gap,
        weakest_measures=weakest, results=results,
    )
    below = sum(1 for r in results if r.verdict == MeasureVerdict.BELOW_BENCHMARK)
    sc.headline = (
        f"Quality composite {composite:.1f}/100 (~{star:.1f} stars) across "
        f"{len(results)} measures; {below} below benchmark, "
        f"{total_gap:,} patient-gaps to close. Priorities: "
        f"{', '.join(weakest)}."
    )
    return sc
