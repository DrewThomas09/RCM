"""Labor shortage cascade — nurse turnover propagates.

Third canonical healthcare cascade (after RCM and payer-mix). When
clinician turnover rises, the downstream effects are:

1. **Turnover delta** — departures rise in pp from baseline.
2. **Agency / contingent premium** — backfill uses agency staff
   at ~70% premium over W-2 hourly. Sudden spikes drive the
   premium higher.
3. **Margin compression** — contingent cost × hours × span.
4. **Quality / volume impact** — high-turnover units book fewer
   cases and score worse on quality. Revenue dips.
5. **Covenant pressure** — EBITDA dip + rising interest (if
   floating) closes covenant headroom.

Partner reflex: agency spend is a canary. If it's trending up in
Q3 2025, the 2026 EBITDA model needs a haircut. The cascade
makes the math explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LaborCascadeInputs:
    baseline_turnover_pct: float = 0.15
    current_turnover_pct: float = 0.22
    clinician_headcount: int = 500
    avg_annual_wage_k: float = 85.0        # W-2 baseline
    agency_premium_pct: float = 0.70       # agency cost over W-2
    agency_current_share: float = 0.05     # % hours staffed by agency
    agency_peak_share: float = 0.15        # projected peak
    contribution_margin_labor: float = 0.45
    quality_revenue_elasticity: float = 0.05
    current_ebitda_m: float = 50.0
    current_covenant_coverage: float = 2.5
    debt_m: float = 300.0
    interest_rate: float = 0.095


@dataclass
class LaborCascadeStep:
    step: int
    name: str
    description: str
    value: float
    unit: str
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "name": self.name,
            "description": self.description,
            "value": self.value, "unit": self.unit,
            "partner_note": self.partner_note,
        }


@dataclass
class LaborCascadeReport:
    steps: List[LaborCascadeStep] = field(default_factory=list)
    ebitda_hit_m: float = 0.0
    post_shock_covenant_coverage: float = 0.0
    covenant_breach: bool = False
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "ebitda_hit_m": self.ebitda_hit_m,
            "post_shock_covenant_coverage": self.post_shock_covenant_coverage,
            "covenant_breach": self.covenant_breach,
            "partner_note": self.partner_note,
        }


def trace_labor_cascade(
    inputs: LaborCascadeInputs,
) -> LaborCascadeReport:
    steps: List[LaborCascadeStep] = []

    # Step 1: Turnover delta.
    delta_turnover = inputs.current_turnover_pct - inputs.baseline_turnover_pct
    steps.append(LaborCascadeStep(
        step=1, name="turnover_delta",
        description=(f"Turnover {inputs.baseline_turnover_pct*100:.0f}% "
                     f"→ {inputs.current_turnover_pct*100:.0f}%"),
        value=round(delta_turnover * 100, 2), unit="pp",
        partner_note=(
            f"{delta_turnover*100:.1f}pp above baseline. "
            f"{int(inputs.clinician_headcount * delta_turnover)} extra "
            "departures annually. Recruiting cycle is 90 days; gap is "
            "filled by agency."),
    ))

    # Step 2: Agency premium.
    agency_share_delta = (inputs.agency_peak_share
                           - inputs.agency_current_share)
    # $ impact: headcount × annual wage × agency_premium × hours share.
    w2_cost_m = (inputs.clinician_headcount
                  * inputs.avg_annual_wage_k / 1000.0)
    agency_incremental_m = (w2_cost_m * inputs.agency_premium_pct
                              * agency_share_delta)
    steps.append(LaborCascadeStep(
        step=2, name="agency_premium_cost",
        description=(f"Agency share "
                     f"{inputs.agency_current_share*100:.1f}% → "
                     f"{inputs.agency_peak_share*100:.1f}% at "
                     f"{inputs.agency_premium_pct*100:.0f}% premium"),
        value=round(agency_incremental_m, 2), unit="$M",
        partner_note=(
            f"${agency_incremental_m:,.1f}M incremental agency cost. "
            "Watch: agency premiums compounded in 2022; current "
            "book already reflects partial relief. Base case assumes "
            "premium holds — bear case assumes it re-spikes."),
    ))

    # Step 3: Margin compression.
    margin_hit_m = agency_incremental_m  # pass-through to EBITDA
    steps.append(LaborCascadeStep(
        step=3, name="margin_compression",
        description="EBITDA hit from incremental labor cost",
        value=round(-margin_hit_m, 2), unit="$M",
        partner_note=(
            "Labor cost is 100% pass-through to EBITDA — no offsetting "
            "lever works in < 12 months."),
    ))

    # Step 4: Quality / volume impact.
    quality_rev_hit = (inputs.current_ebitda_m
                        * inputs.quality_revenue_elasticity
                        * (delta_turnover / 0.05))  # scale
    steps.append(LaborCascadeStep(
        step=4, name="quality_volume_impact",
        description=("Volume / quality revenue impact from "
                      "unit-level staffing gaps"),
        value=round(-quality_rev_hit, 2), unit="$M",
        partner_note=(
            f"${quality_rev_hit:,.1f}M additional EBITDA hit from "
            "quality-driven volume dip. High-turnover units reduce "
            "throughput 3-8%."),
    ))

    total_ebitda_hit = margin_hit_m + quality_rev_hit
    stressed_ebitda = inputs.current_ebitda_m - total_ebitda_hit
    stressed_interest = inputs.debt_m * inputs.interest_rate
    post_cov = (stressed_ebitda / stressed_interest
                if stressed_interest > 0 else 99.0)
    covenant_breach = post_cov < inputs.current_covenant_coverage * 0.80

    # Step 5: Covenant pressure.
    steps.append(LaborCascadeStep(
        step=5, name="covenant_pressure",
        description=(f"Post-shock coverage {post_cov:.2f}x vs "
                     f"current {inputs.current_covenant_coverage:.2f}x"),
        value=round(post_cov, 2), unit="x",
        partner_note=(
            "Covenant coverage tightens; if already close to minimum, "
            "this could trip mid-hold. Floating debt compounds the "
            "pressure."
            + (" **BREACH LIKELY** — escalate." if covenant_breach else "")),
    ))

    if covenant_breach:
        note = (f"Labor cascade is a covenant breach scenario. EBITDA "
                f"hit ${total_ebitda_hit:,.1f}M; coverage drops to "
                f"{post_cov:.2f}x. Not tolerable given base posture.")
    elif total_ebitda_hit / max(0.01, inputs.current_ebitda_m) >= 0.15:
        note = (f"Labor cascade is material (${total_ebitda_hit:,.1f}M, "
                f"{total_ebitda_hit/inputs.current_ebitda_m*100:.0f}% "
                "of base EBITDA). Focus diligence on retention plan + "
                "agency contract terms.")
    elif total_ebitda_hit > 0:
        note = (f"Labor cascade is manageable (${total_ebitda_hit:,.1f}M "
                "EBITDA hit). Monitor agency trends quarterly.")
    else:
        note = ("Labor cascade is immaterial under current assumptions.")

    return LaborCascadeReport(
        steps=steps,
        ebitda_hit_m=round(total_ebitda_hit, 2),
        post_shock_covenant_coverage=round(post_cov, 2),
        covenant_breach=covenant_breach,
        partner_note=note,
    )


def render_labor_cascade_markdown(r: LaborCascadeReport) -> str:
    lines = [
        "# Labor shortage cascade",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total EBITDA hit: ${r.ebitda_hit_m:,.2f}M",
        f"- Post-shock coverage: {r.post_shock_covenant_coverage:.2f}x",
        f"- Covenant breach: {'**YES**' if r.covenant_breach else 'no'}",
        "",
    ]
    for s in r.steps:
        lines.append(f"## Step {s.step}: {s.name}")
        lines.append(f"- **{s.description}**: {s.value}{s.unit}")
        lines.append(f"- {s.partner_note}")
        lines.append("")
    return "\n".join(lines)
