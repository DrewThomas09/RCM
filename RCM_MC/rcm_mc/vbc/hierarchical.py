"""Hierarchical Bayesian model for cohort-level PMPM.

Replaces the precision-weighted blend in ``shrinkage.py`` with a
proper hierarchical Normal-Normal model. The data structure:

    μ_pop ~ Normal(μ_0, τ²_0)              (population mean)
    θ_k   ~ Normal(μ_pop, σ²_between)     (cohort k's true PMPM)
    y_k   ~ Normal(θ_k, σ²_within / n_k)  (observed PMPM)

The hierarchical aspect: μ_pop AND σ²_between are themselves
estimated from the cohort data (method-of-moments / empirical
Bayes), not passed in as fixed priors. This is the textbook
upgrade path from naïve "shrink toward a guess" to "shrink
toward the data-implied population center."

The posterior mean for each cohort θ_k is:

    θ_k_post = w_k × y_k + (1 − w_k) × μ̂_pop
    w_k      = σ̂²_between / (σ̂²_between + σ̂²_within / n_k)

w_k is the cohort's "trust weight" — large cohorts (n_k high)
get pulled less toward the population mean; small cohorts get
pulled more. When σ²_between is small relative to within-cohort
sampling noise, ALL cohorts shrink hard toward μ̂_pop (because
the data say cohorts are essentially the same).

No MCMC needed for the conjugate-Normal case — closed-form
posteriors. Pure numpy.

Public API::

    fit_hierarchical_pmpm(observations) -> HierarchicalFit
    HierarchicalFit.posterior(cohort_id) -> (mean, std)
    HierarchicalFit.population_mean
    HierarchicalFit.population_between_std
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass
class CohortObservation:
    """One cohort's observed PMPM history."""
    cohort_id: str
    observed_pmpms: List[float] = field(default_factory=list)
    # Optional override for within-cohort sampling variance per
    # observation; defaults to the residual MoM estimate.
    obs_std: Optional[float] = None


@dataclass
class CohortPosterior:
    """Per-cohort posterior summary."""
    cohort_id: str
    n_observations: int
    observed_mean: float
    posterior_mean: float
    posterior_std: float
    shrinkage_weight: float    # 0 = full shrinkage to pop mean,
                               # 1 = trust the cohort observation
                               # entirely


@dataclass
class HierarchicalFit:
    """Result of fit_hierarchical_pmpm — population params + per-
    cohort posteriors keyed by cohort_id."""
    population_mean: float
    population_between_std: float    # σ_between estimate
    population_within_std: float     # σ_within estimate
    posteriors: Dict[str, CohortPosterior] = field(
        default_factory=dict)
    n_cohorts: int = 0

    def posterior(self, cohort_id: str) -> Optional[CohortPosterior]:
        return self.posteriors.get(cohort_id)


def fit_hierarchical_pmpm(
    observations: Iterable[CohortObservation],
    *,
    fallback_within_std: float = 100.0,
) -> HierarchicalFit:
    """Fit the Normal-Normal hierarchical model by method of
    moments + closed-form Bayes update.

    Steps:
      1. Per-cohort observed mean ȳ_k and SE.
      2. μ̂_pop = weighted mean of ȳ_k, weights = n_k.
      3. σ̂²_within = pooled within-cohort variance (when ≥ 2 obs/cohort).
      4. σ̂²_between = max(0, var(ȳ_k) − mean(σ̂²_within / n_k))
         (method-of-moments residual).
      5. Per-cohort posterior θ_k_post = w_k × ȳ_k +
         (1 − w_k) × μ̂_pop where w_k = σ̂²_between /
         (σ̂²_between + σ̂²_within / n_k).
    """
    obs_list = [o for o in observations if o.observed_pmpms]
    if not obs_list:
        return HierarchicalFit(
            population_mean=0.0,
            population_between_std=0.0,
            population_within_std=fallback_within_std,
        )

    # Step 1
    means: List[float] = []
    sizes: List[int] = []
    within_vars: List[float] = []
    for o in obs_list:
        arr = np.array(o.observed_pmpms, dtype=float)
        means.append(float(arr.mean()))
        sizes.append(len(arr))
        if len(arr) >= 2:
            within_vars.append(float(arr.var(ddof=1)))
    means_arr = np.array(means)
    sizes_arr = np.array(sizes, dtype=float)

    # Step 2: μ̂_pop weighted by sample size
    pop_mean = float(np.average(means_arr, weights=sizes_arr))

    # Step 3: σ̂_within
    if within_vars:
        sigma2_within = float(np.mean(within_vars))
    else:
        sigma2_within = fallback_within_std ** 2

    # Step 4: σ̂²_between via MoM residual
    if len(means_arr) >= 2:
        between_total = float(means_arr.var(ddof=1))
        avg_se_squared = float(np.mean(sigma2_within / sizes_arr))
        sigma2_between = max(0.0, between_total - avg_se_squared)
    else:
        sigma2_between = 0.0

    sigma_within = float(np.sqrt(sigma2_within))
    sigma_between = float(np.sqrt(sigma2_between))

    # Step 5: per-cohort posterior
    posteriors: Dict[str, CohortPosterior] = {}
    for o, mean_k, n_k in zip(obs_list, means, sizes):
        sampling_var = sigma2_within / max(1, n_k)
        denom = sigma2_between + sampling_var
        if denom <= 0:
            # Degenerate: between-cohort variance is zero — full
            # shrinkage to population mean.
            w_k = 0.0
        else:
            w_k = sigma2_between / denom
        post_mean = w_k * mean_k + (1.0 - w_k) * pop_mean
        # Posterior std combines cohort and population uncertainty
        if denom <= 0:
            post_var = 0.0
        else:
            post_var = (sigma2_between * sampling_var) / denom
        posteriors[o.cohort_id] = CohortPosterior(
            cohort_id=o.cohort_id,
            n_observations=n_k,
            observed_mean=mean_k,
            posterior_mean=float(post_mean),
            posterior_std=float(np.sqrt(post_var)),
            shrinkage_weight=float(w_k),
        )

    return HierarchicalFit(
        population_mean=pop_mean,
        population_between_std=sigma_between,
        population_within_std=sigma_within,
        posteriors=posteriors,
        n_cohorts=len(obs_list),
    )
