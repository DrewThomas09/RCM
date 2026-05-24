"""Cross-metric correlation layer over the six live CMS verticals.

For one vertical it computes, across all providers that publicly report both
measures, the **pairwise association** (Pearson r and Spearman rho) between
every pair of reported quality measures — e.g. in SNFs, how staffing-hours
co-move with the health-inspection rating.

Hard honesty rules (enforced in tests):
- This is **association, NOT causation**. A correlation never licenses a
  causal, predictive, commercial-revenue, market-share, or investment claim.
- Pairwise-complete only: each pair uses providers reporting BOTH measures;
  the sample size n is reported alongside every coefficient.
- Coefficients are suppressed below ``_MIN_N`` (unreliable at small n).
- Each measure's *direction* (higher-is-better / lower-is-better) is exposed
  so the reader interprets the SIGN themselves — we never relabel a metric as
  "good" or "bad".
- Several measures are CMS risk-adjusted estimates; correlations among them
  reflect the adjusted values, not raw outcomes.

Lives in data/; only reads the existing data/ loaders (via cross_sector).
Never imports the ui/ layer, never hits the network.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cross_sector import SECTOR_BY_ID, SectorSpec

_MIN_N = 30  # below this a correlation coefficient is too noisy to report


# Human label + direction for every reported measure key across the six
# verticals. direction: "higher" = higher is better, "lower" = lower is
# better, "rating" = ordinal CMS star/rating (higher better). Used only to let
# the reader interpret a coefficient's sign — never to score a provider.
_METRIC_META: Dict[str, Tuple[str, str]] = {
    # Home Health
    "star_rating": ("Quality star rating", "rating"),
    "timely_initiation_pct": ("Timely initiation of care", "higher"),
    "discharge_to_community_rate": ("Discharge to community", "higher"),
    "improve_ambulation_pct": ("Improvement in ambulation", "higher"),
    "improve_bathing_pct": ("Improvement in bathing", "higher"),
    "improve_bed_transfer_pct": ("Improvement in bed transferring", "higher"),
    "cahps_summary_star": ("Patient-survey summary star", "rating"),
    "cahps_professional_star": ("Care of patients star", "rating"),
    "cahps_communication_star": ("Communication star", "rating"),
    "cahps_medicines_star": ("Medicines discussion star", "rating"),
    "cahps_overall_star": ("Overall care star", "rating"),
    "cahps_overall_9_10_pct": ("Rated agency 9-10", "higher"),
    "cahps_recommend_pct": ("Would recommend", "higher"),
    # Hospice
    "composite_process": ("Composite process measure", "higher"),
    "care_index_overall": ("Hospice Care Index", "higher"),
    "visits_last_days": ("Visits in last days of life", "higher"),
    "pain_screening": ("Pain screening", "higher"),
    "treatment_preferences": ("Treatment preferences", "higher"),
    "beliefs_values": ("Beliefs/values addressed", "higher"),
    "cahps_rating_9_10_pct": ("Family rating 9-10", "higher"),
    "cahps_communication_pct": ("Communication with family", "higher"),
    "cahps_symptoms_pct": ("Help for symptoms", "higher"),
    "cahps_respect_pct": ("Treated with respect", "higher"),
    "cahps_timely_pct": ("Timely help", "higher"),
    "cahps_emotional_pct": ("Emotional/spiritual support", "higher"),
    # SNF / Nursing Home
    "overall_rating": ("Overall star rating", "rating"),
    "health_inspection_rating": ("Health-inspection rating", "rating"),
    "staffing_rating": ("Staffing rating", "rating"),
    "qm_rating": ("Quality-measure rating", "rating"),
    "rn_hprd": ("RN hours per resident day", "higher"),
    "total_nurse_hprd": ("Total nurse hours per resident day", "higher"),
    "total_nurse_turnover_pct": ("Total nurse turnover", "lower"),
    "num_fines": ("Number of fines", "lower"),
    "total_fines_usd": ("Total fine dollars", "lower"),
    "num_payment_denials": ("Payment denials", "lower"),
    "num_penalties": ("Total penalties", "lower"),
    # Dialysis
    "five_star": ("Overall 5-star rating", "rating"),
    "mortality_rate": ("Mortality rate (risk-adj.)", "lower"),
    "hospitalization_rate": ("Hospitalization rate (risk-adj.)", "lower"),
    "readmission_rate": ("Readmission rate (risk-adj.)", "lower"),
    "transfusion_rate": ("Transfusion rate (risk-adj.)", "lower"),
    "cahps_facility_star": ("Patient-survey facility star", "rating"),
    "cahps_nephrologist_comm_star": ("Nephrologist communication star", "rating"),
    "cahps_center_care_star": ("Center care & operations star", "rating"),
    "cahps_information_star": ("Providing information star", "rating"),
    "cahps_nephrologist_star": ("Rating of nephrologist star", "rating"),
    "cahps_staff_star": ("Rating of dialysis-center staff star", "rating"),
    # IRF + LTCH (shared keys)
    "dtc_rs_rate": ("Successful return to home/community", "higher"),
    "selfcare_fn_pct": ("Self-care function at/above expected", "higher"),
    "mobility_fn_pct": ("Mobility function at/above expected", "higher"),
    "hcp_flu_pct": ("Healthcare-personnel flu vaccination", "higher"),
    "med_review_pct": ("Medication review & follow-up", "higher"),
    "med_list_next_pct": ("Medication list to next provider", "higher"),
    "vent_weaning_pct": ("Successfully weaned from ventilator", "higher"),
    "readmission_rsrr": ("Readmission (risk-std. rate)", "lower"),
    "within_stay_readmit_rsrr": ("Within-stay readmission (RSRR)", "lower"),
    "mspb_score": ("Medicare spend per beneficiary", "lower"),
    "pressure_ulcer_rate": ("Pressure-ulcer rate", "lower"),
    "falls_major_injury_rate": ("Falls with major injury", "lower"),
    "cauti_sir": ("CAUTI standardized infection ratio", "lower"),
    "clabsi_sir": ("CLABSI standardized infection ratio", "lower"),
    "cdi_sir": ("C. diff standardized infection ratio", "lower"),
}

CORR_CAVEATS: Tuple[str, ...] = (
    "Association only — NOT causation. A correlation between two public "
    "measures does not mean one drives the other; both may track an "
    "unmeasured factor (case mix, geography, size).",
    "Pairwise-complete: each coefficient uses only providers that report "
    "BOTH measures; read it with the n shown.",
    "Coefficients below n=30 are suppressed as unreliable.",
    "Several measures are CMS risk-adjusted estimates; correlations reflect "
    "the adjusted values, not raw outcomes.",
    "Not a forecast, not an investment signal, not a commercial-revenue or "
    "market-share claim.",
)


@dataclass(frozen=True)
class CorrPair:
    key_a: str
    key_b: str
    label_a: str
    label_b: str
    direction_a: str
    direction_b: str
    pearson_r: float
    spearman_rho: Optional[float]
    n: int

    @property
    def same_direction(self) -> bool:
        """True when both measures point the same way (both higher- or both
        lower-is-better). Lets a UI flag a 'directionally consistent' pair
        without us asserting why."""
        norm = {"rating": "higher"}
        return (norm.get(self.direction_a, self.direction_a)
                == norm.get(self.direction_b, self.direction_b))


@dataclass
class SectorCorrelations:
    sector_id: str
    sector_label: str
    provider_n: int
    pairs: List[CorrPair]            # sorted by |pearson_r| desc
    metrics: List[Tuple[str, str, str]]  # (key, label, direction) included
    caveats: List[str] = field(default_factory=lambda: list(CORR_CAVEATS))


def metric_meta(key: str) -> Tuple[str, str]:
    """(label, direction) for a measure key; humanized fallback if unmapped."""
    return _METRIC_META.get(key, (key.replace("_", " ").title(), "neutral"))


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:          # a constant column has no correlation
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(sxy / math.sqrt(sxx * syy), 3)


def _rank(vals: List[float]) -> List[float]:
    """Average-rank transform (ties share the mean rank)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based average rank for the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    return _pearson(_rank(xs), _rank(ys))


