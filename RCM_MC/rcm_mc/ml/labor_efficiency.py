"""Labor efficiency model — staffing vs peers + EBITDA impact.

HCRIS Worksheet S-3 Part II reports total FTEs and salary cost.
The partner-relevant questions are:

  • Is this hospital over- or under-staffed vs peer cohort?
  • What's the EBITDA impact of right-sizing to peer median?

Three canonical staffing metrics drive the analysis:

  • **FTE per AOB** (adjusted occupied bed) — the headline
    intensity ratio. Industry median is ~5.5; <4.5 lean,
    >7.0 heavy.
  • **Labor cost per adjusted discharge** — captures wage-rate
    + intensity together. Median ~$8K; <$6K lean, >$11K heavy.
  • **Labor as % of NPSR** — catches the ratio in $ terms when
    revenue is the binding constraint. Median ~52%; >60% is the
    'labor-pressured' band.

Identify over/understaffing:

  • Over-staffed: any of the three metrics above p75 of peers
    AND not in a quality-flagged category (turnover-vacancy
    inflated FTE numbers don't count as 'overstaffed').
  • Under-staffed: any below p25 — quality + burnout risk.
  • Otherwise: in-line.

EBITDA optimization model:

  • Target staffing = peer p50 FTE/AOB × hospital AOB.
  • Realism factor 0.40 default — labor is sticky (attrition,
    union contracts, skill mix). Override per-deal.
  • EBITDA savings = (current_fte - target_fte) × salary_per_fte
    × realism. Conservative / realistic / optimistic at
    0.7× / 1.0× / 1.3× the realism factor (matching the
    improvement_potential.py scenario taxonomy).

Public API::

    from rcm_mc.ml.labor_efficiency import (
        HospitalLaborProfile,
        LaborPeerBenchmarks,
        LaborEfficiencyResult,
        compute_labor_efficiency,
        model_labor_optimization_impact,
        compute_peer_benchmarks,
    )
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Industry medians for fallback when peer data is sparse. Sourced
# from MGMA + AHA labor benchmark reports.
INDUSTRY_FALLBACK = {
    "fte_per_aob": {"p25": 4.5, "p50": 5.5, "p75": 7.0},
    "labor_cost_per_adj_discharge":
        {"p25": 6_000, "p50": 8_000, "p75": 11_000},
    "labor_pct_of_npsr":
        {"p25": 0.45, "p50": 0.52, "p75": 0.60},
    "salary_per_fte":
        {"p25": 75_000, "p50": 95_000, "p75": 125_000},
}

# Realism factor — share of identified labor gap that is
# realistically closeable in 12-18 months. Lower than RCM levers
# because labor is sticky (attrition, skill mix, contracts).
DEFAULT_LABOR_REALISM = 0.40

# Scenario multipliers — match improvement_potential.py taxonomy
# so partner sees the same conservative / realistic / optimistic
# language across all uplift estimates.
_SCENARIO_MULTIPLIERS = {
    "conservative": 0.70,
    "realistic": 1.00,
    "optimistic": 1.30,
}


@dataclass
class HospitalLaborProfile:
    """Inputs for one hospital × fiscal year.

    All numbers from HCRIS S-3 Part II + G-2 + S-3 Part I:
      - total_fte: Worksheet S-3 Part II col 12 (paid + worked
        FTE total).
      - total_labor_cost: Worksheet A col 1+2 + benefits.
      - adjusted_occupied_beds (AOB): inpatient days + outpatient-
        equivalent days, all-payer (Worksheet S-3 Part I).
      - adjusted_discharges: discharges + outpatient-equivalent
        discharges.
      - net_patient_revenue: Worksheet G-2 line 1.
    """
    ccn: str
    fiscal_year: int
    beds: float
    adjusted_occupied_beds: float
    adjusted_discharges: float
    total_fte: float
    total_labor_cost: float
    net_patient_revenue: float
    # Optional peer-cohort tags
    bed_size_bucket: Optional[str] = None
    region: Optional[str] = None
    teaching_status: Optional[str] = None  # 'major' | 'minor' | 'non'

    @property
    def fte_per_aob(self) -> Optional[float]:
        if self.adjusted_occupied_beds <= 0:
            return None
        return self.total_fte / self.adjusted_occupied_beds

    @property
    def labor_cost_per_adj_discharge(
        self,
    ) -> Optional[float]:
        if self.adjusted_discharges <= 0:
            return None
        return (self.total_labor_cost
                / self.adjusted_discharges)

    @property
    def labor_pct_of_npsr(self) -> Optional[float]:
        if self.net_patient_revenue <= 0:
            return None
        return (self.total_labor_cost
                / self.net_patient_revenue)

    @property
    def salary_per_fte(self) -> Optional[float]:
        if self.total_fte <= 0:
            return None
        return self.total_labor_cost / self.total_fte


@dataclass
class LaborPeerBenchmarks:
    """Peer percentile lookup for the four staffing metrics."""
    fte_per_aob: Dict[str, float] = field(
        default_factory=dict)
    labor_cost_per_adj_discharge: Dict[str, float] = field(
        default_factory=dict)
    labor_pct_of_npsr: Dict[str, float] = field(
        default_factory=dict)
    salary_per_fte: Dict[str, float] = field(
        default_factory=dict)
    n_peers: int = 0
    cohort_label: str = ""


@dataclass
class MetricVariance:
    metric: str
    hospital_value: float
    peer_p25: float
    peer_p50: float
    peer_p75: float
    percentile: float            # 0-100
    direction: str               # 'over_staffed' / 'under_staffed' / 'in_line'
    higher_is_efficient: bool    # for labor: usually False
    gap_to_p50: float            # signed: hospital - peer p50


@dataclass
class LaborOptimizationScenario:
    target_fte: float
    fte_reduction: float
    annual_labor_savings: float
    ebitda_impact: float       # = labor savings (1:1 for labor)
    realism_factor: float


@dataclass
class LaborEfficiencyResult:
    ccn: str
    fiscal_year: int
    profile_metrics: Dict[str, Optional[float]]
    variances: List[MetricVariance]
    overall_staffing_label: str  # 'over' / 'under' / 'in_line'
    n_metrics_over: int
    n_metrics_under: int
    optimization: Dict[str, LaborOptimizationScenario] = (
        field(default_factory=dict))
    notes: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────

def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    n = len(vs)
    if n == 1:
        return vs[0]
    k = (n - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vs[int(k)]
    return vs[f] * (c - k) + vs[c] * (k - f)


def _percentile_of(value: float,
                   sorted_values: List[float]) -> float:
    """Return the percentile (0-100) of ``value`` within sorted_values."""
    if not sorted_values:
        return 50.0
    n = len(sorted_values)
    below = sum(1 for v in sorted_values if v < value)
    return round(100 * below / n, 1)


def _bed_size_bucket(beds: float) -> str:
    b = float(beds or 0)
    if b < 50:
        return "critical_access"
    if b < 150:
        return "small"
    if b < 400:
        return "mid"
    return "large"


# ── Peer benchmarks ──────────────────────────────────────────

def compute_peer_benchmarks(
    peers: Iterable[HospitalLaborProfile],
    *,
    target_bucket: Optional[str] = None,
    target_region: Optional[str] = None,
    target_teaching: Optional[str] = None,
) -> LaborPeerBenchmarks:
    """Compute peer percentiles for a cohort.

    Filters peers to the given bucket/region/teaching status,
    then computes p25/p50/p75 across each metric. When fewer than
    5 peers match, the function falls back to industry medians
    (INDUSTRY_FALLBACK) so callers always get usable numbers.
    """
    filtered = []
    for p in peers:
        if (target_bucket and p.bed_size_bucket
                and p.bed_size_bucket != target_bucket):
            continue
        if (target_region and p.region
                and p.region != target_region):
            continue
        if (target_teaching and p.teaching_status
                and p.teaching_status != target_teaching):
            continue
        filtered.append(p)

    cohort_label_parts = []
    if target_bucket:
        cohort_label_parts.append(target_bucket)
    if target_region:
        cohort_label_parts.append(target_region)
    if target_teaching:
        cohort_label_parts.append(
            f"teaching={target_teaching}")
    cohort_label = (" / ".join(cohort_label_parts)
                    or "all peers")

    if len(filtered) < 5:
        # Fall back to industry medians but record the gap
        return LaborPeerBenchmarks(
            fte_per_aob=dict(
                INDUSTRY_FALLBACK["fte_per_aob"]),
            labor_cost_per_adj_discharge=dict(
                INDUSTRY_FALLBACK[
                    "labor_cost_per_adj_discharge"]),
            labor_pct_of_npsr=dict(
                INDUSTRY_FALLBACK["labor_pct_of_npsr"]),
            salary_per_fte=dict(
                INDUSTRY_FALLBACK["salary_per_fte"]),
            n_peers=len(filtered),
            cohort_label=f"{cohort_label} (fallback)",
        )

    def _compute(metric_attr: str) -> Dict[str, float]:
        vals = []
        for p in filtered:
            v = getattr(p, metric_attr)
            if v is not None:
                vals.append(float(v))
        if not vals:
            return INDUSTRY_FALLBACK.get(
                metric_attr,
                {"p25": 0.0, "p50": 0.0, "p75": 0.0})
        return {
            "p25": round(_percentile(vals, 0.25), 4),
            "p50": round(_percentile(vals, 0.50), 4),
            "p75": round(_percentile(vals, 0.75), 4),
        }

    return LaborPeerBenchmarks(
        fte_per_aob=_compute("fte_per_aob"),
        labor_cost_per_adj_discharge=_compute(
            "labor_cost_per_adj_discharge"),
        labor_pct_of_npsr=_compute(
            "labor_pct_of_npsr"),
        salary_per_fte=_compute("salary_per_fte"),
        n_peers=len(filtered),
        cohort_label=cohort_label,
    )


# ── Variance computation ─────────────────────────────────────

def _build_variance(
    metric: str,
    hospital_value: Optional[float],
    bench: Dict[str, float],
    peers_sorted: List[float],
) -> Optional[MetricVariance]:
    """Compare hospital metric to peer percentiles. For labor
    metrics lower is more efficient (less staff per bed, less
    cost per discharge), so above p75 = over-staffed, below p25
    = under-staffed."""
    if hospital_value is None:
        return None
    p25 = bench.get("p25", 0.0)
    p50 = bench.get("p50", 0.0)
    p75 = bench.get("p75", 0.0)
    pct = _percentile_of(hospital_value, peers_sorted)

    direction = "in_line"
    if hospital_value > p75:
        direction = "over_staffed"
    elif hospital_value < p25:
        direction = "under_staffed"
    return MetricVariance(
        metric=metric,
        hospital_value=round(hospital_value, 4),
        peer_p25=p25, peer_p50=p50, peer_p75=p75,
        percentile=pct,
        direction=direction,
        higher_is_efficient=False,
        gap_to_p50=round(hospital_value - p50, 4),
    )


def compute_labor_efficiency(
    profile: HospitalLaborProfile,
    peers: Iterable[HospitalLaborProfile],
    *,
    use_cohort: bool = True,
) -> LaborEfficiencyResult:
    """Score a hospital's labor efficiency vs peers.

    Args:
      profile: target hospital.
      peers: peer hospitals (typically the bed-size cohort).
      use_cohort: when True, filter peers to the same bed-size
        bucket. When False, compare to the full peer set.
    """
    bucket = (profile.bed_size_bucket
              or _bed_size_bucket(profile.beds))
    benchmarks = compute_peer_benchmarks(
        peers,
        target_bucket=bucket if use_cohort else None,
    )

    # Pre-sort peer values for percentile-of computation
    peers_list = list(peers)

    def _peer_vals(attr: str) -> List[float]:
        out = []
        for p in peers_list:
            v = getattr(p, attr)
            if v is not None:
                out.append(float(v))
        return sorted(out)

    metrics_to_check = [
        ("fte_per_aob", profile.fte_per_aob,
         benchmarks.fte_per_aob),
        ("labor_cost_per_adj_discharge",
         profile.labor_cost_per_adj_discharge,
         benchmarks.labor_cost_per_adj_discharge),
        ("labor_pct_of_npsr",
         profile.labor_pct_of_npsr,
         benchmarks.labor_pct_of_npsr),
        ("salary_per_fte",
         profile.salary_per_fte,
         benchmarks.salary_per_fte),
    ]
    variances = []
    for metric, value, bench in metrics_to_check:
        v = _build_variance(
            metric, value, bench,
            _peer_vals(metric))
        if v is not None:
            variances.append(v)

    n_over = sum(1 for v in variances
                 if v.direction == "over_staffed")
    n_under = sum(1 for v in variances
                  if v.direction == "under_staffed")
    if n_over >= 2 and n_over > n_under:
        overall = "over_staffed"
    elif n_under >= 2 and n_under > n_over:
        overall = "under_staffed"
    else:
        overall = "in_line"

    notes: List[str] = []
    if benchmarks.n_peers < 5:
        notes.append(
            f"Peer cohort '{benchmarks.cohort_label}' has "
            f"{benchmarks.n_peers} hospitals — falling back "
            f"to industry medians.")
    if (profile.fte_per_aob is not None
            and benchmarks.fte_per_aob.get("p75")
            and (profile.fte_per_aob
                 > benchmarks.fte_per_aob["p75"] * 1.20)):
        notes.append(
            "FTE/AOB >20% above peer p75 — significant "
            "overstaffing or measurement issue worth "
            "reconciling.")
    if (profile.fte_per_aob is not None
            and benchmarks.fte_per_aob.get("p25")
            and (profile.fte_per_aob
                 < benchmarks.fte_per_aob["p25"] * 0.85)):
        notes.append(
            "FTE/AOB >15% below peer p25 — quality / "
            "burnout / vacancy risk; may not be a true "
            "efficiency win.")

    profile_metrics = {
        "fte_per_aob": profile.fte_per_aob,
        "labor_cost_per_adj_discharge":
            profile.labor_cost_per_adj_discharge,
        "labor_pct_of_npsr": profile.labor_pct_of_npsr,
        "salary_per_fte": profile.salary_per_fte,
    }

    return LaborEfficiencyResult(
        ccn=profile.ccn,
        fiscal_year=profile.fiscal_year,
        profile_metrics=profile_metrics,
        variances=variances,
        overall_staffing_label=overall,
        n_metrics_over=n_over,
        n_metrics_under=n_under,
        notes=notes,
    )


# ── Optimization model ──────────────────────────────────────

def model_labor_optimization_impact(
    profile: HospitalLaborProfile,
    benchmarks: LaborPeerBenchmarks,
    *,
    target_percentile: str = "p50",
    realism_factor: float = DEFAULT_LABOR_REALISM,
) -> Dict[str, LaborOptimizationScenario]:
    """Model EBITDA impact of right-sizing staffing to a peer
    percentile target.

    Three scenarios — conservative (0.7×), realistic (1.0×),
    optimistic (1.3×) on the realism factor — for the IC
    bull/base/bear range.

    Returns: {scenario_name: LaborOptimizationScenario}.

    Returns an empty dict when the hospital is already at or below
    target staffing — the model refuses to compute 'savings' from
    further-cutting an already-lean operation.
    """
    if profile.fte_per_aob is None:
        return {}
    target_ratio = benchmarks.fte_per_aob.get(
        target_percentile)
    if not target_ratio:
        return {}

    target_fte = target_ratio * profile.adjusted_occupied_beds
    if target_fte >= profile.total_fte:
        return {}

    salary_per_fte = profile.salary_per_fte
    if salary_per_fte is None or salary_per_fte <= 0:
        return {}

    raw_reduction = profile.total_fte - target_fte
    out: Dict[str, LaborOptimizationScenario] = {}
    for label, mult in _SCENARIO_MULTIPLIERS.items():
        eff_realism = realism_factor * mult
        actual_reduction = raw_reduction * eff_realism
        savings = actual_reduction * salary_per_fte
        out[label] = LaborOptimizationScenario(
            target_fte=round(
                profile.total_fte - actual_reduction, 1),
            fte_reduction=round(actual_reduction, 1),
            annual_labor_savings=round(savings, 0),
            ebitda_impact=round(savings, 0),
            realism_factor=round(eff_realism, 4),
        )
    return out


def analyze_labor_efficiency(
    profile: HospitalLaborProfile,
    peers: Iterable[HospitalLaborProfile],
    *,
    target_percentile: str = "p50",
    realism_factor: float = DEFAULT_LABOR_REALISM,
) -> LaborEfficiencyResult:
    """One-call wrapper — efficiency variance + optimization
    EBITDA scenarios in a single result."""
    peers_list = list(peers)
    result = compute_labor_efficiency(profile, peers_list)
    bucket = (profile.bed_size_bucket
              or _bed_size_bucket(profile.beds))
    benchmarks = compute_peer_benchmarks(
        peers_list, target_bucket=bucket)
    if result.overall_staffing_label == "over_staffed":
        result.optimization = (
            model_labor_optimization_impact(
                profile, benchmarks,
                target_percentile=target_percentile,
                realism_factor=realism_factor))
        if result.optimization:
            recurring = result.optimization[
                "realistic"].annual_labor_savings
            result.notes.append(
                f"Realistic labor optimization: "
                f"${recurring/1e6:.1f}M annual EBITDA "
                f"uplift (target {target_percentile}, "
                f"realism {realism_factor:.0%}).")
    return result
