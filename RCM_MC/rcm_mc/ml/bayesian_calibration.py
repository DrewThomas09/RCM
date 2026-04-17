"""Hierarchical Bayesian calibration for hospital KPI estimation.

Beta-Binomial partial pooling for rate metrics (denial rate, collection
rate, clean claim rate). Gamma-Lognormal for dollar metrics (AR days,
cost to collect). Multilevel shrinkage by payer, state, hospital type.

When target data is thin, estimates shrink toward peer-group priors.
When target data is rich, they converge to the observed values.
This prevents unstable estimates from small samples while letting
real evidence dominate as data grows.

References: Gelman et al., Bayesian Data Analysis (3rd ed.)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import lgamma, log, exp, sqrt
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class BayesianEstimate:
    metric: str
    prior_mean: float
    prior_strength: float
    observed_mean: float
    observed_n: int
    posterior_mean: float
    posterior_strength: float
    credible_interval_90: Tuple[float, float]
    shrinkage_factor: float
    data_quality: str  # "strong", "moderate", "weak", "prior_only"


def _beta_params_from_mean_strength(mean: float, strength: float) -> Tuple[float, float]:
    """Convert (mean, effective sample size) to Beta(alpha, beta)."""
    mean = max(0.001, min(0.999, mean))
    alpha = mean * strength
    beta = (1 - mean) * strength
    return max(0.1, alpha), max(0.1, beta)


def _beta_posterior(
    prior_mean: float, prior_strength: float,
    observed_successes: float, observed_trials: float,
) -> Tuple[float, float, float, Tuple[float, float]]:
    """Beta-Binomial conjugate update.

    Returns (posterior_mean, posterior_strength, shrinkage, 90% credible interval).
    """
    alpha0, beta0 = _beta_params_from_mean_strength(prior_mean, prior_strength)
    alpha_post = alpha0 + observed_successes
    beta_post = beta0 + (observed_trials - observed_successes)
    post_strength = alpha_post + beta_post
    post_mean = alpha_post / post_strength

    shrinkage = prior_strength / (prior_strength + observed_trials) if (prior_strength + observed_trials) > 0 else 1.0

    # 90% credible interval via normal approximation to Beta
    var = (alpha_post * beta_post) / (post_strength ** 2 * (post_strength + 1))
    sd = sqrt(max(0, var))
    ci_lo = max(0, post_mean - 1.645 * sd)
    ci_hi = min(1, post_mean + 1.645 * sd)

    return post_mean, post_strength, shrinkage, (ci_lo, ci_hi)


def _gamma_posterior(
    prior_mean: float, prior_strength: float,
    observed_mean: float, observed_n: int,
) -> Tuple[float, float, float, Tuple[float, float]]:
    """Gamma conjugate update for positive-valued metrics (AR days, cost).

    Uses Normal-Gamma approximation for simplicity.
    """
    if observed_n == 0:
        return prior_mean, prior_strength, 1.0, (prior_mean * 0.5, prior_mean * 1.5)

    total_weight = prior_strength + observed_n
    post_mean = (prior_mean * prior_strength + observed_mean * observed_n) / total_weight
    shrinkage = prior_strength / total_weight

    # Approximate 90% CI
    se = prior_mean * 0.15 / sqrt(max(1, total_weight))
    ci_lo = max(0, post_mean - 1.645 * se)
    ci_hi = post_mean + 1.645 * se

    return post_mean, total_weight, shrinkage, (ci_lo, ci_hi)


# Peer-group priors by hospital type
_RATE_PRIORS = {
    "denial_rate": {"mean": 0.085, "strength": 30,
                     "by_type": {"large": 0.065, "medium": 0.085, "small": 0.11, "rural": 0.10}},
    "clean_claim_rate": {"mean": 0.925, "strength": 40,
                          "by_type": {"large": 0.945, "medium": 0.925, "small": 0.900, "rural": 0.89}},
    "net_collection_rate": {"mean": 0.963, "strength": 35,
                             "by_type": {"large": 0.975, "medium": 0.963, "small": 0.950, "rural": 0.94}},
    "first_pass_resolution": {"mean": 0.78, "strength": 25,
                               "by_type": {"large": 0.82, "medium": 0.78, "small": 0.74, "rural": 0.72}},
    "appeals_overturn_rate": {"mean": 0.45, "strength": 20,
                               "by_type": {"large": 0.52, "medium": 0.45, "small": 0.38, "rural": 0.35}},
}

_CONTINUOUS_PRIORS = {
    "days_in_ar": {"mean": 42.5, "strength": 20,
                    "by_type": {"large": 38, "medium": 42.5, "small": 48, "rural": 52}},
    "cost_to_collect": {"mean": 0.021, "strength": 25,
                         "by_type": {"large": 0.018, "medium": 0.021, "small": 0.028, "rural": 0.032}},
    "dnfb_days": {"mean": 5.2, "strength": 15,
                   "by_type": {"large": 4.0, "medium": 5.2, "small": 6.5, "rural": 7.0}},
    "charge_lag_days": {"mean": 2.8, "strength": 15,
                         "by_type": {"large": 2.0, "medium": 2.8, "small": 3.5, "rural": 4.0}},
}


def _classify_hospital_type(beds: float) -> str:
    if beds >= 300:
        return "large"
    if beds >= 100:
        return "medium"
    if beds >= 50:
        return "small"
    return "rural"


def calibrate_rate_metric(
    metric: str,
    observed_rate: Optional[float],
    observed_n: int,
    beds: float = 150,
    state: str = "",
) -> BayesianEstimate:
    """Bayesian calibration for a rate metric using Beta-Binomial."""
    prior_info = _RATE_PRIORS.get(metric)
    if not prior_info:
        prior_info = {"mean": 0.5, "strength": 10, "by_type": {}}

    hosp_type = _classify_hospital_type(beds)
    prior_mean = prior_info["by_type"].get(hosp_type, prior_info["mean"])
    prior_strength = prior_info["strength"]

    if observed_rate is not None and observed_n > 0:
        successes = observed_rate * observed_n
        post_mean, post_strength, shrinkage, ci = _beta_posterior(
            prior_mean, prior_strength, successes, observed_n)
        obs_mean = observed_rate
        if observed_n >= 100:
            quality = "strong"
        elif observed_n >= 30:
            quality = "moderate"
        else:
            quality = "weak"
    else:
        post_mean = prior_mean
        post_strength = prior_strength
        shrinkage = 1.0
        ci = _beta_posterior(prior_mean, prior_strength, 0, 0)[3]
        obs_mean = 0
        quality = "prior_only"

    return BayesianEstimate(
        metric=metric,
        prior_mean=round(prior_mean, 4),
        prior_strength=prior_strength,
        observed_mean=round(obs_mean, 4),
        observed_n=observed_n,
        posterior_mean=round(post_mean, 4),
        posterior_strength=round(post_strength, 1),
        credible_interval_90=(round(ci[0], 4), round(ci[1], 4)),
        shrinkage_factor=round(shrinkage, 3),
        data_quality=quality,
    )


def calibrate_continuous_metric(
    metric: str,
    observed_mean: Optional[float],
    observed_n: int,
    beds: float = 150,
) -> BayesianEstimate:
    """Bayesian calibration for a continuous metric using Gamma approximation."""
    prior_info = _CONTINUOUS_PRIORS.get(metric)
    if not prior_info:
        prior_info = {"mean": 50, "strength": 10, "by_type": {}}

    hosp_type = _classify_hospital_type(beds)
    prior_mean = prior_info["by_type"].get(hosp_type, prior_info["mean"])
    prior_strength = prior_info["strength"]

    if observed_mean is not None and observed_n > 0:
        post_mean, post_strength, shrinkage, ci = _gamma_posterior(
            prior_mean, prior_strength, observed_mean, observed_n)
        obs_mean = observed_mean
        quality = "strong" if observed_n >= 100 else ("moderate" if observed_n >= 30 else "weak")
    else:
        post_mean = prior_mean
        post_strength = prior_strength
        shrinkage = 1.0
        se = prior_mean * 0.15
        ci = (max(0, prior_mean - 1.645 * se), prior_mean + 1.645 * se)
        obs_mean = 0
        quality = "prior_only"

    return BayesianEstimate(
        metric=metric,
        prior_mean=round(prior_mean, 4),
        prior_strength=prior_strength,
        observed_mean=round(obs_mean, 4),
        observed_n=observed_n,
        posterior_mean=round(post_mean, 4),
        posterior_strength=round(post_strength, 1),
        credible_interval_90=(round(ci[0], 4), round(ci[1], 4)),
        shrinkage_factor=round(shrinkage, 3),
        data_quality=quality,
    )


def calibrate_hospital_profile(
    observed: Dict[str, Any],
    beds: float = 150,
    state: str = "",
) -> List[BayesianEstimate]:
    """Calibrate all KPIs for a hospital using Bayesian partial pooling.

    Takes whatever data is available and produces calibrated estimates
    for every metric, with explicit uncertainty and shrinkage.
    """
    results = []

    for metric in _RATE_PRIORS:
        val = observed.get(metric)
        n = observed.get(f"{metric}_n", observed.get("claims_volume", 0))
        results.append(calibrate_rate_metric(metric, val, int(n or 0), beds, state))

    for metric in _CONTINUOUS_PRIORS:
        val = observed.get(metric)
        n = observed.get(f"{metric}_n", observed.get("claims_volume", 0))
        results.append(calibrate_continuous_metric(metric, val, int(n or 0), beds))

    return results


def compute_missing_data_score(observed: Dict[str, Any]) -> Dict[str, Any]:
    """Quantify data completeness and estimate information loss.

    Returns a score (0-100) and per-metric missingness indicators.
    Missingness itself is informative in healthcare diligence — sellers
    who don't provide denial data often have bad denial rates.
    """
    all_metrics = list(_RATE_PRIORS.keys()) + list(_CONTINUOUS_PRIORS.keys())
    present = 0
    missing = []
    suspicious = []

    for metric in all_metrics:
        val = observed.get(metric)
        if val is not None:
            present += 1
            # Check for suspicious values
            if metric == "denial_rate" and val < 0.01:
                suspicious.append(f"{metric}: {val:.1%} — implausibly low")
            if metric == "clean_claim_rate" and val > 0.99:
                suspicious.append(f"{metric}: {val:.1%} — implausibly high")
        else:
            missing.append(metric)

    total = len(all_metrics)
    completeness = present / total * 100 if total > 0 else 0

    # Missing data penalty: absence is informative
    penalty = 0
    high_value_missing = {"denial_rate", "days_in_ar", "net_collection_rate", "clean_claim_rate"}
    for m in missing:
        if m in high_value_missing:
            penalty += 15
        else:
            penalty += 5

    adjusted_score = max(0, completeness - penalty * 0.5)

    if adjusted_score >= 80:
        grade = "A"
    elif adjusted_score >= 60:
        grade = "B"
    elif adjusted_score >= 40:
        grade = "C"
    else:
        grade = "D"

    return {
        "completeness_pct": round(completeness, 1),
        "adjusted_score": round(adjusted_score, 1),
        "grade": grade,
        "present_count": present,
        "missing_count": len(missing),
        "total_metrics": total,
        "missing_metrics": missing,
        "suspicious_values": suspicious,
        "missing_is_informative": len(missing) > len(all_metrics) * 0.3,
    }
