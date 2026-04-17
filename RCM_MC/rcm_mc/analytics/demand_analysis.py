"""Demand analysis: disease density, stickiness, price elasticity, tailwinds.

Combines CMS chronic conditions data with DRG utilization and market
structure to assess demand defensibility for PE hospital diligence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class DemandProfile:
    ccn: str
    hospital_name: str
    county: str
    state: str
    disease_density_index: float
    stickiness_score: float
    price_elasticity: float
    tailwind_score: float
    top_conditions: List[Dict[str, Any]]
    drg_alignment: float
    drg_mix_summary: List[Dict[str, Any]]
    competitor_count: int
    nearest_competitor_miles: float
    stickiness_breakdown: Dict[str, float]
    elasticity_detail: List[Dict[str, Any]]
    tailwind_detail: List[Dict[str, Any]]
    explanations: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "hospital_name": self.hospital_name,
            "county": self.county,
            "state": self.state,
            "disease_density_index": round(self.disease_density_index, 1),
            "stickiness_score": round(self.stickiness_score, 1),
            "price_elasticity": round(self.price_elasticity, 3),
            "tailwind_score": round(self.tailwind_score, 1),
            "top_conditions": self.top_conditions,
            "drg_alignment": round(self.drg_alignment, 2),
            "drg_mix_summary": self.drg_mix_summary,
            "competitor_count": self.competitor_count,
            "stickiness_breakdown": self.stickiness_breakdown,
            "elasticity_detail": self.elasticity_detail,
            "tailwind_detail": self.tailwind_detail,
            "explanations": self.explanations,
        }


def compute_disease_density_index(
    county_prevalence: List[Dict[str, Any]],
) -> Tuple[float, List[Dict[str, Any]]]:
    """Weighted disease density score (0-100).

    Higher = more high-acuity chronic conditions in this county.
    Weights: heart failure 3x, cancer 3x, CKD 2.5x, etc.
    """
    from ..data.drg_weights import CONDITION_ACUITY_WEIGHTS

    if not county_prevalence:
        return 50.0, []

    weighted_sum = 0
    weight_total = 0
    enriched = []

    for cp in county_prevalence:
        cond = cp.get("condition", "")
        pct = float(cp.get("prevalence_pct", 0))
        nat = float(cp.get("national_avg_pct", 0))
        weight = CONDITION_ACUITY_WEIGHTS.get(cond, 1.0)

        weighted_sum += pct * weight
        weight_total += weight

        enriched.append({
            "condition": cond,
            "prevalence_pct": round(pct, 1),
            "national_avg_pct": round(nat, 1),
            "delta_pct": round(pct - nat, 1),
            "acuity_weight": weight,
            "weighted_score": round(pct * weight, 1),
        })

    if weight_total == 0:
        return 50.0, enriched

    raw = weighted_sum / weight_total
    index = min(100, max(0, raw * 2.5))

    enriched.sort(key=lambda x: -x["weighted_score"])
    return round(index, 1), enriched


def compute_stickiness_score(
    chronic_pct: float,
    competitor_count: int,
    high_acuity_drg_pct: float,
) -> Tuple[float, Dict[str, float]]:
    """How captive is the patient population? (0-100)

    Three components:
    1. Condition chronicity (33pts) — % volume from chronic conditions
    2. Geographic monopoly (33pts) — inverse competitor density
    3. Switching cost (34pts) — high-acuity DRG concentration
    """
    # Chronicity: 80%+ chronic = full 33 pts
    chron_score = min(33, chronic_pct / 80 * 33)

    # Monopoly: 0 competitors = 33, 10+ = 0
    mono_score = max(0, 33 - competitor_count * 3.3)

    # Switching cost: high-acuity DRGs are hard to shop for
    switch_score = min(34, high_acuity_drg_pct / 60 * 34)

    total = round(chron_score + mono_score + switch_score, 1)
    breakdown = {
        "chronicity": round(chron_score, 1),
        "geographic_monopoly": round(mono_score, 1),
        "switching_cost": round(switch_score, 1),
    }
    return total, breakdown


def compute_price_elasticity(
    drg_volumes: List[Dict[str, Any]],
    state: str = "",
) -> Tuple[float, List[Dict[str, Any]]]:
    """Estimated price elasticity from DRG payment vs volume variation.

    Returns negative number: -0.1 (very inelastic) to -0.8 (elastic).
    Cross-sectional estimate from payment-to-charge ratio variation.
    """
    from ..data.drg_weights import CHRONIC_STICKY_CONDITIONS, classify_drg

    if not drg_volumes:
        return -0.3, []

    detail = []
    elasticities = []
    weights = []

    for drg in drg_volumes[:20]:
        code = str(drg.get("drg_code", ""))
        vol = float(drg.get("total_discharges", 0))
        charges = float(drg.get("average_covered_charges", 0))
        payments = float(drg.get("average_total_payments", 0))
        condition = classify_drg(code)
        is_sticky = condition in CHRONIC_STICKY_CONDITIONS

        if charges > 0 and payments > 0:
            ratio = payments / charges
            if is_sticky:
                elas = -0.15
            elif ratio > 0.5:
                elas = -0.25
            else:
                elas = -0.45

            elasticities.append(elas)
            weights.append(vol)
            detail.append({
                "drg_code": code,
                "drg_description": drg.get("drg_description", ""),
                "condition": condition,
                "volume": int(vol),
                "elasticity": round(elas, 2),
                "sticky": is_sticky,
            })

    if not elasticities:
        return -0.3, detail

    avg_elas = float(np.average(elasticities, weights=weights))
    detail.sort(key=lambda x: -x["volume"])
    return round(avg_elas, 3), detail[:10]


def compute_tailwind_score(
    county_prevalence: List[Dict[str, Any]],
    state: str = "",
) -> Tuple[float, List[Dict[str, Any]]]:
    """Demand growth outlook (-50 to +50).

    Positive = growing demand (aging population, chronic disease increase).
    Based on county disease burden vs national average.
    """
    from ..data.drg_weights import CONDITION_ACUITY_WEIGHTS

    if not county_prevalence:
        return 0, []

    detail = []
    score = 0

    for cp in county_prevalence:
        cond = cp.get("condition", "")
        delta = float(cp.get("delta_pct", 0))
        weight = CONDITION_ACUITY_WEIGHTS.get(cond, 1.0)

        if delta > 2:
            direction = "tailwind"
            impact = min(5, delta * weight * 0.3)
        elif delta < -2:
            direction = "headwind"
            impact = max(-5, delta * weight * 0.3)
        else:
            direction = "neutral"
            impact = 0

        score += impact
        if abs(delta) > 1:
            detail.append({
                "condition": cond,
                "delta_pct": round(delta, 1),
                "direction": direction,
                "impact": round(impact, 1),
            })

    score = max(-50, min(50, score))
    detail.sort(key=lambda x: -abs(x["impact"]))
    return round(score, 1), detail[:8]


def compute_demand_profile(
    ccn: str,
    store: Any,
) -> DemandProfile:
    """Full demand analysis for a hospital. Orchestrates all computations."""
    from ..data.hcris import _get_latest_per_ccn, load_hcris
    from ..data.disease_density import get_county_prevalence
    from ..data.drg_weights import classify_drg, is_sticky_drg

    # Load hospital data
    hdf = _get_latest_per_ccn()
    match = hdf[hdf["ccn"] == ccn]
    if match.empty:
        return _empty_profile(ccn)

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    county = str(hospital.get("county", ""))
    state = str(hospital.get("state", ""))

    # Get county disease prevalence
    prevalence_records = get_county_prevalence(county, state, store)
    prevalence_dicts = [p.to_dict() if hasattr(p, "to_dict") else p for p in prevalence_records]

    # Disease density
    density_index, top_conditions = compute_disease_density_index(prevalence_dicts)

    # Load DRG data for this hospital
    drg_records = []
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT * FROM hospital_benchmarks WHERE provider_id = ? AND source = 'UTILIZATION'",
                (ccn,),
            ).fetchall()
            if rows:
                for r in rows:
                    drg_records.append(dict(r))
    except Exception:
        pass

    # Compute stickiness
    chronic_count = sum(1 for d in drg_records if is_sticky_drg(str(d.get("metric_key", ""))))
    total_drgs = max(1, len(drg_records))
    chronic_pct = chronic_count / total_drgs * 100

    # Count competitors
    competitors = hdf[(hdf["state"] == state) & (hdf["ccn"] != ccn)]
    if county:
        county_comps = competitors[competitors["county"].str.upper() == county.upper()]
        comp_count = len(county_comps) if len(county_comps) >= 2 else len(competitors.head(20))
    else:
        comp_count = min(20, len(competitors))

    high_acuity_pct = density_index * 0.6

    stickiness, stickiness_breakdown = compute_stickiness_score(
        chronic_pct, comp_count, high_acuity_pct)

    # Price elasticity
    elasticity, elasticity_detail = compute_price_elasticity(drg_records, state)

    # Tailwinds
    tailwind, tailwind_detail = compute_tailwind_score(prevalence_dicts, state)

    # DRG alignment
    drg_conditions = {}
    for d in drg_records:
        cond = classify_drg(str(d.get("metric_key", d.get("drg_code", ""))))
        drg_conditions[cond] = drg_conditions.get(cond, 0) + 1

    disease_conditions = {cp["condition"] for cp in prevalence_dicts if cp.get("delta_pct", 0) > 0}
    drg_condition_set = set(drg_conditions.keys()) - {"Other"}
    alignment = len(disease_conditions & drg_condition_set) / max(1, len(disease_conditions)) if disease_conditions else 0.5

    drg_mix = [{"condition": c, "count": n} for c, n in sorted(drg_conditions.items(), key=lambda x: -x[1])][:8]

    # Explanations
    explanations = {
        "density": (
            f"Disease density index of {density_index:.0f}/100 in {county}, {state}. "
            f"{'High chronic disease burden — strong inpatient demand driver.' if density_index > 65 else 'Moderate disease burden.' if density_index > 45 else 'Lower disease burden — demand may be more elective.'}"
        ),
        "stickiness": (
            f"Stickiness score of {stickiness:.0f}/100. "
            f"{'Highly captive patient population — strong revenue defensibility.' if stickiness > 65 else 'Moderate stickiness.' if stickiness > 45 else 'Patients have alternatives — competitive pressure on pricing.'}"
        ),
        "elasticity": (
            f"Price elasticity of {elasticity:.2f}. "
            f"{'Very inelastic — a 10% rate cut reduces volume only {abs(elasticity)*10:.0f}%.' if abs(elasticity) < 0.2 else 'Moderately inelastic.' if abs(elasticity) < 0.4 else 'Elastic — volume is sensitive to payment rate changes.'}"
        ),
        "tailwind": (
            f"Tailwind score of {tailwind:+.0f}. "
            f"{'Strong demand tailwind from growing chronic disease burden.' if tailwind > 15 else 'Mild tailwind.' if tailwind > 0 else 'Neutral demand outlook.' if tailwind > -10 else 'Headwind — shrinking demand in this market.'}"
        ),
    }

    return DemandProfile(
        ccn=ccn, hospital_name=name, county=county, state=state,
        disease_density_index=density_index, stickiness_score=stickiness,
        price_elasticity=elasticity, tailwind_score=tailwind,
        top_conditions=top_conditions, drg_alignment=alignment,
        drg_mix_summary=drg_mix, competitor_count=comp_count,
        nearest_competitor_miles=0, stickiness_breakdown=stickiness_breakdown,
        elasticity_detail=elasticity_detail, tailwind_detail=tailwind_detail,
        explanations=explanations,
    )


def _empty_profile(ccn: str) -> DemandProfile:
    return DemandProfile(
        ccn=ccn, hospital_name=f"Hospital {ccn}", county="", state="",
        disease_density_index=50, stickiness_score=50,
        price_elasticity=-0.3, tailwind_score=0,
        top_conditions=[], drg_alignment=0.5, drg_mix_summary=[],
        competitor_count=0, nearest_competitor_miles=0,
        stickiness_breakdown={}, elasticity_detail=[], tailwind_detail=[],
        explanations={},
    )
