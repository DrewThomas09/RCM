"""Patient acquisition cost benchmark — CAC vs. specialty norm with LTV payback.

Partner statement: "Healthcare growth stories often
don't price the CAC. The deck says '+12% new
patients per year' but doesn't show marketing /
referral-management / admin cost per new patient.
Per specialty there's a typical CAC and a typical
LTV. If CAC is 2x the specialty norm, either
marketing is inefficient or the market is saturated.
Either way, the growth story is more expensive than
it looks."

Distinct from:
- `physician_specialty_economic_profiler` — per-
  specialty economic shape.
- `growth_algorithm_diagnostic` — growth source.
- `pricing_power_diagnostic` — pricing-side.

This module benchmarks observed CAC against
specialty norm and computes LTV payback.

### Per-specialty CAC / LTV (illustrative norms)

CAC = marketing + sales + admin intake per new
patient.
LTV = annual revenue × contribution margin × tenure
years.

### Output

- observed CAC vs. specialty norm (× multiple)
- LTV
- LTV/CAC ratio
- payback period in months
- verdict: efficient / acceptable / expensive /
  unsustainable
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# Per-specialty CAC and LTV norms.
# (cac_usd, annual_rev_usd, contribution_margin_pct,
#  tenure_years)
SPECIALTY_CAC_NORMS: Dict[str, Dict[str, float]] = {
    "orthopedic_surgery": {
        "cac_usd": 350.0,
        "annual_revenue_usd": 8000.0,
        "contribution_margin_pct": 0.45,
        "tenure_years": 2.5,
    },
    "gastroenterology": {
        "cac_usd": 250.0,
        "annual_revenue_usd": 4500.0,
        "contribution_margin_pct": 0.42,
        "tenure_years": 4.0,
    },
    "dermatology": {
        "cac_usd": 400.0,
        "annual_revenue_usd": 1800.0,
        "contribution_margin_pct": 0.50,
        "tenure_years": 3.0,
    },
    "cardiology": {
        "cac_usd": 200.0,
        "annual_revenue_usd": 6500.0,
        "contribution_margin_pct": 0.40,
        "tenure_years": 5.0,
    },
    "ophthalmology": {
        "cac_usd": 300.0,
        "annual_revenue_usd": 3500.0,
        "contribution_margin_pct": 0.45,
        "tenure_years": 4.0,
    },
    "dental": {
        "cac_usd": 350.0,
        "annual_revenue_usd": 1200.0,
        "contribution_margin_pct": 0.30,
        "tenure_years": 5.0,
    },
    "behavioral": {
        "cac_usd": 500.0,
        "annual_revenue_usd": 2400.0,
        "contribution_margin_pct": 0.25,
        "tenure_years": 1.5,
    },
    "primary_care": {
        "cac_usd": 180.0,
        "annual_revenue_usd": 1500.0,
        "contribution_margin_pct": 0.25,
        "tenure_years": 6.0,
    },
}


@dataclass
class PatientCACInputs:
    specialty: str = "dermatology"
    observed_cac_usd: float = 0.0
    """If 0, uses specialty norm as observed."""
    observed_annual_revenue_per_patient_usd: float = 0.0
    """If 0, uses specialty norm."""
    observed_contribution_margin_pct: float = 0.0
    """If 0, uses specialty norm."""
    observed_tenure_years: float = 0.0
    """If 0, uses specialty norm."""


@dataclass
class PatientCACReport:
    specialty: str = ""
    in_catalog: bool = False
    observed_cac_usd: float = 0.0
    norm_cac_usd: float = 0.0
    cac_multiple_of_norm: float = 0.0
    ltv_usd: float = 0.0
    ltv_cac_ratio: float = 0.0
    payback_months: float = 0.0
    verdict: str = "acceptable"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialty": self.specialty,
            "in_catalog": self.in_catalog,
            "observed_cac_usd": self.observed_cac_usd,
            "norm_cac_usd": self.norm_cac_usd,
            "cac_multiple_of_norm":
                self.cac_multiple_of_norm,
            "ltv_usd": self.ltv_usd,
            "ltv_cac_ratio": self.ltv_cac_ratio,
            "payback_months": self.payback_months,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def benchmark_patient_cac(
    inputs: PatientCACInputs,
) -> PatientCACReport:
    norm = SPECIALTY_CAC_NORMS.get(inputs.specialty)
    if norm is None:
        return PatientCACReport(
            specialty=inputs.specialty,
            in_catalog=False,
            partner_note=(
                f"Specialty '{inputs.specialty}' not in "
                "CAC catalog — partner should research "
                "specialty-specific CAC norm."
            ),
        )

    observed_cac = (
        inputs.observed_cac_usd
        if inputs.observed_cac_usd > 0
        else norm["cac_usd"]
    )
    annual_rev = (
        inputs.observed_annual_revenue_per_patient_usd
        if inputs.observed_annual_revenue_per_patient_usd > 0
        else norm["annual_revenue_usd"]
    )
    margin = (
        inputs.observed_contribution_margin_pct
        if inputs.observed_contribution_margin_pct > 0
        else norm["contribution_margin_pct"]
    )
    tenure = (
        inputs.observed_tenure_years
        if inputs.observed_tenure_years > 0
        else norm["tenure_years"]
    )

    ltv = annual_rev * margin * tenure
    ltv_cac = ltv / max(1.0, observed_cac)
    cac_multiple = observed_cac / max(1.0, norm["cac_usd"])
    monthly_contribution = annual_rev * margin / 12.0
    payback = (
        observed_cac / max(0.01, monthly_contribution)
    )

    if cac_multiple <= 0.8:
        verdict = "efficient"
        note = (
            f"CAC {cac_multiple:.2f}× specialty norm. "
            "Marketing / intake is efficient — protect "
            "the channel; CAC goes up when volume "
            "chases."
        )
    elif cac_multiple <= 1.2:
        verdict = "acceptable"
        note = (
            f"CAC {cac_multiple:.2f}× specialty norm — "
            "in-band. Growth math holds against typical "
            "specialty economics."
        )
    elif cac_multiple <= 2.0:
        verdict = "expensive"
        note = (
            f"CAC {cac_multiple:.2f}× specialty norm — "
            "expensive. Either marketing is inefficient "
            "or the market is saturated. Price the "
            "growth cost explicitly."
        )
    else:
        verdict = "unsustainable"
        note = (
            f"CAC {cac_multiple:.2f}× specialty norm. "
            "At this spend, new-patient growth has "
            "negative unit economics; either the "
            "tenure assumption is wrong or marketing "
            "is burning cash."
        )

    if ltv_cac < 3.0:
        note += (
            f" LTV/CAC {ltv_cac:.1f} is below healthcare "
            "payback threshold (3×); scrutinize tenure "
            "and contribution margin assumptions."
        )

    return PatientCACReport(
        specialty=inputs.specialty,
        in_catalog=True,
        observed_cac_usd=round(observed_cac, 2),
        norm_cac_usd=round(norm["cac_usd"], 2),
        cac_multiple_of_norm=round(cac_multiple, 3),
        ltv_usd=round(ltv, 2),
        ltv_cac_ratio=round(ltv_cac, 2),
        payback_months=round(payback, 1),
        verdict=verdict,
        partner_note=note,
    )


def render_patient_cac_markdown(
    r: PatientCACReport,
) -> str:
    if not r.in_catalog:
        return (
            "# Patient CAC benchmark\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# Patient CAC benchmark",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Specialty: {r.specialty}",
        f"- Observed CAC: ${r.observed_cac_usd:,.0f}",
        f"- Norm CAC: ${r.norm_cac_usd:,.0f}",
        f"- CAC multiple of norm: "
        f"{r.cac_multiple_of_norm:.2f}×",
        f"- LTV: ${r.ltv_usd:,.0f}",
        f"- LTV/CAC: {r.ltv_cac_ratio:.1f}",
        f"- Payback: {r.payback_months:.1f} months",
    ]
    return "\n".join(lines)
