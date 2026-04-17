from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


class DistributionError(ValueError):
    pass


def _as_float(x: Any, name: str) -> float:
    try:
        return float(x)
    except Exception as e:
        raise DistributionError(f"Expected numeric for '{name}', got: {x!r}") from e


def beta_alpha_beta_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]:
    """
    Method-of-moments conversion.

    For Beta(a,b):
      mean = a/(a+b)
      var  = a*b / ((a+b)^2 * (a+b+1))

    Requires: sd^2 < mean*(1-mean).
    """
    mean = float(mean)
    sd = float(sd)
    if not (0.0 < mean < 1.0):
        raise DistributionError(f"beta mean must be in (0,1), got {mean}")
    if sd <= 0:
        raise DistributionError(f"beta sd must be >0, got {sd}")

    var = sd * sd
    max_var = mean * (1 - mean)
    if var >= max_var:
        # Clamp to a feasible variance (keeps the run alive; validation warns upstream)
        var = 0.95 * max_var

    k = mean * (1 - mean) / var - 1.0
    a = mean * k
    b = (1 - mean) * k
    # Numerical guard
    a = max(a, 1e-6)
    b = max(b, 1e-6)
    return a, b


def lognormal_mu_sigma_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]:
    mean = float(mean)
    sd = float(sd)
    if mean <= 0:
        raise DistributionError(f"lognormal mean must be >0, got {mean}")
    if sd <= 0:
        raise DistributionError(f"lognormal sd must be >0, got {sd}")
    sigma2 = np.log(1.0 + (sd * sd) / (mean * mean))
    mu = np.log(mean) - 0.5 * sigma2
    return float(mu), float(np.sqrt(sigma2))


def gamma_shape_scale_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]:
    mean = float(mean)
    sd = float(sd)
    if mean <= 0:
        raise DistributionError(f"gamma mean must be >0, got {mean}")
    if sd <= 0:
        raise DistributionError(f"gamma sd must be >0, got {sd}")
    shape = (mean / sd) ** 2
    scale = (sd * sd) / mean
    return float(shape), float(scale)


def triangular_mean_var(low: float, mode: float, high: float) -> Tuple[float, float]:
    low = float(low)
    mode = float(mode)
    high = float(high)
    if not (low <= mode <= high):
        raise DistributionError(f"triangular requires low<=mode<=high, got {low},{mode},{high}")
    mean = (low + mode + high) / 3.0
    var = (low * low + mode * mode + high * high - low * mode - low * high - mode * high) / 18.0
    return mean, var


def dist_moments(spec: Dict[str, Any]) -> Tuple[float, float]:
    """
    Return (mean, variance) for a supported distribution spec.
    """
    d = (spec or {}).get("dist", "fixed")
    d = str(d).lower()

    if d == "fixed":
        v = _as_float(spec.get("value", 0.0), "value")
        return v, 0.0

    if d == "beta":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        a, b = beta_alpha_beta_from_mean_sd(mean, sd)
        var = (a * b) / (((a + b) ** 2) * (a + b + 1))
        return mean, float(var)

    if d == "triangular":
        low = _as_float(spec.get("low"), "low")
        mode = _as_float(spec.get("mode"), "mode")
        high = _as_float(spec.get("high"), "high")
        return triangular_mean_var(low, mode, high)

    if d in ("normal_trunc", "normal", "gaussian"):
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        if d == "normal_trunc" and sd > 0:
            a_lo = float(spec.get("min", -np.inf))
            a_hi = float(spec.get("max", np.inf))
            if np.isfinite(a_lo) or np.isfinite(a_hi):
                try:
                    from scipy.stats import truncnorm as _tn
                    alpha = (a_lo - mean) / sd if np.isfinite(a_lo) else -10.0
                    beta_tn = (a_hi - mean) / sd if np.isfinite(a_hi) else 10.0
                    tn_mean, tn_var = _tn.stats(alpha, beta_tn, loc=mean, scale=sd, moments="mv")
                    return float(tn_mean), float(tn_var)
                except ImportError:
                    pass
        return mean, sd * sd

    if d == "lognormal":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        return mean, sd * sd

    if d == "gamma":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        return mean, sd * sd

    if d == "empirical":
        values = spec.get("values", [])
        if not values:
            raise DistributionError("empirical distribution requires non-empty 'values' list")
        arr = np.array(values, dtype=float)
        return float(np.mean(arr)), float(np.var(arr))

    raise DistributionError(f"Unsupported dist: {d}")


