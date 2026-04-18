"""EHR transition risk — migration cost + productivity dip + revenue cliff.

Partner statement: "EHR migrations are different
animal from RCM switching. Epic from Cerner is 18-24
months, $10-30M in capex, and physicians fight it
every step. There's a 6-12 month productivity dip of
10-25% post-go-live. The revenue cliff is real; the
model's 'savings' don't show up until year 2."

Distinct from:
- `rcm_vendor_switching_cost_assessor` — RCM
  platform transition.
- `technology_debt_assessor` — general tech debt.

This module sizes the **EHR migration cost + revenue
dip**:
- one-time capex (hardware + license + config)
- productivity dip magnitude and duration
- revenue dip during transition
- payback years based on post-migration savings
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Transition profiles by source → destination pair.
# (months, capex_band, prod_dip_pct, prod_dip_months)
TRANSITION_PROFILES: Dict[str, Dict[str, Any]] = {
    "cerner_to_epic": {
        "months": 24,
        "capex_band_usd_per_bed": 70000,
        "prod_dip_pct": 0.18,
        "prod_dip_months": 9,
        "note": (
            "Epic migration from Cerner: 18-24 months, "
            "6-9 month productivity dip 15-25%. Physician "
            "adoption is rate-limiter."
        ),
    },
    "meditech_to_epic": {
        "months": 22,
        "capex_band_usd_per_bed": 80000,
        "prod_dip_pct": 0.20,
        "prod_dip_months": 10,
        "note": (
            "MEDITECH → Epic: longer migration + bigger "
            "physician-adoption dip; rural facility "
            "tradition makes Epic a culture shift."
        ),
    },
    "legacy_to_athena": {
        "months": 9,
        "capex_band_usd_per_bed": 15000,
        "prod_dip_pct": 0.08,
        "prod_dip_months": 4,
        "note": (
            "Athena migration for ambulatory: faster "
            "cloud deployment; smaller productivity hit; "
            "fits medical groups not hospitals."
        ),
    },
    "legacy_to_nextgen": {
        "months": 10,
        "capex_band_usd_per_bed": 12000,
        "prod_dip_pct": 0.10,
        "prod_dip_months": 5,
        "note": (
            "NextGen / eClinicalWorks: ambulatory-tier "
            "platforms; lighter but specialty-modules "
            "vary widely."
        ),
    },
    "epic_version_upgrade": {
        "months": 6,
        "capex_band_usd_per_bed": 5000,
        "prod_dip_pct": 0.05,
        "prod_dip_months": 2,
        "note": (
            "Epic in-system upgrade: minimal disruption "
            "but still a formal project."
        ),
    },
}


@dataclass
class EHRTransitionInputs:
    transition_type: str = "cerner_to_epic"
    beds_or_providers: int = 200
    """Beds for hospital, providers for ambulatory."""
    annual_revenue_m: float = 300.0
    post_transition_annual_savings_m: float = 3.0


@dataclass
class EHRTransitionReport:
    transition_type: str = ""
    in_catalog: bool = False
    migration_months: int = 0
    capex_m: float = 0.0
    productivity_dip_pct: float = 0.0
    productivity_dip_months: int = 0
    revenue_dip_during_transition_m: float = 0.0
    total_all_in_cost_m: float = 0.0
    payback_years: Optional[float] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_type": self.transition_type,
            "in_catalog": self.in_catalog,
            "migration_months":
                self.migration_months,
            "capex_m": self.capex_m,
            "productivity_dip_pct":
                self.productivity_dip_pct,
            "productivity_dip_months":
                self.productivity_dip_months,
            "revenue_dip_during_transition_m":
                self.revenue_dip_during_transition_m,
            "total_all_in_cost_m":
                self.total_all_in_cost_m,
            "payback_years": self.payback_years,
            "partner_note": self.partner_note,
        }


def assess_ehr_transition(
    inputs: EHRTransitionInputs,
) -> EHRTransitionReport:
    profile = TRANSITION_PROFILES.get(
        inputs.transition_type)
    if profile is None:
        return EHRTransitionReport(
            transition_type=inputs.transition_type,
            in_catalog=False,
            partner_note=(
                f"Transition type '{inputs.transition_type}' "
                "not in catalog."
            ),
        )

    capex = (
        inputs.beds_or_providers *
        profile["capex_band_usd_per_bed"] / 1_000_000
    )
    revenue_during_dip = (
        inputs.annual_revenue_m *
        (profile["prod_dip_months"] / 12.0) *
        profile["prod_dip_pct"]
    )
    total_cost = capex + revenue_during_dip
    annual_savings = inputs.post_transition_annual_savings_m
    if annual_savings > 0:
        payback = total_cost / annual_savings
    else:
        payback = None

    if profile["prod_dip_pct"] >= 0.15:
        note = (
            f"Heavy migration: "
            f"{profile['prod_dip_pct']:.0%} productivity "
            f"dip over {profile['prod_dip_months']} mo; "
            f"${revenue_during_dip:.1f}M revenue cliff. "
            "Model's year-1 FCF must absorb this; price "
            "migration into entry multiple."
        )
    elif profile["prod_dip_pct"] >= 0.08:
        note = (
            f"Moderate migration: "
            f"{profile['prod_dip_pct']:.0%} dip over "
            f"{profile['prod_dip_months']} mo. "
            f"${revenue_during_dip:.1f}M revenue drag "
            "but manageable."
        )
    else:
        note = (
            f"Light migration: "
            f"{profile['prod_dip_pct']:.0%} dip. "
            "Standard project cadence."
        )

    if payback is not None and payback > 5.0:
        note += (
            f" Payback {payback:.1f} years — verify "
            "savings assumption. EHR migrations "
            "rarely pay back within a 5-year hold."
        )

    return EHRTransitionReport(
        transition_type=inputs.transition_type,
        in_catalog=True,
        migration_months=profile["months"],
        capex_m=round(capex, 2),
        productivity_dip_pct=round(
            profile["prod_dip_pct"], 3),
        productivity_dip_months=profile["prod_dip_months"],
        revenue_dip_during_transition_m=round(
            revenue_during_dip, 2),
        total_all_in_cost_m=round(total_cost, 2),
        payback_years=(
            round(payback, 2) if payback else None),
        partner_note=note,
    )


def render_ehr_transition_markdown(
    r: EHRTransitionReport,
) -> str:
    if not r.in_catalog:
        return (
            "# EHR transition risk\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# EHR transition risk",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Transition: {r.transition_type}",
        f"- Migration months: {r.migration_months}",
        f"- Capex: ${r.capex_m:.2f}M",
        f"- Productivity dip: "
        f"{r.productivity_dip_pct:.0%} over "
        f"{r.productivity_dip_months} months",
        f"- Revenue dip: "
        f"${r.revenue_dip_during_transition_m:.2f}M",
        f"- Total all-in cost: ${r.total_all_in_cost_m:.2f}M",
        f"- Payback: "
        f"{r.payback_years if r.payback_years else 'n/a'} years",
    ]
    return "\n".join(lines)
