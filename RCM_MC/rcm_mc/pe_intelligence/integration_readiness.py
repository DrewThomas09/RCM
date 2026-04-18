"""Integration readiness — post-close integration scorecard.

Different from `hundred_day_plan.py` (which is the action list),
this module scores whether the deal TEAM is ready to integrate.
Partners commonly lose value here because integration bandwidth
is the binding constraint, not the plan itself.

Dimensions:

1. **Integration officer** — named pre-close?
2. **Day-1 systems plan** — which systems cutover day-1 vs deferred?
3. **Management continuity** — CEO/CFO retained + comp aligned?
4. **Cross-functional workstream leads** — IT, RCM, clinical,
   finance, HR each have a named lead?
5. **Budget** — integration budget sized and allocated?
6. **Communications plan** — employees / physicians / payers / patients?

Returns a 0..100 readiness score + gap list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IntegrationInputs:
    integration_officer_named: Optional[bool] = None
    day_one_system_plan_ready: Optional[bool] = None
    management_retention_signed: Optional[bool] = None
    management_comp_aligned: Optional[bool] = None
    rcm_lead_named: Optional[bool] = None
    it_lead_named: Optional[bool] = None
    clinical_lead_named: Optional[bool] = None
    finance_lead_named: Optional[bool] = None
    hr_lead_named: Optional[bool] = None
    integration_budget_sized: Optional[bool] = None
    communications_plan_ready: Optional[bool] = None
    tsa_duration_months: Optional[int] = None
    has_rollup_thesis: Optional[bool] = None


@dataclass
class IntegrationFinding:
    area: str
    score: int                         # 0..100
    status: str                        # "ready" | "gap" | "unknown"
    commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "score": self.score,
            "status": self.status,
            "commentary": self.commentary,
        }


@dataclass
class IntegrationReport:
    score: int                          # 0..100
    verdict: str                        # "ready" | "qualified" | "not_ready"
    findings: List[IntegrationFinding] = field(default_factory=list)
    gap_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
            "gap_count": self.gap_count,
            "partner_note": self.partner_note,
        }


def _yn(value: Optional[bool], area: str,
        ready_text: str, gap_text: str) -> IntegrationFinding:
    if value is True:
        return IntegrationFinding(area=area, score=100, status="ready",
                                   commentary=ready_text)
    if value is False:
        return IntegrationFinding(area=area, score=0, status="gap",
                                   commentary=gap_text)
    return IntegrationFinding(area=area, score=50, status="unknown",
                               commentary="Status unknown.")


_WEIGHTS = {
    "integration_officer": 0.15,
    "day_one_systems": 0.10,
    "mgmt_retention": 0.10,
    "mgmt_comp_alignment": 0.08,
    "rcm_lead": 0.10,
    "it_lead": 0.08,
    "clinical_lead": 0.08,
    "finance_lead": 0.08,
    "hr_lead": 0.07,
    "integration_budget": 0.08,
    "communications_plan": 0.08,
}


def assess_integration_readiness(
    inputs: IntegrationInputs,
) -> IntegrationReport:
    findings: List[IntegrationFinding] = [
        _yn(inputs.integration_officer_named, "integration_officer",
            "Named integration officer pre-close.",
            "No named integration officer — critical gap."),
        _yn(inputs.day_one_system_plan_ready, "day_one_systems",
            "Day-1 system plan ready.",
            "No day-1 system plan — expect operational hiccups."),
        _yn(inputs.management_retention_signed, "mgmt_retention",
            "Management retention signed.",
            "Management retention not secured — transition risk."),
        _yn(inputs.management_comp_aligned, "mgmt_comp_alignment",
            "Management comp aligned to deal thesis.",
            "Management comp not aligned — incentive gap."),
        _yn(inputs.rcm_lead_named, "rcm_lead",
            "RCM workstream lead named.",
            "No RCM workstream lead — lever plan at risk."),
        _yn(inputs.it_lead_named, "it_lead",
            "IT workstream lead named.",
            "No IT workstream lead — systems integration at risk."),
        _yn(inputs.clinical_lead_named, "clinical_lead",
            "Clinical workstream lead named.",
            "No clinical workstream lead — quality continuity at risk."),
        _yn(inputs.finance_lead_named, "finance_lead",
            "Finance workstream lead named.",
            "No finance workstream lead — reporting at risk."),
        _yn(inputs.hr_lead_named, "hr_lead",
            "HR workstream lead named.",
            "No HR workstream lead — comms / retention at risk."),
        _yn(inputs.integration_budget_sized, "integration_budget",
            "Integration budget sized and approved.",
            "Integration budget not sized — cost surprises likely."),
        _yn(inputs.communications_plan_ready, "communications_plan",
            "Communications plan ready.",
            "No communications plan — day-1 uncertainty for staff."),
    ]

    # Composite: weighted average.
    total_weight = sum(_WEIGHTS.values())
    weighted = sum(f.score * _WEIGHTS.get(f.area, 0.0) for f in findings)
    composite = int(round(weighted / max(total_weight, 1e-9)))

    gap_count = sum(1 for f in findings if f.status == "gap")

    # TSA duration penalty: long TSAs compound integration risk.
    if inputs.tsa_duration_months is not None and inputs.tsa_duration_months > 12:
        composite = max(0, composite - 8)

    # Rollup thesis: integration_officer is even more critical.
    if inputs.has_rollup_thesis and not inputs.integration_officer_named:
        composite = max(0, composite - 10)

    if composite >= 80:
        verdict = "ready"
        note = "Integration machinery is in place. Proceed on schedule."
    elif composite >= 60:
        verdict = "qualified"
        note = (f"{gap_count} gap(s) remain. Close the highest-weight "
                "gaps before close or plan to absorb the integration risk.")
    else:
        verdict = "not_ready"
        note = ("Materially unready for integration. Delay close or "
                "flex the lever plan to account for integration lag.")

    return IntegrationReport(
        score=composite,
        verdict=verdict,
        findings=findings,
        gap_count=gap_count,
        partner_note=note,
    )


def render_integration_report_markdown(
    report: IntegrationReport,
) -> str:
    lines = [
        "# Integration readiness",
        "",
        f"**Score:** {report.score}/100  ",
        f"**Verdict:** {report.verdict}  ",
        f"**Gap count:** {report.gap_count}",
        "",
        f"_{report.partner_note}_",
        "",
        "| Area | Score | Status | Commentary |",
        "|---|---:|---|---|",
    ]
    for f in report.findings:
        lines.append(
            f"| {f.area} | {f.score} | {f.status} | {f.commentary} |"
        )
    return "\n".join(lines)
