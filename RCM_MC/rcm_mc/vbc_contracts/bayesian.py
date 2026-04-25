"""Bayesian updating on prior PMPM performance.

If a target has 1-2 years of observed PMPM under VBC contracts,
the partner can update their prior belief about the underlying
true PMPM. We model this as a Normal-Normal conjugate update —
sufficient for diligence-grade modeling where the partner cares
about a posterior mean and variance, not the full distribution.

  Prior:        N(mu_0, sigma_0^2)
  Observations: N(mu_obs, sigma_obs^2 / n)
  Posterior:    N(mu_post, sigma_post^2)

  mu_post = (mu_0 / sigma_0^2 + n × mu_obs / sigma_obs^2) /
            (1 / sigma_0^2 + n / sigma_obs^2)
  sigma_post^2 = 1 / (1 / sigma_0^2 + n / sigma_obs^2)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass
class PriorBelief:
    """Operator's prior on the cohort's true PMPM."""
    mean_pmpm: float
    stddev_pmpm: float = 80.0       # default ±$80 PMPM uncertainty


def bayesian_update_pmpm(
    prior: PriorBelief,
    observations: Iterable[float],
    *,
    obs_stddev: float = 100.0,
) -> Tuple[float, float]:
    """Conjugate Normal-Normal update.

    Inputs:
      prior — partner's belief before seeing data.
      observations — list of observed annual PMPMs.
      obs_stddev — sampling SD per observation (default $100).

    Returns:
      (posterior_mean_pmpm, posterior_stddev_pmpm)
    """
    obs = [float(o) for o in observations]
    if not obs:
        return (prior.mean_pmpm, prior.stddev_pmpm)
    n = len(obs)
    obs_mean = sum(obs) / n

    prior_var = prior.stddev_pmpm ** 2
    obs_var = (obs_stddev ** 2) / n

    if prior_var == 0:
        return (prior.mean_pmpm, prior.stddev_pmpm)
    if obs_var == 0:
        return (obs_mean, 0.0)

    post_var = 1.0 / (1.0 / prior_var + 1.0 / obs_var)
    post_mean = post_var * (
        prior.mean_pmpm / prior_var + obs_mean / obs_var)
    return (float(post_mean), float(post_var ** 0.5))
