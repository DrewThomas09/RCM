"""Archetype heuristic router — which rules matter most?

Partner statement: "A payer-mix-shift thesis needs
different heuristics than a roll-up. Loading every rule
on every deal is noise. The brain should know which 10
rules actually decide this archetype's fate."

Distinct from `archetype_subrunners` (which runs
archetype-specific subrunner logic). This module is the
**meta-router** that tells the brain *which judgment
layers* to prioritize for a named archetype, across the
existing pattern libraries, subsector lens, thesis chain,
and failure-mode catalogs.

### 8 archetypes routed

1. **payer_mix_shift** — shifting commercial/Medicare mix.
2. **rollup_consolidation** — platform + add-ons.
3. **cmi_uplift** — clinical documentation improvement.
4. **outpatient_migration** — inpatient → outpatient.
5. **cost_basis_compression** — labor / cost-out thesis.
6. **capacity_expansion** — new sites / beds.
7. **back_office_consolidation** — shared services.
8. **payer_renegotiation** — commercial rate lift.

### Routing per archetype

Each archetype maps to:
- **primary_thesis_chain** — which chain to walk.
- **priority_failure_patterns** — named patterns most
  relevant.
- **priority_traps** — partner traps most common.
- **priority_archetypes** (from failure_archetype_library)
  — shape-level patterns.
- **subsector_tags** — which subsectors most exposed.
- **specific_heuristics** — top 3-5 rules that decide
  the archetype.
- **partner_first_question** — single question a partner
  asks about this archetype.

### Why routing matters

Loading every heuristic on every deal produces noise.
Partners read archetype-specific heuristics first. The
router is the partner's "which lens do I pick up first"
gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArchetypeRouting:
    archetype: str
    primary_thesis_chain: str
    priority_failure_patterns: List[str] = field(default_factory=list)
    priority_traps: List[str] = field(default_factory=list)
    priority_shape_archetypes: List[str] = field(default_factory=list)
    subsector_tags: List[str] = field(default_factory=list)
    specific_heuristics: List[str] = field(default_factory=list)
    partner_first_question: str = ""


ROUTING_LIBRARY: Dict[str, ArchetypeRouting] = {
    "payer_mix_shift": ArchetypeRouting(
        archetype="payer_mix_shift",
        primary_thesis_chain="payer_mix_shift",
        priority_failure_patterns=[
            "us_renal_care_medicare_advantage",
            "ma_provider_risk_contract_2023",
            "ma_startup_unwind_2023",
        ],
        priority_traps=[
            "payer_renegotiation_is_coming",
            "medicare_advantage_will_make_it_up",
            "underpenetrated_market",
        ],
        priority_shape_archetypes=[
            "payer_shift_without_contract_renewal",
            "ma_pass_through_over_reliance",
        ],
        subsector_tags=[
            "specialty_physician_practice",
            "hospital_general",
            "home_health",
        ],
        specific_heuristics=[
            "Top-5 payer contracts must open in hold.",
            "Commercial payer capacity confirmed pre-LOI.",
            "DSH / UPL exposure if Medicaid share drops.",
            "Mix shift phased 18-36 mo, not day-1.",
            "Case-mix rises with shift — not dilutes.",
        ],
        partner_first_question=(
            "Which commercial payers have confirmed "
            "capacity for the volume shift, and when do "
            "those contracts open?"
        ),
    ),
    "rollup_consolidation": ArchetypeRouting(
        archetype="rollup_consolidation",
        primary_thesis_chain="rollup_consolidation",
        priority_failure_patterns=[
            "envision_surprise_billing_2023",
            "21st_century_oncology_2017",
            "dental_dso_over_rollup_2021",
        ],
        priority_traps=[
            "robust_pipeline_of_add_ons",
            "back_office_year_1_synergies",
            "ceo_will_stay_through_close",
        ],
        priority_shape_archetypes=[
            "serial_add_on_overhire",
            "back_office_integration_optimism",
            "specialty_practice_succession_gap",
        ],
        subsector_tags=[
            "specialty_physician_practice",
            "dental_office",
            "ambulatory_surgery_center",
        ],
        specific_heuristics=[
            "Signed LOIs at close ≥ 3; not 'pipeline'.",
            "Integration cost ratio ≥ 40% of synergy.",
            "Y1 synergy timing = partner-reject.",
            "Acquired-CEO retention at platform roles.",
            "Debt capacity scales with delayed-draw.",
        ],
        partner_first_question=(
            "How many add-ons are signed at LOI, and "
            "what's the integration cost ratio vs "
            "synergy?"
        ),
    ),
    "cmi_uplift": ArchetypeRouting(
        archetype="cmi_uplift",
        primary_thesis_chain="cmi_uplift",
        priority_failure_patterns=[
            "pdgm_transition_fallout_2020",
            "hahnemann_bankruptcy_2019",
        ],
        priority_traps=[
            "fix_denials_in_12_months",
        ],
        priority_shape_archetypes=[],
        subsector_tags=[
            "hospital_general",
            "home_health",
        ],
        specific_heuristics=[
            "CDI FTE count vs. peer ratio.",
            "Open OIG / MAC / RAC audit exposure.",
            "CMI trend pre-COVID baseline.",
            "Phase-in multiplier not day-1 uplift.",
        ],
        partner_first_question=(
            "How many CDI FTEs do you have, and what's "
            "the CMI trend vs. pre-COVID baseline?"
        ),
    ),
    "outpatient_migration": ArchetypeRouting(
        archetype="outpatient_migration",
        primary_thesis_chain="payer_mix_shift",
        priority_failure_patterns=[
            "adeptus_freestanding_er_2017",
            "nsa_platform_rate_shock_2022",
        ],
        priority_traps=[
            "underpenetrated_market",
        ],
        priority_shape_archetypes=[
            "site_neutral_hostage",
        ],
        subsector_tags=[
            "ambulatory_surgery_center",
            "urgent_care",
            "hospital_general",
        ],
        specific_heuristics=[
            "HOPD exposure vs. site-neutral calendar.",
            "ASC vs. HOPD rate differential narrowing.",
            "Physician ownership ≥ 30%.",
            "Commercial steering contracts in hand.",
        ],
        partner_first_question=(
            "What's your HOPD revenue exposure and "
            "when does site-neutral finalize?"
        ),
    ),
    "cost_basis_compression": ArchetypeRouting(
        archetype="cost_basis_compression",
        primary_thesis_chain="cost_basis_compression",
        priority_failure_patterns=[
            "steward_reit_dependency_2024",
            "behavioral_staffing_collapse_2024",
        ],
        priority_traps=[
            "back_office_year_1_synergies",
            "quality_and_growth",
        ],
        priority_shape_archetypes=[
            "rent_belowmarket_related_party",
        ],
        subsector_tags=[
            "hospital_general",
            "behavioral_health",
        ],
        specific_heuristics=[
            "Union / licensure constraint on staffing.",
            "Contract-labor % of worked hours target.",
            "Quality metrics hold post-cut.",
            "Regional wage inflation overlay.",
        ],
        partner_first_question=(
            "What's your union / licensure constraint "
            "on staffing, and can quality metrics hold "
            "through the cost cut?"
        ),
    ),
    "capacity_expansion": ArchetypeRouting(
        archetype="capacity_expansion",
        primary_thesis_chain="rollup_consolidation",
        priority_failure_patterns=[
            "adeptus_freestanding_er_2017",
            "prospect_medical_cashflow_2023",
        ],
        priority_traps=[
            "robust_pipeline_of_add_ons",
        ],
        priority_shape_archetypes=[
            "serial_add_on_overhire",
        ],
        subsector_tags=[
            "ambulatory_surgery_center",
            "urgent_care",
            "home_health",
        ],
        specific_heuristics=[
            "Per-new-site payback ≤ 36 months.",
            "CON exposure where applicable.",
            "Volume ramp not Y1.",
            "Capex per site against peer.",
        ],
        partner_first_question=(
            "What's the payback per new site, and do "
            "you have CON approvals in hand?"
        ),
    ),
    "back_office_consolidation": ArchetypeRouting(
        archetype="back_office_consolidation",
        primary_thesis_chain="cost_basis_compression",
        priority_failure_patterns=[
            "rcm_vendor_concentration_loss_2022",
        ],
        priority_traps=[
            "back_office_year_1_synergies",
            "tech_platform_play",
        ],
        priority_shape_archetypes=[
            "back_office_integration_optimism",
        ],
        subsector_tags=[
            "clinical_lab",
            "durable_medical_equipment",
            "dental_office",
        ],
        specific_heuristics=[
            "# of EHR / ERP systems to merge.",
            "Integration cost load ≥ 40% of synergy.",
            "Customer concentration limits scope.",
            "Y2-Y4 synergy ramp, not Y1.",
        ],
        partner_first_question=(
            "How many EHR / ERP systems would we "
            "consolidate, and what's the integration "
            "cost load?"
        ),
    ),
    "payer_renegotiation": ArchetypeRouting(
        archetype="payer_renegotiation",
        primary_thesis_chain="payer_mix_shift",
        priority_failure_patterns=[
            "radiology_partners_rate_shock_2022",
            "team_health_pricing_fight",
        ],
        priority_traps=[
            "payer_renegotiation_is_coming",
        ],
        priority_shape_archetypes=[
            "payer_shift_without_contract_renewal",
        ],
        subsector_tags=[
            "specialty_physician_practice",
            "ambulatory_surgery_center",
            "clinical_lab",
        ],
        specific_heuristics=[
            "Rate-growth > 3%/yr = partner-reject.",
            "Contract timing within hold window.",
            "Payer mix of contract pool.",
            "Earn-out tied to actually-signed rates.",
        ],
        partner_first_question=(
            "Which contracts are open in the next 12 "
            "months, and what's the realistic rate "
            "lift vs. your plan?"
        ),
    ),
}


@dataclass
class ArchetypeRoutingReport:
    archetype: str
    routing: Optional[ArchetypeRouting] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "routing": (
                {
                    "archetype": self.routing.archetype,
                    "primary_thesis_chain":
                        self.routing.primary_thesis_chain,
                    "priority_failure_patterns":
                        list(self.routing.priority_failure_patterns),
                    "priority_traps":
                        list(self.routing.priority_traps),
                    "priority_shape_archetypes":
                        list(self.routing.priority_shape_archetypes),
                    "subsector_tags":
                        list(self.routing.subsector_tags),
                    "specific_heuristics":
                        list(self.routing.specific_heuristics),
                    "partner_first_question":
                        self.routing.partner_first_question,
                }
                if self.routing else None
            ),
            "partner_note": self.partner_note,
        }


def route_archetype(archetype: str) -> ArchetypeRoutingReport:
    r = ROUTING_LIBRARY.get(archetype)
    if r is None:
        return ArchetypeRoutingReport(
            archetype=archetype,
            routing=None,
            partner_note=(
                f"Archetype '{archetype}' not modeled. "
                "Partner: apply generic heuristics + "
                "first-impression shape check."
            ),
        )
    return ArchetypeRoutingReport(
        archetype=archetype,
        routing=r,
        partner_note=(
            f"Archetype '{archetype}' routes to: thesis "
            f"chain '{r.primary_thesis_chain}', "
            f"{len(r.priority_failure_patterns)} priority "
            f"failure patterns, "
            f"{len(r.priority_traps)} priority traps, "
            f"{len(r.specific_heuristics)} archetype-"
            "specific heuristics. Partner first question: "
            f"{r.partner_first_question}"
        ),
    )


def list_routed_archetypes() -> List[str]:
    return sorted(ROUTING_LIBRARY.keys())


def render_archetype_routing_markdown(
    r: ArchetypeRoutingReport,
) -> str:
    lines = [
        f"# Archetype routing — `{r.archetype}`",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    if r.routing is None:
        return "\n".join(lines)
    rt = r.routing
    lines.append(
        f"**First question:** {rt.partner_first_question}"
    )
    lines.append("")
    lines.append(f"- Thesis chain: `{rt.primary_thesis_chain}`")
    lines.append(
        f"- Priority failure patterns: "
        f"{', '.join(rt.priority_failure_patterns) or '—'}"
    )
    lines.append(
        f"- Priority traps: "
        f"{', '.join(rt.priority_traps) or '—'}"
    )
    lines.append(
        f"- Priority shape archetypes: "
        f"{', '.join(rt.priority_shape_archetypes) or '—'}"
    )
    lines.append(
        f"- Subsector tags: "
        f"{', '.join(rt.subsector_tags) or '—'}"
    )
    lines.append("")
    lines.append("## Archetype-specific heuristics")
    lines.append("")
    for i, h in enumerate(rt.specific_heuristics, 1):
        lines.append(f"{i}. {h}")
    return "\n".join(lines)
