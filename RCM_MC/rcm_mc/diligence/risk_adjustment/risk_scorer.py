"""CMS-HCC RAF scoring + risk-adjusted peer benchmarking.

Two jobs, both diligence questions:

1. **RAF scoring** (:func:`compute_raf`, :func:`score_panel`) — turn a
   demographic + condition profile into a Risk Adjustment Factor. A
   panel RAF tells you how sick the population is relative to the
   program average (1.00).

2. **Risk-adjusted benchmarking** (:func:`risk_adjust_metric`) — the
   load-bearing one. Comparing a target's cost/outcome to peers
   without normalizing for case mix gets you fooled by a sicker (or
   healthier) panel. This divides observed performance by the
   case-mix expectation so you compare apples-to-apples. The output
   is the observed-to-expected (O/E) ratio every payer and ACO uses:

       O/E = observed_metric / (peer_metric_per_RAF × target_RAF)

   O/E ≈ 1.0 means the target performs as its case mix predicts.
   O/E > 1.0 on a *cost* metric means it is expensive after adjusting
   for how sick its patients are — an operator signal, not a panel
   artifact. The verdict flips sign for "lower-is-better" metrics
   (cost, readmissions, ED visits) vs "higher-is-better" (quality
   stars, gap-closure rate).

Every output carries ``source_module`` / ``citation_key`` so it slots
into the provenance graph like the rest of the diligence marts.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Sequence, Tuple

from .hcc_library import (
    CITATION_KEY,
    DISEASE_INTERACTIONS,
    SEGMENT,
    SOURCE_MODULE,
    apply_hierarchies,
    demographic_factor,
    get_hcc,
    map_condition_to_hcc,
)


class RiskVerdict(str, Enum):
    """How the target looks *after* case-mix normalization."""
    EFFICIENT = "EFFICIENT"     # meaningfully better than case mix predicts
    IN_LINE = "IN_LINE"         # within noise of expectation
    ELEVATED = "ELEVATED"       # worse than expected, watch
    OUTLIER = "OUTLIER"         # materially worse than expected


@dataclass(frozen=True)
class Demographics:
    """Minimum demographic inputs for the RAF demographic component."""
    age: int
    sex: str = "F"
    disabled: bool = False      # under-65 Medicare via disability

    def to_dict(self) -> Dict[str, Any]:
        return {"age": self.age, "sex": self.sex, "disabled": self.disabled}


@dataclass
class RiskScore:
    """Decomposed RAF for one patient or one panel-average."""
    raf: float
    demographic_component: float
    disease_component: float
    interaction_component: float
    hccs: List[str] = field(default_factory=list)          # post-hierarchy
    interactions: List[str] = field(default_factory=list)
    unmapped_conditions: List[str] = field(default_factory=list)
    segment: str = SEGMENT
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raf": round(self.raf, 4),
            "demographic_component": round(self.demographic_component, 4),
            "disease_component": round(self.disease_component, 4),
            "interaction_component": round(self.interaction_component, 4),
            "hccs": list(self.hccs),
            "interactions": list(self.interactions),
            "unmapped_conditions": list(self.unmapped_conditions),
            "segment": self.segment,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def compute_raf(
    demographics: Demographics,
    conditions: Sequence[str],
) -> RiskScore:
    """Compute a single beneficiary's RAF.

    ``conditions`` is a list of ICD-10 codes and/or free-text condition
    names; each is crosswalked, the disease hierarchy is applied
    (severe trumps mild within a family), surviving HCC coefficients
    are summed, and documented interaction factors are added.

    Conditions that don't crosswalk are returned in
    ``unmapped_conditions`` rather than dropped, so the analyst can
    judge crosswalk coverage on the target's actual coding."""
    demo = demographic_factor(
        demographics.sex, demographics.age, demographics.disabled,
    )

    mapped: List[str] = []
    unmapped: List[str] = []
    for c in conditions:
        hcc = map_condition_to_hcc(c)
        if hcc is None:
            unmapped.append(str(c))
        else:
            mapped.append(hcc)

    survivors = apply_hierarchies(mapped)
    disease = 0.0
    for h in survivors:
        f = get_hcc(h)
        if f is not None:
            disease += f.coefficient

    survivor_set = set(survivors)
    inter_total = 0.0
    inter_labels: List[str] = []
    for required, label, coef in DISEASE_INTERACTIONS:
        if required.issubset(survivor_set):
            inter_total += coef
            if label not in inter_labels:
                inter_labels.append(label)

    raf = demo + disease + inter_total
    return RiskScore(
        raf=raf,
        demographic_component=demo,
        disease_component=disease,
        interaction_component=inter_total,
        hccs=survivors,
        interactions=inter_labels,
        unmapped_conditions=unmapped,
    )


