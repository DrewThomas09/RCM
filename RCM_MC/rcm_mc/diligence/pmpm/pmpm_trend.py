"""Risk-adjusted PMPM (per-member-per-month) trend mart — numpy + stdlib.

The diligence question PE actually underwrites: *is this asset's cost
trend a problem, or is its panel just getting sicker?* Raw PMPM growth
conflates two very different stories:

    1. Costs rising because the panel's acuity (RAF) is rising — often
       defensible, sometimes even good (you're keeping sicker patients
       out of the ED), and in MA-risk it's revenue you also capture.
    2. Costs rising at *constant* case mix — a genuine efficiency or
       leakage problem the operator owns.

Dividing PMPM by the panel RAF strips story (1) out, leaving the
**risk-adjusted PMPM** whose trend is story (2). This mart computes
both trends side by side so the analyst sees how much of the headline
cost growth is case-mix drift versus real cost inflation, benchmarks
the latest risk-adjusted level against a peer cohort (reusing the O/E
engine from :mod:`diligence.risk_adjustment`), and rolls a continuing
trend forward into an EBITDA-at-risk overlay.

Maps to the Tuva ``pmpm`` / financial mart; reuses the risk_adjustment
denominator rather than reimplementing case-mix logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from rcm_mc.diligence.risk_adjustment import RiskAdjustedBenchmark, risk_adjust_metric

CITATION_KEY = "PM1"
SOURCE_MODULE = "diligence.pmpm"


class PMPMVerdict(str, Enum):
    EFFICIENT = "EFFICIENT"      # risk-adjusted cost trend benign/declining
    IN_LINE = "IN_LINE"
    ELEVATED = "ELEVATED"        # real cost inflation beyond case mix
    OUTLIER = "OUTLIER"


# Annual risk-adjusted PMPM growth bands (medical-cost-trend context:
# ~3-4% is the long-run baseline; materially above that is the signal).
_IN_LINE_CAGR = 0.04
_ELEVATED_CAGR = 0.08


@dataclass
class PMPMPeriod:
    """One period's PMPM and the panel RAF that produced it."""
    period: str                  # ISO date or "2026Q1"
    pmpm: float
    raf: float = 1.0
    member_months: Optional[float] = None

    @property
    def risk_adjusted_pmpm(self) -> float:
        return self.pmpm / self.raf if self.raf > 0 else self.pmpm

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "pmpm": round(self.pmpm, 2),
            "raf": round(self.raf, 4),
            "member_months": self.member_months,
            "risk_adjusted_pmpm": round(self.risk_adjusted_pmpm, 2),
        }


@dataclass
class PMPMTrendResult:
    periods: List[PMPMPeriod]
    nominal_cagr: float              # raw PMPM annualized growth
    risk_adjusted_cagr: float        # PMPM/RAF annualized growth
    case_mix_drift_cagr: float       # RAF annualized growth
    latest_pmpm: float
    latest_risk_adjusted_pmpm: float
    years_observed: float
    peer_benchmark: Optional[RiskAdjustedBenchmark]
    verdict: PMPMVerdict
    projected_ebitda_impact_usd: Optional[float]
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "periods": [p.to_dict() for p in self.periods],
            "nominal_cagr": round(self.nominal_cagr, 6),
            "risk_adjusted_cagr": round(self.risk_adjusted_cagr, 6),
            "case_mix_drift_cagr": round(self.case_mix_drift_cagr, 6),
            "latest_pmpm": round(self.latest_pmpm, 2),
            "latest_risk_adjusted_pmpm": round(self.latest_risk_adjusted_pmpm, 2),
            "years_observed": round(self.years_observed, 3),
            "peer_benchmark": (
                self.peer_benchmark.to_dict() if self.peer_benchmark else None
            ),
            "verdict": self.verdict.value,
            "projected_ebitda_impact_usd": (
                None if self.projected_ebitda_impact_usd is None
                else round(self.projected_ebitda_impact_usd, 2)
            ),
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def _cagr(first: float, last: float, years: float) -> float:
    """Compound annual growth rate. Falls back to 0 on degenerate input."""
    if first <= 0 or last <= 0 or years <= 0:
        return 0.0
    return (last / first) ** (1.0 / years) - 1.0


