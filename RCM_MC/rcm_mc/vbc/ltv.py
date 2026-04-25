"""Cohort lifetime value (LTV) projection.

Multi-period model that compounds capitation revenue, shared-
savings, and operating cost over a holding period. Patient-level
attrition (panel turnover) is modeled at the cohort level; HCC
risk score drift is captured via the V28 phase-in schedule.

Output is partner-ready: LTV per member, total panel LTV across
the hold, and a year-by-year cash-flow table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .cohort import Cohort, CohortPanel
from .contracts import (
    ContractTerms, compute_capitation_revenue,
    compute_shared_savings,
)
from .hcc import compute_hcc_score, V28_PHASE_IN


@dataclass
class LTVResult:
    panel_id: str
    horizon_years: int
    starting_lives: int
    nominal_ltv: float
    nominal_ltv_per_life: float
    discounted_ltv: float
    cashflow_by_year: List[Dict[str, float]] = field(default_factory=list)
    risk_score_by_year: List[float] = field(default_factory=list)


def _attrition(size: int, rate: float) -> int:
    return max(0, int(round(size * (1.0 - rate))))


def compute_cohort_ltv(
    cohort: Cohort,
    contract: ContractTerms,
    *,
    horizon_years: int = 5,
    discount_rate: float = 0.10,
    starting_payment_year: int = 2026,
    operating_cost_pmpm: float = 75.0,
) -> LTVResult:
    """Project annual capitation + shared-savings + opex for one
    cohort over the partner's hold period. Returns an LTVResult
    with a full cash-flow table."""

    cashflows: List[Dict[str, float]] = []
    risk_track: List[float] = []
    nominal_total = 0.0
    discounted_total = 0.0

    current_size = cohort.size

    for yr_idx in range(horizon_years):
        year = starting_payment_year + yr_idx

        # Risk score for the year (HCC score with V28 phase-in)
        avg_score = compute_hcc_score(
            age=cohort.avg_age + yr_idx,
            female=cohort.pct_female > 0.5,
            hcc_distribution=cohort.hcc_distribution,
            payment_year=year,
            dual_eligible=cohort.pct_dual_eligible > 0.5,
            originally_disabled=cohort.pct_originally_disabled > 0.5,
        )

        # Apply the cohort's actual demographic + dual mix as a
        # weighted blend so partial-population rates work.
        avg_score_blended = (
            avg_score * cohort.pct_dual_eligible
            + compute_hcc_score(
                age=cohort.avg_age + yr_idx,
                female=cohort.pct_female > 0.5,
                hcc_distribution=cohort.hcc_distribution,
                payment_year=year,
                dual_eligible=False,
                originally_disabled=False,
            ) * (1.0 - cohort.pct_dual_eligible)
        )

        # Per-year contract — risk score drifts by year
        yr_contract = ContractTerms(
            contract_type=contract.contract_type,
            benchmark_pmpm=contract.benchmark_pmpm,
            risk_score=avg_score_blended,
            quality_withhold_pct=contract.quality_withhold_pct,
            msr_pct=contract.msr_pct,
            mlr_pct=contract.mlr_pct,
            upside_share=contract.upside_share,
            downside_share=contract.downside_share,
            upside_cap_pct=contract.upside_cap_pct,
            downside_cap_pct=contract.downside_cap_pct,
        )

        rev = compute_capitation_revenue(
            current_size, yr_contract,
            quality_score=cohort.quality_score,
        )
        ss = compute_shared_savings(
            current_size, yr_contract,
            actual_pmpm=cohort.annual_pmpm_cost,
        )
        opex = current_size * operating_cost_pmpm * 12.0

        net_year = (rev["net_revenue"]
                    + ss["net_shared"]
                    - opex)
        nominal_total += net_year
        discount_factor = 1.0 / ((1.0 + discount_rate) ** yr_idx)
        discounted_total += net_year * discount_factor

        cashflows.append({
            "year": year,
            "lives": current_size,
            "risk_score": round(avg_score_blended, 4),
            "gross_capitation": rev["gross_capitation"],
            "quality_released": rev["quality_released"],
            "shared_savings": ss["net_shared"],
            "operating_cost": round(opex, 2),
            "net_cashflow": round(net_year, 2),
            "discount_factor": round(discount_factor, 4),
            "discounted_cashflow": round(net_year * discount_factor, 2),
        })
        risk_track.append(round(avg_score_blended, 4))

        # Attrition end-of-year
        current_size = _attrition(
            current_size, cohort.expected_attrition_rate)

    starting = cohort.size
    return LTVResult(
        panel_id=cohort.cohort_id,
        horizon_years=horizon_years,
        starting_lives=starting,
        nominal_ltv=round(nominal_total, 2),
        nominal_ltv_per_life=round(
            nominal_total / max(1, starting), 2),
        discounted_ltv=round(discounted_total, 2),
        cashflow_by_year=cashflows,
        risk_score_by_year=risk_track,
    )


def project_panel_lifetime_value(
    panel: CohortPanel,
    contract: ContractTerms,
    *,
    horizon_years: int = 5,
    discount_rate: float = 0.10,
    operating_cost_pmpm: float = 75.0,
    pmpm_observations: Optional[Dict[str, List[float]]] = None,
) -> dict:
    """Aggregate LTV across every cohort in the panel.

    Returns a dict ready to drop into a UI page or CLI report.

    ``pmpm_observations`` (optional) — a dict mapping cohort_id →
    list of historical observed PMPMs. When supplied, fit the
    hierarchical Normal-Normal model and replace each cohort's
    ``annual_pmpm_cost`` with its posterior mean before running
    the LTV projection. This pulls noisy small-cohort observations
    toward the panel-implied population mean — the textbook
    diligence-grade upgrade over treating the observed PMPM as
    truth.
    """
    # Hierarchical fit (when observations supplied)
    hierarchical_fit = None
    shrunk_pmpms: Dict[str, float] = {}
    if pmpm_observations:
        from .hierarchical import (
            fit_hierarchical_pmpm, CohortObservation,
        )
        observations = [
            CohortObservation(
                cohort_id=cid, observed_pmpms=list(vals))
            for cid, vals in pmpm_observations.items() if vals
        ]
        hierarchical_fit = fit_hierarchical_pmpm(observations)
        for cid, post in hierarchical_fit.posteriors.items():
            shrunk_pmpms[cid] = post.posterior_mean

    per_cohort: List[LTVResult] = []
    for c in panel.cohorts:
        # Apply the shrunk PMPM if we have one for this cohort
        if c.cohort_id in shrunk_pmpms:
            c = Cohort(
                cohort_id=c.cohort_id, name=c.name, size=c.size,
                avg_age=c.avg_age, pct_female=c.pct_female,
                pct_dual_eligible=c.pct_dual_eligible,
                pct_lis=c.pct_lis,
                pct_originally_disabled=c.pct_originally_disabled,
                hcc_distribution=dict(c.hcc_distribution),
                annual_pmpm_cost=shrunk_pmpms[c.cohort_id],
                quality_score=c.quality_score,
                expected_attrition_rate=c.expected_attrition_rate,
                cbsa=c.cbsa,
            )
        per_cohort.append(compute_cohort_ltv(
            c, contract,
            horizon_years=horizon_years,
            discount_rate=discount_rate,
            starting_payment_year=panel.benchmark_year,
            operating_cost_pmpm=operating_cost_pmpm,
        ))
    total_lives = panel.total_lives()
    total_nominal = sum(r.nominal_ltv for r in per_cohort)
    total_discounted = sum(r.discounted_ltv for r in per_cohort)
    return {
        "panel_id": panel.panel_id,
        "operator_name": panel.operator_name,
        "starting_lives": total_lives,
        "horizon_years": horizon_years,
        "discount_rate": discount_rate,
        "total_nominal_ltv": round(total_nominal, 2),
        "total_discounted_ltv": round(total_discounted, 2),
        "ltv_per_life": (round(total_nominal / max(1, total_lives), 2)
                          if total_lives else 0.0),
        "per_cohort": [
            {
                "cohort_id": r.panel_id,
                "lives": r.starting_lives,
                "nominal_ltv": r.nominal_ltv,
                "discounted_ltv": r.discounted_ltv,
                "ltv_per_life": r.nominal_ltv_per_life,
                "risk_score_by_year": r.risk_score_by_year,
            }
            for r in per_cohort
        ],
        "hierarchical_fit": (
            {
                "population_mean": hierarchical_fit.population_mean,
                "population_between_std":
                    hierarchical_fit.population_between_std,
                "population_within_std":
                    hierarchical_fit.population_within_std,
                "n_cohorts": hierarchical_fit.n_cohorts,
                "posteriors": {
                    cid: {
                        "observed_mean": p.observed_mean,
                        "posterior_mean": p.posterior_mean,
                        "posterior_std": p.posterior_std,
                        "shrinkage_weight": p.shrinkage_weight,
                        "n_observations": p.n_observations,
                    }
                    for cid, p in hierarchical_fit.posteriors.items()
                },
            } if hierarchical_fit else None
        ),
    }
