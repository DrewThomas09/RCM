"""Logistic-style flight-risk predictor.

Hand-calibrated coefficients (no sklearn dependency). The model
maps a 9-dim :class:`AttritionFeatures` vector to an 18-month
flight-risk probability via a sigmoid.

Calibration source: public PE-healthcare deal post-mortems that
flagged physician-retention as a thesis-breaker (Envision/KKR
2018-2023, Steward 2010-2024, USPI JV outcomes, IC Packet retros
from the Adeptus / Prospect / Genesis library). Coefficients
are partner-readable, not gradient-descended — each one has a
plain-English story:

    comp_gap_normalized        β= 1.8   below/above FMV = flight
    tenure_short               β= 1.5   new hires leave at higher rates
    age_inflection             β= 1.2   early + late career peaks
    productivity_decline       β= 2.2   declining collections signals prep
    local_competitor_density   β= 1.0   alternatives matter
    stark_overlap_flag         β= 2.5   comp unwind at close → exit
    employment_status_risk     β= 1.4   locum vs partner spread
    solo_line_revenue_share    β= 0.4   concentration amplifies partner-
                                        facing risk but not probability;
                                        small coefficient
    specialty_mobility         β= 1.3   surgeons move, PCP's don't

Intercept −3.2 sets the base rate at ~4% for a fully-zero vector
(matches MGMA 2024 5-year physician turnover baseline of ~4-6%
annualised for hospital-employed full-time).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple

from .features import AttritionFeatures


# Intercept + 9 coefficients — order matches AttritionFeatures.as_tuple().
DEFAULT_INTERCEPT: float = -3.2

DEFAULT_COEFFICIENTS: Tuple[float, ...] = (
    1.8,   # comp_gap_normalized
    1.5,   # tenure_short
    1.2,   # age_inflection
    2.2,   # productivity_decline
    1.0,   # local_competitor_density
    2.5,   # stark_overlap_flag
    1.4,   # employment_status_risk
    0.4,   # solo_line_revenue_share
    1.3,   # specialty_mobility
)


def _sigmoid(z: float) -> float:
    # Numerically stable sigmoid.
    if z >= 0:
        e = math.exp(-z)
        return 1.0 / (1.0 + e)
    e = math.exp(z)
    return e / (1.0 + e)


def flight_risk_probability(
    features: AttritionFeatures,
    *,
    intercept: float = DEFAULT_INTERCEPT,
    coefficients: Tuple[float, ...] = DEFAULT_COEFFICIENTS,
) -> float:
    """Return an 18-month flight-risk probability in [0.0, 1.0]."""
    if len(coefficients) != len(features.FEATURE_NAMES):
        raise ValueError(
            f"coefficients must have length "
            f"{len(features.FEATURE_NAMES)}, got {len(coefficients)}",
        )
    z = intercept
    for beta, x in zip(coefficients, features.as_tuple()):
        z += beta * x
    return _sigmoid(z)


# ────────────────────────────────────────────────────────────────────
# Flight-risk bands
# ────────────────────────────────────────────────────────────────────

class FlightRiskBand(str, Enum):
    """Partner-facing flight-risk bucket.

    Thresholds tuned so CRITICAL captures the "do not close without a
    retention bond" band; HIGH triggers a partner-level conversation
    but is typically structurable; MEDIUM warrants monitoring; LOW is
    a stable employee.
    """
    CRITICAL = "CRITICAL"   # ≥ 0.85
    HIGH     = "HIGH"       # 0.60 – 0.85
    MEDIUM   = "MEDIUM"     # 0.30 – 0.60
    LOW      = "LOW"        # < 0.30


def band_for(probability: float) -> FlightRiskBand:
    p = max(0.0, min(1.0, float(probability)))
    if p >= 0.85:
        return FlightRiskBand.CRITICAL
    if p >= 0.60:
        return FlightRiskBand.HIGH
    if p >= 0.30:
        return FlightRiskBand.MEDIUM
    return FlightRiskBand.LOW


def feature_contributions(
    features: AttritionFeatures,
    *,
    intercept: float = DEFAULT_INTERCEPT,
    coefficients: Tuple[float, ...] = DEFAULT_COEFFICIENTS,
) -> Dict[str, float]:
    """Per-feature β·x contribution to the log-odds.

    Used by the UI to surface the top drivers of a provider's flight
    probability — "Dr. X is flagged mostly by comp_gap + Stark
    overlap" is more actionable than a single probability.
    """
    out: Dict[str, float] = {"intercept": intercept}
    for name, beta, x in zip(
        features.FEATURE_NAMES, coefficients, features.as_tuple(),
    ):
        out[name] = beta * x
    return out