def analyze_pmpm(
    periods: Sequence[PMPMPeriod],
    periods_per_year: float = 12.0,
    peer_risk_adjusted_pmpm: Optional[Sequence[float]] = None,
    peer_rafs: Optional[Sequence[float]] = None,
    annual_member_months: Optional[float] = None,
    projection_years: float = 3.0,
) -> PMPMTrendResult:
    """Analyze a PMPM time series.

    ``periods_per_year`` is 12 for monthly data, 4 for quarterly, 1 for
    annual — it converts the observed span into years for the CAGRs.

    If a peer cohort is supplied, the latest **risk-adjusted** PMPM is
    benchmarked O/E against it via :func:`risk_adjust_metric` (the
    target's RAF is folded into the risk-adjusted value already, so the
    benchmark is run at RAF 1.0 on both sides — a like-for-like
    risk-adjusted-level comparison).

    If ``annual_member_months`` is given, a continuing risk-adjusted
    trend is projected ``projection_years`` forward into an
    EBITDA-at-risk overlay (extra cost = ΔPMPM × member-months)."""
    periods = list(periods)
    if len(periods) < 2:
        latest = periods[-1] if periods else PMPMPeriod("", 0.0)
        return PMPMTrendResult(
            periods=periods, nominal_cagr=0.0, risk_adjusted_cagr=0.0,
            case_mix_drift_cagr=0.0, latest_pmpm=latest.pmpm,
            latest_risk_adjusted_pmpm=latest.risk_adjusted_pmpm,
            years_observed=0.0, peer_benchmark=None,
            verdict=PMPMVerdict.IN_LINE, projected_ebitda_impact_usd=None,
            headline="Insufficient history for a PMPM trend (need ≥2 periods).",
        )

    years = (len(periods) - 1) / periods_per_year
    first, last = periods[0], periods[-1]
    nominal_cagr = _cagr(first.pmpm, last.pmpm, years)
    ra_cagr = _cagr(
        first.risk_adjusted_pmpm, last.risk_adjusted_pmpm, years,
    )
    raf_cagr = _cagr(first.raf, last.raf, years)

    peer_bench: Optional[RiskAdjustedBenchmark] = None
    if peer_risk_adjusted_pmpm:
        peer_vals = list(peer_risk_adjusted_pmpm)
        peer_r = (
            list(peer_rafs) if peer_rafs is not None
            else [1.0] * len(peer_vals)
        )
        peer_bench = risk_adjust_metric(
            "risk_adjusted_pmpm",
            target_value=last.risk_adjusted_pmpm, target_raf=1.0,
            peer_values=peer_vals, peer_rafs=peer_r,
            lower_is_better=True,
        )

    verdict = _classify(ra_cagr)

    projected: Optional[float] = None
    if annual_member_months and annual_member_months > 0:
        future_ra_pmpm = last.risk_adjusted_pmpm * (
            (1 + ra_cagr) ** projection_years
        )
        delta_pmpm = future_ra_pmpm - last.risk_adjusted_pmpm
        # member_months are per-month membership × 12 already (annual);
        # PMPM is per-member-per-month, so annual cost = pmpm × member_months.
        projected = delta_pmpm * annual_member_months

    res = PMPMTrendResult(
        periods=periods, nominal_cagr=nominal_cagr,
        risk_adjusted_cagr=ra_cagr, case_mix_drift_cagr=raf_cagr,
        latest_pmpm=last.pmpm,
        latest_risk_adjusted_pmpm=last.risk_adjusted_pmpm,
        years_observed=years, peer_benchmark=peer_bench, verdict=verdict,
        projected_ebitda_impact_usd=projected,
    )
    res.headline = _headline(res)
    return res


def _classify(ra_cagr: float) -> PMPMVerdict:
    if ra_cagr < 0:
        return PMPMVerdict.EFFICIENT
    if ra_cagr <= _IN_LINE_CAGR:
        return PMPMVerdict.IN_LINE
    if ra_cagr <= _ELEVATED_CAGR:
        return PMPMVerdict.ELEVATED
    return PMPMVerdict.OUTLIER


def _headline(res: PMPMTrendResult) -> str:
    drift_share = ""
    if res.nominal_cagr != 0:
        explained = res.case_mix_drift_cagr / res.nominal_cagr
        drift_share = f" Case mix explains ~{explained * 100:.0f}% of headline growth."
    base = (
        f"PMPM trend: nominal {res.nominal_cagr * 100:+.1f}%/yr, "
        f"risk-adjusted {res.risk_adjusted_cagr * 100:+.1f}%/yr "
        f"(case-mix drift {res.case_mix_drift_cagr * 100:+.1f}%/yr) — "
        f"verdict {res.verdict.value}.{drift_share}"
    )
    if res.peer_benchmark is not None:
        base += (
            f" Risk-adjusted level O/E {res.peer_benchmark.oe_ratio:.2f} "
            f"vs peers ({res.peer_benchmark.verdict.value})."
        )
    if res.projected_ebitda_impact_usd:
        base += (
            f" Continuing the trend adds "
            f"${res.projected_ebitda_impact_usd / 1e6:.2f}M of annual cost "
            f"in {3} years."
        )
    return base