def sector_correlations(sector_id: str, min_n: int = _MIN_N
                        ) -> Optional[SectorCorrelations]:
    """Pairwise associations among the reported measures of one vertical.

    Returns None if the sector id is unknown.
    """
    spec: Optional[SectorSpec] = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return None
    quality = spec.quality_loader()

    # Metric keys actually present, in a stable order: known keys first
    # (in _METRIC_META insertion order), then any unmapped extras sorted.
    present = set()
    for row in quality.values():
        present |= {k for k, v in row.items() if v is not None}
    ordered = [k for k in _METRIC_META if k in present]
    ordered += sorted(k for k in present if k not in _METRIC_META)

    pairs: List[CorrPair] = []
    for ai in range(len(ordered)):
        for bi in range(ai + 1, len(ordered)):
            ka, kb = ordered[ai], ordered[bi]
            xs: List[float] = []
            ys: List[float] = []
            for row in quality.values():
                va, vb = row.get(ka), row.get(kb)
                if va is not None and vb is not None:
                    xs.append(float(va))
                    ys.append(float(vb))
            if len(xs) < min_n:
                continue
            r = _pearson(xs, ys)
            if r is None:
                continue
            la, da = metric_meta(ka)
            lb, db = metric_meta(kb)
            pairs.append(CorrPair(
                key_a=ka, key_b=kb, label_a=la, label_b=lb,
                direction_a=da, direction_b=db,
                pearson_r=r, spearman_rho=_spearman(xs, ys), n=len(xs)))

    pairs.sort(key=lambda p: -abs(p.pearson_r))
    metrics = [(k, *metric_meta(k)) for k in ordered]
    return SectorCorrelations(
        sector_id=sector_id, sector_label=spec.label,
        provider_n=len(quality), pairs=pairs, metrics=metrics)


def top_correlations(sector_id: str, k: int = 10, min_n: int = _MIN_N
                     ) -> List[CorrPair]:
    """The k strongest associations (by |Pearson r|) for the vertical."""
    sc = sector_correlations(sector_id, min_n=min_n)
    return sc.pairs[:k] if sc else []
