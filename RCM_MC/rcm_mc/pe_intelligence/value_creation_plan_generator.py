"""Value creation plan (VCP) — 3-year roadmap on one page.

Different from 100-day plan (immediate actions) and QoR agenda
(quarterly cadence). VCP is the full hold-period roadmap of
EBITDA-expanding initiatives: each has owner, year of impact,
expected $ contribution, and dependency graph.

A senior partner wants this on ONE PAGE at IC — "here's how we
get from $X to $Y over 5 years." The module consumes thesis
pillars + packet signals and returns:

- Initiative list with year / owner / $ impact / dependencies.
- Bridge table (base EBITDA → target EBITDA by lever).
- Top-3 execution risks (dependencies that could stall
  downstream initiatives).
- Partner note on realistic vs aspirational.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class VCPContext:
    deal_name: str = "Deal"
    entry_ebitda_m: float = 0.0
    target_ebitda_m: float = 0.0
    hold_years: int = 5
    # Signals that unlock/hurt specific initiatives:
    has_rcm_denial_upside: bool = False
    has_cdi_opportunity: bool = False
    has_mna_pipeline: bool = False
    has_payer_renegotiation: bool = False
    has_site_consolidation: bool = False
    has_labor_productivity_program: bool = False
    has_procurement_gpo_uplift: bool = False
    has_tech_productivity: bool = False
    # Discipline signals:
    management_capacity_0_100: int = 60     # team bandwidth
    capex_budget_m: float = 0.0


@dataclass
class VCPInitiative:
    name: str
    category: str
    year_starts: int
    year_ebitda_impact: int
    expected_impact_m: float
    owner: str
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "year_starts": self.year_starts,
            "year_ebitda_impact": self.year_ebitda_impact,
            "expected_impact_m": self.expected_impact_m,
            "owner": self.owner,
            "dependencies": list(self.dependencies),
        }


@dataclass
class VCPRoadmap:
    deal_name: str
    entry_ebitda_m: float
    target_ebitda_m: float
    bridge_gap_m: float
    total_initiative_impact_m: float
    over_or_undershoot_pct: float
    initiatives: List[VCPInitiative] = field(default_factory=list)
    execution_risks: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "entry_ebitda_m": self.entry_ebitda_m,
            "target_ebitda_m": self.target_ebitda_m,
            "bridge_gap_m": self.bridge_gap_m,
            "total_initiative_impact_m": self.total_initiative_impact_m,
            "over_or_undershoot_pct": self.over_or_undershoot_pct,
            "initiatives": [i.to_dict() for i in self.initiatives],
            "execution_risks": list(self.execution_risks),
            "partner_note": self.partner_note,
        }


def _denial_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_rcm_denial_upside:
        # Assume 2-3% EBITDA lift from denial program over 2 years.
        impact = ctx.entry_ebitda_m * 0.03
        return VCPInitiative(
            name="RCM denial-reduction program",
            category="RCM",
            year_starts=1, year_ebitda_impact=2,
            expected_impact_m=round(impact, 2),
            owner="VP Revenue Cycle",
            dependencies=["coding-rigor program", "payer scorecards"],
        )
    return None


def _cdi_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_cdi_opportunity:
        # ~1.5% lift in 18-24 months.
        impact = ctx.entry_ebitda_m * 0.02
        return VCPInitiative(
            name="CDI program + CMI uplift",
            category="RCM",
            year_starts=1, year_ebitda_impact=2,
            expected_impact_m=round(impact, 2),
            owner="CMO + VP RCM",
            dependencies=["RAC audit defense"],
        )
    return None


def _mna_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_mna_pipeline:
        # Bolt-on EBITDA contribution = 8-15% of entry per closed year.
        impact = ctx.entry_ebitda_m * 0.30  # 3-4 bolt-ons over hold
        return VCPInitiative(
            name="M&A — bolt-on pipeline",
            category="inorganic_growth",
            year_starts=1, year_ebitda_impact=5,
            expected_impact_m=round(impact, 2),
            owner="Platform CEO + Corp Dev",
            dependencies=["capital structure room", "integration PMO"],
        )
    return None


def _payer_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_payer_renegotiation:
        # 2-4% rev lift over 2 years → 3-5% EBITDA lift.
        impact = ctx.entry_ebitda_m * 0.04
        return VCPInitiative(
            name="Payer renegotiation — named contracts",
            category="commercial",
            year_starts=1, year_ebitda_impact=3,
            expected_impact_m=round(impact, 2),
            owner="Chief Commercial Officer",
            dependencies=["signed contract wins"],
        )
    return None


def _site_consolidation(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_site_consolidation:
        impact = ctx.entry_ebitda_m * 0.025
        return VCPInitiative(
            name="Site footprint optimization",
            category="operations",
            year_starts=1, year_ebitda_impact=3,
            expected_impact_m=round(impact, 2),
            owner="COO",
            dependencies=["lease negotiations", "workforce transitions"],
        )
    return None


def _labor_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_labor_productivity_program:
        impact = ctx.entry_ebitda_m * 0.03
        return VCPInitiative(
            name="Labor productivity + scheduling",
            category="operations",
            year_starts=2, year_ebitda_impact=3,
            expected_impact_m=round(impact, 2),
            owner="COO + CNO",
            dependencies=["tech platform upgrade"],
        )
    return None


def _procurement_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_procurement_gpo_uplift:
        impact = ctx.entry_ebitda_m * 0.015
        return VCPInitiative(
            name="Procurement — GPO & supply",
            category="cost",
            year_starts=1, year_ebitda_impact=2,
            expected_impact_m=round(impact, 2),
            owner="CFO + VP Procurement",
            dependencies=[],
        )
    return None


def _tech_initiative(ctx: VCPContext) -> Optional[VCPInitiative]:
    if ctx.has_tech_productivity:
        impact = ctx.entry_ebitda_m * 0.02
        return VCPInitiative(
            name="Technology platform enablement",
            category="operations",
            year_starts=1, year_ebitda_impact=4,
            expected_impact_m=round(impact, 2),
            owner="CIO",
            dependencies=["ERP consolidation",
                           "workflow redesign"],
        )
    return None


BUILDERS = (
    _denial_initiative,
    _cdi_initiative,
    _mna_initiative,
    _payer_initiative,
    _site_consolidation,
    _labor_initiative,
    _procurement_initiative,
    _tech_initiative,
)


def build_vcp(ctx: VCPContext) -> VCPRoadmap:
    initiatives = [b(ctx) for b in BUILDERS]
    initiatives = [i for i in initiatives if i is not None]
    total_impact = sum(i.expected_impact_m for i in initiatives)
    gap = ctx.target_ebitda_m - ctx.entry_ebitda_m
    over_under = ((total_impact - gap) / gap
                  if gap > 0 else 0.0)

    # Execution risks: initiatives sharing dependencies are stacked risk.
    all_deps: Dict[str, List[str]] = {}
    for i in initiatives:
        for d in i.dependencies:
            all_deps.setdefault(d, []).append(i.name)
    risks: List[str] = []
    # Dependency chains blocking 2+ initiatives.
    for dep, names in all_deps.items():
        if len(names) >= 2:
            risks.append(
                f"Dependency '{dep}' blocks {len(names)} initiatives "
                f"({', '.join(names[:2])}); single-point-of-failure "
                "risk in the plan.")
    # Management capacity risk.
    if ctx.management_capacity_0_100 < 55 and len(initiatives) >= 5:
        risks.append(
            f"Management capacity {ctx.management_capacity_0_100}/100 "
            f"vs {len(initiatives)} concurrent initiatives — team "
            "cannot execute all in parallel.")
    # Capex bottleneck.
    tech_imp = sum(i.expected_impact_m for i in initiatives
                    if i.category in ("operations", "rcm"))
    if tech_imp > 0 and ctx.capex_budget_m < 2.0:
        risks.append(
            f"Capex budget ${ctx.capex_budget_m:.1f}M does not "
            "support the tech-enablement and ops-heavy initiatives. "
            "Capex bottleneck.")
    risks = risks[:3]

    if not initiatives:
        note = ("No initiatives scoped. Either the signals didn't "
                "reveal levers or the thesis is not yet articulated.")
    elif over_under < -0.20:
        note = (f"VCP only closes "
                f"{(total_impact / max(0.01, gap))*100:.0f}% of the "
                f"${gap:,.1f}M bridge. The plan doesn't reach target; "
                "either target is wrong or plan is incomplete.")
    elif over_under > 0.30:
        note = (f"VCP overshoots the bridge by "
                f"{over_under*100:.0f}%. Either plan is optimistic or "
                "target is conservative. Partners haircut 20-30%.")
    else:
        note = (f"VCP closes ${total_impact:,.1f}M vs ${gap:,.1f}M "
                "bridge — reasonable fit. Execution risks are what "
                "matters now.")

    return VCPRoadmap(
        deal_name=ctx.deal_name,
        entry_ebitda_m=round(ctx.entry_ebitda_m, 2),
        target_ebitda_m=round(ctx.target_ebitda_m, 2),
        bridge_gap_m=round(gap, 2),
        total_initiative_impact_m=round(total_impact, 2),
        over_or_undershoot_pct=round(over_under, 4),
        initiatives=initiatives,
        execution_risks=risks,
        partner_note=note,
    )


def render_vcp_markdown(r: VCPRoadmap) -> str:
    lines = [
        f"# {r.deal_name} — Value creation plan",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Entry EBITDA: ${r.entry_ebitda_m:,.1f}M",
        f"- Target EBITDA: ${r.target_ebitda_m:,.1f}M",
        f"- Bridge gap: ${r.bridge_gap_m:,.1f}M",
        f"- Initiative total: ${r.total_initiative_impact_m:,.1f}M",
        f"- Over / undershoot: {r.over_or_undershoot_pct*100:+.0f}%",
        "",
        "## Initiatives",
        "",
        "| Year in | Year impact | Initiative | Category | $M | Owner | Dependencies |",
        "|---:|---:|---|---|---:|---|---|",
    ]
    for i in r.initiatives:
        deps = ", ".join(i.dependencies) if i.dependencies else "—"
        lines.append(
            f"| Y{i.year_starts} | Y{i.year_ebitda_impact} | "
            f"{i.name} | {i.category} | "
            f"${i.expected_impact_m:,.2f}M | {i.owner} | {deps} |"
        )
    if r.execution_risks:
        lines.extend(["", "## Execution risks", ""])
        for risk in r.execution_risks:
            lines.append(f"- {risk}")
    return "\n".join(lines)
