"""Tax structure trap scanner — red-flag detectors.

Partner statement: "Tax drives after-tax IRR. I don't
need to be a tax lawyer, but I need the top 10 traps
flagged before I sign. Every one of them costs 100-300
bps of IRR if missed."

Distinct from `tax_structuring` (high-level entity-type
+ state-drag + F-reorg math). This module is a **red-
flag scanner** for specific tax traps that partners
check pre-close because missing one compresses after-
tax IRR by 100-300 bps each.

### 10 trap detectors

1. **golden_parachute_280g_exposure** — executives with
   stock-based payouts > 3× base comp, no safe-harbor.
2. **nol_382_limitation** — target has NOLs that limit
   post-close use.
3. **sales_tax_nexus_services** — telehealth / multi-
   state services create nexus in states with gross
   receipts tax.
4. **r_and_d_credit_carryforward_risk** — credit may not
   survive ownership change.
5. **stock_option_acceleration** — unvested options
   accelerate, triggering §83 income.
6. **ubti_exposure_tax_exempt_lps** — operating structure
   generates UBTI for tax-exempt LPs.
7. **cod_income_seller_note** — seller note forgiveness
   or modification triggers cancellation-of-debt income.
8. **state_provider_tax** — CA, NY, OR, TX, etc. provider
   taxes can approach 2-4% of revenue.
9. **section_263a_healthcare_r_and_d** — research-credit
   eligibility lost on ownership change.
10. **unclaimed_hsa_balances** — unclaimed employee HSA
    balances become corporate liability post-close.

### Output

Matched traps with partner commentary + IRR-drag
estimate. Aggregated partner-note escalates by number
and severity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaxTrapFlag:
    name: str
    triggered: bool
    estimated_irr_drag_bps: float
    partner_commentary: str


@dataclass
class TaxTrapInputs:
    # 280G / golden parachute
    executives_with_acceleration_gt_3x_base: int = 0
    golden_parachute_safe_harbor_in_place: bool = False
    # NOL 382
    target_has_material_nols: bool = False
    target_ownership_change: bool = True
    # Sales-tax nexus on services
    telehealth_or_multi_state_services: bool = False
    nexus_states_with_gross_receipts_tax_exposed: bool = False
    # R&D credit carryforward
    r_and_d_credits_carryforward_material: bool = False
    # Stock option acceleration
    unvested_options_accelerating_at_close: bool = False
    # UBTI exposure
    structure_generates_ubti: bool = False
    tax_exempt_lps_in_fund: bool = False
    # COD income from seller note
    seller_note_at_close: bool = False
    seller_note_modification_planned: bool = False
    # State provider tax
    operating_states: List[str] = field(default_factory=list)
    # Section 263(a) R&D credit
    r_and_d_activities_material: bool = False
    # Unclaimed HSA
    employer_sponsored_hsa_in_place: bool = False
    unclaimed_hsa_balances_material: bool = False


PROVIDER_TAX_STATES = {"CA", "NY", "OR", "TX", "MI", "WA"}


@dataclass
class TaxTrapReport:
    triggered_count: int
    total_estimated_irr_drag_bps: float
    flags: List[TaxTrapFlag] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered_count": self.triggered_count,
            "total_estimated_irr_drag_bps":
                self.total_estimated_irr_drag_bps,
            "flags": [
                {"name": f.name,
                 "triggered": f.triggered,
                 "estimated_irr_drag_bps":
                     f.estimated_irr_drag_bps,
                 "partner_commentary": f.partner_commentary}
                for f in self.flags
            ],
            "partner_note": self.partner_note,
        }


def scan_tax_traps(inputs: TaxTrapInputs) -> TaxTrapReport:
    flags: List[TaxTrapFlag] = []

    # 1. Golden parachute
    gp = (
        inputs.executives_with_acceleration_gt_3x_base >= 1
        and not inputs.golden_parachute_safe_harbor_in_place
    )
    flags.append(TaxTrapFlag(
        name="golden_parachute_280g_exposure",
        triggered=gp,
        estimated_irr_drag_bps=150 if gp else 0,
        partner_commentary=(
            f"{inputs.executives_with_acceleration_gt_3x_base} "
            "exec(s) with > 3× base acceleration + no safe "
            "harbor. Gross-up adds ~$5M per exec."
            if gp else
            "No 280G exposure flagged."
        ),
    ))

    # 2. NOL 382
    nol = (
        inputs.target_has_material_nols
        and inputs.target_ownership_change
    )
    flags.append(TaxTrapFlag(
        name="nol_382_limitation",
        triggered=nol,
        estimated_irr_drag_bps=200 if nol else 0,
        partner_commentary=(
            "Target has material NOLs + ownership change "
            "post-close → §382 annual-use limit. Verify "
            "carryforward economics."
            if nol else
            "No §382 NOL drag flagged."
        ),
    ))

    # 3. Sales tax nexus on services
    st = (
        inputs.telehealth_or_multi_state_services
        and inputs.nexus_states_with_gross_receipts_tax_exposed
    )
    flags.append(TaxTrapFlag(
        name="sales_tax_nexus_services",
        triggered=st,
        estimated_irr_drag_bps=100 if st else 0,
        partner_commentary=(
            "Telehealth / multi-state services + gross-"
            "receipts-tax states → retroactive nexus "
            "exposure. State-by-state audit needed."
            if st else
            "No multi-state gross-receipts exposure flagged."
        ),
    ))

    # 4. R&D credit carryforward
    rd = inputs.r_and_d_credits_carryforward_material
    flags.append(TaxTrapFlag(
        name="r_and_d_credit_carryforward_risk",
        triggered=rd,
        estimated_irr_drag_bps=80 if rd else 0,
        partner_commentary=(
            "Material R&D credit carryforward; verify "
            "preservation under §382 and acquisition "
            "structure."
            if rd else
            "No R&D credit carryforward flagged."
        ),
    ))

    # 5. Stock option acceleration
    so = inputs.unvested_options_accelerating_at_close
    flags.append(TaxTrapFlag(
        name="stock_option_acceleration",
        triggered=so,
        estimated_irr_drag_bps=80 if so else 0,
        partner_commentary=(
            "Unvested options accelerate at close → §83 "
            "income + withholding. Plan liquidity + "
            "employer tax cost."
            if so else
            "No unvested-option acceleration flagged."
        ),
    ))

    # 6. UBTI
    ub = (
        inputs.structure_generates_ubti
        and inputs.tax_exempt_lps_in_fund
    )
    flags.append(TaxTrapFlag(
        name="ubti_exposure_tax_exempt_lps",
        triggered=ub,
        estimated_irr_drag_bps=120 if ub else 0,
        partner_commentary=(
            "Structure generates UBTI + fund has tax-"
            "exempt LPs. Consider blocker vehicle or "
            "restructure."
            if ub else
            "No UBTI risk flagged."
        ),
    ))

    # 7. COD income seller note
    cod = (
        inputs.seller_note_at_close
        and inputs.seller_note_modification_planned
    )
    flags.append(TaxTrapFlag(
        name="cod_income_seller_note",
        triggered=cod,
        estimated_irr_drag_bps=60 if cod else 0,
        partner_commentary=(
            "Seller note + planned modification → "
            "potential cancellation-of-debt income. "
            "Structure to avoid §108 recognition."
            if cod else
            "No seller-note COD flagged."
        ),
    ))

    # 8. State provider tax
    operating_in_ptax = [
        s for s in inputs.operating_states
        if s.upper() in PROVIDER_TAX_STATES
    ]
    spt = len(operating_in_ptax) >= 1
    flags.append(TaxTrapFlag(
        name="state_provider_tax",
        triggered=spt,
        estimated_irr_drag_bps=100 if spt else 0,
        partner_commentary=(
            f"Operations in provider-tax state(s): "
            f"{', '.join(operating_in_ptax)} — 2-4% of "
            "revenue exposure. Verify compliance + any "
            "managed-care pass-through."
            if spt else
            "No state provider-tax exposure flagged."
        ),
    ))

    # 9. Section 263(a) R&D preservation
    rd_loss = (
        inputs.r_and_d_activities_material
        and inputs.target_ownership_change
    )
    flags.append(TaxTrapFlag(
        name="section_263a_healthcare_r_and_d",
        triggered=rd_loss,
        estimated_irr_drag_bps=50 if rd_loss else 0,
        partner_commentary=(
            "Material R&D activities + ownership change "
            "may disturb research-credit eligibility."
            if rd_loss else
            "No §263A R&D preservation concern flagged."
        ),
    ))

    # 10. Unclaimed HSA
    hsa = (
        inputs.employer_sponsored_hsa_in_place
        and inputs.unclaimed_hsa_balances_material
    )
    flags.append(TaxTrapFlag(
        name="unclaimed_hsa_balances",
        triggered=hsa,
        estimated_irr_drag_bps=30 if hsa else 0,
        partner_commentary=(
            "Employer-sponsored HSA with material "
            "unclaimed balances — post-close corporate "
            "liability + escheatment compliance."
            if hsa else
            "No HSA escheatment exposure flagged."
        ),
    ))

    triggered = sum(1 for f in flags if f.triggered)
    total_bps = round(
        sum(f.estimated_irr_drag_bps for f in flags if f.triggered),
        0,
    )

    if total_bps >= 400:
        note = (
            f"{triggered} tax traps firing totaling "
            f"{total_bps:.0f} bps of IRR drag. Partner: "
            "retain tax counsel pre-LOI; specific "
            "restructuring required before IC."
        )
    elif total_bps >= 150:
        note = (
            f"{triggered} tax traps, {total_bps:.0f} bps "
            "IRR drag. Partner: tax-counsel review scoped "
            "in diligence."
        )
    elif triggered > 0:
        note = (
            f"{triggered} tax trap(s), {total_bps:.0f} bps. "
            "Partner: document in tax workstream."
        )
    else:
        note = (
            "No tax-structure traps detected. Partner: "
            "proceed on standard tax diligence scope."
        )

    return TaxTrapReport(
        triggered_count=triggered,
        total_estimated_irr_drag_bps=total_bps,
        flags=flags,
        partner_note=note,
    )


def render_tax_trap_markdown(r: TaxTrapReport) -> str:
    lines = [
        "# Tax structure trap scan",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Triggered: {r.triggered_count} / 10",
        f"- Total IRR drag: "
        f"{r.total_estimated_irr_drag_bps:.0f} bps",
        "",
        "| Trap | Triggered | IRR drag | Partner commentary |",
        "|---|---|---|---|",
    ]
    for f in r.flags:
        check = "✓" if f.triggered else "—"
        lines.append(
            f"| {f.name} | {check} | "
            f"{f.estimated_irr_drag_bps:.0f} bps | "
            f"{f.partner_commentary} |"
        )
    return "\n".join(lines)