@dataclass
class PanelRiskScore:
    """RAF rolled up across a panel of beneficiaries."""
    n_beneficiaries: int
    mean_raf: float
    median_raf: float
    p90_raf: float
    demographic_component: float        # panel-mean decomposition
    disease_component: float
    interaction_component: float
    hcc_prevalence: Dict[str, float] = field(default_factory=dict)
    segment: str = SEGMENT
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_beneficiaries": self.n_beneficiaries,
            "mean_raf": round(self.mean_raf, 4),
            "median_raf": round(self.median_raf, 4),
            "p90_raf": round(self.p90_raf, 4),
            "demographic_component": round(self.demographic_component, 4),
            "disease_component": round(self.disease_component, 4),
            "interaction_component": round(self.interaction_component, 4),
            "hcc_prevalence": {
                k: round(v, 4) for k, v in self.hcc_prevalence.items()
            },
            "segment": self.segment,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def _percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0,1]. stdlib-only."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def score_panel(
    beneficiaries: Sequence[Tuple[Demographics, Sequence[str]]],
) -> PanelRiskScore:
    """Score a panel: a sequence of (Demographics, conditions) pairs.

    Returns mean/median/p90 RAF, the panel-mean RAF decomposition, and
    per-HCC prevalence (share of the panel carrying each HCC after
    hierarchy) — the prevalence table is what tells you *which*
    conditions are driving a high panel RAF."""
    if not beneficiaries:
        return PanelRiskScore(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    scores = [compute_raf(d, c) for d, c in beneficiaries]
    n = len(scores)
    rafs = sorted(s.raf for s in scores)
    hcc_counts: Dict[str, int] = {}
    for s in scores:
        for h in set(s.hccs):
            hcc_counts[h] = hcc_counts.get(h, 0) + 1
    prevalence = {h: c / n for h, c in sorted(
        hcc_counts.items(), key=lambda kv: -kv[1],
    )}
    return PanelRiskScore(
        n_beneficiaries=n,
        mean_raf=sum(rafs) / n,
        median_raf=statistics.median(rafs),
        p90_raf=_percentile(rafs, 0.90),
        demographic_component=sum(
            s.demographic_component for s in scores) / n,
        disease_component=sum(s.disease_component for s in scores) / n,
        interaction_component=sum(
            s.interaction_component for s in scores) / n,
        hcc_prevalence=prevalence,
    )


# ────────────────────────────────────────────────────────────────────
# Risk-adjusted benchmarking
# ────────────────────────────────────────────────────────────────────

@dataclass
class RiskAdjustedBenchmark:
    """Observed-to-expected comparison of one metric vs a peer cohort."""
    metric_name: str
    lower_is_better: bool
    target_value: float
    target_raf: float
    peer_mean_value: float
    peer_mean_raf: float
    expected_value: float           # case-mix-adjusted expectation
    oe_ratio: float                 # observed / expected
    raw_ratio: float                # observed / peer mean (un-adjusted)
    case_mix_effect: float          # how much of the raw gap was case mix
    percentile_vs_peers: float      # O/E percentile rank, 0..1
    verdict: RiskVerdict
    headline: str = ""
    n_peers: int = 0
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "lower_is_better": self.lower_is_better,
            "target_value": self.target_value,
            "target_raf": round(self.target_raf, 4),
            "peer_mean_value": self.peer_mean_value,
            "peer_mean_raf": round(self.peer_mean_raf, 4),
            "expected_value": round(self.expected_value, 4),
            "oe_ratio": round(self.oe_ratio, 4),
            "raw_ratio": round(self.raw_ratio, 4),
            "case_mix_effect": round(self.case_mix_effect, 4),
            "percentile_vs_peers": round(self.percentile_vs_peers, 4),
            "verdict": self.verdict.value,
            "headline": self.headline,
            "n_peers": self.n_peers,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


# O/E bands. Symmetric around 1.0; >10% off expectation = ELEVATED,
# >25% off = OUTLIER. Tuned to the same "material" threshold the rest
# of the workbench uses for EBITDA-moving findings.
_IN_LINE_BAND = 0.10
_OUTLIER_BAND = 0.25


def _classify_oe(oe: float, lower_is_better: bool) -> RiskVerdict:
    """Map an O/E ratio to a verdict, respecting metric polarity."""
    # Normalize so that "worse than expected" is always oe > 1.
    worse = oe if lower_is_better else (1.0 / oe if oe > 0 else 99.0)
    if worse >= 1.0 + _OUTLIER_BAND:
        return RiskVerdict.OUTLIER
    if worse >= 1.0 + _IN_LINE_BAND:
        return RiskVerdict.ELEVATED
    if worse <= 1.0 - _IN_LINE_BAND:
        return RiskVerdict.EFFICIENT
    return RiskVerdict.IN_LINE


def risk_adjust_metric(
    metric_name: str,
    target_value: float,
    target_raf: float,
    peer_values: Sequence[float],
    peer_rafs: Sequence[float],
    lower_is_better: bool = True,
) -> RiskAdjustedBenchmark:
    """Risk-adjust one metric against a peer cohort.

    The peer cohort defines the per-RAF rate (metric per unit of risk):

        peer_rate_per_raf = mean(peer_value) / mean(peer_raf)
        expected_value    = peer_rate_per_raf × target_raf
        O/E               = target_value / expected_value

    ``case_mix_effect`` decomposes the raw (unadjusted) target-vs-peer
    gap into the portion explained purely by the target being sicker
    or healthier than peers — the number that stops a partner reading
    a sick-panel cost as an operator failure.

    Per-peer O/E ratios give the percentile rank, so the verdict is
    grounded in the cohort's actual spread rather than a fixed band
    alone."""
    peer_values = list(peer_values)
    peer_rafs = list(peer_rafs)
    n = len(peer_values)
    if n == 0 or len(peer_rafs) != n:
        raise ValueError("peer_values and peer_rafs must be same non-zero length")

    peer_mean_value = sum(peer_values) / n
    peer_mean_raf = sum(peer_rafs) / n
    if peer_mean_raf <= 0 or target_raf <= 0:
        raise ValueError("RAF values must be positive")

    peer_rate_per_raf = peer_mean_value / peer_mean_raf
    expected_value = peer_rate_per_raf * target_raf
    oe = target_value / expected_value if expected_value != 0 else 0.0
    raw_ratio = target_value / peer_mean_value if peer_mean_value != 0 else 0.0
    # Case-mix effect: the multiplicative gap attributable to RAF alone.
    case_mix_effect = (target_raf / peer_mean_raf) if peer_mean_raf else 1.0

    # Per-peer O/E for percentile placement (each peer vs the cohort).
    peer_oes: List[float] = []
    for v, r in zip(peer_values, peer_rafs):
        exp = peer_rate_per_raf * r
        peer_oes.append(v / exp if exp != 0 else 0.0)
    below = sum(1 for x in peer_oes if x < oe)
    pct = below / n

    verdict = _classify_oe(oe, lower_is_better)
    headline = _benchmark_headline(
        metric_name, oe, case_mix_effect, raw_ratio,
        lower_is_better, verdict,
    )
    return RiskAdjustedBenchmark(
        metric_name=metric_name,
        lower_is_better=lower_is_better,
        target_value=target_value,
        target_raf=target_raf,
        peer_mean_value=peer_mean_value,
        peer_mean_raf=peer_mean_raf,
        expected_value=expected_value,
        oe_ratio=oe,
        raw_ratio=raw_ratio,
        case_mix_effect=case_mix_effect,
        percentile_vs_peers=pct,
        verdict=verdict,
        headline=headline,
        n_peers=n,
    )


def _benchmark_headline(
    metric: str, oe: float, case_mix: float, raw: float,
    lower_is_better: bool, verdict: RiskVerdict,
) -> str:
    """Partner-facing one-liner that separates the case-mix story from
    the operator story — the whole point of risk adjustment."""
    raw_gap = (raw - 1.0) * 100
    oe_gap = (oe - 1.0) * 100
    cm_gap = (case_mix - 1.0) * 100
    direction = "above" if raw_gap >= 0 else "below"
    if verdict == RiskVerdict.IN_LINE:
        return (
            f"{metric}: {abs(raw_gap):.1f}% {direction} peers raw, but the "
            f"panel is {cm_gap:+.1f}% on case mix — performance is in line "
            f"with expectation (O/E {oe:.2f})."
        )
    polarity = "favorable" if (
        (oe < 1.0) == lower_is_better
    ) else "unfavorable"
    return (
        f"{metric}: O/E {oe:.2f} ({oe_gap:+.1f}% vs case-mix expectation, "
        f"{polarity}). Raw gap to peers {raw_gap:+.1f}%; case mix explains "
        f"{cm_gap:+.1f}% of it — verdict {verdict.value}."
    )
