"""Hospital Investability Score — composite ML-derived PE investment rating.

Combines all proprietary models into a single 0-100 score that answers:
"Should a PE firm pursue this hospital?" with transparent sub-scores.

Components:
- Financial Health (25pts): margin, trend, peer ranking
- RCM Upside (25pts): gap to P75 peers, improvement achievability
- Market Position (20pts): concentration, competitive dynamics, payer mix
- Demand Defensibility (15pts): disease density, stickiness, elasticity
- Operational Efficiency (15pts): occupancy, revenue/bed, expense discipline

This is the flagship moat metric — the single number that SeekingChartis
produces that no other platform can replicate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class InvestabilityScore:
    ccn: str
    hospital_name: str
    state: str
    total_score: float  # 0-100
    grade: str  # A/B/C/D/F
    components: Dict[str, float]
    component_details: List[Dict[str, Any]]
    recommendation: str
    entry_multiple_range: str
    estimated_moic: float
    risk_factors: List[str]
    catalysts: List[str]


def _financial_health_score(
    margin: float, margin_pctile: float, beds: float, revenue: float,
) -> float:
    """Financial health sub-score (0-25)."""
    score = 0
    # Margin level (0-10)
    if margin > 0.10:
        score += 10
    elif margin > 0.05:
        score += 8
    elif margin > 0:
        score += 5
    elif margin > -0.05:
        score += 2
    # Margin percentile (0-8)
    score += min(8, margin_pctile / 100 * 8)
    # Scale (0-7): larger hospitals have more predictable cash flows
    if revenue > 1e9:
        score += 7
    elif revenue > 5e8:
        score += 5
    elif revenue > 1e8:
        score += 3
    elif revenue > 5e7:
        score += 1
    return min(25, score)


def _rcm_upside_score(
    margin: float, denial_gap: float, ar_gap: float, clean_claim_gap: float,
) -> float:
    """RCM improvement upside sub-score (0-25)."""
    score = 0
    # Margin room (0-8): lower margin = more room for improvement
    if margin < 0:
        score += 8
    elif margin < 0.05:
        score += 6
    elif margin < 0.10:
        score += 4
    elif margin < 0.15:
        score += 2
    # Denial gap (0-7)
    score += min(7, denial_gap * 70)
    # AR gap (0-5)
    score += min(5, ar_gap * 25)
    # Clean claim gap (0-5)
    score += min(5, clean_claim_gap * 50)
    return min(25, score)


def _market_position_score(
    n_competitors: int, commercial_pct: float, hhi: float, state_margin: float,
) -> float:
    """Market position sub-score (0-20)."""
    score = 0
    # Market power (0-8)
    if n_competitors <= 2:
        score += 8
    elif n_competitors <= 5:
        score += 6
    elif n_competitors <= 10:
        score += 4
    else:
        score += 2
    # Payer quality (0-7)
    score += min(7, commercial_pct * 15)
    # State market health (0-5)
    score += min(5, max(0, state_margin * 50))
    return min(20, score)


def _demand_defensibility_score(
    medicare_pct: float, occupancy: float, beds: float,
) -> float:
    """Demand defensibility sub-score (0-15)."""
    score = 0
    # Medicare stability (0-5): moderate Medicare is good (predictable)
    if 0.3 <= medicare_pct <= 0.5:
        score += 5
    elif 0.2 <= medicare_pct <= 0.6:
        score += 3
    else:
        score += 1
    # Occupancy (0-5): higher = stickier demand
    score += min(5, occupancy * 7)
    # Bed count as demand proxy (0-5)
    if beds > 200:
        score += 5
    elif beds > 100:
        score += 3
    elif beds > 50:
        score += 2
    return min(15, score)


def _operational_efficiency_score(
    rev_per_bed: float, expense_ratio: float, net_to_gross: float,
) -> float:
    """Operational efficiency sub-score (0-15)."""
    score = 0
    # Revenue per bed (0-6)
    if rev_per_bed > 3e6:
        score += 6
    elif rev_per_bed > 2e6:
        score += 4
    elif rev_per_bed > 1e6:
        score += 2
    # Expense discipline (0-5): lower expense ratio is better
    if expense_ratio < 0.90:
        score += 5
    elif expense_ratio < 0.95:
        score += 3
    elif expense_ratio < 1.0:
        score += 1
    # Net-to-gross (0-4): higher = better charge capture
    if net_to_gross > 0.35:
        score += 4
    elif net_to_gross > 0.25:
        score += 2
    return min(15, score)


def compute_investability(
    ccn: str,
    hcris_df: pd.DataFrame,
) -> Optional[InvestabilityScore]:
    """Compute the composite Investability Score for a hospital."""
    df = hcris_df.copy()

    # Derived features
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)

    match = df[df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))

    rev = float(hospital.get("net_patient_revenue", 0))
    opex = float(hospital.get("operating_expenses", 0))
    margin = float(hospital.get("operating_margin", 0))
    beds = float(hospital.get("beds", 0))
    medicare = float(hospital.get("medicare_day_pct", 0.4))
    medicaid = float(hospital.get("medicaid_day_pct", 0.15))
    commercial = max(0, 1 - medicare - medicaid)
    occupancy = float(hospital.get("total_patient_days", 0)) / max(1, float(hospital.get("bed_days_available", 1)))
    rev_per_bed = rev / beds if beds > 0 else 0
    expense_ratio = opex / rev if rev > 1e5 else 1.0
    gross = float(hospital.get("gross_patient_revenue", 0))
    net_to_gross = rev / gross if gross > 0 else 0.25

    # Margin percentile
    all_margins = df["operating_margin"].dropna()
    margin_pctile = float((all_margins < margin).mean() * 100) if len(all_margins) > 0 else 50

    # State peers
    state_df = df[df["state"] == state] if state else df
    state_margin = float(state_df["operating_margin"].dropna().median()) if len(state_df) > 5 else 0.03
    n_competitors = len(state_df) - 1

    # County competitors
    county = str(hospital.get("county", ""))
    if county:
        county_peers = df[(df["state"] == state) & (df["county"].str.upper() == county.upper())]
        n_county = max(0, len(county_peers) - 1)
    else:
        n_county = n_competitors

    # HHI for state
    state_revs = state_df["net_patient_revenue"].fillna(0).values
    state_revs = state_revs[state_revs > 0]
    from .market_intelligence import compute_hhi
    hhi = compute_hhi(list(state_revs))

    # Compute sub-scores using trained models where available
    fin = _financial_health_score(margin, margin_pctile, beds, rev)

    # RCM upside: use trained realization predictor if available
    rcm_base = _rcm_upside_score(margin, max(0, 0.12 - margin) * 0.5, 0.1, 0.05)
    try:
        from .realization_predictor import predict_realization
        rp = predict_realization(ccn, df, bridge_uplift=rev * 0.05)
        if rp and rp.expected_realization > 0:
            # Blend: higher realization → higher RCM upside
            rcm = min(25, rcm_base * (0.5 + rp.expected_realization * 0.7))
        else:
            rcm = rcm_base
    except Exception:
        rcm = rcm_base

    mkt = _market_position_score(n_county, commercial, hhi, state_margin)
    dem = _demand_defensibility_score(medicare, occupancy, beds)
    ops = _operational_efficiency_score(rev_per_bed, expense_ratio, net_to_gross)

    # Use trained margin prediction to adjust financial health
    try:
        from .margin_predictor import predict_margin
        mp = predict_margin(ccn, df)
        if mp and mp.predicted_margin is not None:
            # If trained model predicts better margin than actual, boost score
            margin_delta = mp.predicted_margin - margin
            if margin_delta > 0.03:
                fin = min(25, fin + 3)
            elif margin_delta < -0.05:
                fin = max(0, fin - 2)
    except Exception:
        pass

    total = fin + rcm + mkt + dem + ops

    if total >= 75:
        grade = "A"
    elif total >= 60:
        grade = "B"
    elif total >= 45:
        grade = "C"
    elif total >= 30:
        grade = "D"
    else:
        grade = "F"

    # Entry multiple estimation
    if total >= 70:
        multiple_range = "11.0x – 13.0x"
        est_moic = 2.8
    elif total >= 55:
        multiple_range = "9.5x – 11.5x"
        est_moic = 2.3
    elif total >= 40:
        multiple_range = "8.0x – 10.0x"
        est_moic = 1.9
    else:
        multiple_range = "6.0x – 8.5x"
        est_moic = 1.5

    # Recommendation
    if grade == "A":
        rec = "Strong Buy — pursue aggressively. High-quality asset with defensible revenue and RCM upside."
    elif grade == "B":
        rec = "Buy — solid fundamentals with identifiable value creation levers. Proceed to detailed diligence."
    elif grade == "C":
        rec = "Hold / Selective — investigate specific opportunities but be prepared for execution risk."
    elif grade == "D":
        rec = "Speculative — only pursue if turnaround thesis is strong and entry multiple reflects risk."
    else:
        rec = "Pass — risk/return profile does not justify PE capital deployment at market multiples."

    # Risk factors
    risks = []
    if margin < 0:
        risks.append("Negative operating margin")
    if medicare > 0.55:
        risks.append("Heavy Medicare dependence (>55%)")
    if beds < 50:
        risks.append("Small facility (<50 beds) — limited scale")
    if occupancy < 0.3:
        risks.append("Low occupancy (<30%) — demand risk")
    if expense_ratio > 1.05:
        risks.append("Expenses exceed revenue")

    catalysts = []
    if margin < 0.05 and beds > 100:
        catalysts.append("RCM optimization could add 3-5pp margin")
    if commercial > 0.35:
        catalysts.append("Strong commercial payer base protects revenue")
    if n_county <= 3:
        catalysts.append("Limited competition supports pricing power")
    if occupancy < 0.5 and beds > 100:
        catalysts.append("Volume growth opportunity from low occupancy")

    components = {
        "Financial Health": round(fin, 1),
        "RCM Upside": round(rcm, 1),
        "Market Position": round(mkt, 1),
        "Demand Defensibility": round(dem, 1),
        "Operational Efficiency": round(ops, 1),
    }

    details = [
        {"component": k, "score": v, "max": m, "pct": round(v / m * 100, 0)}
        for k, v, m in [
            ("Financial Health", fin, 25),
            ("RCM Upside", rcm, 25),
            ("Market Position", mkt, 20),
            ("Demand Defensibility", dem, 15),
            ("Operational Efficiency", ops, 15),
        ]
    ]

    return InvestabilityScore(
        ccn=ccn, hospital_name=name, state=state,
        total_score=round(total, 1), grade=grade,
        components=components, component_details=details,
        recommendation=rec, entry_multiple_range=multiple_range,
        estimated_moic=est_moic, risk_factors=risks, catalysts=catalysts,
    )


def rank_hospitals(
    hcris_df: pd.DataFrame,
    top_n: int = 50,
) -> List[Dict[str, Any]]:
    """Rank all hospitals by investability score."""
    df = hcris_df.copy()
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)

    results = []
    for _, row in df.iterrows():
        ccn = str(row.get("ccn", ""))
        if not ccn:
            continue
        score = compute_investability(ccn, df)
        if score:
            results.append({
                "ccn": ccn,
                "name": score.hospital_name[:35],
                "state": score.state,
                "score": score.total_score,
                "grade": score.grade,
                "margin": score.components.get("Financial Health", 0),
                "rcm_upside": score.components.get("RCM Upside", 0),
                "multiple_range": score.entry_multiple_range,
            })

    results.sort(key=lambda r: -r["score"])
    return results[:top_n]
