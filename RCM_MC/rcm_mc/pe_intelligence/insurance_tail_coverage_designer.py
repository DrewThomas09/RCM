"""Insurance tail coverage designer — close-date package.

Partner statement: "Insurance tail coverage is one of
those line items that gets skipped in diligence and
then costs you a fortune when a claim lands 8 months
post-close. I want D&O, cyber, pro-liability, and EPL
tail math done before we sign."

Distinct from `insurance_diligence` (reviews existing
policies + gaps). This module **designs** the close-date
tail / run-off coverage that protects against claims
arising from pre-close conduct.

### 6 tail coverage types

1. **D&O run-off** — 6 years standard; covers pre-close
   director / officer liability.
2. **Cyber tail** — 3 years (HIPAA breach window + tail).
3. **Professional liability tail** — 7+ years (med-mal
   statute of limitations).
4. **EPL run-off** — 3 years (employment claims).
5. **Environmental tail** — 5 years (if physical sites).
6. **Representations & warranties** — 6 years for
   fundamental reps, 18-36 mo for standard.

Tail premiums typically 150-300% of expiring annual
premium. Partner sets coverage limits at levels that
match indemnity caps + known exposures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TailCoverage:
    policy: str
    tail_years: int
    recommended_limit_m: float
    premium_multiplier: float
    estimated_premium_m: float
    partner_commentary: str


@dataclass
class InsuranceTailInputs:
    ev_m: float
    has_physical_real_estate: bool = True
    asset_type_is_provider: bool = True
    prior_cyber_incident: bool = False
    material_medmal_exposure: bool = False
    material_environmental_exposure: bool = False
    expiring_annual_premium_total_m: float = 0.0


@dataclass
class InsuranceTailReport:
    coverages: List[TailCoverage] = field(default_factory=list)
    total_estimated_premium_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverages": [
                {"policy": c.policy,
                 "tail_years": c.tail_years,
                 "recommended_limit_m": c.recommended_limit_m,
                 "premium_multiplier": c.premium_multiplier,
                 "estimated_premium_m": c.estimated_premium_m,
                 "partner_commentary": c.partner_commentary}
                for c in self.coverages
            ],
            "total_estimated_premium_m":
                self.total_estimated_premium_m,
            "partner_note": self.partner_note,
        }


def design_insurance_tail_package(
    inputs: InsuranceTailInputs,
) -> InsuranceTailReport:
    coverages: List[TailCoverage] = []

    # 1. D&O run-off: 6 years standard.
    # Partner-typical limit ≈ 5% of EV.
    do_limit = round(inputs.ev_m * 0.05, 1)
    do_annual = (
        inputs.expiring_annual_premium_total_m * 0.30
        if inputs.expiring_annual_premium_total_m > 0
        else 0.15  # default baseline
    )
    do_premium = round(do_annual * 2.50, 2)
    coverages.append(TailCoverage(
        policy="directors_and_officers_runoff",
        tail_years=6,
        recommended_limit_m=do_limit,
        premium_multiplier=2.50,
        estimated_premium_m=do_premium,
        partner_commentary=(
            "6-year D&O run-off; covers pre-close "
            "claims. Limit sized to ~5% of EV."
        ),
    ))

    # 2. Cyber tail: 3 years (material cyber → higher limits).
    cyber_limit = round(
        inputs.ev_m * (0.04 if inputs.prior_cyber_incident
                       else 0.02),
        1,
    )
    cyber_premium_mult = (
        2.00 if inputs.prior_cyber_incident else 1.50
    )
    cyber_annual = (
        inputs.expiring_annual_premium_total_m * 0.15
        if inputs.expiring_annual_premium_total_m > 0
        else 0.08
    )
    cyber_premium = round(cyber_annual * cyber_premium_mult, 2)
    coverages.append(TailCoverage(
        policy="cyber_tail",
        tail_years=3,
        recommended_limit_m=cyber_limit,
        premium_multiplier=cyber_premium_mult,
        estimated_premium_m=cyber_premium,
        partner_commentary=(
            "3-year cyber tail aligns with HIPAA breach "
            "detection + reporting window." +
            (" Elevated limit + multiplier given prior "
             "incident." if inputs.prior_cyber_incident
             else "")
        ),
    ))

    # 3. Professional liability tail: 7 years (provider).
    if inputs.asset_type_is_provider:
        prof_limit = round(
            inputs.ev_m * (0.08 if
                           inputs.material_medmal_exposure
                           else 0.05),
            1,
        )
        prof_mult = (
            3.00 if inputs.material_medmal_exposure else 2.00
        )
        prof_annual = (
            inputs.expiring_annual_premium_total_m * 0.35
            if inputs.expiring_annual_premium_total_m > 0
            else 0.30
        )
        prof_premium = round(prof_annual * prof_mult, 2)
        coverages.append(TailCoverage(
            policy="professional_liability_tail",
            tail_years=7,
            recommended_limit_m=prof_limit,
            premium_multiplier=prof_mult,
            estimated_premium_m=prof_premium,
            partner_commentary=(
                "7-year pro-liability tail; aligns with "
                "med-mal statute of limitations." +
                (" Higher limit reflects material med-"
                 "mal exposure." if
                 inputs.material_medmal_exposure else "")
            ),
        ))

    # 4. EPL run-off: 3 years.
    epl_limit = round(inputs.ev_m * 0.01, 1)
    epl_annual = (
        inputs.expiring_annual_premium_total_m * 0.08
        if inputs.expiring_annual_premium_total_m > 0
        else 0.03
    )
    epl_premium = round(epl_annual * 1.50, 2)
    coverages.append(TailCoverage(
        policy="epl_runoff",
        tail_years=3,
        recommended_limit_m=epl_limit,
        premium_multiplier=1.50,
        estimated_premium_m=epl_premium,
        partner_commentary=(
            "3-year EPL run-off; class-action employment "
            "claims most common in 24-mo window."
        ),
    ))

    # 5. Environmental tail: 5 years (if physical sites).
    if (inputs.has_physical_real_estate
            and inputs.material_environmental_exposure):
        env_limit = round(inputs.ev_m * 0.02, 1)
        env_premium = round(
            (inputs.expiring_annual_premium_total_m * 0.05
             if inputs.expiring_annual_premium_total_m > 0
             else 0.05) * 1.50,
            2,
        )
        coverages.append(TailCoverage(
            policy="environmental_tail",
            tail_years=5,
            recommended_limit_m=env_limit,
            premium_multiplier=1.50,
            estimated_premium_m=env_premium,
            partner_commentary=(
                "5-year environmental tail; Phase 2 ESA "
                "findings indicate exposure."
            ),
        ))

    # 6. R&W — tracked separately; add partner note.
    # (Not a separate tail policy; covered in LOI review.)

    total = round(
        sum(c.estimated_premium_m for c in coverages), 2
    )

    if total >= 5.0:
        note = (
            f"Total tail premium ${total:,.1f}M. Partner: "
            "material close cost; negotiate with seller "
            "for partial cost-sharing or escrow."
        )
    elif total >= 2.0:
        note = (
            f"Total tail premium ${total:,.1f}M. Budget "
            "into close-cost line item; standard for deal "
            "size."
        )
    else:
        note = (
            f"Total tail premium ${total:,.1f}M. Lean; "
            "proceed on standard close-cost basis."
        )

    return InsuranceTailReport(
        coverages=coverages,
        total_estimated_premium_m=total,
        partner_note=note,
    )


def render_insurance_tail_markdown(
    r: InsuranceTailReport,
) -> str:
    lines = [
        "# Insurance tail coverage package",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total estimated premium: "
        f"${r.total_estimated_premium_m:,.1f}M",
        "",
        "| Policy | Tail yrs | Limit | Premium mult | "
        "Est. premium | Partner commentary |",
        "|---|---|---|---|---|---|",
    ]
    for c in r.coverages:
        lines.append(
            f"| {c.policy} | {c.tail_years} | "
            f"${c.recommended_limit_m:,.1f}M | "
            f"{c.premium_multiplier:.2f}x | "
            f"${c.estimated_premium_m:,.2f}M | "
            f"{c.partner_commentary} |"
        )
    return "\n".join(lines)
