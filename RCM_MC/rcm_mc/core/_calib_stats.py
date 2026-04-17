"""Statistical helpers for the calibration pipeline."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from .distributions import beta_alpha_beta_from_mean_sd


def _beta_posterior_mean_sd(prior_mean: float, prior_sd: float, obs_mean: float, n_eff: float) -> Tuple[float, float]:
    """Beta posterior using fractional pseudo-counts (n_eff can be non-integer)."""
    prior_mean = float(np.clip(prior_mean, 1e-6, 1 - 1e-6))
    prior_sd = float(max(prior_sd, 1e-6))
    obs_mean = float(np.clip(obs_mean, 1e-6, 1 - 1e-6))
    n_eff = float(max(n_eff, 0.0))

    a0, b0 = beta_alpha_beta_from_mean_sd(prior_mean, prior_sd)
    s = obs_mean * n_eff
    f = (1.0 - obs_mean) * n_eff
    a1 = a0 + s
    b1 = b0 + f
    mean = a1 / (a1 + b1)
    var = (a1 * b1) / (((a1 + b1) ** 2) * (a1 + b1 + 1.0))
    return float(mean), float(np.sqrt(var))


def _smooth_shares(prior: Dict[str, float], obs_counts: Dict[str, float], prior_strength: float = 200.0) -> Dict[str, float]:
    keys = sorted(set(prior.keys()) | set(obs_counts.keys()))
    prior_strength = float(max(prior_strength, 1.0))
    prior_counts = {k: float(prior.get(k, 0.0)) * prior_strength for k in keys}
    post = {k: prior_counts.get(k, 0.0) + float(obs_counts.get(k, 0.0)) for k in keys}
    s = sum(post.values())
    if s <= 0:
        return {k: 1.0 / len(keys) for k in keys}
    return {k: float(v / s) for k, v in post.items()}


def _top_n_with_other(shares: Dict[str, float], n: int) -> Dict[str, float]:
    items = sorted(((k, float(v)) for k, v in shares.items()), key=lambda kv: kv[1], reverse=True)
    top = items[: max(int(n), 1)]
    rest = items[max(int(n), 1) :]
    out = {k: v for k, v in top}
    other = sum(v for _, v in rest)
    if other > 0:
        out["other"] = out.get("other", 0.0) + other
    s = sum(out.values())
    if s <= 0:
        return {"other": 1.0}
    return {k: float(v / s) for k, v in out.items()}
