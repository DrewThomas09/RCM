"""Market intelligence engine — state/regional analytics and scoring.

Computes market-level statistics that PE firms need for hospital
evaluations: market concentration (HHI), competitive dynamics,
reimbursement environment, and growth indicators.

Moat: No other platform computes healthcare-specific market scores
at the county/state level from raw HCRIS + CMS data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class MarketScore:
    state: str
    n_hospitals: int
    total_beds: int
    total_revenue: float
    median_margin: float
    margin_iqr: float
    hhi: float
    market_concentration: str
    payer_mix: Dict[str, float]
    distress_rate: float
    growth_score: float
    investability_score: float
    investability_grade: str
    top_hospitals: List[Dict[str, Any]]
    risk_factors: List[str]
    opportunity_factors: List[str]


def compute_hhi(revenue_shares: List[float]) -> float:
    """Herfindahl-Hirschman Index for market concentration."""
    if not revenue_shares:
        return 0
    total = sum(revenue_shares)
    if total <= 0:
        return 0
    shares = [r / total * 100 for r in revenue_shares]
    return sum(s ** 2 for s in shares)


def compute_state_markets(hcris_df: pd.DataFrame) -> List[MarketScore]:
    """Compute market intelligence for every state."""
    df = hcris_df.copy()

    # Ensure derived columns
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)

    results = []
    for state in sorted(df["state"].dropna().unique()):
        st = df[df["state"] == state]
        if len(st) < 3:
            continue

        n = len(st)
        beds = float(st["beds"].fillna(0).sum())
        revenue = float(st["net_patient_revenue"].fillna(0).sum())
        margins = st["operating_margin"].dropna()
        median_margin = float(margins.median()) if len(margins) > 0 else 0
        margin_iqr = float(margins.quantile(0.75) - margins.quantile(0.25)) if len(margins) > 3 else 0

        # HHI
        revs = st["net_patient_revenue"].fillna(0).values
        revs = revs[revs > 0]
        hhi = compute_hhi(list(revs)) if len(revs) > 1 else 10000

        if hhi > 2500:
            concentration = "Highly Concentrated"
        elif hhi > 1500:
            concentration = "Moderately Concentrated"
        else:
            concentration = "Competitive"

        # Payer mix
        mc = float(st["medicare_day_pct"].fillna(0).median()) if "medicare_day_pct" in st.columns else 0.4
        md = float(st["medicaid_day_pct"].fillna(0).median()) if "medicaid_day_pct" in st.columns else 0.15
        payer_mix = {"medicare": round(mc, 3), "medicaid": round(md, 3), "commercial": round(max(0, 1 - mc - md), 3)}

        # Distress rate
        distress_rate = float((margins < -0.05).mean()) if len(margins) > 0 else 0

        # Growth score (0-100): based on revenue concentration, margin health, competition
        growth_parts = []
        growth_parts.append(min(30, max(0, (1 - distress_rate) * 30)))
        growth_parts.append(min(25, max(0, median_margin * 250)))
        growth_parts.append(min(25, max(0, (payer_mix["commercial"]) * 60)))
        growth_parts.append(min(20, max(0, (1 - hhi / 10000) * 20)))
        growth_score = sum(growth_parts)

        # Investability score (0-100)
        inv_parts = []
        inv_parts.append(min(25, max(0, n * 0.5)))  # market depth
        inv_parts.append(min(25, max(0, growth_score * 0.25)))  # growth
        inv_parts.append(min(25, max(0, (1 - distress_rate) * 25)))  # health
        inv_parts.append(min(25, max(0, payer_mix["commercial"] * 60)))  # payer quality
        inv_score = sum(inv_parts)

        if inv_score >= 70:
            inv_grade = "A"
        elif inv_score >= 55:
            inv_grade = "B"
        elif inv_score >= 40:
            inv_grade = "C"
        else:
            inv_grade = "D"

        # Top hospitals
        top = st.nlargest(5, "net_patient_revenue")
        top_list = []
        for _, row in top.iterrows():
            top_list.append({
                "ccn": str(row.get("ccn", "")),
                "name": str(row.get("name", ""))[:35],
                "beds": int(row.get("beds", 0)),
                "revenue": float(row.get("net_patient_revenue", 0)),
                "margin": float(row.get("operating_margin", 0)),
            })

        # Risk/opportunity factors
        risks = []
        opps = []
        if distress_rate > 0.3:
            risks.append(f"{distress_rate:.0%} of hospitals below -5% margin")
        if mc > 0.5:
            risks.append(f"High Medicare dependence ({mc:.0%})")
        if hhi > 2500:
            risks.append("Highly concentrated market — antitrust risk")
        if md > 0.25:
            risks.append(f"High Medicaid exposure ({md:.0%})")

        if payer_mix["commercial"] > 0.35:
            opps.append(f"Strong commercial payer mix ({payer_mix['commercial']:.0%})")
        if median_margin > 0.05:
            opps.append(f"Healthy median margin ({median_margin:.1%})")
        if concentration == "Competitive":
            opps.append("Competitive market — acquisition opportunities at fair multiples")
        if distress_rate > 0.2:
            opps.append(f"Distressed targets available ({distress_rate:.0%} distress rate)")

        results.append(MarketScore(
            state=state, n_hospitals=n, total_beds=int(beds),
            total_revenue=revenue, median_margin=round(median_margin, 4),
            margin_iqr=round(margin_iqr, 4), hhi=round(hhi, 0),
            market_concentration=concentration, payer_mix=payer_mix,
            distress_rate=round(distress_rate, 3), growth_score=round(growth_score, 1),
            investability_score=round(inv_score, 1), investability_grade=inv_grade,
            top_hospitals=top_list, risk_factors=risks, opportunity_factors=opps,
        ))

    results.sort(key=lambda m: -m.investability_score)
    return results


def compute_county_market(
    state: str,
    county: str,
    hcris_df: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """County-level market analysis for hyperlocal competitive dynamics."""
    matches = hcris_df[
        (hcris_df["state"] == state) &
        (hcris_df["county"].str.upper() == county.upper())
    ]
    if matches.empty:
        return None

    n = len(matches)
    rev = matches.get("net_patient_revenue", pd.Series(dtype=float)).fillna(0)
    beds = int(matches["beds"].fillna(0).sum())
    hhi = compute_hhi(list(rev.values[rev.values > 0]))

    return {
        "state": state,
        "county": county,
        "n_hospitals": n,
        "total_beds": beds,
        "total_revenue": float(rev.sum()),
        "hhi": round(hhi, 0),
        "concentration": "Monopoly" if n <= 1 else ("Duopoly" if n == 2 else
                          "Concentrated" if hhi > 2500 else "Competitive"),
        "hospitals": [
            {"ccn": str(r.get("ccn", "")), "name": str(r.get("name", ""))[:35],
             "beds": int(r.get("beds", 0))}
            for _, r in matches.iterrows()
        ],
    }
