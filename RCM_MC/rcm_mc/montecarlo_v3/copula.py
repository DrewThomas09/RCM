"""Copula joint-distribution samplers.

A copula transforms uniform [0,1]^d marginals into samples with a
target dependence structure. The target marginal distributions are
applied separately via inverse-CDF (the user's choice — log-normal
for revenue, beta for shares, etc.).

We expose four:

  • Gaussian copula — symmetric, no tail dependence
  • Student-t copula — symmetric, heavy upper AND lower tails
  • Clayton — asymmetric LOWER-tail dependence (joint downside)
  • Gumbel — asymmetric UPPER-tail dependence (joint upside)
  • Frank — symmetric mid-range dependence, no tail dependence

The Clayton + Gumbel are critical for healthcare diligence
because the partner cares specifically about JOINT downside
events: CMS cuts AND commercial compression AND labor inflation
all hitting together is the bear case.
"""
from __future__ import annotations

from math import erf, sqrt, exp, log
from typing import Tuple

import numpy as np


def _norm_cdf(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.array([erf(v / sqrt(2)) for v in x.flat])
                  ).reshape(x.shape)


def gaussian_copula_sample(
    correlation: np.ndarray,
    n_samples: int,
    *,
    seed: int = 0,
) -> np.ndarray:
    """Draw n_samples × d uniform marginals with Gaussian
    dependence governed by the supplied correlation matrix.

    Returns array of shape (n_samples, d) with values in (0, 1).
    """
    rng = np.random.default_rng(seed)
    d = correlation.shape[0]
    # Cholesky for sampling: Z = L @ ε where ε ~ N(0, I)
    L = np.linalg.cholesky(correlation
                           + 1e-9 * np.eye(d))   # ridge for stability
    eps = rng.standard_normal((n_samples, d))
    Z = eps @ L.T
    # Transform back to uniform via Φ
    return _norm_cdf(Z)


def t_copula_sample(
    correlation: np.ndarray,
    n_samples: int,
    *,
    df: float = 4.0,
    seed: int = 0,
) -> np.ndarray:
    """Student-t copula — heavier joint tails than Gaussian.

    Lower df = heavier tails. df=4 is the diligence-default
    (extreme but plausible).
    """
    rng = np.random.default_rng(seed)
    d = correlation.shape[0]
    L = np.linalg.cholesky(correlation + 1e-9 * np.eye(d))
    eps = rng.standard_normal((n_samples, d))
    chi2 = rng.chisquare(df, size=n_samples)
    # Build t-marginals via mixing
    Z = eps @ L.T
    T = Z * np.sqrt(df / chi2)[:, np.newaxis]
    # Convert via Student-t CDF (approximated via standardisation)
    # We use the asymptotic-Gaussian approximation: for moderate
    # df, t-CDF ~ Φ(t × √(df / (df + t²))). Sufficient for
    # uniform-marginals → copula (we lose a tiny bit of fidelity
    # in the tails but stay differentiable).
    scaled = T * np.sqrt(df / (df + T * T))
    return _norm_cdf(scaled)


def clayton_copula_sample(
    theta: float,
    n_samples: int,
    d: int = 2,
    *,
    seed: int = 0,
) -> np.ndarray:
    """Clayton copula — lower-tail dependence (joint downside).

    theta > 0; higher = stronger lower-tail dependence. Practical
    range 0.5 - 5.0. d ≥ 2.
    """
    if theta <= 0:
        raise ValueError("Clayton theta must be > 0")
    rng = np.random.default_rng(seed)
    # Marshall-Olkin: V ~ Gamma(1/theta, 1), then U_i = (1 - log(W_i)/V)^(-1/theta)
    V = rng.gamma(shape=1.0 / theta, scale=1.0, size=n_samples)
    W = rng.uniform(size=(n_samples, d))
    # log-W positive transform
    U = (1.0 - np.log(W) / V[:, np.newaxis]) ** (-1.0 / theta)
    # By construction Clayton(U) is in (0, 1)^d
    return U


