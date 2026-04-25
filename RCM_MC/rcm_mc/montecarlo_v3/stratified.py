"""Stratified sampling — variance reduction via deterministic
coverage of the unit hypercube.

Standard MC samples uniformly with random clustering — some
strata get over-sampled, others under-sampled. Stratified
sampling enforces that each of K strata gets exactly n/K
samples, eliminating that source of variance.

For diligence-grade integrands (smooth, low-dimensional), the
variance reduction over plain MC is typically 2-5× — not as
strong as Sobol on smooth functions but useful when the
integrand has known structure that's well-aligned with strata.

We expose two strategies:

  • 1-D stratification — for univariate integrals. Splits
    [0, 1] into K equal-width strata + draws one uniform per
    stratum.
  • Latin-hypercube — multivariate. For each dimension
    independently, partition [0, 1] into n strata and assign
    one sample per stratum, then permute across dimensions so
    every stratum in every dimension is hit exactly once.
"""
from __future__ import annotations

from typing import Callable, Tuple

import numpy as np


def stratified_uniform(
    n_samples: int,
    *,
    seed: int = 0,
) -> np.ndarray:
    """1-D stratified sample of (0, 1).

    Returns a length-n vector with one uniform draw inside each
    of n equal-width strata.
    """
    if n_samples <= 0:
        return np.array([])
    rng = np.random.default_rng(seed)
    edges = np.arange(n_samples) / n_samples
    jitter = rng.uniform(0.0, 1.0 / n_samples, size=n_samples)
    return edges + jitter


def latin_hypercube(
    n_samples: int,
    dim: int,
    *,
    seed: int = 0,
) -> np.ndarray:
    """Latin-hypercube sample on (0, 1)^dim.

    Each dimension partitioned into n_samples strata; one sample
    per stratum per dimension; cross-dimension permutation so
    every (column, stratum) combination is hit exactly once.

    Returns shape (n_samples, dim).
    """
    if n_samples <= 0 or dim <= 0:
        return np.zeros((0, dim))
    rng = np.random.default_rng(seed)
    out = np.zeros((n_samples, dim))
    for d in range(dim):
        edges = np.arange(n_samples) / n_samples
        jitter = rng.uniform(
            0.0, 1.0 / n_samples, size=n_samples)
        col = edges + jitter
        # Cross-dimension permutation
        rng.shuffle(col)
        out[:, d] = col
    return out


def stratified_estimate(
    f: Callable[[np.ndarray], np.ndarray],
    *,
    n_samples: int,
    dim: int = 1,
    seed: int = 0,
) -> Tuple[float, float]:
    """Stratified MC estimate of E[f(U)] for U ~ Uniform[0,1]^dim.

    Uses 1-D stratification when dim=1, Latin-hypercube otherwise.
    Returns (estimate, standard_error).

    Note: SE here is computed under the assumption of independence
    across strata (same as plain MC). This OVER-estimates the
    true SE since stratification reduces variance, so partners
    treating SE as a conservative bound stay safe.
    """
    if dim == 1:
        u = stratified_uniform(n_samples, seed=seed)
        u = u.reshape(-1, 1)
    else:
        u = latin_hypercube(n_samples, dim, seed=seed)
    payoffs = f(u)
    estimate = float(payoffs.mean())
    se = float(payoffs.std(ddof=1) / np.sqrt(n_samples)
               if n_samples > 1 else 0.0)
    return estimate, se
