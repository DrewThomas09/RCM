"""Monte Carlo over patient mix, attribution drift, and HCC coding
intensity.

Three uncertainty sources:

  1. **Patient mix drift** — HCC distribution shifts year-over-year
     as the panel ages and the comorbidity mix evolves. Modeled
     as a multiplicative log-normal shock per HCC category.

  2. **Attribution drift** — panel size churns ±10% / year, with
     PMPM cost following the new mix.

  3. **HCC coding intensity** — CMS sets the coding intensity
     factor annually. The V28 cliff (PY2026: 5.9% reduction;
     PY2027+ contemplated higher) is the dominant downside
     scenario for risk-bearing contracts.

The simulator runs N draws, each producing one sample contract
NPV. Output is a numpy array of NPVs across draws plus the mean
+ percentile distribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from ..vbc.cohort import Cohort
from ..vbc.contracts import (
    ContractTerms, compute_capitation_revenue, compute_shared_savings,
)
from ..vbc.hcc import compute_hcc_score, _v28_phase


@dataclass
class StochasticInputs:
    """All Monte Carlo parameters in one place."""
    n_simulations: int = 500
    horizon_years: int = 5
    seed: int = 42

    patient_mix_volatility: float = 0.10   # ±σ on each HCC prevalence
    attribution_volatility: float = 0.08   # ±σ on cohort_size YoY
    coding_intensity_volatility: float = 0.03  # ±σ on CMS factor

    discount_rate: float = 0.10
    operating_cost_pmpm: float = 75.0


def sample_patient_mix(
    base: Dict[str, float], rng: np.random.Generator,
    *, sigma: float = 0.10,
) -> Dict[str, float]:
    """Apply a per-category log-normal shock to the prevalence
    distribution, clipped to [0, 1]."""
    out: Dict[str, float] = {}
    for k, v in base.items():
        shock = rng.lognormal(mean=0.0, sigma=sigma)
        out[k] = float(min(1.0, max(0.0, v * shock)))
    return out


def sample_attribution_drift(
    size: int, rng: np.random.Generator,
    *, sigma: float = 0.08,
) -> int:
    """One-year attribution drift — multiplicative log-normal."""
    factor = rng.lognormal(mean=-0.02, sigma=sigma)  # slight bias down
    return max(0, int(round(size * factor)))


def sample_coding_intensity(
    base_factor: float, rng: np.random.Generator,
    *, sigma: float = 0.03,
) -> float:
    """Coding intensity is multiplicative. CMS publishes it
    deterministically each year; the volatility here represents
    the partner's uncertainty about the next-year setting."""
    shock = rng.lognormal(mean=0.0, sigma=sigma)
    return float(max(0.85, min(1.0, base_factor * shock)))


def _one_simulation_npv(
    cohort: Cohort,
    contract: ContractTerms,
    inputs: StochasticInputs,
    starting_year: int,
    rng: np.random.Generator,
) -> float:
    """Single MC draw — projects ``horizon_years`` and returns the
    discounted contract NPV."""
    current_size = cohort.size
    current_mix = dict(cohort.hcc_distribution)

    npv = 0.0
    for yr_idx in range(inputs.horizon_years):
        year = starting_year + yr_idx
        ci = sample_coding_intensity(
            base_factor=0.941,
            rng=rng,
            sigma=inputs.coding_intensity_volatility,
        )

        avg_score_dual = compute_hcc_score(
            age=cohort.avg_age + yr_idx,
            female=cohort.pct_female > 0.5,
            hcc_distribution=current_mix,
            payment_year=year,
            dual_eligible=True,
            coding_intensity_factor=ci,
        )
        avg_score_nondual = compute_hcc_score(
            age=cohort.avg_age + yr_idx,
            female=cohort.pct_female > 0.5,
            hcc_distribution=current_mix,
            payment_year=year,
            dual_eligible=False,
            coding_intensity_factor=ci,
        )
        avg_score = (avg_score_dual * cohort.pct_dual_eligible
                     + avg_score_nondual * (1.0 - cohort.pct_dual_eligible))

        yr_contract = ContractTerms(
            contract_type=contract.contract_type,
            benchmark_pmpm=contract.benchmark_pmpm,
            risk_score=avg_score,
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
        opex = current_size * inputs.operating_cost_pmpm * 12.0
        net_year = rev["net_revenue"] + ss["net_shared"] - opex
        df = 1.0 / ((1.0 + inputs.discount_rate) ** yr_idx)
        npv += net_year * df

        # Update state for next year
        current_mix = sample_patient_mix(
            current_mix, rng, sigma=inputs.patient_mix_volatility)
        current_size = sample_attribution_drift(
            current_size, rng, sigma=inputs.attribution_volatility)
    return npv


def run_monte_carlo_npv(
    cohort: Cohort,
    contract: ContractTerms,
    inputs: Optional[StochasticInputs] = None,
    *,
    starting_year: int = 2026,
) -> Dict[str, float]:
    """Run the Monte Carlo and return distribution stats.

    Returns a dict with: mean_npv_mm, p5, p25, p50, p75, p95,
    prob_loss (% of draws where NPV < 0), n_simulations.
    """
    inputs = inputs or StochasticInputs()
    rng = np.random.default_rng(inputs.seed)

    npvs = np.zeros(inputs.n_simulations, dtype=float)
    for i in range(inputs.n_simulations):
        npvs[i] = _one_simulation_npv(
            cohort, contract, inputs, starting_year, rng)

    return {
        "mean_npv_mm": float(np.mean(npvs)),
        "p5_mm": float(np.percentile(npvs, 5)),
        "p25_mm": float(np.percentile(npvs, 25)),
        "p50_mm": float(np.percentile(npvs, 50)),
        "p75_mm": float(np.percentile(npvs, 75)),
        "p95_mm": float(np.percentile(npvs, 95)),
        "prob_loss": float(np.mean(npvs < 0)),
        "n_simulations": int(inputs.n_simulations),
    }