def sample_dist(rng: np.random.Generator, spec: Optional[Dict[str, Any]], size: Optional[int] = None) -> np.ndarray:
    """
    Sample from a distribution spec.

    Convention: if size is None, returns an array of length 1 (not a scalar),
    so callers can safely index [0].
    """
    spec = spec or {}
    d = str(spec.get("dist", "fixed")).lower()
    n = 1 if size is None else int(size)

    if d == "fixed":
        val = _as_float(spec.get("value", 0.0), "value")
        return np.full(n, val, dtype=float)

    if d == "beta":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        a, b = beta_alpha_beta_from_mean_sd(mean, sd)
        x = rng.beta(a, b, size=n)
        xmin = float(spec.get("min", 0.0))
        xmax = float(spec.get("max", 1.0))
        return np.clip(x, xmin, xmax)

    if d == "triangular":
        low = _as_float(spec.get("low"), "low")
        mode = _as_float(spec.get("mode"), "mode")
        high = _as_float(spec.get("high"), "high")
        return rng.triangular(low, mode, high, size=n)

    if d in ("normal_trunc", "normal", "gaussian"):
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        x = rng.normal(mean, sd, size=n)
        if d == "normal_trunc":
            xmin = float(spec.get("min", -np.inf))
            xmax = float(spec.get("max", np.inf))
            x = np.clip(x, xmin, xmax)
        return x

    if d == "lognormal":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        mu, sigma = lognormal_mu_sigma_from_mean_sd(mean, sd)
        return rng.lognormal(mu, sigma, size=n)

    if d == "gamma":
        mean = _as_float(spec.get("mean"), "mean")
        sd = _as_float(spec.get("sd"), "sd")
        shape, scale = gamma_shape_scale_from_mean_sd(mean, sd)
        return rng.gamma(shape, scale, size=n)

    # Step 53: Empirical distribution (resample from observed values)
    if d == "empirical":
        values = spec.get("values", [])
        if not values:
            raise DistributionError("empirical distribution requires non-empty 'values' list")
        arr = np.array(values, dtype=float)
        return rng.choice(arr, size=n, replace=True)

    raise DistributionError(f"Unsupported dist: {d}")



def sample_dirichlet(rng: np.random.Generator, base_shares: Dict[str, float], concentration: float) -> Dict[str, float]:
    """
    Sample a random share vector around base_shares, using a Dirichlet distribution.

    concentration:
      - high -> shares stay close to base
      - low  -> more variability in mix
    """
    keys = list(base_shares.keys())
    p = np.array([float(base_shares[k]) for k in keys], dtype=float)
    if p.min() < 0:
        raise DistributionError("Dirichlet base shares must be non-negative.")
    s = float(p.sum())
    if s <= 0:
        raise DistributionError("Dirichlet base shares must sum > 0.")
    p = p / s
    concentration = float(concentration)
    if concentration <= 0:
        raise DistributionError("Dirichlet concentration must be > 0.")
    alpha = p * concentration
    draw = rng.dirichlet(alpha)
    return {k: float(draw[i]) for i, k in enumerate(keys)}


def sample_sum_iid_as_gamma(
    rng: np.random.Generator,
    per_unit_spec: Dict[str, Any],
    n: float,
    min_total: float = 0.0,
) -> float:
    """
    Approximate sum of n IID random variables with the specified per-unit distribution
    as a Gamma distribution matched on mean/variance.

    This avoids per-claim simulation while still preserving variability that scales with volume.
    """
    n = float(max(n, 0.0))
    mu, var = dist_moments(per_unit_spec)
    mean_sum = n * mu
    var_sum = n * var

    if var_sum <= 1e-12:
        return float(max(mean_sum, min_total))

    shape = (mean_sum ** 2) / var_sum
    scale = var_sum / mean_sum
    total = rng.gamma(shape, scale)
    return float(max(total, min_total))
