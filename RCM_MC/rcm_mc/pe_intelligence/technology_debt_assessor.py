"""Technology debt assessor — score tech-debt drag on the deal.

Healthcare services companies often carry significant technology
debt: aged EHRs, fragmented billing systems, homegrown RCM
tooling, insufficient security posture. Under new PE ownership,
this debt shows up as:

- **Scalability blockers** on M&A integration.
- **Cybersecurity exposure** (regulatory and reputational).
- **Operational drag** (manual processes, data gaps).
- **Exit-readiness gaps** (strategic buyers discount legacy tech).

This module scores tech debt across dimensions and quantifies
**remediation cost + timeline + urgency**.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TechDebtInputs:
    ehr_system: str = "modern"            # "modern" / "aging" / "legacy"
    ehr_age_years: int = 3
    billing_system: str = "modern"        # same
    integrations_count: int = 5           # number of integrations
    has_api_layer: bool = True
    has_cloud_migration: bool = True
    has_sso: bool = True
    has_mfa: bool = True
    has_soc2: bool = False
    has_hitrust: bool = False
    pen_test_recent: bool = False         # within last 12 months
    data_warehouse_status: str = "modern"  # "modern" / "partial" / "none"
    outage_hours_last_12mo: float = 0.0
    it_spend_pct_revenue: float = 0.03
    eng_headcount_per_1k_employees: float = 5.0


@dataclass
class TechDebtFinding:
    area: str
    severity: str                         # "low" / "medium" / "high"
    cost_m: float
    months: int
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area, "severity": self.severity,
            "cost_m": self.cost_m, "months": self.months,
            "description": self.description,
        }


@dataclass
class TechDebtReport:
    total_remediation_m: float
    longest_path_months: int
    total_findings: int
    high_severity: int
    risk_score_0_100: int                 # higher = worse
    findings: List[TechDebtFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_remediation_m": self.total_remediation_m,
            "longest_path_months": self.longest_path_months,
            "total_findings": self.total_findings,
            "high_severity": self.high_severity,
            "risk_score_0_100": self.risk_score_0_100,
            "findings": [f.to_dict() for f in self.findings],
            "partner_note": self.partner_note,
        }


def _ehr_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.ehr_system == "legacy" or inputs.ehr_age_years >= 12:
        return TechDebtFinding(
            area="EHR", severity="high",
            cost_m=15.0, months=24,
            description=("Legacy / aged EHR — data model is out-of-date, "
                         "integration surface thin, vendor upgrade path "
                         "uncertain. Full replacement typically $10-20M."),
        )
    if inputs.ehr_system == "aging" or inputs.ehr_age_years >= 8:
        return TechDebtFinding(
            area="EHR", severity="medium",
            cost_m=3.0, months=12,
            description=("Aging EHR — upgrade or modernization program "
                         "needed within 3 years."),
        )
    return None


def _billing_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.billing_system == "legacy":
        return TechDebtFinding(
            area="Billing / RCM", severity="high",
            cost_m=5.0, months=18,
            description=("Legacy billing system — limits RCM lever upside. "
                         "Common target for platform consolidation."),
        )
    if inputs.billing_system == "aging":
        return TechDebtFinding(
            area="Billing / RCM", severity="medium",
            cost_m=1.5, months=9,
            description=("Aging billing system — invest in interface "
                         "upgrades to support claims automation."),
        )
    return None


def _integration_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.integrations_count >= 20 and not inputs.has_api_layer:
        return TechDebtFinding(
            area="Integrations", severity="high",
            cost_m=2.5, months=12,
            description=(f"{inputs.integrations_count} point-to-point "
                         "integrations without a shared API layer — "
                         "every change ripples across all connections."),
        )
    if inputs.integrations_count >= 10 and not inputs.has_api_layer:
        return TechDebtFinding(
            area="Integrations", severity="medium",
            cost_m=1.0, months=6,
            description=(f"{inputs.integrations_count} integrations but "
                         "no API layer — invest in integration hub."),
        )
    return None


def _security_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    gaps = []
    if not inputs.has_mfa:
        gaps.append("MFA missing")
    if not inputs.has_sso:
        gaps.append("SSO missing")
    if not inputs.has_soc2 and not inputs.has_hitrust:
        gaps.append("no SOC 2 or HITRUST")
    if not inputs.pen_test_recent:
        gaps.append("no recent pen test")
    if gaps:
        high = len(gaps) >= 3
        return TechDebtFinding(
            area="Security", severity="high" if high else "medium",
            cost_m=0.8 * len(gaps), months=6,
            description=(f"Security gaps: {', '.join(gaps)}. Remediate "
                         "before any customer-facing diligence."),
        )
    return None


def _data_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.data_warehouse_status == "none":
        return TechDebtFinding(
            area="Data / analytics", severity="high",
            cost_m=2.0, months=12,
            description=("No data warehouse — reporting and KPI "
                         "operations are manual. Blocker for platform "
                         "KPI rollup."),
        )
    if inputs.data_warehouse_status == "partial":
        return TechDebtFinding(
            area="Data / analytics", severity="medium",
            cost_m=1.0, months=6,
            description=("Partial data warehouse — gaps in coverage; "
                         "finish the build for platform KPI rollup."),
        )
    return None


def _uptime_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.outage_hours_last_12mo > 48:
        return TechDebtFinding(
            area="Uptime / reliability", severity="high",
            cost_m=1.5, months=9,
            description=(f"{inputs.outage_hours_last_12mo:.0f} hours of "
                         "outage in last 12 months — structural reliability "
                         "work required (observability, HA)."),
        )
    if inputs.outage_hours_last_12mo > 16:
        return TechDebtFinding(
            area="Uptime / reliability", severity="medium",
            cost_m=0.5, months=4,
            description=(f"{inputs.outage_hours_last_12mo:.0f} outage hours "
                         "— add observability and runbook discipline."),
        )
    return None


def _staffing_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if inputs.eng_headcount_per_1k_employees < 2.0:
        return TechDebtFinding(
            area="Eng staffing", severity="high",
            cost_m=3.0, months=12,
            description=(f"Engineering density "
                         f"{inputs.eng_headcount_per_1k_employees:.1f}/1k — "
                         "understaffed for platform demands."),
        )
    return None


def _cloud_finding(inputs: TechDebtInputs) -> Optional[TechDebtFinding]:
    if not inputs.has_cloud_migration:
        return TechDebtFinding(
            area="Infrastructure", severity="medium",
            cost_m=2.0, months=18,
            description=("On-premise infrastructure — capex intensity and "
                         "DR risk. Plan cloud migration."),
        )
    return None


def assess_technology_debt(inputs: TechDebtInputs) -> TechDebtReport:
    findings = [f for f in [
        _ehr_finding(inputs),
        _billing_finding(inputs),
        _integration_finding(inputs),
        _security_finding(inputs),
        _data_finding(inputs),
        _uptime_finding(inputs),
        _staffing_finding(inputs),
        _cloud_finding(inputs),
    ] if f is not None]

    total_cost = sum(f.cost_m for f in findings)
    longest = max((f.months for f in findings), default=0)
    high = sum(1 for f in findings if f.severity == "high")
    med = sum(1 for f in findings if f.severity == "medium")

    # Risk score 0-100: higher = worse.
    score = min(100, 15 * high + 7 * med)

    if high >= 3:
        note = (f"Significant tech debt: {high} high-severity findings, "
                f"~${total_cost:,.1f}M and {longest}mo remediation. "
                "Flag to IC as material pre-close risk.")
    elif high >= 1:
        note = (f"Material tech-debt remediation budget "
                f"(~${total_cost:,.1f}M, {longest}mo) required. "
                "Fold into 100-day plan.")
    elif findings:
        note = (f"Manageable tech debt (~${total_cost:,.1f}M). "
                "Include in operating plan.")
    else:
        note = "Technology posture is clean — no material findings."

    return TechDebtReport(
        total_remediation_m=round(total_cost, 2),
        longest_path_months=longest,
        total_findings=len(findings),
        high_severity=high,
        risk_score_0_100=score,
        findings=findings,
        partner_note=note,
    )


def render_tech_debt_markdown(report: TechDebtReport) -> str:
    lines = [
        "# Technology debt assessment",
        "",
        f"_{report.partner_note}_",
        "",
        f"- Risk score: {report.risk_score_0_100}/100",
        f"- Total remediation cost: ${report.total_remediation_m:,.1f}M",
        f"- Longest path: {report.longest_path_months} months",
        f"- Findings: {report.total_findings} "
        f"({report.high_severity} high)",
        "",
        "## Findings",
        "",
    ]
    for f in report.findings:
        lines.append(f"### {f.area} ({f.severity.upper()})")
        lines.append(f"- {f.description}")
        lines.append(f"- Cost: ${f.cost_m:,.1f}M | Timeline: {f.months} months")
        lines.append("")
    return "\n".join(lines)
