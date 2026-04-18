"""CMS annual rule cycle tracker — which rules touch this deal's service lines.

Partner statement: "The CMS rule cycle is a calendar
you can set your watch to. IPPS proposed April /
final July. OPPS proposed July / final November.
MPFS proposed July / final November. MA Advance
Notice February / Rate Announcement April. Each rule
touches specific service lines. If the deal's
revenue is ambulatory surgery, OPPS and MPFS are the
ones that matter. If it's inpatient, IPPS is the
whole year."

Distinct from:
- `regulatory_watch` — general event registry.
- `reimbursement_cliff_calendar_2026_2029` — broader
  CMS/state calendar.
- `healthcare_regulatory_calendar` — event list.

This module names the **4 annual CMS rules** with
their cycle dates, the service lines each rule
touches, and surfaces which rules matter given the
deal's service-line profile.

### 4 major CMS rules

- **IPPS** (Inpatient Prospective Payment System):
  hospital inpatient rates. Proposed April, final
  July/August, effective October 1.
- **OPPS** (Outpatient Prospective Payment System):
  hospital outpatient + ASC rates. Proposed July,
  final November, effective January 1.
- **MPFS** (Medicare Physician Fee Schedule):
  physician services. Proposed July, final November,
  effective January 1.
- **MA Rates** (Medicare Advantage): Advance Notice
  February, Rate Announcement April, effective
  January 1.

### Service-line → rule mapping

- Inpatient medicine / surgery → IPPS
- Outpatient surgery (HOPD, ASC) → OPPS
- Physician office / eval-mgmt → MPFS
- MA risk contracts → MA rates

### Output

Active rules in current cycle + which apply to
deal's mix + partner note on diligence focus.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RULES: Dict[str, Dict[str, Any]] = {
    "IPPS": {
        "proposed_month": 4,
        "final_month": 8,
        "effective_month": 10,
        "service_lines": {
            "inpatient_medicine",
            "inpatient_surgery",
            "acute_care_hospital",
        },
        "partner_note_template": (
            "IPPS affects inpatient rates; watch the "
            "proposed rule in April for market-basket, "
            "readmission penalties, and wage index "
            "changes."
        ),
    },
    "OPPS": {
        "proposed_month": 7,
        "final_month": 11,
        "effective_month": 1,  # next year
        "service_lines": {
            "hopd_outpatient",
            "asc",
            "outpatient_surgery",
            "infusion",
            "observation",
        },
        "partner_note_template": (
            "OPPS drives HOPD and ASC rates; site-"
            "neutral expansion is the big signal. "
            "Watch July proposed for new service lines "
            "added."
        ),
    },
    "MPFS": {
        "proposed_month": 7,
        "final_month": 11,
        "effective_month": 1,
        "service_lines": {
            "physician_office",
            "evaluation_management",
            "professional_services",
            "telehealth",
        },
        "partner_note_template": (
            "MPFS conversion factor + code-level RVU "
            "changes hit physician deals. Watch for "
            "specialty-specific RVU updates."
        ),
    },
    "MA_RATES": {
        "proposed_month": 2,
        "final_month": 4,
        "effective_month": 1,
        "service_lines": {
            "medicare_advantage",
            "ma_risk_contract",
            "capitation",
        },
        "partner_note_template": (
            "MA Rate Announcement in April sets PMPM "
            "benchmarks; risk-score recalibration + "
            "star-bonus changes drive contract "
            "economics."
        ),
    },
}


@dataclass
class ServiceLineProfile:
    service_line: str
    share_of_npr_pct: float


@dataclass
class CMSRuleCycleInputs:
    service_lines: List[ServiceLineProfile] = field(
        default_factory=list)
    current_month: int = 4


@dataclass
class RuleTouch:
    rule: str
    applies: bool
    touched_service_lines: List[str] = field(
        default_factory=list)
    combined_npr_share_pct: float = 0.0
    cycle_stage: str = ""  # "proposed_phase" / "final_phase" / "effective" / "pre_cycle"
    partner_note: str = ""


@dataclass
class CMSRuleCycleReport:
    rules: List[RuleTouch] = field(default_factory=list)
    applicable_rules_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": [
                {"rule": r.rule,
                 "applies": r.applies,
                 "touched_service_lines":
                     r.touched_service_lines,
                 "combined_npr_share_pct":
                     r.combined_npr_share_pct,
                 "cycle_stage": r.cycle_stage,
                 "partner_note": r.partner_note}
                for r in self.rules
            ],
            "applicable_rules_count":
                self.applicable_rules_count,
            "partner_note": self.partner_note,
        }


def _cycle_stage(
    current_month: int,
    proposed_month: int,
    final_month: int,
    effective_month: int,
) -> str:
    # Assumes effective_month might be < proposed for MA
    # (MA: prop Feb, final Apr, effective Jan next year)
    if proposed_month <= current_month < final_month:
        return "proposed_phase"
    if current_month >= final_month:
        return "final_phase"
    if current_month < proposed_month:
        return "pre_cycle"
    return "effective"


def track_cms_rule_cycle(
    inputs: CMSRuleCycleInputs,
) -> CMSRuleCycleReport:
    rules: List[RuleTouch] = []
    applicable = 0
    for rule_name, rule_spec in RULES.items():
        touched = [
            sl.service_line for sl in inputs.service_lines
            if sl.service_line in rule_spec["service_lines"]
        ]
        combined_share = sum(
            sl.share_of_npr_pct
            for sl in inputs.service_lines
            if sl.service_line in rule_spec["service_lines"]
        )
        applies = len(touched) > 0
        if applies:
            applicable += 1
        stage = _cycle_stage(
            inputs.current_month,
            rule_spec["proposed_month"],
            rule_spec["final_month"],
            rule_spec["effective_month"],
        )
        note = (
            rule_spec["partner_note_template"]
            if applies
            else f"Rule does not touch deal service mix."
        )
        rules.append(RuleTouch(
            rule=rule_name,
            applies=applies,
            touched_service_lines=touched,
            combined_npr_share_pct=round(
                combined_share, 4),
            cycle_stage=stage,
            partner_note=note,
        ))

    # Highest-exposure rule drives aggregate partner note
    rules_sorted = sorted(
        rules,
        key=lambda r: r.combined_npr_share_pct,
        reverse=True,
    )
    top = rules_sorted[0] if rules else None
    if top and top.applies and top.combined_npr_share_pct >= 0.30:
        note = (
            f"{top.rule} touches "
            f"{top.combined_npr_share_pct:.0%} of NPR "
            f"({', '.join(top.touched_service_lines)}) "
            f"and is in {top.cycle_stage}. Priority rule "
            "for diligence cycle; allocate counsel + "
            "specialist time."
        )
    elif applicable > 0:
        note = (
            f"{applicable} CMS rule(s) touch deal "
            "service mix. Modest exposure; monitor "
            "proposed rules but not IC-blocking."
        )
    else:
        note = (
            "No CMS rules touch deal service mix — "
            "deal is not CMS-rate-driven."
        )

    return CMSRuleCycleReport(
        rules=rules,
        applicable_rules_count=applicable,
        partner_note=note,
    )


def render_cms_rule_cycle_markdown(
    r: CMSRuleCycleReport,
) -> str:
    lines = [
        "# CMS annual rule cycle",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Applicable rules: "
        f"{r.applicable_rules_count}/4",
        "",
        "| Rule | Applies | NPR share | Cycle stage | Service lines |",
        "|---|---|---|---|---|",
    ]
    for rule in r.rules:
        lines.append(
            f"| {rule.rule} | "
            f"{'yes' if rule.applies else 'no'} | "
            f"{rule.combined_npr_share_pct:.0%} | "
            f"{rule.cycle_stage} | "
            f"{', '.join(rule.touched_service_lines) if rule.touched_service_lines else '—'} |"
        )
    for rule in r.rules:
        if rule.applies:
            lines.append("")
            lines.append(f"### {rule.rule}")
            lines.append(f"- {rule.partner_note}")
    return "\n".join(lines)
