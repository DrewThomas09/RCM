"""RCM Improvement Opportunity Scorer.

Estimates the revenue uplift potential from RCM optimization at a target
hospital. Compares the hospital's operational metrics against best-in-class
peers to quantify the "value creation" thesis that PE firms pay for.

This is THE core moat — no other platform can answer "how much EBITDA
improvement is achievable through RCM optimization at Hospital X?"

Methodology:
1. Identify comparable hospitals (same size/region/payer mix)
2. Compute the gap between target and P75 peers on each RCM metric
3. Apply conservative improvement assumptions (50-75% of gap closure)
4. Convert metric improvements to dollar revenue impact
5. Risk-adjust based on hospital size and complexity
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_RCM_LEVERS = [
    {
        "lever": "Denial Rate Reduction",
        "metric": "denial_rate",
        "direction": "lower_is_better",
        "benchmark_p75": 0.045,
        "benchmark_p25": 0.12,
        "revenue_multiplier": 1.0,
        "description": "Reduce initial claim denials through better coding, prior auth, and eligibility verification.",
        "implementation_months": 12,
        "confidence": 0.85,
    },
    {
        "lever": "AR Days Reduction",
        "metric": "days_in_ar",
        "direction": "lower_is_better",
        "benchmark_p75": 35,
        "benchmark_p25": 55,
        "cash_acceleration_rate": 0.00027,
        "description": "Accelerate collections by reducing average days outstanding.",
        "implementation_months": 9,
        "confidence": 0.80,
    },
    {
        "lever": "Clean Claim Rate Improvement",
        "metric": "clean_claim_rate",
        "direction": "higher_is_better",
        "benchmark_p75": 0.96,
        "benchmark_p25": 0.88,
        "revenue_multiplier": 0.5,
        "description": "Increase first-pass acceptance rate to reduce rework and accelerate payment.",
        "implementation_months": 6,
        "confidence": 0.90,
    },
    {
        "lever": "Net-to-Gross Ratio Improvement",
        "metric": "net_to_gross_ratio",
        "direction": "higher_is_better",
        "benchmark_p75": 0.38,
        "benchmark_p25": 0.22,
        "revenue_multiplier": 0.3,
        "description": "Improve charge capture and reduce contractual write-offs through better payer contracting.",
        "implementation_months": 18,
        "confidence": 0.65,
    },
    {
        "lever": "Payer Mix Optimization",
        "metric": "commercial_pct",
        "direction": "higher_is_better",
        "benchmark_p75": 0.42,
        "benchmark_p25": 0.20,
        "revenue_per_pct_point": 500000,
        "description": "Shift payer mix toward higher-reimbursement commercial contracts.",
        "implementation_months": 24,
        "confidence": 0.50,
    },
    {
        "lever": "Occupancy Improvement",
        "metric": "occupancy_rate",
        "direction": "higher_is_better",
        "benchmark_p75": 0.68,
        "benchmark_p25": 0.40,
        "revenue_per_pct_point": 200000,
        "description": "Increase patient volume through service line expansion and referral network development.",
        "implementation_months": 24,
        "confidence": 0.55,
    },
]


@dataclass
class RCMLever:
    lever: str
    current_value: float
    benchmark_value: float
    gap: float
    achievable_improvement: float
    estimated_annual_impact: float
    implementation_months: int
    confidence: float
    description: str
    risk_adjusted_impact: float


@dataclass
class RCMOpportunityScore:
    ccn: str
    hospital_name: str
    state: str
    total_opportunity: float
    risk_adjusted_opportunity: float
    opportunity_score: float  # 0-100
    levers: List[RCMLever]
    net_patient_revenue: float
    current_margin: float
    projected_margin: float
    projected_ebitda_uplift: float
    comparable_count: int
    grade: str  # A/B/C/D


def compute_rcm_opportunity(
    ccn: str,
    hcris_df: pd.DataFrame,
    deal_profile: Optional[Dict[str, Any]] = None,
) -> Optional[RCMOpportunityScore]:
    """Compute RCM improvement opportunity for a hospital."""
    df = hcris_df.copy()

    # Add derived features
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "net_to_gross_ratio" not in df.columns:
        df["net_to_gross_ratio"] = (
            df.get("net_patient_revenue", 0) / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)
    if "commercial_pct" not in df.columns:
        mc = df.get("medicare_day_pct", pd.Series(0, index=df.index)).fillna(0)
        md = df.get("medicaid_day_pct", pd.Series(0, index=df.index)).fillna(0)
        df["commercial_pct"] = (1.0 - mc - md).clip(0, 1)

    match = df[df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    revenue = float(hospital.get("net_patient_revenue", 0))
    margin = float(hospital.get("operating_margin", 0))
    beds = float(hospital.get("beds", 0))

    if revenue < 1e5:
        return None

    # Find comparable peers (same state or similar size)
    size_lo = max(10, beds * 0.5)
    size_hi = beds * 2.0
    peers = df[(df["beds"] >= size_lo) & (df["beds"] <= size_hi) & (df["ccn"] != ccn)]
    state_peers = peers[peers["state"] == state] if state else peers
    if len(state_peers) >= 10:
        comp_df = state_peers
    else:
        comp_df = peers
    n_comps = len(comp_df)

    # Merge deal profile metrics if available
    dp = deal_profile or {}

    levers = []
    total_impact = 0
    total_risk_adj = 0

    for lever_def in _RCM_LEVERS:
        metric = lever_def["metric"]

        # Get current value from deal profile or HCRIS
        current = dp.get(metric)
        if current is None:
            current = hospital.get(metric)
        if current is None or pd.isna(current):
            continue
        current = float(current)

        # Compute benchmark from peers
        if metric in comp_df.columns:
            peer_vals = comp_df[metric].dropna()
            if len(peer_vals) < 5:
                benchmark = lever_def.get("benchmark_p75", 0)
            else:
                if lever_def["direction"] == "lower_is_better":
                    benchmark = float(peer_vals.quantile(0.25))
                else:
                    benchmark = float(peer_vals.quantile(0.75))
        else:
            benchmark = lever_def.get("benchmark_p75", lever_def.get("benchmark_p25", 0))

        # Compute gap
        if lever_def["direction"] == "lower_is_better":
            gap = current - benchmark
            achievable = gap * 0.6  # 60% gap closure
        else:
            gap = benchmark - current
            achievable = gap * 0.6

        if gap <= 0:
            achievable = 0
            gap = 0

        # Estimate dollar impact
        if "revenue_multiplier" in lever_def:
            impact = achievable * revenue * lever_def["revenue_multiplier"]
        elif "cash_acceleration_rate" in lever_def:
            impact = achievable * revenue * lever_def["cash_acceleration_rate"]
        elif "revenue_per_pct_point" in lever_def:
            impact = achievable * lever_def["revenue_per_pct_point"] * 100
        else:
            impact = 0

        impact = abs(impact)
        confidence = lever_def["confidence"]
        risk_adj = impact * confidence

        levers.append(RCMLever(
            lever=lever_def["lever"],
            current_value=current,
            benchmark_value=benchmark,
            gap=round(gap, 4),
            achievable_improvement=round(achievable, 4),
            estimated_annual_impact=round(impact, 0),
            implementation_months=lever_def["implementation_months"],
            confidence=confidence,
            description=lever_def["description"],
            risk_adjusted_impact=round(risk_adj, 0),
        ))

        total_impact += impact
        total_risk_adj += risk_adj

    levers.sort(key=lambda l: -l.risk_adjusted_impact)

    # Opportunity score (0-100)
    if revenue > 0:
        uplift_pct = total_risk_adj / revenue
        score = min(100, max(0, uplift_pct * 500))
    else:
        score = 0

    # Grade
    if score >= 70:
        grade = "A"
    elif score >= 50:
        grade = "B"
    elif score >= 30:
        grade = "C"
    else:
        grade = "D"

    projected_margin = margin + (total_risk_adj / revenue if revenue > 0 else 0)

    return RCMOpportunityScore(
        ccn=ccn,
        hospital_name=name,
        state=state,
        total_opportunity=round(total_impact, 0),
        risk_adjusted_opportunity=round(total_risk_adj, 0),
        opportunity_score=round(score, 1),
        levers=levers,
        net_patient_revenue=revenue,
        current_margin=round(margin, 4),
        projected_margin=round(projected_margin, 4),
        projected_ebitda_uplift=round(total_risk_adj, 0),
        comparable_count=n_comps,
        grade=grade,
    )
