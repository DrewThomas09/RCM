"""Carve-out risks — risks unique to divestiture deals.

Buying a business that is being carved out of a parent is harder
than buying a standalone:

- Shared services (IT, HR, finance, legal) need to be rebuilt or
  transitioned.
- Customer contracts may be assigned with carve-out provisions
  (change-of-control → re-sign, re-price, terminate).
- Payer contracts (in healthcare) may need re-credentialing on
  new NPI/TIN.
- Carve-out financial statements differ from audited consolidated
  (allocations are judgmental — verify).
- Transition Services Agreement (TSA) scope, duration, and cost
  govern the first 12-24 months.

This module scores carve-out-specific risks and produces a
diligence checklist + partner-priority ranking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CarveOutInputs:
    is_healthcare: bool = True
    shared_services_count: int = 0        # IT, HR, finance, legal, procurement, etc.
    tsa_duration_months: int = 12
    tsa_scope_coverage_pct: float = 0.80  # % of shared services covered by TSA
    has_separate_financials: bool = False  # carve-out financials audited?
    change_of_control_contracts_pct: float = 0.30  # % of revenue with CoC clauses
    shared_it_systems_count: int = 0
    parent_brand_dependency: bool = False
    payer_contracts_to_recredential: int = 0       # healthcare-specific
    key_employees_retained_pct: float = 0.80       # expected retention


@dataclass
class CarveOutRisk:
    name: str
    severity: str                         # "low" / "medium" / "high"
    estimated_cost_m: float               # one-time separation cost
    estimated_months: int                 # timeline to resolve
    description: str
    mitigation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "estimated_cost_m": self.estimated_cost_m,
            "estimated_months": self.estimated_months,
            "description": self.description,
            "mitigation": self.mitigation,
        }


@dataclass
class CarveOutAssessment:
    risks: List[CarveOutRisk] = field(default_factory=list)
    total_separation_cost_m: float = 0.0
    longest_path_months: int = 0
    high_severity_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risks": [r.to_dict() for r in self.risks],
            "total_separation_cost_m": self.total_separation_cost_m,
            "longest_path_months": self.longest_path_months,
            "high_severity_count": self.high_severity_count,
            "partner_note": self.partner_note,
        }


def assess_carve_out(inputs: CarveOutInputs) -> CarveOutAssessment:
    risks: List[CarveOutRisk] = []

    # TSA coverage risk.
    if inputs.tsa_scope_coverage_pct < 0.80:
        sev = "high" if inputs.tsa_scope_coverage_pct < 0.50 else "medium"
        risks.append(CarveOutRisk(
            name="TSA coverage gap",
            severity=sev,
            estimated_cost_m=2.0 + (1 - inputs.tsa_scope_coverage_pct) * 10.0,
            estimated_months=max(inputs.tsa_duration_months, 6),
            description=(f"TSA only covers "
                         f"{inputs.tsa_scope_coverage_pct*100:.0f}% of "
                         "shared services — gaps must be stood up "
                         "independently on Day 1."),
            mitigation=("Expand TSA scope in purchase agreement or "
                        "budget build-out before close."),
        ))

    # TSA duration risk.
    if inputs.tsa_duration_months < 12:
        risks.append(CarveOutRisk(
            name="Short TSA duration",
            severity="medium",
            estimated_cost_m=3.0,
            estimated_months=18,
            description=(f"TSA expires in {inputs.tsa_duration_months} months "
                         "— standalone IT/HR/finance infrastructure must be "
                         "operational before then."),
            mitigation=("Negotiate TSA extension options; start "
                        "standalone build in parallel."),
        ))

    # Change-of-control contracts.
    if inputs.change_of_control_contracts_pct >= 0.20:
        sev = "high" if inputs.change_of_control_contracts_pct >= 0.40 else "medium"
        risks.append(CarveOutRisk(
            name="Change-of-control contract exposure",
            severity=sev,
            estimated_cost_m=inputs.change_of_control_contracts_pct * 5.0,
            estimated_months=9,
            description=(f"{inputs.change_of_control_contracts_pct*100:.0f}% "
                         "of revenue carries CoC clauses — customers can "
                         "re-price or exit."),
            mitigation=("Pre-close consent outreach; prioritize top-20 "
                        "customers; legal review of CoC triggers."),
        ))

    # Carve-out financials quality.
    if not inputs.has_separate_financials:
        risks.append(CarveOutRisk(
            name="Unaudited carve-out financials",
            severity="high",
            estimated_cost_m=1.5,
            estimated_months=4,
            description=("Carve-out financials are management allocations, "
                         "not audited standalone — allocation methodology "
                         "drives EBITDA materially."),
            mitigation=("Engage accounting firm to validate allocations; "
                        "request parent's cost accounting manuals."),
        ))

    # Shared IT systems.
    if inputs.shared_it_systems_count >= 3:
        risks.append(CarveOutRisk(
            name="Shared IT system migration",
            severity="high" if inputs.shared_it_systems_count >= 5 else "medium",
            estimated_cost_m=2.0 * inputs.shared_it_systems_count,
            estimated_months=14,
            description=(f"{inputs.shared_it_systems_count} IT systems "
                         "shared with parent — ERP, CRM, data warehouse, "
                         "email, identity; each requires migration or "
                         "licensing."),
            mitigation=("Build-vs-buy analysis per system; stand up "
                        "standalone identity/email first."),
        ))

    # Parent brand dependency.
    if inputs.parent_brand_dependency:
        risks.append(CarveOutRisk(
            name="Parent brand dependency",
            severity="medium",
            estimated_cost_m=3.0,
            estimated_months=12,
            description=("Business relies on parent brand for customer "
                         "trust / regulatory licensing — rebrand required."),
            mitigation=("Brand transition plan; customer communication; "
                        "co-branding during TSA."),
        ))

    # Payer re-credentialing (healthcare).
    if inputs.is_healthcare and inputs.payer_contracts_to_recredential >= 5:
        sev = ("high" if inputs.payer_contracts_to_recredential >= 20
               else "medium")
        risks.append(CarveOutRisk(
            name="Payer re-credentialing",
            severity=sev,
            estimated_cost_m=0.3 * inputs.payer_contracts_to_recredential,
            estimated_months=9,
            description=(f"{inputs.payer_contracts_to_recredential} payer "
                         "contracts require re-credentialing on new NPI/TIN "
                         "— 90-120 day typical timeline each, potential "
                         "claims hold."),
            mitigation=("Start credentialing paperwork pre-close; "
                        "negotiate interim billing under parent's NPI."),
        ))

    # Employee retention risk.
    if inputs.key_employees_retained_pct < 0.75:
        risks.append(CarveOutRisk(
            name="Key employee flight risk",
            severity=("high" if inputs.key_employees_retained_pct < 0.60
                      else "medium"),
            estimated_cost_m=5.0,
            estimated_months=6,
            description=(f"Only {inputs.key_employees_retained_pct*100:.0f}% "
                         "of key employees expected to stay post-close — "
                         "operational continuity at risk."),
            mitigation=("Retention bonuses; MIP equity offers; "
                        "identify critical-path roles."),
        ))

    total = sum(r.estimated_cost_m for r in risks)
    longest = max((r.estimated_months for r in risks), default=0)
    high = sum(1 for r in risks if r.severity == "high")

    if high >= 3:
        note = (f"Severe carve-out profile: {high} high-severity risks. "
                f"Estimated ${total:,.1f}M separation cost, "
                f"{longest}-month longest path. Re-underwrite.")
    elif high >= 1:
        note = (f"Material carve-out exposure: {high} high-severity "
                f"risk(s), ${total:,.1f}M separation budget.")
    elif risks:
        note = (f"Standard carve-out profile: {len(risks)} manageable "
                f"risks, ${total:,.1f}M separation budget.")
    else:
        note = "Clean carve-out — no flagged risks."

    return CarveOutAssessment(
        risks=risks,
        total_separation_cost_m=round(total, 2),
        longest_path_months=longest,
        high_severity_count=high,
        partner_note=note,
    )


def render_carve_out_markdown(a: CarveOutAssessment) -> str:
    lines = [
        "# Carve-out risk assessment",
        "",
        f"_{a.partner_note}_",
        "",
        f"- Total separation cost estimate: ${a.total_separation_cost_m:,.1f}M",
        f"- Longest-path timeline: {a.longest_path_months} months",
        f"- High-severity risk count: {a.high_severity_count}",
        "",
        "## Risks",
        "",
    ]
    for r in a.risks:
        lines.append(f"### {r.name} ({r.severity})")
        lines.append(f"- {r.description}")
        lines.append(f"- Estimated cost: ${r.estimated_cost_m:,.1f}M | "
                     f"Timeline: {r.estimated_months} months")
        lines.append(f"- Mitigation: {r.mitigation}")
        lines.append("")
    return "\n".join(lines)
