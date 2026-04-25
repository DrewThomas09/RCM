"""Bayesian hierarchical shrinkage for cohort-level estimates.

Why this matters: a cohort with 200 attributed lives has noisy
PMPM observations — observed PMPM swings ±$200 year-to-year just
from sampling. Naïve LTV math anchors on the noisy point estimate
and over-weights luck.

The standard fix is hierarchical Bayes: treat each cohort's true
PMPM as draws from a population-level distribution, then shrink
the per-cohort point estimate toward the population mean by a
factor proportional to the per-cohort sample size relative to
the population variance.

The classic empirical-Bayes formula (James-Stein-style)::

    posterior = w · cohort_observed + (1 - w) · population_mean
    w = n / (n + (population_var / cohort_var))

For diligence-grade modeling this is dramatically more honest
than the maximum-likelihood point estimate. We expose it as a
single helper and pair it with a tiny smoke test in the suite.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple


def bayesian_shrink_cohort(
    cohort_observed_pmpm: float,
    cohort_size: int,
    population_pmpms: Iterable[float],
    *,
    population_sizes: Iterable[int] = (),
) -> Tuple[float, float]:
    """Shrink a single cohort's observed PMPM toward the population
    mean. Returns (posterior_pmpm, shrinkage_weight).

    A shrinkage_weight of 1.0 means we trust the cohort's observed
    PMPM fully; 0.0 means we ignore it. In practice a 200-life
    cohort gets weight ~0.3-0.5 against a 50-cohort, 60K-life
    population.

    Implementation note: we use a simple precision-weighted
    blend rather than a full hierarchical model, because (a) the
    full model needs more inputs than diligence packets typically
    expose and (b) the precision-weighted form is what's
    auditable to a partner who's never seen MCMC output.
    """
    population_pmpms = list(population_pmpms)
    if not population_pmpms:
        return float(cohort_observed_pmpm), 1.0
    if cohort_size <= 0:
        return (sum(population_pmpms) / len(population_pmpms), 0.0)

    pop_mean = sum(population_pmpms) / len(population_pmpms)
    if len(population_pmpms) > 1:
        pop_var = (sum((p - pop_mean) ** 2 for p in population_pmpms)
                   / (len(population_pmpms) - 1))
    else:
        pop_var = 0.0

    # Cohort-level sampling variance: PMPM standard error scales
    # as ~$300/sqrt(n) for typical populations. Use that as the
    # sampling variance baseline.
    cohort_var = (300.0 ** 2) / max(1, cohort_size)

    if pop_var == 0:
        # No spread across cohorts → cohort estimate dominates
        weight = 1.0
    else:
        weight = cohort_var / (cohort_var + pop_var)
        # weight here is the AMOUNT of shrinkage toward the mean;
        # invert so shrinkage_weight = trust in cohort observation.
        weight = max(0.0, min(1.0, 1.0 - weight))

    posterior = (weight * cohort_observed_pmpm
                 + (1.0 - weight) * pop_mean)
    return float(posterior), float(weight)


def bayesian_shrink_panel(
    panel_pmpms: List[Tuple[float, int]],
) -> List[Tuple[float, float]]:
    """Apply ``bayesian_shrink_cohort`` to every cohort in a panel,
    using the panel itself as the reference population.

    Input: list of (observed_pmpm, cohort_size) tuples.
    Output: list of (posterior_pmpm, shrinkage_weight) tuples.
    """
    pop = [pmpm for pmpm, _ in panel_pmpms]
    return [bayesian_shrink_cohort(pmpm, size, pop)
            for pmpm, size in panel_pmpms]
