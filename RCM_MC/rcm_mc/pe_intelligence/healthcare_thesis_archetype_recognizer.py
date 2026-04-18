"""Healthcare thesis archetype recognizer — recognize the deal on sight.

Partner statement: "There are seven healthcare deal
shapes. Payer-mix shift. Back-office consolidation.
Outpatient migration. CMI uplift. Roll-up platform.
Cost-basis compression. Capacity expansion. Every
deal I see fits one or two of these. Naming the
archetype before I model tells me which levers
matter, which risks are real, and which parts of the
packet I should zoom in on. The numbers come next.
The shape comes first."

Distinct from:
- `deal_archetype` — sponsor-structure archetypes
  (platform_rollup / take_private / carve_out /
  turnaround / etc.).
- `thesis_templates` — generic thesis narrative
  scaffolds.

This module reads packet-level signals and classifies
the deal into one or more of **7 healthcare-specific
thesis shapes**. Each archetype carries:

- **diagnostic_signals** — the packet patterns that
  indicate this shape.
- **confidence** — how strongly the signals match.
- **lever_stack** — the specific operating levers
  that matter for this shape.
- **named_risks** — the traps specific to this
  archetype.
- **partner_zoom** — where the partner reads next.
- **archetype_specific_sniff** — fast pattern-match
  to the most common failure for this shape.

### 7 healthcare thesis archetypes

1. **payer_mix_shift** — shift from Medicare/
   Medicaid to commercial via in-network /
   geographic expansion / service-line add.
2. **back_office_consolidation** — RCM / billing /
   HR / supply-chain centralization across sites.
3. **outpatient_migration** — shift inpatient
   procedures to outpatient (ASC, HOPD site-of-
   service arbitrage).
4. **cmi_uplift** — CDI / physician documentation /
   coding investments to move case-mix index.
5. **rollup_platform** — multi-site roll-up with
   platform services + acquired sites.
6. **cost_basis_compression** — unit economics
   improvement on existing volume (labor, supply,
   productivity).
7. **capacity_expansion** — de novo locations, bed
   expansion, service line addition.

### Output

Ranked archetype hits with signals, lever stack,
risks, partner zoom, sniff.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HealthcareArchetypeSignals:
    # Payer / mix shift
    commercial_mix_change_planned_pct: float = 0.0
    network_expansion_planned: bool = False
    # Back-office
    multi_site_count: int = 1
    centralized_rcm_investment_m: float = 0.0
    it_platform_investment_planned_m: float = 0.0
    # Outpatient migration
    inpatient_to_outpatient_shift_planned: bool = False
    owns_asc_or_hopd: bool = False
    # CMI uplift
    cdi_program_planned: bool = False
    coding_gap_vs_peers_bps: float = 0.0
    # Roll-up
    bolt_on_pipeline_count: int = 0
    platform_services_named: bool = False
    # Cost-basis compression
    labor_cost_reduction_planned_bps: float = 0.0
    supply_cost_reduction_planned_bps: float = 0.0
    productivity_improvement_planned_pct: float = 0.0
    # Capacity expansion
    de_novo_count_planned: int = 0
    bed_expansion_planned_count: int = 0
    service_line_addition_count: int = 0


@dataclass
class ArchetypeMatch:
    archetype: str
    confidence: float
    diagnostic_signals: List[str] = field(
        default_factory=list)
    lever_stack: List[str] = field(default_factory=list)
    named_risks: List[str] = field(default_factory=list)
    partner_zoom: str = ""
    archetype_specific_sniff: str = ""


@dataclass
class HealthcareArchetypeReport:
    matches: List[ArchetypeMatch] = field(
        default_factory=list)
    dominant_archetype: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [
                {"archetype": m.archetype,
                 "confidence": m.confidence,
                 "diagnostic_signals":
                     m.diagnostic_signals,
                 "lever_stack": m.lever_stack,
                 "named_risks": m.named_risks,
                 "partner_zoom": m.partner_zoom,
                 "archetype_specific_sniff":
                     m.archetype_specific_sniff}
                for m in self.matches
            ],
            "dominant_archetype":
                self.dominant_archetype,
            "partner_note": self.partner_note,
        }


def _payer_mix(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if (s.commercial_mix_change_planned_pct <= 0.03 and
            not s.network_expansion_planned):
        return None
    confidence = min(1.0,
                     s.commercial_mix_change_planned_pct * 10)
    signals = []
    if s.commercial_mix_change_planned_pct > 0.03:
        signals.append(
            f"planned commercial mix shift "
            f"+{s.commercial_mix_change_planned_pct:.0%}"
        )
    if s.network_expansion_planned:
        signals.append("in-network / network expansion planned")
    return ArchetypeMatch(
        archetype="payer_mix_shift",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "in-network contracting with commercial payers",
            "geographic expansion into commercial-dense MSAs",
            "service-line additions commercial-skewed (elective surgery, imaging)",
        ],
        named_risks=[
            "payer doesn't grant favorable in-network terms",
            "commercial patients don't follow across "
            "geography without network effect",
            "physician comp structure doesn't re-align "
            "to new mix incentives",
        ],
        partner_zoom=(
            "Read the specific in-network contract "
            "strategy — named payers, target rates, "
            "contract timing; without these, the "
            "thesis is aspiration."
        ),
        archetype_specific_sniff=(
            "If the thesis is 'more commercial' but "
            "the deal sits in a 70%-penetrated "
            "managed-care MSA, the shift is taken."
        ),
    )


def _back_office(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if s.multi_site_count < 3:
        return None
    if (s.centralized_rcm_investment_m + s.it_platform_investment_planned_m) < 1.0:
        return None
    confidence = min(1.0,
                     (s.centralized_rcm_investment_m +
                      s.it_platform_investment_planned_m) / 10.0)
    signals = [
        f"{s.multi_site_count} sites",
        f"RCM investment ${s.centralized_rcm_investment_m:.1f}M",
        f"IT platform investment ${s.it_platform_investment_planned_m:.1f}M",
    ]
    return ArchetypeMatch(
        archetype="back_office_consolidation",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "centralized RCM platform",
            "shared services for HR / finance",
            "supply-chain consolidation",
            "IT platform unification (EHR/PM)",
        ],
        named_risks=[
            "site resistance to shared-services "
            "migration; cost savings delayed 18-24mo",
            "RCM conversion creates DSO spike in "
            "transition window",
            "physician-group sites insist on "
            "autonomy; synergies never realize",
        ],
        partner_zoom=(
            "Check for the named integration lead with "
            "platform experience — without one, "
            "shared-services synergies slip 12 months."
        ),
        archetype_specific_sniff=(
            "If the bolt-ons all kept their own RCM "
            "vendor post-close, the back-office "
            "consolidation thesis is stalled."
        ),
    )


def _outpatient(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if not s.inpatient_to_outpatient_shift_planned:
        return None
    confidence = 0.8 if s.owns_asc_or_hopd else 0.5
    signals = ["planned inpatient → outpatient shift"]
    if s.owns_asc_or_hopd:
        signals.append("owns ASC or HOPD capacity")
    return ArchetypeMatch(
        archetype="outpatient_migration",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "ASC / HOPD site-of-service arbitrage",
            "physician alignment toward outpatient case mix",
            "payer contract riders for OP site-neutral",
        ],
        named_risks=[
            "OBBBA site-neutral payment collapses "
            "the arbitrage",
            "physician-group resistance to shifting "
            "from hospital-employed to ASC",
            "payer site-of-service requirements "
            "outpace provider ability to shift",
        ],
        partner_zoom=(
            "Model the OP arbitrage NET of site-"
            "neutral rule impact; if the arbitrage "
            "depends on current payment asymmetry, "
            "it's at risk."
        ),
        archetype_specific_sniff=(
            "If the deal assumes the OP arbitrage "
            "persists through OBBBA unchanged, "
            "it's the site-neutral trap."
        ),
    )


def _cmi_uplift(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if not s.cdi_program_planned and s.coding_gap_vs_peers_bps < 50:
        return None
    confidence = 0.6 if s.cdi_program_planned else 0.4
    if s.coding_gap_vs_peers_bps > 100:
        confidence += 0.3
    signals = []
    if s.cdi_program_planned:
        signals.append("CDI program planned")
    if s.coding_gap_vs_peers_bps > 50:
        signals.append(
            f"coding gap vs peers "
            f"{s.coding_gap_vs_peers_bps:.0f} bps"
        )
    return ArchetypeMatch(
        archetype="cmi_uplift",
        confidence=round(min(1.0, confidence), 2),
        diagnostic_signals=signals,
        lever_stack=[
            "CDI specialist hires (documentation "
            "improvement)",
            "physician coding education + feedback",
            "payer-specific medical-policy library",
            "coder productivity platform",
        ],
        named_risks=[
            "RAC audit exposure on aggressive "
            "coding",
            "physician comp tied to productivity "
            "resists accurate-but-lower-value "
            "documentation",
            "CMI lift doesn't translate to revenue "
            "in capitated or bundled contracts",
        ],
        partner_zoom=(
            "Compare CMI vs peer CMI by DRG family — "
            "is the gap in specific conditions "
            "(documentation opportunity) or across "
            "the board (coding aggressiveness risk)?"
        ),
        archetype_specific_sniff=(
            "If the CMI bridge depends on 50+ bps "
            "uplift in year 1, the RAC will find it."
        ),
    )


def _rollup(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if s.bolt_on_pipeline_count < 2:
        return None
    confidence = min(1.0, s.bolt_on_pipeline_count / 8.0)
    signals = [f"{s.bolt_on_pipeline_count} bolt-on pipeline"]
    if s.platform_services_named:
        signals.append("platform services named")
    return ArchetypeMatch(
        archetype="rollup_platform",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "platform multiple arbitrage on bolt-ons",
            "centralized platform services (RCM, IT, HR)",
            "proprietary deal flow from operating "
            "partners + physician network",
        ],
        named_risks=[
            "platform mgmt capacity saturates at 5-8 "
            "bolt-ons",
            "integration costs > projected; first "
            "3 bolt-ons deliver, 4+ slip",
            "auction fatigue raises bolt-on multiples "
            "over time; arbitrage compresses",
        ],
        partner_zoom=(
            "Run rollup_arbitrage_math — what % of "
            "MOIC is multiple arbitrage vs. real "
            "EBITDA growth?"
        ),
        archetype_specific_sniff=(
            "If the bolt-on pipeline is 'warm leads' "
            "not named LOIs, the math is decorative."
        ),
    )


def _cost_basis(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    total_bps = (
        s.labor_cost_reduction_planned_bps +
        s.supply_cost_reduction_planned_bps
    )
    if total_bps < 100 and s.productivity_improvement_planned_pct < 0.05:
        return None
    confidence = min(1.0, (total_bps + s.productivity_improvement_planned_pct * 1000) / 500)
    signals = []
    if s.labor_cost_reduction_planned_bps > 50:
        signals.append(
            f"labor cost reduction "
            f"{s.labor_cost_reduction_planned_bps:.0f} bps"
        )
    if s.supply_cost_reduction_planned_bps > 50:
        signals.append(
            f"supply cost reduction "
            f"{s.supply_cost_reduction_planned_bps:.0f} bps"
        )
    if s.productivity_improvement_planned_pct > 0.05:
        signals.append(
            f"productivity improvement "
            f"{s.productivity_improvement_planned_pct:.0%}"
        )
    return ArchetypeMatch(
        archetype="cost_basis_compression",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "labor productivity + staffing model "
            "redesign",
            "GPO / supply-chain renegotiation",
            "facility utilization",
            "back-office automation",
        ],
        named_risks=[
            "labor reductions hit quality/safety "
            "metrics (Star, HCAHPS)",
            "savings assume stable volume; any "
            "decline reverses the gain",
            "physician groups resist productivity "
            "metrics without comp realignment",
        ],
        partner_zoom=(
            "Check quality-metric baselines — if "
            "already below peer median, labor "
            "reductions will collapse them."
        ),
        archetype_specific_sniff=(
            "200+ bps labor reduction in year 1 "
            "without a named ops partner is a red "
            "flag — cost-basis compression is "
            "execution-heavy."
        ),
    )


def _capacity(s: HealthcareArchetypeSignals) -> Optional[ArchetypeMatch]:
    if (s.de_novo_count_planned == 0 and
            s.bed_expansion_planned_count == 0 and
            s.service_line_addition_count == 0):
        return None
    confidence = min(1.0,
                     (s.de_novo_count_planned * 0.2 +
                      s.bed_expansion_planned_count * 0.05 +
                      s.service_line_addition_count * 0.2))
    signals = []
    if s.de_novo_count_planned:
        signals.append(
            f"{s.de_novo_count_planned} de novo sites"
        )
    if s.bed_expansion_planned_count:
        signals.append(
            f"{s.bed_expansion_planned_count} bed "
            "expansion"
        )
    if s.service_line_addition_count:
        signals.append(
            f"{s.service_line_addition_count} new "
            "service lines"
        )
    return ArchetypeMatch(
        archetype="capacity_expansion",
        confidence=round(confidence, 2),
        diagnostic_signals=signals,
        lever_stack=[
            "de novo site build-out",
            "service-line additions",
            "payer contract expansion for new "
            "capacity",
            "physician recruiting for new sites",
        ],
        named_risks=[
            "de novo ramp slower than model (18-36 mo "
            "to breakeven)",
            "new sites cannibalize existing volume",
            "capex over-run; ROI pushed out",
        ],
        partner_zoom=(
            "Capex-scoped IRR must include de novo "
            "ramp curves; year-3 stabilized assumption "
            "is aggressive for healthcare sites."
        ),
        archetype_specific_sniff=(
            "If de novos ramp in 12 months per model, "
            "re-check peer comps — 18-36 mo is "
            "healthcare reality."
        ),
    )


_RECOGNIZERS = [
    _payer_mix,
    _back_office,
    _outpatient,
    _cmi_uplift,
    _rollup,
    _cost_basis,
    _capacity,
]


def recognize_healthcare_thesis_archetypes(
    signals: HealthcareArchetypeSignals,
) -> HealthcareArchetypeReport:
    matches: List[ArchetypeMatch] = []
    for fn in _RECOGNIZERS:
        m = fn(signals)
        if m is not None:
            matches.append(m)

    matches.sort(key=lambda m: m.confidence, reverse=True)

    if not matches:
        dominant = ""
        note = (
            "No clear healthcare thesis archetype — "
            "packet signals too sparse or the thesis is "
            "generic operating-lift. Read the CIM thesis "
            "statement directly."
        )
    else:
        dominant = matches[0].archetype
        note = (
            f"Dominant archetype: **{dominant}** "
            f"(confidence {matches[0].confidence:.0%}). "
            f"{len(matches)} archetype(s) match. "
            "Each archetype has named risks and a "
            "lever stack — zoom in per archetype "
            "rather than read the deal as generic."
        )

    return HealthcareArchetypeReport(
        matches=matches,
        dominant_archetype=dominant,
        partner_note=note,
    )


def render_healthcare_archetype_markdown(
    r: HealthcareArchetypeReport,
) -> str:
    lines = [
        "# Healthcare thesis archetype",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    for m in r.matches:
        lines.append(
            f"## {m.archetype} "
            f"(confidence {m.confidence:.0%})"
        )
        lines.append("")
        lines.append(
            "**Signals:** " +
            "; ".join(m.diagnostic_signals)
        )
        lines.append("")
        lines.append("**Lever stack:**")
        for l in m.lever_stack:
            lines.append(f"- {l}")
        lines.append("")
        lines.append("**Named risks:**")
        for risk in m.named_risks:
            lines.append(f"- {risk}")
        lines.append("")
        lines.append(
            f"**Partner zoom:** {m.partner_zoom}")
        lines.append("")
        lines.append(
            f"**Archetype-specific sniff:** "
            f"{m.archetype_specific_sniff}"
        )
        lines.append("")
    return "\n".join(lines)
