"""Denial fix pace — can you actually move the rate that fast?

Partner statement: "Every RCM deck says we can take
the initial-denial rate from 9% to 6% in 12 months.
Five percent of them actually do. The rest find out
that some denial categories drop in 90 days with
front-end eligibility tools, and others — medical-
necessity denials rooted in coding and documentation
— take 18-24 months if they move at all. Don't buy
the 'denials down 300 bps in year one' story without
knowing WHICH denial categories and what the
trajectory is per category. That's the 'we can fix
denials in 12 months' trap."

Distinct from:
- `pe/rcm_ebitda_bridge.py` — 7-lever bridge (outside
  pe_intelligence).
- `cash_conversion_drift_detector` — same-direction
  trend detector.
- `operational_kpi_cascade` — broader KPI linking.

This module decomposes a claimed denial-rate
improvement into **per-category yield timelines** and
checks whether the sum of achievable per-category
improvements clears the headline target by year.

### 8 denial categories with empirical pace bands

Pace = basis-point reduction per **quarter** achievable
given normal operator discipline (not heroics):

| Category | Q1 | Q2 | Q3 | Q4 | Yr 2 total |
|---|---|---|---|---|---|
| eligibility_verification | 30 | 20 | 10 | 10 | 20 |
| prior_authorization | 10 | 25 | 25 | 20 | 25 |
| timely_filing | 25 | 15 | 10 | 5 | 5 |
| duplicate_claim | 20 | 20 | 10 | 5 | 5 |
| coordination_of_benefits | 10 | 15 | 15 | 10 | 10 |
| invalid_format | 40 | 10 | 0 | 0 | 0 |
| medical_necessity | 0 | 5 | 10 | 15 | 50 |
| non_covered_service | 0 | 0 | 5 | 5 | 10 |

Numbers are **per category share of overall claim
volume**. A category at 2% of claim volume improving
100 bps contributes 2bps of headline denial reduction.

### Diligence defensibility tiers

- **defensible** — implied per-category pace is within
  empirical bands for the category mix.
- **stretch** — implied pace requires aggressive
  execution on top-3 categories; achievable with
  named ops partner + IT investment.
- **trap** — implied pace is faster than empirical
  top-decile; "we can fix denials in 12 months" pattern.

### Output

Per-category feasibility flag, implied bps vs.
feasible bps by year, category-specific operator
actions, and the trap verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Empirical achievable bps/qtr for each denial sub-
# category in the first 2 years, per % of claim volume
# in that category. Values represent bps of
# within-category denial-rate reduction (not headline).
CATEGORY_PACE: Dict[str, Dict[str, float]] = {
    "eligibility_verification": {
        "q1": 30, "q2": 20, "q3": 10, "q4": 10,
        "yr2_total": 20,
        "action": (
            "front-end eligibility & benefits "
            "verification automation; real-time 270/271"
        ),
    },
    "prior_authorization": {
        "q1": 10, "q2": 25, "q3": 25, "q4": 20,
        "yr2_total": 25,
        "action": (
            "centralized auth unit + payer-specific "
            "guidelines repository; peer-to-peer "
            "escalation protocol"
        ),
    },
    "timely_filing": {
        "q1": 25, "q2": 15, "q3": 10, "q4": 5,
        "yr2_total": 5,
        "action": (
            "daily A/R hold alerts + aged-over-60 "
            "sweep; per-payer filing deadline calendar"
        ),
    },
    "duplicate_claim": {
        "q1": 20, "q2": 20, "q3": 10, "q4": 5,
        "yr2_total": 5,
        "action": (
            "clearinghouse dedup rules + edit-before-"
            "send discipline"
        ),
    },
    "coordination_of_benefits": {
        "q1": 10, "q2": 15, "q3": 15, "q4": 10,
        "yr2_total": 10,
        "action": (
            "COB discovery at registration + payer "
            "portal validation"
        ),
    },
    "invalid_format": {
        "q1": 40, "q2": 10, "q3": 0, "q4": 0,
        "yr2_total": 0,
        "action": (
            "claim-scrubber ruleset refresh; 837 "
            "validation at submission"
        ),
    },
    "medical_necessity": {
        "q1": 0, "q2": 5, "q3": 10, "q4": 15,
        "yr2_total": 50,
        "action": (
            "CDI program + physician education + "
            "payer-specific medical policy library"
        ),
    },
    "non_covered_service": {
        "q1": 0, "q2": 0, "q3": 5, "q4": 5,
        "yr2_total": 10,
        "action": (
            "ABN/waiver workflow discipline + "
            "charge-capture rules"
        ),
    },
}


@dataclass
class DenialFixInputs:
    current_initial_denial_rate_pct: float = 0.095
    target_denial_rate_pct: float = 0.065
    target_years: int = 1
    # share of total claim volume in each category; should sum ~1
    category_mix_pct: Dict[str, float] = field(
        default_factory=lambda: {
            "eligibility_verification": 0.25,
            "prior_authorization": 0.20,
            "timely_filing": 0.08,
            "duplicate_claim": 0.08,
            "coordination_of_benefits": 0.07,
            "invalid_format": 0.07,
            "medical_necessity": 0.20,
            "non_covered_service": 0.05,
        })
    named_ops_partner: bool = False
    it_platform_investment_m: float = 0.0


@dataclass
class CategoryFeasibility:
    category: str
    mix_pct: float
    achievable_yr1_bps: float
    achievable_yr2_bps: float
    operator_action: str


@dataclass
class DenialFixReport:
    implied_total_bps: int = 0
    implied_yr1_bps: int = 0
    achievable_yr1_headline_bps: float = 0.0
    achievable_yr2_headline_bps: float = 0.0
    categories: List[CategoryFeasibility] = field(
        default_factory=list)
    verdict: str = "defensible"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "implied_total_bps": self.implied_total_bps,
            "implied_yr1_bps": self.implied_yr1_bps,
            "achievable_yr1_headline_bps":
                self.achievable_yr1_headline_bps,
            "achievable_yr2_headline_bps":
                self.achievable_yr2_headline_bps,
            "categories": [
                {"category": c.category,
                 "mix_pct": c.mix_pct,
                 "achievable_yr1_bps":
                     c.achievable_yr1_bps,
                 "achievable_yr2_bps":
                     c.achievable_yr2_bps,
                 "operator_action": c.operator_action}
                for c in self.categories
            ],
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def analyze_denial_fix_pace(
    inputs: DenialFixInputs,
) -> DenialFixReport:
    implied_total = int(round(
        (inputs.current_initial_denial_rate_pct -
         inputs.target_denial_rate_pct) * 10000
    ))
    # Implied bps for year 1 specifically (assume
    # linear if target spans multiple years).
    span = max(1, inputs.target_years)
    implied_yr1 = implied_total // span

    achievable_yr1_headline = 0.0
    achievable_yr2_headline = 0.0
    cat_feasibility: List[CategoryFeasibility] = []

    # Apply optional named-ops-partner and IT
    # investment premium: scale yr1 achievable by a
    # small factor (not the easy-win categories, which
    # are already near ceiling).
    yr1_scale = 1.0
    if inputs.named_ops_partner:
        yr1_scale += 0.15
    if inputs.it_platform_investment_m >= 3.0:
        yr1_scale += 0.10

    for cat, mix in inputs.category_mix_pct.items():
        pace = CATEGORY_PACE.get(cat)
        if pace is None:
            continue
        # within-category yr1 bps = q1+q2+q3+q4
        in_cat_yr1_bps = (
            pace["q1"] + pace["q2"] +
            pace["q3"] + pace["q4"]
        )
        in_cat_yr2_bps = pace["yr2_total"]
        # Headline contribution = within-category bps ×
        # mix share.
        headline_yr1 = (
            in_cat_yr1_bps * mix * yr1_scale
        )
        headline_yr2 = (
            in_cat_yr2_bps * mix
        )
        achievable_yr1_headline += headline_yr1
        achievable_yr2_headline += headline_yr2
        cat_feasibility.append(CategoryFeasibility(
            category=cat,
            mix_pct=round(mix, 3),
            achievable_yr1_bps=round(headline_yr1, 2),
            achievable_yr2_bps=round(headline_yr2, 2),
            operator_action=pace["action"],
        ))

    # Verdict: compare implied yr1 vs achievable yr1
    gap_pct = (
        (implied_yr1 - achievable_yr1_headline) /
        max(1.0, implied_yr1)
    )

    if gap_pct <= 0.0:
        verdict = "defensible"
        note = (
            f"Implied Year-1 improvement "
            f"{implied_yr1} bps is within empirical "
            f"achievable "
            f"{achievable_yr1_headline:.0f} bps. "
            "Plan holds at normal execution cadence."
        )
    elif gap_pct <= 0.25:
        verdict = "stretch"
        note = (
            f"Implied Year-1 of {implied_yr1} bps "
            f"needs aggressive execution — "
            f"empirical Year-1 is "
            f"{achievable_yr1_headline:.0f} bps. "
            "Achievable only with named ops partner + "
            "IT platform investment; price the "
            "execution risk."
        )
    else:
        verdict = "trap"
        note = (
            f"Implied Year-1 of {implied_yr1} bps far "
            f"exceeds empirical "
            f"{achievable_yr1_headline:.0f} bps. "
            "This is the 'we can fix denials in 12 "
            "months' trap — medical-necessity and "
            "non-covered-service denials take 18-24 "
            "months if they move at all, and the model "
            "extends their Year-1 trajectory. Re-"
            "underwrite EBITDA without the excess "
            "denial-fix dollars."
        )

    return DenialFixReport(
        implied_total_bps=implied_total,
        implied_yr1_bps=implied_yr1,
        achievable_yr1_headline_bps=round(
            achievable_yr1_headline, 2),
        achievable_yr2_headline_bps=round(
            achievable_yr2_headline, 2),
        categories=cat_feasibility,
        verdict=verdict,
        partner_note=note,
    )


def render_denial_fix_markdown(
    r: DenialFixReport,
) -> str:
    flag = {
        "defensible": "defensible",
        "stretch": "stretch",
        "trap": "⚠ denial-fix trap",
    }.get(r.verdict, r.verdict)
    lines = [
        "# Denial fix pace",
        "",
        f"_**{flag}**_ — {r.partner_note}",
        "",
        f"- Implied total: {r.implied_total_bps} bps",
        f"- Implied Year-1: {r.implied_yr1_bps} bps",
        f"- Achievable Year-1 headline: "
        f"{r.achievable_yr1_headline_bps:.0f} bps",
        f"- Achievable Year-2 headline: "
        f"{r.achievable_yr2_headline_bps:.0f} bps",
        "",
        "| Category | Mix % | Yr1 bps | Yr2 bps | "
        "Operator action |",
        "|---|---|---|---|---|",
    ]
    for c in r.categories:
        lines.append(
            f"| {c.category} | "
            f"{c.mix_pct:.0%} | "
            f"{c.achievable_yr1_bps:.1f} | "
            f"{c.achievable_yr2_bps:.1f} | "
            f"{c.operator_action} |"
        )
    return "\n".join(lines)
