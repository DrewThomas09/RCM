"""Antithetic variate sampling — variance reduction via paired
inverse samples.

For each random draw X ~ N(0, I), pair it with its antithetic
partner −X. The estimator becomes:

    Ŷ = (f(X) + f(−X)) / 2

When f is monotone, Var(Ŷ) ≤ Var(f(X)) / 2 — a 2× speedup at
the same N. For non-monotone f the variance reduction is
smaller but still positive in most diligence-relevant cases.

Pairs cleanly with Sobol (use Sobol-uniforms, transform to
N(0,1) via Φ⁻¹, then antithetic-pair) and with control variates
(antithetic estimator becomes the Y-axis of control-variate
regression).
"""
from __future__ import annotations

from typing import Callable, Tuple

import numpy as np


def antithetic_estimate(
    f: Callable[[np.ndarray], np.ndarray],
    *,
    n_pairs: int,
    dim: int,
    seed: int = 0,
) -> Tuple[float, float]:
    """Antithetic-paired Monte Carlo estimate of E[f(X)] for
    X ~ N(0, I).

    n_pairs draws of (X, -X) pairs → 2 × n_pairs total samples.
    Returns (estimate, standard_error).
    """
    if n_pairs <= 0 or dim <= 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_pairs, dim))
    f_pos = f(X)
    f_neg = f(-X)
    paired = (f_pos + f_neg) / 2.0
    estimate = float(paired.mean())
    se = float(paired.std(ddof=1) / np.sqrt(n_pairs)
               if n_pairs > 1 else 0.0)
    return estimate, se


def antithetic_pair(
    samples: np.ndarray,
) -> np.ndarray:
    """Given a (n × d) matrix of N(0, I) samples, return the
    (2n × d) matrix interleaving X and -X. Useful when caller
    wants to manage the function evaluation themselves."""
    if samples.size == 0:
        return samples
    return np.vstack([samples, -samples])
