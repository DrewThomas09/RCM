"""Physician-group friction — post-close execution drag.

Partner statement: "On a physician-practice deal, the
thesis closes at LOI. The friction starts day 1 of
integration. Knowing the friction list before we sign
decides whether the 100-day plan is the first plan or
the second."

Distinct from:
- `physician_compensation_benchmark` — MGMA bands.
- `physician_comp_normalization_check` — pro-forma
  EBITDA haircut math.
- `management_bench_depth_check` — C-suite depth.

This module catalogs 10 post-close friction points
specific to physician-group PE integration. Each
carries:
- probability (high / medium / low) of occurring
- EBITDA-impact (% of current EBITDA if realized)
- partner counter (what to require at LOI / close)

### 10 friction points

1. **ancillary_ownership_unwind** — DI, lab, path,
   surgery ownership roll-up resistance.
2. **rvu_target_resistance** — physicians reject
   quota-based comp.
3. **state_noncompete_gap** — CA/ND/etc. unenforceable.
4. **referral_source_loss** — physicians move in
   cohorts.
5. **cdi_documentation_pushback** — clinical
   documentation program resistance.
6. **financial_incentive_restructure** — comp-model
   change creates flight risk.
7. **supervisory_physician_gap** — mid-level coverage
   ratio breaks.
8. **stark_antikickback_exposure** — post-restructure
   compliance.
9. **pms_ehr_change** — forced platform switch
   dismantles cadence.
10. **clinical_protocol_standardization** — physicians
    reject one-size-fits-all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PhysicianFrictionPoint:
    name: str
    description: str
    probability: str                       # high / medium / low
    ebitda_impact_pct: float               # if realized
    early_signals: List[str] = field(default_factory=list)
    partner_counter: str = ""


FRICTION_LIBRARY: List[PhysicianFrictionPoint] = [
    PhysicianFrictionPoint(
        name="ancillary_ownership_unwind",
        description=(
            "Physicians own equity in ancillary services "
            "(DI, lab, pathology, surgery) that the PE "
            "structure needs to roll up. Physicians "
            "resist surrendering distribution streams."
        ),
        probability="high",
        ebitda_impact_pct=0.08,
        early_signals=[
            "ancillary_ownership_disclosed",
            "ancillary_distribution_share_gt_20pct",
            "no_buyout_price_agreed_pre_close",
        ],
        partner_counter=(
            "Buyout price + timeline agreed pre-LOI. "
            "Close with signed acknowledgments; do not "
            "negotiate post-close."
        ),
    ),
    PhysicianFrictionPoint(
        name="rvu_target_resistance",
        description=(
            "Physicians resist productivity (RVU) "
            "targets imposed by new ownership."
        ),
        probability="high",
        ebitda_impact_pct=0.05,
        early_signals=[
            "rvu_target_increase_gt_10pct",
            "no_physician_comp_transition_plan",
        ],
        partner_counter=(
            "18-month transition comp guarantee; phase "
            "RVU targets over 24 months, not day 1."
        ),
    ),
    PhysicianFrictionPoint(
        name="state_noncompete_gap",
        description=(
            "State law weakens or voids non-competes "
            "(CA, CO, ND, OK, VA). Physicians can leave "
            "immediately without restriction."
        ),
        probability="medium",
        ebitda_impact_pct=0.15,
        early_signals=[
            "practice_state_in_noncompete_gap_list",
            "no_alternative_restrictive_covenant",
            "key_physician_unsigned_at_close",
        ],
        partner_counter=(
            "Use non-solicit + deferred-comp clawback "
            "where non-compete is unenforceable. Higher "
            "rollover % for mobility states."
        ),
    ),
    PhysicianFrictionPoint(
        name="referral_source_loss",
        description=(
            "Physicians move in cohorts. Losing one "
            "senior physician often triggers 2-3 "
            "associated departures + referral-network "
            "loss."
        ),
        probability="medium",
        ebitda_impact_pct=0.12,
        early_signals=[
            "physician_referral_concentration_gt_25pct",
            "senior_physician_age_60_plus",
            "no_staggered_retention_timeline",
        ],
        partner_counter=(
            "Staggered retention (2/3/5 year tiers); "
            "identify and pre-align cohort leaders."
        ),
    ),
    PhysicianFrictionPoint(
        name="cdi_documentation_pushback",
        description=(
            "CDI / coding program requires physician "
            "participation. Physicians view it as "
            "administrative burden; documentation "
            "quality drops."
        ),
        probability="medium",
        ebitda_impact_pct=0.04,
        early_signals=[
            "no_cdi_program_currently",
            "cmi_below_peer_median",
            "no_physician_champion_for_cdi",
        ],
        partner_counter=(
            "Recruit physician CDI champion before "
            "rollout. Tie participation to comp."
        ),
    ),
    PhysicianFrictionPoint(
        name="financial_incentive_restructure",
        description=(
            "Comp-model transition (base + productivity "
            "+ quality) creates flight risk during "
            "transition period."
        ),
        probability="high",
        ebitda_impact_pct=0.06,
        early_signals=[
            "proposed_comp_model_materially_different",
            "no_hold_harmless_year_1",
        ],
        partner_counter=(
            "Hold-harmless guarantee year 1; transition "
            "to new model year 2-3."
        ),
    ),
    PhysicianFrictionPoint(
        name="supervisory_physician_gap",
        description=(
            "Mid-level (NP/PA) supervision ratios break "
            "when a supervising physician leaves. State "
            "requirements cap mid-level volume per "
            "physician."
        ),
        probability="low",
        ebitda_impact_pct=0.03,
        early_signals=[
            "midlevel_to_physician_ratio_gt_state_max",
            "supervisor_physician_near_retirement",
        ],
        partner_counter=(
            "Identify backup supervisors pre-close. "
            "Monitor ratio in first 90 days."
        ),
    ),
    PhysicianFrictionPoint(
        name="stark_antikickback_exposure",
        description=(
            "Restructuring distribution, ancillary "
            "ownership, or compensation creates Stark / "
            "AKS compliance exposure."
        ),
        probability="low",
        ebitda_impact_pct=0.10,
        early_signals=[
            "restructure_touches_referral_flow",
            "no_stark_compliance_review_planned",
            "ancillary_services_in_scope",
        ],
        partner_counter=(
            "Stark / AKS counsel review of final "
            "structure before close. Document safe-"
            "harbor compliance explicitly."
        ),
    ),
    PhysicianFrictionPoint(
        name="pms_ehr_change",
        description=(
            "Forced PMS / EHR platform switch dismantles "
            "workflow for 3-6 months. Physicians blame "
            "the new owner."
        ),
        probability="medium",
        ebitda_impact_pct=0.04,
        early_signals=[
            "ehr_change_in_100_day_plan",
            "no_physician_rep_on_selection_committee",
        ],
        partner_counter=(
            "Delay EHR change until year 2. Physician "
            "representatives on selection; pilot before "
            "rollout."
        ),
    ),
    PhysicianFrictionPoint(
        name="clinical_protocol_standardization",
        description=(
            "Physicians reject one-size-fits-all "
            "clinical protocols imposed by central "
            "practice management."
        ),
        probability="medium",
        ebitda_impact_pct=0.02,
        early_signals=[
            "standardization_day_1",
            "no_physician_advisory_board",
        ],
        partner_counter=(
            "Physician advisory board approves protocol "
            "changes; pilot with early-adopter sites."
        ),
    ),
]


@dataclass
class FrictionMatch:
    friction: PhysicianFrictionPoint
    signals_hit: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "friction": {
                "name": self.friction.name,
                "description": self.friction.description,
                "probability": self.friction.probability,
                "ebitda_impact_pct":
                    self.friction.ebitda_impact_pct,
                "partner_counter":
                    self.friction.partner_counter,
            },
            "signals_hit": list(self.signals_hit),
        }


@dataclass
class PhysicianFrictionReport:
    matches: List[FrictionMatch] = field(default_factory=list)
    expected_friction_ebitda_impact_pct: float = 0.0
    high_probability_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "expected_friction_ebitda_impact_pct":
                self.expected_friction_ebitda_impact_pct,
            "high_probability_count":
                self.high_probability_count,
            "partner_note": self.partner_note,
        }


_PROB_WEIGHT: Dict[str, float] = {
    "high": 0.80,
    "medium": 0.50,
    "low": 0.25,
}


def scan_physician_friction(
    signals: Dict[str, Any],
) -> PhysicianFrictionReport:
    matches: List[FrictionMatch] = []
    expected_impact = 0.0
    high_prob_count = 0
    for fp in FRICTION_LIBRARY:
        hit = [s for s in fp.early_signals
               if bool(signals.get(s, False))]
        if not hit:
            continue
        matches.append(FrictionMatch(
            friction=fp,
            signals_hit=hit,
        ))
        # Expected-value impact = probability × realized impact.
        prob_w = _PROB_WEIGHT.get(fp.probability, 0.50)
        expected_impact += prob_w * fp.ebitda_impact_pct
        if fp.probability == "high":
            high_prob_count += 1

    # Sort by probability tier then impact.
    prob_rank = {"high": 2, "medium": 1, "low": 0}
    matches.sort(key=lambda m: (
        -prob_rank.get(m.friction.probability, 0),
        -m.friction.ebitda_impact_pct,
    ))

    if not matches:
        note = (
            "No physician-friction signals detected. "
            "Partner: still tag the top-3 friction risks "
            "as explicit 100-day-plan items."
        )
    elif expected_impact >= 0.10:
        note = (
            f"Expected-value friction impact "
            f"{expected_impact*100:.1f}% of EBITDA with "
            f"{high_prob_count} high-probability risks. "
            "Partner: price the friction into underwrite "
            "+ 100-day plan must pre-empt each."
        )
    elif expected_impact >= 0.05:
        note = (
            f"Expected-value friction impact "
            f"{expected_impact*100:.1f}%. Partner: named "
            "mitigation per friction point in the 100-"
            "day plan."
        )
    else:
        note = (
            f"Expected-value friction impact "
            f"{expected_impact*100:.1f}%. Manageable; "
            "document mitigation but shape is clean."
        )

    return PhysicianFrictionReport(
        matches=matches,
        expected_friction_ebitda_impact_pct=round(
            expected_impact, 4
        ),
        high_probability_count=high_prob_count,
        partner_note=note,
    )


def list_friction_points() -> List[str]:
    return [fp.name for fp in FRICTION_LIBRARY]


def render_physician_friction_markdown(
    r: PhysicianFrictionReport,
) -> str:
    lines = [
        "# Physician-group friction",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Expected-value EBITDA impact: "
        f"{r.expected_friction_ebitda_impact_pct*100:.1f}%",
        f"- High-probability risks: {r.high_probability_count}",
        f"- Total matches: {len(r.matches)}",
        "",
        "| Friction | Probability | Impact | "
        "Partner counter |",
        "|---|---|---|---|",
    ]
    for m in r.matches:
        fp = m.friction
        lines.append(
            f"| {fp.name} | {fp.probability} | "
            f"{fp.ebitda_impact_pct*100:.0f}% EBITDA | "
            f"{fp.partner_counter} |"
        )
    return "\n".join(lines)
