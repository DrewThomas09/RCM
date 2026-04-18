"""Diligence spend budget — how much to spend to decide.

Partner statement: "I don't run the same diligence on a
$100M deal that I run on a $1B deal. I don't run the same
diligence on a clean asset that I run on one matching
three failure archetypes. The spend has to fit the shape."

Partners size diligence budget based on:

- **Deal scale** — EV-driven base budget.
- **Pattern risk** — each compound risk adds a scope.
- **Source quality** — proprietary gets deeper scope;
  broad auction gets compressed scope.
- **Subsector complexity** — hospital vs. practice vs. lab.
- **Regulatory overhang** — specific reg exposure adds
  specialized counsel.

### Budget components

Each workstream sized separately:

1. **QofE (financial)** — percent of EV.
2. **Legal / corporate / tax** — scale by complexity.
3. **Regulatory / healthcare compliance** — triggered by
   signals.
4. **Clinical / quality** — for operator-side assets.
5. **Commercial / market** — when market thesis is a
   primary lever.
6. **IT / cyber** — baseline plus ransomware exposure.
7. **Insurance / R&W** — premium + deal scope.
8. **Consultants / operators** — for turnaround /
   integration-heavy deals.

### Output

Dollar budget per workstream + total + partner note on
the biggest line item and the axis it addresses.

### Why partners care

Excessive diligence spend compresses IRR. Inadequate
diligence spend causes post-close surprises. This module
makes the tradeoff explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Base budget as percent of EV for a clean $500M deal.
BASE_TOTAL_PCT_OF_EV: float = 0.0050   # 50 bps

# Workstream share of base budget on a clean deal.
BASE_WORKSTREAM_SHARES: Dict[str, float] = {
    "qofe": 0.30,
    "legal_corporate_tax": 0.25,
    "regulatory_healthcare_compliance": 0.05,
    "clinical_quality": 0.05,
    "commercial_market": 0.10,
    "it_cyber": 0.08,
    "insurance_rw": 0.07,
    "consultants_operators": 0.10,
}


@dataclass
class DiligenceBudgetInputs:
    ev_m: float
    subsector: str = "healthcare_services"
    source: str = "limited_auction_invited"   # from deal_source_quality_reader
    compound_pattern_risk_count: int = 0
    regulatory_overhang_count: int = 0        # OBBBA / NSA / PAMA / etc.
    clinical_risk_material: bool = False
    cyber_exposure_material: bool = False
    turnaround_thesis: bool = False
    commercial_thesis: bool = False


@dataclass
class WorkstreamBudget:
    name: str
    base_m: float
    scale_factor: float
    final_m: float
    partner_rationale: str


@dataclass
class DiligenceBudgetReport:
    total_m: float
    total_pct_of_ev: float
    workstreams: List[WorkstreamBudget] = field(default_factory=list)
    biggest_line: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_m": self.total_m,
            "total_pct_of_ev": self.total_pct_of_ev,
            "workstreams": [
                {"name": w.name, "base_m": w.base_m,
                 "scale_factor": w.scale_factor,
                 "final_m": w.final_m,
                 "partner_rationale": w.partner_rationale}
                for w in self.workstreams
            ],
            "biggest_line": self.biggest_line,
            "partner_note": self.partner_note,
        }


def _source_scale(source: str) -> float:
    # Broad auction = compressed, proprietary = extended.
    return {
        "broad_auction": 0.70,
        "limited_auction_invited": 1.00,
        "proprietary_from_relationship": 1.25,
        "second_look_after_broken_process": 1.40,
        "distressed_forced_sale": 0.80,
        "continuation_vehicle_inside": 0.95,
        "reverse_inquiry": 1.15,
        "management_led_carveout": 1.30,
    }.get(source, 1.00)


def _subsector_qofe_scale(subsector: str) -> float:
    return {
        "hospital_general": 1.25,
        "specialty_physician_practice": 1.10,
        "behavioral_health": 1.15,
        "home_health": 1.20,
        "hospice": 1.30,
        "ambulatory_surgery_center": 1.05,
        "clinical_lab": 1.20,
        "dental_office": 0.95,
        "urgent_care": 1.00,
        "durable_medical_equipment": 1.15,
    }.get(subsector, 1.00)


def size_diligence_budget(
    inputs: DiligenceBudgetInputs,
) -> DiligenceBudgetReport:
    ev = max(1.0, inputs.ev_m)
    # Diligence as pct of EV generally declines with size.
    # Partner heuristic: 50 bps at $500M, 35 bps at $1B.
    size_adj = 0.0050
    if ev >= 1000:
        size_adj = 0.0035
    elif ev >= 500:
        size_adj = 0.0045
    elif ev < 200:
        size_adj = 0.0070
    base_total = ev * size_adj

    workstreams: List[WorkstreamBudget] = []
    for name, share in BASE_WORKSTREAM_SHARES.items():
        base_m = round(base_total * share, 2)
        scale = 1.0

        # Per-workstream scaling.
        if name == "qofe":
            scale *= _subsector_qofe_scale(inputs.subsector)
            if inputs.compound_pattern_risk_count >= 2:
                scale *= 1.20
            rationale = (
                f"QofE scaled for {inputs.subsector}; "
                f"+{int((scale-1)*100)}% if ≥ 2 compound "
                "patterns."
            )
        elif name == "regulatory_healthcare_compliance":
            scale *= (1.0 + 0.30 *
                       inputs.regulatory_overhang_count)
            rationale = (
                f"{inputs.regulatory_overhang_count} "
                "regulatory overhangs add specialized "
                "counsel scope."
            )
        elif name == "clinical_quality":
            if inputs.clinical_risk_material:
                scale *= 1.80
            rationale = (
                "Clinical / quality diligence deep when "
                "clinical risk is material."
                if inputs.clinical_risk_material else
                "Baseline clinical scope."
            )
        elif name == "it_cyber":
            if inputs.cyber_exposure_material:
                scale *= 2.00
            rationale = (
                "Cyber diligence 2x baseline on material "
                "exposure."
                if inputs.cyber_exposure_material else
                "Baseline IT diligence."
            )
        elif name == "consultants_operators":
            if inputs.turnaround_thesis:
                scale *= 2.50
            rationale = (
                "Operator / turnaround consultant spend "
                "2.5x baseline on turnaround theses."
                if inputs.turnaround_thesis else
                "Baseline ops-consultant allocation."
            )
        elif name == "commercial_market":
            if inputs.commercial_thesis:
                scale *= 1.75
            rationale = (
                "Commercial diligence 1.75x when commercial "
                "is primary lever."
                if inputs.commercial_thesis else
                "Baseline commercial scope."
            )
        elif name == "insurance_rw":
            if ev >= 500:
                scale *= 1.20
            rationale = "R&W premium scales with deal size."
        elif name == "legal_corporate_tax":
            scale *= _source_scale(inputs.source) * 1.0
            rationale = (
                f"Legal scope scales with source "
                f"({inputs.source})."
            )
        else:
            rationale = "Baseline."

        final = round(base_m * scale, 2)
        workstreams.append(WorkstreamBudget(
            name=name, base_m=base_m,
            scale_factor=round(scale, 2),
            final_m=final,
            partner_rationale=rationale,
        ))

    # Overall source scaling applied to total (some sources
    # get compressed timelines; we keep legal per-workstream
    # above and skip double-scaling the rest).
    total = round(sum(w.final_m for w in workstreams), 2)
    pct_of_ev = round(total / ev, 4)

    biggest = max(workstreams, key=lambda w: w.final_m)

    if pct_of_ev >= 0.008:
        note = (
            f"Diligence budget ${total:,.1f}M "
            f"({pct_of_ev*100:.2f}% of EV). High — "
            f"{biggest.name} is the biggest line "
            "because of the identified risk axis."
        )
    elif pct_of_ev <= 0.003:
        note = (
            f"Diligence budget ${total:,.1f}M "
            f"({pct_of_ev*100:.2f}% of EV). Lean — this "
            "is a clean deal on a standard scope."
        )
    else:
        note = (
            f"Diligence budget ${total:,.1f}M "
            f"({pct_of_ev*100:.2f}% of EV). Standard. "
            f"Biggest line: {biggest.name}."
        )

    return DiligenceBudgetReport(
        total_m=total,
        total_pct_of_ev=pct_of_ev,
        workstreams=workstreams,
        biggest_line=biggest.name,
        partner_note=note,
    )


def render_diligence_budget_markdown(
    r: DiligenceBudgetReport,
) -> str:
    lines = [
        "# Diligence spend budget",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total: ${r.total_m:,.1f}M "
        f"({r.total_pct_of_ev*100:.2f}% of EV)",
        f"- Biggest line: {r.biggest_line}",
        "",
        "| Workstream | Base | Scale | Final | Rationale |",
        "|---|---|---|---|---|",
    ]
    for w in r.workstreams:
        lines.append(
            f"| {w.name} | ${w.base_m:,.2f}M | "
            f"{w.scale_factor:.2f}x | "
            f"${w.final_m:,.2f}M | "
            f"{w.partner_rationale} |"
        )
    return "\n".join(lines)
