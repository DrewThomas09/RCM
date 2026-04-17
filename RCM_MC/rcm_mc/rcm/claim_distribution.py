from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Sequence, Tuple, Dict

import numpy as np


@dataclass(frozen=True)
class ClaimBucket:
    idx: int
    q_low: float
    q_high: float
    share_claims: float
    mean_amount: float
    share_dollars: float


def lognormal_mu_sigma_from_mean_cv(mean: float, cv: float) -> Tuple[float, float]:
    """Return (mu, sigma) such that X~LogNormal(mu,sigma) has the given mean and coefficient of variation."""
    mean = float(max(mean, 1e-9))
    cv = float(max(cv, 1e-6))
    sigma2 = float(np.log(cv * cv + 1.0))
    sigma = float(np.sqrt(sigma2))
    mu = float(np.log(mean) - 0.5 * sigma2)
    return mu, sigma


@lru_cache(maxsize=256)
def _bucket_stats_cached(mean: float, cv: float, quantiles: Tuple[float, ...], n_draws: int, seed: int) -> Tuple[ClaimBucket, ...]:
    rng = np.random.default_rng(int(seed))
    mu, sigma = lognormal_mu_sigma_from_mean_cv(float(mean), float(cv))
    x = rng.lognormal(mean=mu, sigma=sigma, size=int(n_draws))
    x = np.asarray(x, dtype=float)

    # Compute amount thresholds for each quantile edge
    qs = np.array(quantiles, dtype=float)
    qs = np.clip(qs, 0.0, 1.0)
    thresh = np.quantile(x, qs)

    total_dollars = float(np.sum(x))
    buckets: List[ClaimBucket] = []
    for i in range(len(qs) - 1):
        lo = float(thresh[i])
        hi = float(thresh[i + 1])

        # Include left edge, exclude right edge except for last bucket
        if i < len(qs) - 2:
            mask = (x >= lo) & (x < hi)
        else:
            mask = (x >= lo) & (x <= hi)

        xb = x[mask]
        share_claims = float(mask.mean())
        mean_amount = float(np.mean(xb)) if xb.size else float((lo + hi) / 2.0)
        share_dollars = float(np.sum(xb) / total_dollars) if total_dollars > 0 and xb.size else share_claims

        buckets.append(
            ClaimBucket(
                idx=i,
                q_low=float(qs[i]),
                q_high=float(qs[i + 1]),
                share_claims=share_claims,
                mean_amount=mean_amount,
                share_dollars=share_dollars,
            )
        )

    # Renormalize shares to avoid small sampling error
    sc = sum(b.share_claims for b in buckets) or 1.0
    sd = sum(b.share_dollars for b in buckets) or 1.0
    buckets2 = []
    for b in buckets:
        buckets2.append(
            ClaimBucket(
                idx=b.idx,
                q_low=b.q_low,
                q_high=b.q_high,
                share_claims=float(b.share_claims / sc),
                mean_amount=b.mean_amount,
                share_dollars=float(b.share_dollars / sd),
            )
        )
    return tuple(buckets2)


def build_lognormal_claim_buckets(
    *,
    mean: float,
    cv: float,
    quantiles: Sequence[float],
    n_draws: int = 120_000,
    seed: int = 123,
) -> List[ClaimBucket]:
    """Return deterministic claim-size buckets for a lognormal claim distribution."""
    q = tuple(float(x) for x in quantiles)
    if len(q) < 3:
        raise ValueError("quantiles must have >= 3 values")
    if abs(q[0] - 0.0) > 1e-9 or abs(q[-1] - 1.0) > 1e-9:
        raise ValueError("quantiles must start at 0.0 and end at 1.0")
    return list(_bucket_stats_cached(float(mean), float(cv), q, int(n_draws), int(seed)))


def solve_alpha_for_target_mean(
    *,
    target: float,
    beta: float,
    x: np.ndarray,
    w: np.ndarray,
    max_iter: int = 60,
) -> float:
    """Solve alpha such that Σ w_i * sigmoid(alpha + beta*x_i) = target."""
    target = float(np.clip(target, 1e-9, 1 - 1e-9))
    beta = float(beta)
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    w = w / (w.sum() if w.sum() > 0 else 1.0)

    def f(alpha: float) -> float:
        p = 1.0 / (1.0 + np.exp(-(alpha + beta * x)))
        return float(np.sum(w * p) - target)

    lo = -20.0
    hi = 20.0
    flo = f(lo)
    fhi = f(hi)
    if flo > 0:
        return lo
    if fhi < 0:
        return hi

    for _ in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < 1e-10:
            return mid
        if fm > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def denial_rate_by_bucket(
    *,
    idr_base: float,
    bucket_mean_amounts: Sequence[float],
    avg_claim: float,
    beta: float,
    bucket_weights: Sequence[float],
) -> np.ndarray:
    """Compute bucket-level denial rates that average back to idr_base."""
    avg_claim = float(max(avg_claim, 1e-9))
    x = np.log(np.asarray(bucket_mean_amounts, dtype=float) / avg_claim)
    w = np.asarray(bucket_weights, dtype=float)
    alpha = solve_alpha_for_target_mean(target=float(idr_base), beta=float(beta), x=x, w=w)
    p = 1.0 / (1.0 + np.exp(-(alpha + float(beta) * x)))
    return np.clip(p, 0.0, 0.98)
