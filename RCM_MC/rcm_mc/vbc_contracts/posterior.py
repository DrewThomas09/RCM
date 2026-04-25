"""Bayesian-aware Track-choice — single-call wrapper.

The existing ``valuate_contract`` and ``choose_optimal_track``
helpers operate on the cohort's raw observed PMPM. When a partner
has a prior belief PLUS 1-3 years of observed PMPM history, the
right thing to do is shrink toward the posterior and run the MC
against THAT — not the noisy point estimate.

This module adds the wrapper that does the full pipeline in one
call:

    1. Apply the Bayesian update to compute posterior PMPM.
    2. Replace the cohort's annual_pmpm_cost with the posterior
       mean.
    3. Run the program-specific Monte Carlo with the additional
       posterior-uncertainty layer (the posterior stddev is fed
       into the stochastic.py within-period noise so the simulator
       reflects "the partner's residual uncertainty about the true
       PMPM after seeing the data").
    4. Return ContractValuationResult enriched with the posterior
       block so the partner can audit the math.

Also adds the cross-program version: ``choose_track_with_posterior``
applies ONE posterior to ALL programs — the partner's belief about
the panel's true PMPM is independent of which Track they pick, so
every program valuation should benchmark against the same shrunk
PMPM (not each against the raw observed value).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional

from ..vbc.cohort import Cohort
from .bayesian import PriorBelief, bayesian_update_pmpm
from .stochastic import StochasticInputs
from .valuator import (
    ContractValuationResult,
    choose_optimal_track,
    valuate_contract,
)


def _shrunk_cohort(cohort: Cohort, posterior_pmpm: float) -> Cohort:
    """Return a Cohort identical to ``cohort`` except its
    annual_pmpm_cost is replaced by the posterior mean."""
    return Cohort(
        cohort_id=cohort.cohort_id,
        name=cohort.name,
        size=cohort.size,
        avg_age=cohort.avg_age,
        pct_female=cohort.pct_female,
        pct_dual_eligible=cohort.pct_dual_eligible,
        pct_lis=cohort.pct_lis,
        pct_originally_disabled=cohort.pct_originally_disabled,
        hcc_distribution=dict(cohort.hcc_distribution),
        annual_pmpm_cost=posterior_pmpm,
        quality_score=cohort.quality_score,
        expected_attrition_rate=cohort.expected_attrition_rate,
        cbsa=cohort.cbsa,
    )


def valuate_contract_with_posterior(
    cohort: Cohort,
    program_id: str,
    prior: PriorBelief,
    observations: Iterable[float],
    *,
    obs_stddev: float = 100.0,
    inputs: Optional[StochasticInputs] = None,
    starting_year: int = 2026,
) -> Dict[str, Any]:
    """Single-call Bayesian-aware contract valuation.

    Returns a dict combining the posterior summary + the
    ContractValuationResult-equivalent block. Output shape
    matches ``valuator.valuate_contract`` plus a ``posterior``
    sub-block carrying the prior, posterior mean/std, and
    observation count for audit.
    """
    post_mean, post_std = bayesian_update_pmpm(
        prior, observations, obs_stddev=obs_stddev,
    )
    shrunk = _shrunk_cohort(cohort, post_mean)
    # Bake additional posterior uncertainty into the MC's
    # within-period sampling. We do this by widening the
    # patient_mix_volatility — partner-conservative.
    if inputs is None:
        inputs = StochasticInputs()
    if post_std > 0:
        # Convert posterior std into a multiplicative volatility
        # bump (relative to the cohort's mean PMPM).
        relative_std = post_std / max(1.0, post_mean)
        inputs = StochasticInputs(
            n_simulations=inputs.n_simulations,
            horizon_years=inputs.horizon_years,
            seed=inputs.seed,
            patient_mix_volatility=(
                inputs.patient_mix_volatility + relative_std),
            attribution_volatility=inputs.attribution_volatility,
            coding_intensity_volatility=(
                inputs.coding_intensity_volatility),
            discount_rate=inputs.discount_rate,
            operating_cost_pmpm=inputs.operating_cost_pmpm,
        )
    result = valuate_contract(
        shrunk, program_id,
        inputs=inputs,
        starting_year=starting_year,
    )
    # Convert dataclass to dict for partner-facing output
    payload = {
        "program_id": result.program_id,
        "label": result.label,
        "distribution": result.distribution,
        "on_ramp_difficulty": result.on_ramp_difficulty,
        "risk_adjusted_score": result.risk_adjusted_score,
        "posterior": {
            "prior_mean": prior.mean_pmpm,
            "prior_stddev": prior.stddev_pmpm,
            "n_observations": len(list(observations))
                if not isinstance(observations, list)
                else len(observations),
            "posterior_mean": round(post_mean, 2),
            "posterior_stddev": round(post_std, 2),
            "obs_stddev": obs_stddev,
        },
    }
    return payload


def choose_track_with_posterior(
    cohort: Cohort,
    prior: PriorBelief,
    observations: Iterable[float],
    *,
    program_ids: Optional[Iterable[str]] = None,
    obs_stddev: float = 100.0,
    inputs: Optional[StochasticInputs] = None,
    starting_year: int = 2026,
) -> Dict[str, Any]:
    """Cross-program Track choice with a SHARED posterior.

    Applies one Bayesian update to the panel's PMPM, then evaluates
    every program against that posterior. This is what a partner
    actually wants — the shrunk PMPM is a panel property, not a
    program property; running each program with its own different
    PMPM would be inconsistent.

    Returns a dict with:
      posterior: the shared shrunk PMPM block
      result: the standard choose_optimal_track output (recommended
              + reasoning + per-program ranked results)
    """
    obs_list = list(observations)
    post_mean, post_std = bayesian_update_pmpm(
        prior, obs_list, obs_stddev=obs_stddev,
    )
    shrunk = _shrunk_cohort(cohort, post_mean)

    if inputs is None:
        inputs = StochasticInputs()
    if post_std > 0:
        relative_std = post_std / max(1.0, post_mean)
        inputs = StochasticInputs(
            n_simulations=inputs.n_simulations,
            horizon_years=inputs.horizon_years,
            seed=inputs.seed,
            patient_mix_volatility=(
                inputs.patient_mix_volatility + relative_std),
            attribution_volatility=inputs.attribution_volatility,
            coding_intensity_volatility=(
                inputs.coding_intensity_volatility),
            discount_rate=inputs.discount_rate,
            operating_cost_pmpm=inputs.operating_cost_pmpm,
        )

    track_result = choose_optimal_track(
        shrunk,
        program_ids=program_ids,
        inputs=inputs,
        starting_year=starting_year,
    )
    return {
        "posterior": {
            "prior_mean": prior.mean_pmpm,
            "prior_stddev": prior.stddev_pmpm,
            "n_observations": len(obs_list),
            "posterior_mean": round(post_mean, 2),
            "posterior_stddev": round(post_std, 2),
            "obs_stddev": obs_stddev,
        },
        "result": track_result,
    }
