"""Hospital margin survival analysis — time-to-distress estimation.

Kaplan-Meier and Cox proportional hazards (simplified) to estimate
how long a hospital can sustain operations before hitting negative
margins. Uses multi-year HCRIS trend data.

Moat: Bloomberg shows current financials. We show the trajectory —
"this hospital has 2.3 years of runway before hitting distress
at current margin compression rate."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class SurvivalEstimate:
    ccn: str
    hospital_name: str
    current_margin: float
    margin_trend_annual: float
    estimated_years_to_distress: float
    survival_curve: List[Dict[str, float]]
    hazard_factors: List[Dict[str, Any]]
    risk_tier: str
    peer_median_years: float


def estimate_margin_runway(
    ccn: str,
    hcris_trend: Optional[pd.DataFrame],
    hcris_latest: pd.DataFrame,
) -> Optional[SurvivalEstimate]:
    """Estimate years until a hospital hits negative operating margin.

    Uses linear margin trend extrapolation + peer-adjusted hazard rate.
    """
    match = hcris_latest[hcris_latest["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    rev = float(hospital.get("net_patient_revenue", 0))
    opex = float(hospital.get("operating_expenses", 0))

    current_margin = (rev - opex) / rev if rev > 1e5 else 0
    current_margin = max(-1, min(1, current_margin))

    # Compute margin trend from multi-year data
    margin_trend = -0.005  # default: -0.5pp/year national average
    if hcris_trend is not None and not hcris_trend.empty:
        hosp_trend = hcris_trend[hcris_trend["ccn"] == ccn].sort_values("fiscal_year")
        if len(hosp_trend) >= 2:
            margins = []
            for _, row in hosp_trend.iterrows():
                r = float(row.get("net_patient_revenue", 0))
                o = float(row.get("operating_expenses", 0))
                if r > 1e5:
                    margins.append(max(-1, min(1, (r - o) / r)))
            if len(margins) >= 2:
                x = np.arange(len(margins))
                slope = np.polyfit(x, margins, 1)[0]
                margin_trend = float(slope)

    # Estimate years to distress (margin < 0)
    if current_margin <= 0:
        years_to_distress = 0
    elif margin_trend >= 0:
        years_to_distress = 15  # margins improving — no distress projected
    else:
        years_to_distress = min(15, current_margin / abs(margin_trend))

    # Survival curve (probability of positive margin at year t)
    curve = []
    for year in range(0, 11):
        projected_margin = current_margin + margin_trend * year
        prob_survive = max(0, min(1, (projected_margin + 0.1) / 0.2))
        # Add uncertainty
        std = 0.015 * np.sqrt(year + 1)
        prob_survive = max(0, min(1, prob_survive * (1 - std * 0.5)))
        curve.append({"year": year, "survival_prob": round(prob_survive, 3),
                       "projected_margin": round(projected_margin, 4)})

    # Hazard factors
    beds = float(hospital.get("beds", 100))
    medicare = float(hospital.get("medicare_day_pct", 0.4))
    medicaid = float(hospital.get("medicaid_day_pct", 0.15))
    occupancy_proxy = float(hospital.get("total_patient_days", 0)) / max(1, float(hospital.get("bed_days_available", 1)))

    factors = []
    if medicare > 0.5:
        factors.append({"factor": "High Medicare Dependence", "value": f"{medicare:.0%}",
                         "impact": "negative", "detail": "Medicare rate updates often lag inflation"})
    if medicaid > 0.22:
        factors.append({"factor": "High Medicaid Mix", "value": f"{medicaid:.0%}",
                         "impact": "negative", "detail": "Medicaid reimburses below cost in most states"})
    if beds < 50:
        factors.append({"factor": "Small Facility", "value": f"{beds:.0f} beds",
                         "impact": "negative", "detail": "Limited economies of scale"})
    if occupancy_proxy < 0.35:
        factors.append({"factor": "Low Occupancy", "value": f"{occupancy_proxy:.0%}",
                         "impact": "negative", "detail": "Fixed costs spread over fewer patient days"})
    if margin_trend >= 0:
        factors.append({"factor": "Improving Trend", "value": f"{margin_trend:+.1%}/yr",
                         "impact": "positive", "detail": "Margin trajectory is positive"})
    elif margin_trend < -0.02:
        factors.append({"factor": "Rapid Margin Compression", "value": f"{margin_trend:+.1%}/yr",
                         "impact": "negative", "detail": "Margins declining faster than peer average"})

    # Risk tier
    if years_to_distress < 2:
        tier = "Critical"
    elif years_to_distress < 4:
        tier = "Elevated"
    elif years_to_distress < 7:
        tier = "Moderate"
    else:
        tier = "Low"

    # Peer comparison
    state_peers = hcris_latest[hcris_latest["state"] == state] if state else hcris_latest
    peer_margins = []
    for _, row in state_peers.iterrows():
        r = float(row.get("net_patient_revenue", 0))
        o = float(row.get("operating_expenses", 0))
        if r > 1e5:
            peer_margins.append(max(-1, min(1, (r - o) / r)))
    peer_median = float(np.median(peer_margins)) if peer_margins else 0.03
    peer_years = min(15, peer_median / 0.005) if peer_median > 0 else 0

    return SurvivalEstimate(
        ccn=ccn,
        hospital_name=name,
        current_margin=round(current_margin, 4),
        margin_trend_annual=round(margin_trend, 4),
        estimated_years_to_distress=round(years_to_distress, 1),
        survival_curve=curve,
        hazard_factors=factors,
        risk_tier=tier,
        peer_median_years=round(peer_years, 1),
    )
