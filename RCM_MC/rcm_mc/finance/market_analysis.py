"""Market analysis: regional concentration, competitive landscape, supply chain.

Uses HCRIS data to build market profiles for a hospital's region:
- Market share by revenue and beds
- HHI concentration index
- Competitive moat indicators (switching costs, scale, network effects)
- Regional payer mix breakdown
- Supply chain analysis from public data

Inspired by "Measure the Moat" (Mauboussin) metrics adapted for healthcare.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Competitor:
    ccn: str
    name: str
    beds: int
    revenue: float
    market_share_revenue: float
    market_share_beds: float
    distance_bucket: str

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in asdict(self).items()}


@dataclass
class MoatMetrics:
    """Mauboussin-inspired moat assessment for healthcare."""
    hhi_index: float
    market_share_rank: int
    market_share_pct: float
    top3_concentration: float
    scale_advantage: str
    switching_cost_indicator: str
    network_density: float
    bed_utilization_vs_market: float
    margin_vs_market: float
    moat_rating: str
    moat_score: int

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in asdict(self).items()}


@dataclass
class MarketAnalysis:
    """Full market analysis for a hospital."""
    target_ccn: str
    target_name: str
    state: str
    county: str
    region_hospitals: int
    total_beds_in_market: int
    total_revenue_in_market: float
    competitors: List[Competitor]
    moat: MoatMetrics
    payer_mix_region: Dict[str, float]
    market_trends: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": {"ccn": self.target_ccn, "name": self.target_name,
                        "state": self.state, "county": self.county},
            "market_size": {
                "hospitals": self.region_hospitals,
                "total_beds": self.total_beds_in_market,
                "total_revenue": round(self.total_revenue_in_market, 2),
            },
            "competitors": [c.to_dict() for c in self.competitors],
            "moat": self.moat.to_dict(),
            "payer_mix_region": {k: round(v, 4) for k, v in self.payer_mix_region.items()},
            "market_trends": self.market_trends,
        }


def analyze_market(
    deal_profile: Dict[str, Any],
    hcris_df: Optional[pd.DataFrame] = None,
) -> MarketAnalysis:
    """Build a market analysis from deal profile + HCRIS data."""
    if hcris_df is None:
        from ..data.hcris import _get_latest_per_ccn
        hcris_df = _get_latest_per_ccn()

    state = str(deal_profile.get("state") or "")
    county = str(deal_profile.get("county") or "")
    target_name = str(deal_profile.get("name") or "")
    target_ccn = str(deal_profile.get("ccn") or deal_profile.get("deal_id") or "")

    if state:
        market = hcris_df[hcris_df["state"] == state].copy()
    else:
        market = hcris_df.copy()

    if county and "county" in market.columns:
        county_match = market[market["county"].str.upper() == county.upper()]
        if len(county_match) >= 3:
            market = county_match

    market_beds = market["beds"].fillna(0)
    total_beds = int(market_beds.sum())
    rev_col = "net_patient_revenue" if "net_patient_revenue" in market.columns else "gross_patient_revenue"
    market_rev = market[rev_col].fillna(0) if rev_col in market.columns else pd.Series(0, index=market.index)
    total_rev = float(market_rev.sum())

    target_beds = float(deal_profile.get("bed_count") or deal_profile.get("beds") or 0)
    target_rev = float(deal_profile.get("net_revenue") or 0)

    competitors = []
    shares = []
    for _, row in market.iterrows():
        try:
            beds = int(float(row.get("beds", 0) or 0))
        except (TypeError, ValueError):
            beds = 0
        try:
            rev = float(row.get(rev_col, 0) or 0)
        except (TypeError, ValueError):
            rev = 0
        ms_rev = rev / total_rev if total_rev > 0 else 0
        ms_beds = beds / total_beds if total_beds > 0 else 0
        shares.append(ms_rev)

        if str(row.get("ccn", "")) == target_ccn:
            continue

        competitors.append(Competitor(
            ccn=str(row.get("ccn", "")),
            name=str(row.get("name", ""))[:50],
            beds=beds,
            revenue=rev,
            market_share_revenue=ms_rev,
            market_share_beds=ms_beds,
            distance_bucket="same_state",
        ))

    competitors.sort(key=lambda c: -c.revenue)
    competitors = competitors[:15]

    hhi = sum(s ** 2 for s in shares) * 10000 if shares else 0
    target_ms = target_rev / total_rev if total_rev > 0 else 0
    sorted_shares = sorted(shares, reverse=True)
    top3 = sum(sorted_shares[:3])
    rank = sum(1 for s in shares if s > target_ms) + 1

    beds_per_hosp = total_beds / len(market) if len(market) > 0 else 0
    scale = "strong" if target_beds > beds_per_hosp * 1.5 else (
        "moderate" if target_beds > beds_per_hosp else "weak"
    )

    switching = "high" if target_beds > 200 else ("moderate" if target_beds > 100 else "low")

    network_density = len(market) / max(total_beds / 100, 1)

    target_margin = float(deal_profile.get("ebitda_margin") or 0.12)
    market_margins = []
    if "operating_expenses" in market.columns and rev_col in market.columns:
        for _, r in market.iterrows():
            rev = float(r.get(rev_col) or 0)
            opex = float(r.get("operating_expenses") or 0)
            if rev > 1e5 and opex > 0:
                m = (rev - opex) / rev
                if -1.0 <= m <= 1.0:
                    market_margins.append(m)
    avg_margin = float(np.median(market_margins)) if market_margins else 0.10
    margin_vs = target_margin - avg_margin

    bed_util = float(deal_profile.get("occupancy_rate") or 0.65)
    market_util = 0.62

    moat_score = 0
    if scale == "strong":
        moat_score += 3
    elif scale == "moderate":
        moat_score += 1
    if switching == "high":
        moat_score += 2
    elif switching == "moderate":
        moat_score += 1
    if hhi < 2500:
        moat_score += 1
    if target_ms > 0.15:
        moat_score += 2
    elif target_ms > 0.08:
        moat_score += 1
    if margin_vs > 0.02:
        moat_score += 2
    elif margin_vs > 0:
        moat_score += 1

    moat_rating = "wide" if moat_score >= 8 else (
        "narrow" if moat_score >= 5 else "none"
    )

    moat = MoatMetrics(
        hhi_index=round(hhi, 1),
        market_share_rank=rank,
        market_share_pct=target_ms,
        top3_concentration=top3,
        scale_advantage=scale,
        switching_cost_indicator=switching,
        network_density=round(network_density, 2),
        bed_utilization_vs_market=bed_util - market_util,
        margin_vs_market=margin_vs,
        moat_rating=moat_rating,
        moat_score=moat_score,
    )

    med_days = market.get("medicare_day_pct")
    mcd_days = market.get("medicaid_day_pct")
    payer_mix = {}
    if med_days is not None:
        payer_mix["medicare"] = float(med_days.mean()) if len(med_days) > 0 else 0
    if mcd_days is not None:
        payer_mix["medicaid"] = float(mcd_days.mean()) if len(mcd_days) > 0 else 0
    payer_mix["commercial"] = max(0, 1.0 - sum(payer_mix.values()))

    trends = {
        "avg_beds_in_market": round(beds_per_hosp, 0),
        "avg_margin_in_market": round(avg_margin, 4),
        "hospital_count_in_state": len(market),
    }

    return MarketAnalysis(
        target_ccn=target_ccn, target_name=target_name,
        state=state, county=county,
        region_hospitals=len(market),
        total_beds_in_market=total_beds,
        total_revenue_in_market=total_rev,
        competitors=competitors,
        moat=moat,
        payer_mix_region=payer_mix,
        market_trends=trends,
    )
