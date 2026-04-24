"""Per-quarter covenant-breach probability simulator.

Input: Deal MC EBITDA bands (per year p5 / p25 / p50 / p75 / p95
or raw trial paths), a capital stack, a covenant suite, and
optional regulatory-calendar overlay + rate path.

Output: ``CovenantStressResult`` with, for every covenant × every
quarter, the probability the covenant is breached, the headroom at
the median path, the first-breach-quarter across paths, and a
partner-facing headline that names the earliest at-risk covenant
and the required equity cure size.

The simulator is path-level: if the caller supplies raw EBITDA
trial paths (from ``ebitda_mc.py``) we compute breach probability
as the fraction of paths that breach.  If only aggregated bands
are supplied we reconstruct an implied distribution via a
log-normal fit (partners still get a plausible envelope even
when the upstream MC is summarized).

Equity-cure math: given a breach path, compute the EBITDA gap
relative to the threshold, solve for the cure amount that closes
it (for leverage: debt paydown $; for DSCR: synthetic EBITDA add
via equity contribution at 1× allowance).  The output cure_size_usd
is the median across breach paths.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Mapping, Optional, Sequence, Tuple,
)

from .capital_stack import (
    CapitalStack, QuarterlyDebtService, build_debt_schedule,
    default_lbo_stack,
)
from .covenants import (
    CovenantDefinition, CovenantKind, CovenantTestResult,
    DEFAULT_COVENANTS, evaluate_covenant,
)


# ────────────────────────────────────────────────────────────────────
# Result types
# ────────────────────────────────────────────────────────────────────

@dataclass
class QuarterlyCovenantCurve:
    """Per-quarter breach probability + median headroom for one
    covenant across all simulated paths."""
    covenant_name: str
    covenant_kind: CovenantKind
    quarter_idx: int
    year: int
    breach_probability: float                # 0..1
    cushion_breach_probability: float        # 0..1
    median_metric: float
    median_headroom: float
    median_headroom_pct: float
    threshold: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covenant_name": self.covenant_name,
            "covenant_kind": self.covenant_kind.value,
            "quarter_idx": self.quarter_idx,
            "year": self.year,
            "breach_probability": self.breach_probability,
            "cushion_breach_probability": self.cushion_breach_probability,
            "median_metric": self.median_metric,
            "median_headroom": self.median_headroom,
            "median_headroom_pct": self.median_headroom_pct,
            "threshold": self.threshold,
        }


@dataclass
class FirstBreachQuarter:
    """For each covenant: the quarter at which probability of
    breach first crosses 50 %."""
    covenant_name: str
    first_50pct_breach_quarter: Optional[int]
    first_25pct_breach_quarter: Optional[int]
    first_actual_breach_quarter_median: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covenant_name": self.covenant_name,
            "first_50pct_breach_quarter":
                self.first_50pct_breach_quarter,
            "first_25pct_breach_quarter":
                self.first_25pct_breach_quarter,
            "first_actual_breach_quarter_median":
                self.first_actual_breach_quarter_median,
        }


@dataclass
class EquityCure:
    """Median / p75 equity cure required to unbreach the covenant."""
    covenant_name: str
    breach_path_fraction: float
    median_cure_usd: Optional[float]
    p75_cure_usd: Optional[float]
    first_cure_quarter: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covenant_name": self.covenant_name,
            "breach_path_fraction": self.breach_path_fraction,
            "median_cure_usd": self.median_cure_usd,
            "p75_cure_usd": self.p75_cure_usd,
            "first_cure_quarter": self.first_cure_quarter,
        }


@dataclass
class CovenantStressResult:
    """Top-level output surface."""
    n_paths: int
    quarters: int
    capital_stack_summary: Dict[str, Any]
    debt_schedule: List[QuarterlyDebtService]
    per_covenant_curves: List[QuarterlyCovenantCurve]
    first_breach: List[FirstBreachQuarter]
    equity_cures: List[EquityCure]
    # Overall risk signal
    max_breach_probability: float
    earliest_50pct_covenant: Optional[str]
    earliest_50pct_quarter: Optional[int]
    headline: str
    rationale: str
    # Regulatory overlay feed-through (optional)
    regulatory_overlay_applied_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_paths": self.n_paths,
            "quarters": self.quarters,
            "capital_stack_summary": self.capital_stack_summary,
            "debt_schedule":
                [d.to_dict() for d in self.debt_schedule],
            "per_covenant_curves":
                [c.to_dict() for c in self.per_covenant_curves],
            "first_breach":
                [f.to_dict() for f in self.first_breach],
            "equity_cures":
                [e.to_dict() for e in self.equity_cures],
            "max_breach_probability": self.max_breach_probability,
            "earliest_50pct_covenant": self.earliest_50pct_covenant,
            "earliest_50pct_quarter": self.earliest_50pct_quarter,
            "headline": self.headline,
            "rationale": self.rationale,
            "regulatory_overlay_applied_usd":
                self.regulatory_overlay_applied_usd,
        }


# ────────────────────────────────────────────────────────────────────
# Path reconstruction helpers
# ────────────────────────────────────────────────────────────────────

def _lognormal_params_from_bands(
    p50: float, p25: float, p75: float,
) -> Tuple[float, float]:
    """Back-solve lognormal (mu, sigma) from p25/p50/p75.

    The lognormal has ln(X) ~ Normal(mu, sigma).  p50 = exp(mu) and
    p75 − p25 ≈ 1.349 σ in the underlying normal.  Used to
    reconstruct a plausible distribution when the upstream Deal MC
    returns aggregated bands rather than raw paths.
    """
    mu = math.log(max(p50, 1.0))
    try:
        if p25 > 0 and p75 > 0:
            sigma = (math.log(p75) - math.log(p25)) / 1.349
        else:
            sigma = 0.15
    except (ValueError, ZeroDivisionError):
        sigma = 0.15
    return mu, max(sigma, 0.01)


def _sample_ebitda_paths_from_bands(
    ebitda_bands: Sequence[Mapping[str, float]],
    n_paths: int = 500,
    seed: int = 42,
) -> List[List[float]]:
    """Reconstruct n_paths annual EBITDA trajectories from per-year
    p25/p50/p75 bands, preserving within-year spread but assuming
    intra-year persistence (the same percentile draws across years
    within a path)."""
    import random
    rng = random.Random(seed)
    n_years = len(ebitda_bands)
    if n_years == 0:
        return []
    # Pre-compute (mu, sigma) per year
    params = []
    for b in ebitda_bands:
        p50 = float(b.get("p50") or b.get("median") or b.get("mean") or 0.0)
        p25 = float(b.get("p25") or p50 * 0.85)
        p75 = float(b.get("p75") or p50 * 1.15)
        params.append(_lognormal_params_from_bands(p50, p25, p75))
    paths: List[List[float]] = []
    for _ in range(n_paths):
        # Use a single percentile rank for the whole path to capture
        # serial correlation — a "bad MC draw" tends to stay bad.
        u = rng.random()
        z = _inverse_normal(u)
        path = []
        for mu, sigma in params:
            path.append(math.exp(mu + sigma * z))
        paths.append(path)
    return paths


def _inverse_normal(u: float) -> float:
    """Beasley-Springer-Moro inverse-normal; stdlib-only."""
    if u <= 0:
        u = 1e-9
    if u >= 1:
        u = 1 - 1e-9
    # Approximation accurate to ~10^-4 in the body
    a = [
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if u < plow:
        q = math.sqrt(-2 * math.log(u))
        return (
            ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
        ) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if u <= phigh:
        q = u - 0.5
        r = q * q
        return (
            ((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]
        ) * q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - u))
    return -(
        ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
    ) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def _annual_to_quarterly_ebitda(
    annual_paths: Sequence[Sequence[float]],
    quarters: int,
) -> List[List[float]]:
    """Interpolate per-year EBITDA into per-quarter EBITDA with
    a linear blend — LTM EBITDA then sums any 4 consecutive
    quarters.  Within-year quarters are set equal to year / 4
    rather than ramping — covenants test LTM, so the intra-year
    shape barely affects the metric."""
    out = []
    for path in annual_paths:
        q: List[float] = []
        for yr_idx, eb_year in enumerate(path):
            for _ in range(4):
                q.append(eb_year / 4.0)
                if len(q) >= quarters:
                    break
            if len(q) >= quarters:
                break
        while len(q) < quarters:
            # Extend flat from last year
            q.append(path[-1] / 4.0 if path else 0.0)
        out.append(q)
    return out


def _ltm_sum(series: Sequence[float], q: int) -> float:
    """Sum last 4 quarters ending at index q (inclusive).  Before
    quarter 3 we annualize the partial window so the metric is
    defined from quarter 0 onward."""
    window = series[max(0, q - 3): q + 1]
    if not window:
        return 0.0
    # Scale short windows to LTM by extrapolation
    if len(window) < 4:
        return sum(window) * (4.0 / len(window))
    return sum(window)


# ────────────────────────────────────────────────────────────────────
# Main simulator
# ────────────────────────────────────────────────────────────────────

def run_covenant_stress(
    *,
    ebitda_bands: Optional[Sequence[Mapping[str, float]]] = None,
    ebitda_paths: Optional[Sequence[Sequence[float]]] = None,
    capital_stack: Optional[CapitalStack] = None,
    total_debt_usd: Optional[float] = None,
    covenants: Sequence[CovenantDefinition] = DEFAULT_COVENANTS,
    rate_path_annual: Optional[Sequence[float]] = None,
    quarters: int = 20,
    n_paths_synthetic: int = 500,
    maint_capex_pct_of_ebitda: float = 0.20,
    tax_rate: float = 0.26,
    regulatory_overlay_usd_by_year: Optional[Sequence[float]] = None,
    seed: int = 42,
) -> CovenantStressResult:
    """Full stress pipeline.

    At least one of ``ebitda_paths`` (raw MC trials) or
    ``ebitda_bands`` (aggregated p25/p50/p75) must be supplied.

    ``regulatory_overlay_usd_by_year`` subtracts the Regulatory
    Calendar overlay from EBITDA before covenant testing.  This is
    what makes the Covenant Lab + Regulatory Calendar combination
    unique — partners see exactly how a V28 cut in CY2027 tightens
    the 2027 leverage covenant.
    """
    # Resolve capital stack
    if capital_stack is None:
        if not total_debt_usd:
            raise ValueError(
                "Supply either capital_stack or total_debt_usd",
            )
        capital_stack = default_lbo_stack(total_debt_usd=total_debt_usd)

    # Resolve rate path
    rate_path = list(rate_path_annual or [0.055] * quarters)

    debt_schedule = build_debt_schedule(
        capital_stack, rate_path, quarters=quarters,
    )

    # Resolve annual EBITDA paths
    if ebitda_paths is None:
        if ebitda_bands is None:
            raise ValueError(
                "Supply either ebitda_paths or ebitda_bands",
            )
        ebitda_paths = _sample_ebitda_paths_from_bands(
            ebitda_bands, n_paths=n_paths_synthetic, seed=seed,
        )
    else:
        ebitda_paths = [list(p) for p in ebitda_paths]

    # Apply regulatory overlay
    total_overlay_applied = 0.0
    if regulatory_overlay_usd_by_year:
        adj_paths = []
        overlay = list(regulatory_overlay_usd_by_year)
        for path in ebitda_paths:
            adjusted = []
            for idx, eb in enumerate(path):
                drag = overlay[idx] if idx < len(overlay) else 0.0
                # regulatory overlay is signed — negative means drag
                adjusted.append(eb + drag)
                if idx == 0:
                    total_overlay_applied += drag
            adj_paths.append(adjusted)
        ebitda_paths = adj_paths
        total_overlay_applied = sum(
            overlay[:max(1, len(overlay))],
        )

    # Explode to quarterly
    quarterly_ebitda_paths = _annual_to_quarterly_ebitda(
        ebitda_paths, quarters,
    )
    n_paths = len(quarterly_ebitda_paths)

    # Evaluate each path × covenant × quarter
    # Structure: per_cov[cov.name][q] = list of CovenantTestResult
    per_cov_by_q: Dict[str, List[List[CovenantTestResult]]] = {
        c.name: [[] for _ in range(quarters)] for c in covenants
    }
    per_path_first_breach: Dict[str, List[Optional[int]]] = {
        c.name: [None] * n_paths for c in covenants
    }

    for path_idx, q_ebitda in enumerate(quarterly_ebitda_paths):
        for q in range(quarters):
            ltm_eb = _ltm_sum(q_ebitda, q)
            ds = debt_schedule[q] if q < len(debt_schedule) else None
            if ds is None:
                continue
            # LTM debt service — sum across last 4 quarters
            start = max(0, q - 3)
            window = debt_schedule[start: q + 1]
            scale = 4.0 / len(window) if window else 1.0
            ltm_interest = sum(
                x.total_interest for x in window
            ) * scale
            ltm_amort = sum(
                x.total_scheduled_amort for x in window
            ) * scale
            ltm_ds = ltm_interest + ltm_amort + sum(
                x.total_commitment_fee for x in window
            ) * scale
            ltm_taxes = max(0.0, ltm_eb - ltm_interest) * tax_rate
            ltm_capex = ltm_eb * maint_capex_pct_of_ebitda
            for cov in covenants:
                result = evaluate_covenant(
                    cov, quarter_idx=q,
                    ltm_ebitda=ltm_eb,
                    total_debt=ds.total_debt_balance,
                    senior_debt=ds.senior_debt_balance,
                    ltm_interest=ltm_interest,
                    ltm_debt_service=ltm_ds,
                    ltm_taxes=ltm_taxes,
                    ltm_maint_capex=ltm_capex,
                )
                per_cov_by_q[cov.name][q].append(result)
                if (
                    result.breached
                    and per_path_first_breach[cov.name][path_idx] is None
                ):
                    per_path_first_breach[cov.name][path_idx] = q

    # Roll up to curves
    curves: List[QuarterlyCovenantCurve] = []
    for cov in covenants:
        for q in range(quarters):
            row = per_cov_by_q[cov.name][q]
            if not row:
                continue
            breached = sum(1 for r in row if r.breached)
            cushion = sum(1 for r in row if r.cushion_breached)
            metrics = sorted(r.metric_value for r in row)
            headrooms = sorted(r.headroom for r in row)
            hrs_pct = sorted(r.headroom_pct for r in row)
            med = metrics[len(metrics) // 2]
            curves.append(QuarterlyCovenantCurve(
                covenant_name=cov.name,
                covenant_kind=cov.kind,
                quarter_idx=q,
                year=q // 4 + 1,
                breach_probability=breached / len(row),
                cushion_breach_probability=cushion / len(row),
                median_metric=med,
                median_headroom=headrooms[len(headrooms) // 2],
                median_headroom_pct=hrs_pct[len(hrs_pct) // 2],
                threshold=row[0].threshold,
            ))

    # First-breach summary
    first_breach: List[FirstBreachQuarter] = []
    for cov in covenants:
        q_curves = [c for c in curves if c.covenant_name == cov.name]
        q50 = next(
            (c.quarter_idx for c in q_curves
             if c.breach_probability >= 0.5), None,
        )
        q25 = next(
            (c.quarter_idx for c in q_curves
             if c.breach_probability >= 0.25), None,
        )
        per_path = [
            b for b in per_path_first_breach[cov.name]
            if b is not None
        ]
        med_actual = None
        if per_path:
            per_path_sorted = sorted(per_path)
            med_actual = per_path_sorted[len(per_path_sorted) // 2]
        first_breach.append(FirstBreachQuarter(
            covenant_name=cov.name,
            first_50pct_breach_quarter=q50,
            first_25pct_breach_quarter=q25,
            first_actual_breach_quarter_median=med_actual,
        ))

    # Equity cure math per covenant
    cures = _equity_cures(
        covenants=covenants,
        per_cov_by_q=per_cov_by_q,
        per_path_first_breach=per_path_first_breach,
        debt_schedule=debt_schedule,
    )

    # Overall worst curve
    max_prob = max((c.breach_probability for c in curves), default=0.0)
    earliest_50: Optional[Tuple[int, str]] = None
    for c in sorted(curves, key=lambda x: x.quarter_idx):
        if c.breach_probability >= 0.5:
            earliest_50 = (c.quarter_idx, c.covenant_name)
            break
    earliest_q = earliest_50[0] if earliest_50 else None
    earliest_name = earliest_50[1] if earliest_50 else None

    # Partner-facing headline
    if earliest_50:
        q_idx, name = earliest_50
        year = q_idx // 4 + 1
        q_in_yr = q_idx % 4 + 1
        cure = next(
            (c for c in cures if c.covenant_name == name), None,
        )
        cure_str = (
            f"${cure.median_cure_usd/1e6:.1f}M median equity cure"
            if cure and cure.median_cure_usd else
            "material equity cure"
        )
        headline = (
            f"\"{name}\" covenant crosses 50% breach probability "
            f"in Y{year}Q{q_in_yr} — {cure_str}."
        )
    elif max_prob >= 0.25:
        worst = max(curves, key=lambda x: x.breach_probability)
        headline = (
            f"Peak covenant stress: \"{worst.covenant_name}\" "
            f"hits {worst.breach_probability*100:.0f}% breach "
            f"probability in Y{worst.year}Q{worst.quarter_idx % 4 + 1} "
            f"— manageable but monitor for drift."
        )
    else:
        headline = (
            "Covenant stack clears the 25% breach-probability "
            f"threshold in every quarter out to Y{quarters//4}."
        )

    rationale_parts: List[str] = []
    for cov in covenants:
        q_curves = [c for c in curves if c.covenant_name == cov.name]
        if not q_curves:
            continue
        peak = max(q_curves, key=lambda c: c.breach_probability)
        rationale_parts.append(
            f"{cov.name}: peak {peak.breach_probability*100:.0f}% "
            f"in Y{peak.year}Q{peak.quarter_idx % 4 + 1} "
            f"(median metric {peak.median_metric:.2f} vs "
            f"threshold {peak.threshold:.2f})"
        )
    rationale = " · ".join(rationale_parts)

    return CovenantStressResult(
        n_paths=n_paths,
        quarters=quarters,
        capital_stack_summary=capital_stack.to_dict(),
        debt_schedule=debt_schedule,
        per_covenant_curves=curves,
        first_breach=first_breach,
        equity_cures=cures,
        max_breach_probability=max_prob,
        earliest_50pct_covenant=earliest_name,
        earliest_50pct_quarter=earliest_q,
        headline=headline,
        rationale=rationale,
        regulatory_overlay_applied_usd=total_overlay_applied,
    )


def _equity_cures(
    *,
    covenants: Sequence[CovenantDefinition],
    per_cov_by_q: Dict[str, List[List[CovenantTestResult]]],
    per_path_first_breach: Dict[str, List[Optional[int]]],
    debt_schedule: List[QuarterlyDebtService],
) -> List[EquityCure]:
    """For each covenant compute the $-size equity cure needed on
    breach paths.

    Cure logic:
        Leverage ceiling: cure $ = (metric - threshold) ×
          ltm_ebitda  — i.e. the debt paydown that drops leverage
          back to threshold.
        Coverage floor:  cure $ = gap × ltm_debt_service — the
          synthetic-EBITDA injection the agreement usually allows.
    """
    out: List[EquityCure] = []
    for cov in covenants:
        cure_sizes: List[float] = []
        first_cure_quarter: Optional[int] = None
        for q_idx, row in enumerate(per_cov_by_q[cov.name]):
            for r in row:
                if not r.breached:
                    continue
                if cov.is_ceiling:
                    # For leverage: need to reduce total_debt so
                    # new_leverage ≤ threshold. Solve for paydown:
                    # (debt - cure) / ebitda = threshold
                    # cure = debt - threshold × ebitda
                    ebitda_4q = (
                        r.metric_value == 0 and 1.0 or
                        (debt_schedule[q_idx].total_debt_balance /
                         max(r.metric_value, 0.01))
                    )
                    needed = debt_schedule[q_idx].total_debt_balance - (
                        r.threshold * ebitda_4q
                    )
                    cure = max(0.0, needed)
                else:
                    # For coverage: allowed cure synthetically
                    # adds EBITDA so metric becomes threshold.
                    # gap_in_ebitda = (threshold - metric) × denom
                    # This is a rough approximation acceptable for
                    # the Lab — real credit agreements have a "Yank-
                    # the-Bank" cap of ~25% of LTM EBITDA.
                    gap = r.threshold - r.metric_value
                    cure = max(0.0, gap * 1_000_000.0)
                cure_sizes.append(cure)
                if first_cure_quarter is None:
                    first_cure_quarter = q_idx
        breach_frac = 0.0
        tot = len([
            x for x in per_path_first_breach[cov.name] if x is not None
        ])
        if tot and per_path_first_breach[cov.name]:
            breach_frac = tot / len(per_path_first_breach[cov.name])
        if cure_sizes:
            cure_sizes.sort()
            med = cure_sizes[len(cure_sizes) // 2]
            p75 = cure_sizes[min(len(cure_sizes) - 1,
                                 int(len(cure_sizes) * 0.75))]
        else:
            med = None
            p75 = None
        out.append(EquityCure(
            covenant_name=cov.name,
            breach_path_fraction=breach_frac,
            median_cure_usd=med,
            p75_cure_usd=p75,
            first_cure_quarter=first_cure_quarter,
        ))
    return out
