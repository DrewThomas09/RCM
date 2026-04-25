"""ISSB IFRS S1 / S2 structured disclosure renderer.

The four-pillar framework that the IFRS Sustainability Standards
mandate:

    Governance       — oversight processes for the topic
    Strategy         — risks and opportunities, time horizons
    Risk Management  — process for identifying, assessing, monitoring
    Metrics & Targets — quantitative measures + forward targets

S1 covers all sustainability-related topics (workforce, governance,
human rights, etc.). S2 is climate-specific (transition plan,
scenario analysis, Scope 1/2/3 emissions).

The existing disclosure.py emits section headings but doesn't
ENFORCE the four-pillar structure — making it harder for an LP
to map our output to the IFRS form they have to file. This module
fixes that with a structured renderer that produces a doc whose
section ordering exactly matches the standard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .carbon import Facility, aggregate_portfolio_footprint
from .dei import DEIMetrics
from .governance import GovernanceScore


@dataclass
class ISSBPillar:
    """One of the four mandated pillars."""
    name: str
    bullets: List[str] = field(default_factory=list)


@dataclass
class ISSBStandardReport:
    """S1 or S2 four-pillar block."""
    standard: str           # "S1" or "S2"
    governance: ISSBPillar
    strategy: ISSBPillar
    risk_management: ISSBPillar
    metrics_and_targets: ISSBPillar


def render_ifrs_s1(
    company_name: str,
    *,
    governance: Optional[GovernanceScore] = None,
    dei: Optional[DEIMetrics] = None,
    cpom_disclosed: bool = False,
) -> ISSBStandardReport:
    """Build the IFRS S1 (general sustainability) four-pillar
    block from the inputs the diligence team has on hand.

    The four pillars are structured even when an input is missing
    — partners get a defensible "this is what we know, this is
    what's still required" view rather than an empty section.
    """
    g_pillar = ISSBPillar(name="Governance")
    if governance:
        g_pillar.bullets.extend([
            f"Composite governance score: "
            f"{governance.composite:.2f} / 1.00",
            f"Board independence: "
            f"{governance.board_independence*100:.0f}%",
            f"Audit / compliance score: "
            f"{governance.audit_compliance:.2f} / 1.00",
        ])
        if cpom_disclosed:
            g_pillar.bullets.append(
                "Friendly-PC / MSO structure disclosed in the "
                "data room and in audited financials.")
        else:
            g_pillar.bullets.append(
                "Friendly-PC / MSO structure not yet disclosed — "
                "remediation in the next reporting period.")
    else:
        g_pillar.bullets.append(
            "Governance score not yet computed — partner to "
            "complete during onsite.")

    s_pillar = ISSBPillar(name="Strategy")
    s_pillar.bullets.extend([
        "Sustainability risks: workforce attrition, payer-mix "
        "concentration, regulatory exposure (FTC noncompete, "
        "state CON/CPOM, OPPS site-neutral, V28 cliff).",
        "Opportunities: value-based-care contract growth, "
        "specialty-pharmacy expansion, AI-enabled RCM.",
        "Time horizons: short (12mo), medium (3yr hold), long "
        "(5yr hold + exit).",
    ])

    r_pillar = ISSBPillar(name="Risk Management")
    r_pillar.bullets.extend([
        "Quarterly risk-review cycle with the operating partner.",
        "Annual third-party compliance audit.",
        "Cross-portfolio dashboard tracking concentration + "
        "regulatory exposure.",
    ])

    m_pillar = ISSBPillar(name="Metrics and Targets")
    if dei:
        m_pillar.bullets.append(
            f"Female workforce: {dei.pct_female*100:.1f}%; "
            f"in management: {dei.pct_female_in_management*100:.1f}%.")
        m_pillar.bullets.append(
            f"Pay-equity ratio (female / male): "
            f"{dei.pay_equity_ratio:.3f}.")
        m_pillar.bullets.append(
            f"Annual voluntary turnover: "
            f"{dei.annual_turnover_rate*100:.1f}%.")
    else:
        m_pillar.bullets.append(
            "Workforce metrics not yet captured — required by "
            "next reporting cycle.")
    m_pillar.bullets.append(
        "Forward target: maintain pay-equity ratio ≥ 0.95 + "
        "voluntary turnover ≤ 12% across the hold.")

    return ISSBStandardReport(
        standard="S1", governance=g_pillar, strategy=s_pillar,
        risk_management=r_pillar,
        metrics_and_targets=m_pillar,
    )


def render_ifrs_s2(
    company_name: str,
    facilities: Optional[List[Facility]] = None,
    *,
    transition_plan_drafted: bool = False,
) -> ISSBStandardReport:
    """Build the IFRS S2 (climate-specific) four-pillar block.

    Scope 1/2/3 emissions land in the Metrics & Targets pillar.
    Strategy pillar carries the transition-plan summary; partners
    typically have this drafted post-close in the 100-day plan.
    """
    g_pillar = ISSBPillar(name="Governance")
    g_pillar.bullets.append(
        "Climate oversight assigned to the operating-partner-on-"
        "deal — quarterly review with the board ESG committee.")

    s_pillar = ISSBPillar(name="Strategy")
    if transition_plan_drafted:
        s_pillar.bullets.append(
            "Decarbonisation transition plan drafted: targets "
            "renewable-electricity 50% by 2030, anesthetic-gas "
            "shift to lower-GWP agents, fleet electrification.")
    else:
        s_pillar.bullets.append(
            "Transition plan in progress — first draft due in "
            "the next 100-day cycle.")
    s_pillar.bullets.append(
        "Climate-related opportunities: CMS sustainability "
        "incentives, energy-cost reduction from grid-mix shifts, "
        "anesthetic-gas margin from sevoflurane → desflurane "
        "phase-out.")
    s_pillar.bullets.append(
        "Scenario analysis: 1.5°C / 2.0°C transition pathways "
        "modeled against the asset's 5yr hold.")

    r_pillar = ISSBPillar(name="Risk Management")
    r_pillar.bullets.extend([
        "Annual Scope 1/2/3 inventory.",
        "Facility-level energy-audit cycle.",
        "Monitoring of state-grid emission factors for Scope 2 "
        "drift.",
    ])

    m_pillar = ISSBPillar(name="Metrics and Targets")
    if facilities:
        agg = aggregate_portfolio_footprint(facilities)
        m_pillar.bullets.append(
            f"Scope 1: {agg['scope_1_kgco2e']:,.0f} kgCO2e "
            f"across {agg['facility_count']} facilities.")
        m_pillar.bullets.append(
            f"Scope 2: {agg['scope_2_kgco2e']:,.0f} kgCO2e "
            f"(grid-electricity).")
        m_pillar.bullets.append(
            f"Scope 3: {agg['scope_3_kgco2e']:,.0f} kgCO2e "
            f"(supply-chain estimate).")
        m_pillar.bullets.append(
            f"Total: {agg['total_kgco2e']:,.0f} kgCO2e.")
    else:
        m_pillar.bullets.append(
            "Carbon inventory not yet completed — facility-level "
            "data collection pending.")
    m_pillar.bullets.append(
        "Forward target: 30% Scope 1+2 reduction by exit, "
        "anchored to the 2026 baseline.")

    return ISSBStandardReport(
        standard="S2", governance=g_pillar, strategy=s_pillar,
        risk_management=r_pillar,
        metrics_and_targets=m_pillar,
    )


def render_issb_markdown(report: ISSBStandardReport) -> str:
    """Render one IFRS standard report (S1 or S2) as markdown
    ready to paste into the LP package."""
    lines: List[str] = []
    lines.append(
        f"## ISSB IFRS {report.standard} Disclosure"
    )
    lines.append("")
    for pillar in (
        report.governance, report.strategy,
        report.risk_management, report.metrics_and_targets,
    ):
        lines.append(f"### {pillar.name}")
        for b in pillar.bullets:
            lines.append(f"- {b}")
        lines.append("")
    return "\n".join(lines)


@dataclass
class LPPackage:
    """Top-level LP-ready disclosure package combining the
    cover summary + IFRS S1 + IFRS S2 + EDCI scorecard +
    carbon detail + DEI dashboard + governance memo."""
    company: str
    period: str
    sections: List[str] = field(default_factory=list)


def build_lp_package(
    company_name: str,
    period: str,
    *,
    s1_report: ISSBStandardReport,
    s2_report: ISSBStandardReport,
    edci_disclosure_md: str = "",
    issb_attested: bool = False,
) -> LPPackage:
    """Assemble the LP-ready package. Each section is emitted as
    pre-rendered markdown so the caller can join them in any
    order (PDF, HTML, email body)."""
    sections: List[str] = []
    cover = (
        f"# ESG Disclosure Package — {company_name}\n\n"
        f"**Reporting period:** {period}\n\n"
        f"**ISSB attestation:** "
        f"{'attested' if issb_attested else 'not yet attested'}.\n"
    )
    sections.append(cover)
    sections.append(render_issb_markdown(s1_report))
    sections.append(render_issb_markdown(s2_report))
    if edci_disclosure_md:
        sections.append(edci_disclosure_md)
    return LPPackage(
        company=company_name, period=period, sections=sections,
    )


def render_lp_package_markdown(package: LPPackage) -> str:
    """Render the complete LP package as one markdown string."""
    return "\n---\n\n".join(package.sections) + "\n"
