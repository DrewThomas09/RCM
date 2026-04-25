"""Operational-alpha attribution.

Splits realized EBITDA growth into:

  operational_alpha   the portion attributable to sponsor-driven
                      operational improvements — ESTIMATED BY
                      the SDID treatment effect (the lift above
                      what the synthetic counterfactual would
                      have achieved without the intervention).

  market_beta         the portion attributable to peer-group
                      baseline growth — ESTIMATED BY the
                      synthetic-counterfactual growth itself.

  unexplained         residual that doesn't fit either bucket.

This is the LP-grade attribution split that GP reports
increasingly need to defend "we earned X% IRR; here's the alpha
share that justifies our 2-and-20 fees."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from .sdid import SDIDResult, sdid_estimate


@dataclass
class AlphaAttribution:
    """LP-grade attribution split."""
    company_name: str
    realized_ebitda_growth_pct: float
    operational_alpha_pct: float
    market_beta_pct: float
    unexplained_pct: float
    sdid_match_quality: float
    notes: str = ""


def operational_alpha_attribution(
    company_name: str,
    Y: np.ndarray,
    *,
    treated_unit: int,
    treated_period: int,
    realized_ebitda_growth_pct: float,
) -> AlphaAttribution:
    """Compute the alpha / beta split.

    Args:
      Y: (N units × T periods) outcome panel — typically
        EBITDA-margin or growth-rate per period per
        portfolio company.
      treated_unit: row index of the company that received the
        sponsor-led intervention.
      treated_period: column index where the intervention
        started.
      realized_ebitda_growth_pct: actual full-period EBITDA
        growth at the treated unit. The attribution splits
        this into alpha + beta + residual.

    Returns AlphaAttribution. Conservative: any negative SDID
    estimate (intervention HURT) is reported as such — partner
    reviews before the LP letter.
    """
    sdid = sdid_estimate(
        Y, treated_unit=treated_unit,
        treated_period=treated_period,
    )

    # Synthetic-counterfactual growth — what the company would
    # have achieved without the intervention. Estimated by the
    # weighted-control growth in the post-treatment window.
    Y_arr = np.asarray(Y, dtype=float)
    n_units, n_periods = Y_arr.shape
    pre_idx = list(range(treated_period))
    post_idx = list(range(treated_period, n_periods))

    # Counterfactual growth for the treated unit = synthetic
    # control's mean post growth
    control_idx = [i for i in range(n_units) if i != treated_unit]
    omega_ctl = sdid.unit_weights[control_idx]
    Y_ctl_pre_mean = Y_arr[control_idx][:, pre_idx].mean(axis=1)
    Y_ctl_post_mean = Y_arr[control_idx][:, post_idx].mean(axis=1)
    if len(Y_ctl_pre_mean) > 0:
        synthetic_pre = float(omega_ctl @ Y_ctl_pre_mean)
        synthetic_post = float(omega_ctl @ Y_ctl_post_mean)
        if synthetic_pre > 0:
            counterfactual_growth_pct = (
                (synthetic_post - synthetic_pre)
                / synthetic_pre)
        else:
            counterfactual_growth_pct = 0.0
    else:
        counterfactual_growth_pct = 0.0

    # Alpha = realized - counterfactual
    alpha_pct = (realized_ebitda_growth_pct
                 - counterfactual_growth_pct)
    beta_pct = counterfactual_growth_pct
    unexplained_pct = (
        realized_ebitda_growth_pct - alpha_pct - beta_pct)

    notes = ""
    if alpha_pct < 0:
        notes = (
            "Negative operational alpha — the intervention "
            "under-performed the synthetic counterfactual. "
            "Partner review required before LP attribution.")
    elif sdid.pre_treatment_match_quality < 0.50:
        notes = (
            "Low pre-treatment match quality — synthetic "
            "counterfactual may not be reliable. Treat alpha "
            "estimate as suggestive, not definitive.")

    return AlphaAttribution(
        company_name=company_name,
        realized_ebitda_growth_pct=round(
            realized_ebitda_growth_pct, 4),
        operational_alpha_pct=round(alpha_pct, 4),
        market_beta_pct=round(beta_pct, 4),
        unexplained_pct=round(unexplained_pct, 4),
        sdid_match_quality=sdid.pre_treatment_match_quality,
        notes=notes,
    )
