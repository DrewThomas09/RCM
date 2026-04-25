"""Healthcare-specific joint tail model.

Wires the three risk factors that systematically threaten
healthcare PE EBITDA in concert:

  1. CMS payment cuts — modeled as a negative shock to Medicare
     reimbursement rates. Empirical SD ~3-5% across cycles;
     down-tail dominated by physician fee schedule expirations,
     OPPS site-neutral expansions, MA STAR cuts.
  2. Commercial rate compression — payer-side margin squeeze.
     Empirical SD ~2-4%; correlated with CMS via "payer copies
     CMS" dynamics + macro labor inflation.
  3. Labor inflation — wage growth above budget. Empirical SD
     ~3-6%; correlated with macro tightness, capacity
     constraints.

The joint distribution is the dominant input to the bear case;
modeling them as independent dramatically under-states tail
risk. A Clayton copula with theta=2.0 captures the stylized
fact that they all hit together when they hit at all.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from .copula import clayton_copula_sample, gaussian_copula_sample


def joint_tail_healthcare_shock(
    n_samples: int,
    *,
    correlation: float = 0.45,
    cms_mean: float = -0.020,
    cms_std: float = 0.040,
    commercial_mean: float = -0.010,
    commercial_std: float = 0.030,
    labor_mean: float = 0.040,
    labor_std: float = 0.045,
    use_clayton: bool = True,
    clayton_theta: float = 2.0,
    seed: int = 0,
) -> Dict[str, np.ndarray]:
    """Sample (n_samples, 3) joint shocks to CMS rates, commercial
    rates, and labor inflation.

    Returns a dict with the three shock arrays:
      cms_rate_shock, commercial_rate_shock, labor_inflation_shock

    Each is centered on the supplied mean with std equal to the
    supplied std. Default params model the historical mean / SD;
    partner can override for a specific cycle.

    With ``use_clayton=True`` (default), the dependence is
    asymmetric lower-tail — joint downside hits harder than
    joint upside. The Gaussian-copula path is provided for
    backtests against the symmetric assumption.
    """
    if use_clayton:
        # Clayton on the (CMS_down, commercial_down, labor_up)
        # axes. Labor "shock" is positive in the bad direction
        # (high inflation), so we invert it after sampling.
        u = clayton_copula_sample(
            theta=clayton_theta,
            n_samples=n_samples, d=3, seed=seed,
        )
    else:
        # Symmetric Gaussian fallback
        rho = correlation
        corr = np.array([
            [1.0, rho, -rho],
            [rho, 1.0, -rho],
            [-rho, -rho, 1.0],
        ])
        u = gaussian_copula_sample(corr, n_samples, seed=seed)

    # Inverse-CDF through Φ^-1 to standard normal, then scale
    from math import erf, sqrt

    def _phi_inv(p: np.ndarray) -> np.ndarray:
        # Beasley-Springer-Moro approximation for Φ^-1 — standard,
        # stable, numpy-vectorizable.
        a = (-3.969683028665376e+01, 2.209460984245205e+02,
             -2.759285104469687e+02, 1.383577518672690e+02,
             -3.066479806614716e+01, 2.506628277459239e+00)
        b = (-5.447609879822406e+01, 1.615858368580409e+02,
             -1.556989798598866e+02, 6.680131188771972e+01,
             -1.328068155288572e+01)
        c = (-7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e+00, -2.549732539343734e+00,
             4.374664141464968e+00, 2.938163982698783e+00)
        d = (7.784695709041462e-03, 3.224671290700398e-01,
             2.445134137142996e+00, 3.754408661907416e+00)
        p = np.clip(p, 1e-12, 1.0 - 1e-12)
        plow = 0.02425
        phigh = 1.0 - plow
        out = np.zeros_like(p)
        # Lower
        mask_low = p < plow
        q = np.sqrt(-2.0 * np.log(p[mask_low]))
        out[mask_low] = (((((c[0] * q + c[1]) * q + c[2]) * q
                          + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        # Upper
        mask_high = p > phigh
        q = np.sqrt(-2.0 * np.log(1.0 - p[mask_high]))
        out[mask_high] = -(((((c[0] * q + c[1]) * q + c[2]) * q
                             + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        # Central
        mask_mid = ~(mask_low | mask_high)
        q = p[mask_mid] - 0.5
        r = q * q
        out[mask_mid] = (((((a[0] * r + a[1]) * r + a[2]) * r
                          + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r
             + b[4]) * r + 1.0)
        return out

    z = _phi_inv(u)
    cms = cms_mean + cms_std * z[:, 0]
    commercial = commercial_mean + commercial_std * z[:, 1]
    labor_pre = labor_mean + labor_std * z[:, 2]
    if use_clayton:
        # Clayton couples lower tails of all three. Invert the
        # labor axis so its downside (joint with CMS/commercial)
        # corresponds to high inflation.
        labor = labor_mean - labor_std * (z[:, 2] - 0.0)
    else:
        labor = labor_pre

    return {
        "cms_rate_shock": cms,
        "commercial_rate_shock": commercial,
        "labor_inflation_shock": labor,
    }