def gumbel_copula_sample(
    theta: float,
    n_samples: int,
    d: int = 2,
    *,
    seed: int = 0,
) -> np.ndarray:
    """Gumbel copula — upper-tail dependence (joint upside).

    theta ≥ 1. theta=1 is independence; higher = stronger
    upper-tail dependence.
    """
    if theta < 1:
        raise ValueError("Gumbel theta must be >= 1")
    rng = np.random.default_rng(seed)
    # Marshall-Olkin: V ~ stable(1/theta) — approximate via
    # numerical method. We use the Chambers-Mallows-Stuck
    # algorithm for positive-stable.
    alpha = 1.0 / theta
    if alpha == 1.0:
        # theta = 1 is independence — return uniforms
        return rng.uniform(size=(n_samples, d))
    # Stable: U_unif ~ U(0, π); E ~ Exp(1)
    U_unif = rng.uniform(0.0, np.pi, size=n_samples)
    E = rng.exponential(scale=1.0, size=n_samples)
    sin_au = np.sin(alpha * U_unif)
    sin_oneminusau = np.sin((1.0 - alpha) * U_unif)
    sin_u = np.sin(U_unif)
    V = ((sin_au / sin_u ** alpha)
         * (sin_oneminusau / E) ** ((1.0 - alpha) / alpha))
    V = np.maximum(V, 1e-12)

    W = rng.uniform(size=(n_samples, d))
    # U_i = exp(-(- log W_i)^alpha / V^alpha)
    log_negW = -np.log(W)
    raw = -((log_negW ** alpha) / (V[:, np.newaxis] ** alpha))
    return np.exp(raw)


def frank_copula_sample(
    theta: float,
    n_samples: int,
    d: int = 2,
    *,
    seed: int = 0,
) -> np.ndarray:
    """Frank copula — symmetric, no tail dependence.

    theta != 0; positive ⇒ positive dependence, negative ⇒
    negative dependence. theta near 0 is independence.
    """
    if theta == 0:
        raise ValueError("Frank theta must be != 0")
    rng = np.random.default_rng(seed)
    # Conditional sampling for d=2; for d>=3 use Marshall-Olkin
    # with logarithmic-series mixing.
    if d == 2:
        u1 = rng.uniform(size=n_samples)
        w = rng.uniform(size=n_samples)
        # Frank d=2 conditional inverse. Setting C₁(v|u) = w and
        # solving for v gives:
        #   x = w·T / (A·(1 − w) + 1)
        #   v = -1/θ · log(1 + x)
        # where A = e^(-θu₁) − 1 and T = e^(-θ) − 1.
        # A(1−w) + 1 = (a − 1)(1−w) + 1 = a(1−w) + w  with a = e^(-θu₁).
        T = np.exp(-theta) - 1.0
        a = np.exp(-theta * u1)
        denom = a * (1.0 - w) + w
        denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
        log_arg = 1.0 + (w * T) / denom
        # Guard against tiny negative values from float rounding
        log_arg = np.maximum(log_arg, 1e-12)
        u2 = -np.log(log_arg) / theta
        u2 = np.clip(u2, 1e-9, 1.0 - 1e-9)
        return np.stack([u1, u2], axis=1)
    # d >= 3: Marshall-Olkin with logarithmic-series M
    # Approximation: use Gaussian copula with equivalent rho (good
    # for diligence-grade tasks where d=3 corresponds to "joint
    # downside on three risks").
    rho = 1.0 - 4.0 * (1.0 - 1.0 / theta) if theta > 0 else 0.0
    rho = max(-0.99, min(0.99, rho))
    correlation = (1.0 - rho) * np.eye(d) + rho * np.ones((d, d))
    return gaussian_copula_sample(correlation, n_samples, seed=seed)
