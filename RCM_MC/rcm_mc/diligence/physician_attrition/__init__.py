"""Predictive Physician Attrition Model (P-PAM).

Given a roster of providers plus optional public-data context (NPI
enumeration date, local-competitor count, specialty FMV benchmark),
score each provider's 18-month flight-risk probability and surface
the top contributors to EBITDA at risk.

Why this is a moat:

    Chartis/VMG/A&M produce aggregate comp benchmarks. They do not
    produce per-provider flight-risk with named providers. The
    Medicare PUF (free, updated annually) contains the billing-
    pattern data to do this. Nobody has productized it.

    For the MD: the output is not "attrition is a risk" — it is
    "Dr. X, Y, Z produce 41% of collections and are 85%+ flight
    risk. Earn-out structure must include retention bonds for
    these five."

Public API::

    from rcm_mc.diligence.physician_attrition import (
        AttritionFeatures, AttritionReport, FlightRiskBand,
        ProviderAttritionScore, analyze_roster,
        extract_features, flight_risk_probability,
    )
"""
from __future__ import annotations

from .features import (
    AttritionFeatures, extract_features,
)
from .model import (
    DEFAULT_COEFFICIENTS, FlightRiskBand,
    flight_risk_probability, band_for,
)
from .analyzer import (
    AttritionReport, ProviderAttritionScore,
    RetentionRecommendation, analyze_roster,
)

__all__ = [
    "AttritionFeatures",
    "AttritionReport",
    "DEFAULT_COEFFICIENTS",
    "FlightRiskBand",
    "ProviderAttritionScore",
    "RetentionRecommendation",
    "analyze_roster",
    "band_for",
    "extract_features",
    "flight_risk_probability",
]
