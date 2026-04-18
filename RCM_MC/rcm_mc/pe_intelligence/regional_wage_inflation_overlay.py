"""Regional wage inflation overlay — labor cost sensitivity by market.

Existing cascades assume one wage-inflation rate. A partner knows
the rate is sharply regional: NYC / SF / LA / Boston / Seattle
clinicians command structurally higher wages AND face structurally
faster wage inflation than rural / tier-3 markets. A $50M EBITDA
asset split 60/40 coastal/non-coastal books a very different
labor-cost trajectory than the same asset in Tennessee.

This module takes a site-level footprint and applies regional
wage-inflation projections to compute the 3-year labor-cost drag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Partner-approximated annual clinical wage inflation 2026-2028 by
# market tier. High-cost coastal markets run structurally hotter.
REGION_WAGE_INFLATION = {
    "coastal_tier1": 0.055,     # NYC, SF, LA, Boston, Seattle, DC
    "coastal_tier2": 0.045,     # Miami, San Diego, Philadelphia
    "major_inland": 0.040,      # Chicago, Denver, Atlanta, Dallas
    "mid_market": 0.035,        # Raleigh, Nashville, Minneapolis
    "rural_tier3": 0.028,       # Rural, non-metro
}

REGION_BASE_PREMIUM = {
    # Premium on national-average base wage per clinical FTE.
    "coastal_tier1": 1.30,
    "coastal_tier2": 1.15,
    "major_inland": 1.05,
    "mid_market": 0.95,
    "rural_tier3": 0.85,
}


@dataclass
class SiteFootprint:
    site_name: str
    region_tier: str             # one of REGION keys
    clinical_fte: int
    avg_wage_k: float = 85.0     # W-2 base


@dataclass
class RegionalOverlayInputs:
    deal_name: str = "Deal"
    base_ebitda_m: float = 0.0
    sites: List[SiteFootprint] = field(default_factory=list)
    contribution_margin_on_labor: float = 0.45
    modeled_wage_inflation_pct: float = 0.03   # single rate in the model


@dataclass
class RegionalOverlayReport:
    total_clinical_wage_base_m: float
    weighted_wage_inflation_pct: float
    modeled_wage_inflation_pct: float
    delta_inflation_pct: float
    three_year_ebitda_drag_m: float
    by_region_breakdown: Dict[str, Dict[str, float]]
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_clinical_wage_base_m":
                self.total_clinical_wage_base_m,
            "weighted_wage_inflation_pct":
                self.weighted_wage_inflation_pct,
            "modeled_wage_inflation_pct":
                self.modeled_wage_inflation_pct,
            "delta_inflation_pct": self.delta_inflation_pct,
            "three_year_ebitda_drag_m":
                self.three_year_ebitda_drag_m,
            "by_region_breakdown":
                {k: dict(v) for k, v in self.by_region_breakdown.items()},
            "partner_note": self.partner_note,
        }


def overlay_wage_inflation(
    inputs: RegionalOverlayInputs,
) -> RegionalOverlayReport:
    # Build per-site wage base (regionally-adjusted) and weighted
    # inflation.
    total_wage_m = 0.0
    weighted_num = 0.0
    by_region: Dict[str, Dict[str, float]] = {}

    for s in inputs.sites:
        region = s.region_tier
        premium = REGION_BASE_PREMIUM.get(region, 1.0)
        inflation = REGION_WAGE_INFLATION.get(region, 0.035)
        site_wage_m = s.clinical_fte * s.avg_wage_k * premium / 1000.0
        total_wage_m += site_wage_m
        weighted_num += site_wage_m * inflation
        agg = by_region.setdefault(region, {
            "fte": 0.0, "wage_base_m": 0.0,
            "annual_inflation_pct": inflation,
        })
        agg["fte"] += s.clinical_fte
        agg["wage_base_m"] += site_wage_m

    weighted_inflation = (weighted_num / total_wage_m
                          if total_wage_m > 0 else 0.0)
    delta = weighted_inflation - inputs.modeled_wage_inflation_pct

    # 3-year EBITDA drag from under-modeling. Compound the gap.
    drag_3yr = 0.0
    if delta > 0 and total_wage_m > 0:
        running_wage = total_wage_m
        for _ in range(3):
            running_wage *= (1 + weighted_inflation)
            # Difference from the model's expected wage level.
            pass
        actual_3yr = total_wage_m * ((1 + weighted_inflation) ** 3)
        modeled_3yr = total_wage_m * (
            (1 + inputs.modeled_wage_inflation_pct) ** 3)
        extra_wage = actual_3yr - modeled_3yr
        drag_3yr = extra_wage * inputs.contribution_margin_on_labor

    if drag_3yr >= inputs.base_ebitda_m * 0.10:
        note = (f"Regional wage overlay reveals "
                f"${drag_3yr:,.1f}M of 3-year EBITDA drag "
                f"({delta*100:.1f}pp under-modeled). This is a "
                "structural underwrite error — fix the model before "
                "IC.")
    elif drag_3yr >= inputs.base_ebitda_m * 0.03:
        note = (f"Model under-states wage inflation by "
                f"{delta*100:.1f}pp; 3-year drag ~"
                f"${drag_3yr:,.1f}M. Material but manageable "
                "— rebuild labor line with regional split.")
    elif delta > 0:
        note = (f"Model under-states wage inflation by "
                f"{delta*100:.2f}pp; immaterial at 3-year horizon "
                f"(~${drag_3yr:,.1f}M). Note in underwrite.")
    elif delta < 0:
        note = (f"Model is conservative — actual weighted inflation "
                f"is {weighted_inflation*100:.1f}% vs modeled "
                f"{inputs.modeled_wage_inflation_pct*100:.1f}%. "
                "No adjustment needed.")
    else:
        note = ("Regional overlay matches the modeled rate — no "
                "adjustment.")

    return RegionalOverlayReport(
        total_clinical_wage_base_m=round(total_wage_m, 2),
        weighted_wage_inflation_pct=round(weighted_inflation, 4),
        modeled_wage_inflation_pct=round(
            inputs.modeled_wage_inflation_pct, 4),
        delta_inflation_pct=round(delta, 4),
        three_year_ebitda_drag_m=round(drag_3yr, 2),
        by_region_breakdown=by_region,
        partner_note=note,
    )


def render_overlay_markdown(r: RegionalOverlayReport) -> str:
    lines = [
        "# Regional wage inflation overlay",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total clinical wage base: "
        f"${r.total_clinical_wage_base_m:,.1f}M",
        f"- Weighted regional inflation: "
        f"{r.weighted_wage_inflation_pct*100:.2f}%",
        f"- Modeled inflation: "
        f"{r.modeled_wage_inflation_pct*100:.2f}%",
        f"- Delta vs model: "
        f"{r.delta_inflation_pct*100:+.2f}pp",
        f"- 3-year EBITDA drag: "
        f"${r.three_year_ebitda_drag_m:,.2f}M",
        "",
        "| Region | FTE | Wage base $M | Annual inflation |",
        "|---|---:|---:|---:|",
    ]
    for region, agg in r.by_region_breakdown.items():
        lines.append(
            f"| {region} | {int(agg['fte'])} | "
            f"${agg['wage_base_m']:,.2f}M | "
            f"{agg['annual_inflation_pct']*100:.1f}% |"
        )
    return "\n".join(lines)
