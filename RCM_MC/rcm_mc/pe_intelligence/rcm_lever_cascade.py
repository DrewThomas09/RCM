"""RCM lever cascade — a denial rate change propagates.

This is the canonical cross-module reasoning the user named:
"a denial rate change has coding implications, which have CMI
implications, which change the Medicare bridge math."

The cascade:

1. **Denial rate ↑** — initial denials rise. Write-off risk rises.
2. **Coding remediation** — CDI / coding-hygiene program triggered.
   CMI usually nudges up (slightly) as coding is tightened; but
   RAC audit exposure rises on the upcoded records.
3. **CMI implications** — if CMI rises, Medicare revenue per
   case rises proportionally. If CMI falls (downcoding from
   overly conservative CDI), Medicare revenue falls.
4. **Medicare bridge** — stressed EBITDA = (cases × CMI × base
   rate × margin). Propagated change vs prior year.
5. **Working capital** — denial increases push DAR, compressing
   cash even if EBITDA holds.

This module accepts a small set of inputs and produces a
cascade: each downstream effect with $ EBITDA + cash impact, plus
a partner-voice narrative connecting the steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CascadeInputs:
    prior_year_denial_rate: float = 0.08
    current_denial_rate: float = 0.10
    medicare_cases_per_year: int = 10000
    medicare_base_rate_per_case_k: float = 8.0    # $8K base rate per case
    current_cmi: float = 1.30
    cdi_program_in_place: bool = False
    expected_cdi_cmi_lift: float = 0.05           # 0.05 points
    contribution_margin: float = 0.45
    days_in_ar: int = 45
    medicare_daily_revenue_m: float = 0.2  # $ per day exposed to DAR


@dataclass
class CascadeStep:
    step: int
    name: str
    delta_description: str
    ebitda_impact_m: float                 # can be negative or positive
    cash_impact_m: float                   # separate from EBITDA
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "name": self.name,
            "delta_description": self.delta_description,
            "ebitda_impact_m": self.ebitda_impact_m,
            "cash_impact_m": self.cash_impact_m,
            "partner_note": self.partner_note,
        }


@dataclass
class CascadeReport:
    steps: List[CascadeStep] = field(default_factory=list)
    total_ebitda_impact_m: float = 0.0
    total_cash_impact_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_ebitda_impact_m": self.total_ebitda_impact_m,
            "total_cash_impact_m": self.total_cash_impact_m,
            "partner_note": self.partner_note,
        }


def trace_cascade(inputs: CascadeInputs) -> CascadeReport:
    steps: List[CascadeStep] = []

    # Step 1: Denial rate delta.
    delta_denials = inputs.current_denial_rate - inputs.prior_year_denial_rate
    # Revenue exposed to denial write-off.
    gross_medicare_rev_m = (
        inputs.medicare_cases_per_year
        * inputs.current_cmi
        * inputs.medicare_base_rate_per_case_k
        / 1000.0  # k → M
    )
    # Assume 40% of denials convert to write-off after appeals.
    write_off_rev_m = delta_denials * gross_medicare_rev_m * 0.40
    step1_ebitda = -write_off_rev_m * inputs.contribution_margin
    step1_cash = -write_off_rev_m
    steps.append(CascadeStep(
        step=1, name="denial_rate_shift",
        delta_description=(
            f"Denial rate {inputs.prior_year_denial_rate*100:.1f}% → "
            f"{inputs.current_denial_rate*100:.1f}% "
            f"({delta_denials*100:+.1f}pp)"),
        ebitda_impact_m=round(step1_ebitda, 2),
        cash_impact_m=round(step1_cash, 2),
        partner_note=(
            f"Every 1pp of denial increase translates to ~"
            f"${gross_medicare_rev_m * 0.01 * 0.40:,.2f}M "
            "of write-off exposure at 40% appeal-conversion. "
            "Not a rounding error."),
    ))

    # Step 2: Coding remediation / CDI effect.
    cmi_lift = inputs.expected_cdi_cmi_lift if inputs.cdi_program_in_place \
        else 0.0
    if cmi_lift > 0:
        # Positive EBITDA — higher CMI means more Medicare revenue
        # per case.
        new_cmi = inputs.current_cmi + cmi_lift
        rev_lift_m = (
            inputs.medicare_cases_per_year
            * cmi_lift * inputs.medicare_base_rate_per_case_k
            / 1000.0
        )
        step2_ebitda = rev_lift_m * inputs.contribution_margin
        step2_cash = rev_lift_m * 0.80  # 80% realized (denials still exist)
        steps.append(CascadeStep(
            step=2, name="coding_remediation",
            delta_description=(
                f"CDI program lifts CMI "
                f"{inputs.current_cmi:.3f} → {new_cmi:.3f}"),
            ebitda_impact_m=round(step2_ebitda, 2),
            cash_impact_m=round(step2_cash, 2),
            partner_note=(
                "CDI lift is real but comes with RAC-audit exposure. "
                "Budget a contingency reserve at 20% of the lift. "
                "Upcoding without clinical documentation is the "
                "21st_century_oncology pattern."),
        ))
    else:
        steps.append(CascadeStep(
            step=2, name="coding_remediation",
            delta_description="No CDI program in place",
            ebitda_impact_m=0.0,
            cash_impact_m=0.0,
            partner_note=(
                "No CDI means denials compound; the lever exists but "
                "is not being pulled. 100-day plan ask."),
        ))

    # Step 3: Medicare bridge math.
    bridge_ebitda = steps[0].ebitda_impact_m + (steps[1].ebitda_impact_m
                                                 if len(steps) > 1 else 0)
    steps.append(CascadeStep(
        step=3, name="medicare_bridge",
        delta_description=(
            f"Net Medicare EBITDA impact: "
            f"${bridge_ebitda:,.2f}M"),
        ebitda_impact_m=0.0,  # already captured in steps 1-2
        cash_impact_m=0.0,
        partner_note=(
            "Denials go straight to the Medicare bridge. The CDI "
            "offset exists only if the program is funded and "
            "staffed — which the packet will tell us."),
    ))

    # Step 4: Working capital effect.
    # Denial increases extend DAR by roughly 5 days per 1pp denial delta.
    extra_dar_days = max(0.0, delta_denials * 100 * 5)
    wc_cash_hit_m = -extra_dar_days * inputs.medicare_daily_revenue_m
    steps.append(CascadeStep(
        step=4, name="working_capital",
        delta_description=(
            f"DAR extension ~{extra_dar_days:.1f} days from denial mix"),
        ebitda_impact_m=0.0,
        cash_impact_m=round(wc_cash_hit_m, 2),
        partner_note=(
            "Denial rise extends DAR 5 days per 1pp. Partner watches "
            "cash, not just EBITDA. Covenant pressure can come from "
            "the cash side even when EBITDA holds."),
    ))

    total_ebitda = sum(s.ebitda_impact_m for s in steps)
    total_cash = sum(s.cash_impact_m for s in steps)

    if total_ebitda < -2.0:
        note = (f"Cascade: ${total_ebitda:,.1f}M EBITDA and "
                f"${total_cash:,.1f}M cash impact. Material — "
                "this is not 'just a denial blip,' it cascades.")
    elif total_ebitda < 0:
        note = (f"Modest cascade (${total_ebitda:,.1f}M EBITDA) but "
                "cash side visible. Watch covenant headroom.")
    elif total_ebitda > 0:
        note = (f"Net positive cascade (${total_ebitda:,.1f}M) — CDI "
                "lift exceeds denial drag. Confirm CDI program is "
                "actually operating, not planned.")
    else:
        note = ("Cascade net-neutral; denial shift absorbed.")

    return CascadeReport(
        steps=steps,
        total_ebitda_impact_m=round(total_ebitda, 2),
        total_cash_impact_m=round(total_cash, 2),
        partner_note=note,
    )


def render_cascade_markdown(r: CascadeReport) -> str:
    lines = [
        "# RCM lever cascade",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total EBITDA impact: ${r.total_ebitda_impact_m:,.2f}M",
        f"- Total cash impact: ${r.total_cash_impact_m:,.2f}M",
        "",
    ]
    for s in r.steps:
        lines.append(f"## Step {s.step}: {s.name}")
        lines.append(f"- **Change:** {s.delta_description}")
        lines.append(f"- EBITDA: ${s.ebitda_impact_m:+,.2f}M  "
                     f"| Cash: ${s.cash_impact_m:+,.2f}M")
        lines.append(f"- **Partner note:** {s.partner_note}")
        lines.append("")
    return "\n".join(lines)
