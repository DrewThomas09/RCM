"""Archetype subrunners — deal-archetype-specific heuristic packs.

Partners don't apply generic checks — they apply checks specific
to the archetype. A payer-mix-shift play needs different scrutiny
than a back-office consolidation play. This module branches into
specialized runners, each applying the heuristics a senior partner
would ask FIRST for that archetype.

Archetypes covered:

- **payer_mix_shift** — moving Medicaid → commercial, or FFS → VBC.
- **roll_up** — platform buys 10+ bolt-ons over hold.
- **cmi_uplift** — document / code to lift Case Mix Index on
  existing volumes.
- **outpatient_migration** — shift inpatient procedures to ASC /
  HOPD / physician office.
- **back_office_consolidation** — RCM / staffing / shared services
  centralization.
- **cost_basis_compression** — labor / supply / procurement / SG&A
  cuts.
- **capacity_expansion** — greenfield capacity add, de novo.

Each runner returns a list of archetype-specific warnings + a
partner note. Warnings are partner-voice, not generic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArchetypeContext:
    """Loose bag of signals; each runner reads what it needs."""
    subsector: str = ""
    # Payer mix.
    medicare_pct: float = 0.30
    medicaid_pct: float = 0.20
    commercial_pct: float = 0.50
    vbc_pct: float = 0.05
    # Growth + operations.
    volume_growth_pct: float = 0.02
    price_growth_pct: float = 0.03
    denial_rate: float = 0.08
    days_in_ar: int = 45
    cmi_current: float = 1.35
    cmi_target: float = 1.50
    # Roll-up.
    platform_age_years: int = 2
    acquisitions_per_year: int = 3
    integrated_pct: float = 0.70
    # Outpatient.
    inpatient_revenue_share: float = 0.50
    ordered_hopd_revenue_share: float = 0.20
    # Consolidation / cost.
    shared_services_count: int = 2
    num_erps: int = 1
    labor_cost_pct_revenue: float = 0.50
    # Capacity.
    utilization_pct: float = 0.75
    new_sites_planned: int = 0


@dataclass
class ArchetypeWarning:
    archetype: str
    severity: str                         # "low" / "medium" / "high"
    message: str


@dataclass
class ArchetypeReport:
    archetype: str
    warnings: List[ArchetypeWarning] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "warnings": [
                {"archetype": w.archetype, "severity": w.severity,
                 "message": w.message} for w in self.warnings
            ],
            "partner_note": self.partner_note,
        }


def payer_mix_shift_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    # Medicaid → commercial thesis requires real payer leverage.
    if ctx.medicaid_pct >= 0.30 and ctx.commercial_pct < 0.40:
        warnings.append(ArchetypeWarning(
            "payer_mix_shift", "high",
            (f"Medicaid {ctx.medicaid_pct*100:.0f}% vs commercial "
             f"{ctx.commercial_pct*100:.0f}% — shifting requires "
             "commercial payer leverage the asset may not have.")
        ))
    # FFS → VBC thesis needs mature VBC infrastructure.
    if ctx.vbc_pct < 0.05 and ctx.medicare_pct > 0.30:
        warnings.append(ArchetypeWarning(
            "payer_mix_shift", "medium",
            ("VBC share < 5% with heavy Medicare — VBC transition "
             "needs 18-24 months build-out. Delay the ramp in underwrite.")
        ))
    # Assumed rate increases must be modest.
    if ctx.price_growth_pct > 0.06:
        warnings.append(ArchetypeWarning(
            "payer_mix_shift", "high",
            (f"Rate growth {ctx.price_growth_pct*100:.1f}% assumed "
             "— payer renegotiation wins > 6%/yr are rare. Haircut.")
        ))
    note = (f"Payer-mix shift thesis: {len(warnings)} warning(s). "
            "Shift cycles are 3+ years and require evidence of "
            "contract wins, not claims of opportunity.") \
        if warnings else ("Payer-mix shift thesis looks "
                           "defensible — no warnings.")
    return ArchetypeReport("payer_mix_shift", warnings, note)


def roll_up_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    if ctx.platform_age_years < 3 and ctx.acquisitions_per_year >= 5:
        warnings.append(ArchetypeWarning(
            "roll_up", "high",
            (f"Platform age {ctx.platform_age_years}y but "
             f"{ctx.acquisitions_per_year} acquisitions/yr — "
             "integration is not keeping pace (AdaptHealth "
             "pattern).")
        ))
    if ctx.integrated_pct < 0.80:
        warnings.append(ArchetypeWarning(
            "roll_up", "medium",
            (f"Only {ctx.integrated_pct*100:.0f}% integrated — "
             "pro-forma EBITDA is fiction until integration closes.")
        ))
    if ctx.volume_growth_pct < 0.03:
        warnings.append(ArchetypeWarning(
            "roll_up", "medium",
            ("Flat organic volume under the roll-up wrapper — "
             "growth is acquisition only. Exit value depends on "
             "roll-up engine, not operating asset.")
        ))
    note = (f"Roll-up thesis: {len(warnings)} warning(s). Key ask: "
            "can we exit via strategic or next-ring-up sponsor, or "
            "is exit dependent on more roll-up?") \
        if warnings else ("Roll-up thesis executing well — "
                           "integration tracking demand.")
    return ArchetypeReport("roll_up", warnings, note)


def cmi_uplift_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    gap = ctx.cmi_target - ctx.cmi_current
    if gap > 0.20:
        warnings.append(ArchetypeWarning(
            "cmi_uplift", "high",
            (f"CMI lift {gap:.2f} (from {ctx.cmi_current:.2f} → "
             f"{ctx.cmi_target:.2f}) — more than 0.15 in 24 months is "
             "aggressive and invites RAC audits.")
        ))
    if ctx.denial_rate > 0.10:
        warnings.append(ArchetypeWarning(
            "cmi_uplift", "medium",
            (f"Denial rate {ctx.denial_rate*100:.1f}% — CMI uplift "
             "via re-coding will raise denials before it raises "
             "collections.")
        ))
    if ctx.days_in_ar > 55:
        warnings.append(ArchetypeWarning(
            "cmi_uplift", "medium",
            (f"DAR {ctx.days_in_ar} days — receivables are already "
             "slow. CMI changes compound the cash lag.")
        ))
    note = (f"CMI uplift thesis: {len(warnings)} warning(s). "
            "Remember: CMI gains without clinical documentation "
            "changes are un-defensible and RAC-vulnerable.") \
        if warnings else ("CMI uplift thesis is conservative and "
                           "defensible.")
    return ArchetypeReport("cmi_uplift", warnings, note)


def outpatient_migration_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    if ctx.inpatient_revenue_share > 0.60:
        warnings.append(ArchetypeWarning(
            "outpatient_migration", "medium",
            (f"Inpatient revenue {ctx.inpatient_revenue_share*100:.0f}% "
             "— 60%+ migration to outpatient in 5 years would "
             "disrupt the physical plant utilization thesis.")
        ))
    if ctx.ordered_hopd_revenue_share > 0.30:
        warnings.append(ArchetypeWarning(
            "outpatient_migration", "high",
            ("HOPD revenue share high — site-neutral rate cuts "
             "kill the migration uplift. Stress at 22% HOPD cut.")
        ))
    note = ("Outpatient migration thesis needs 24-36 months to "
            "materialize; underwrite slower than seller's path.") \
        if warnings else ("Outpatient migration thesis fits the "
                           "asset's profile.")
    return ArchetypeReport("outpatient_migration", warnings, note)


def back_office_consolidation_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    if ctx.num_erps > 3:
        warnings.append(ArchetypeWarning(
            "back_office_consolidation", "high",
            (f"{ctx.num_erps} ERPs — consolidation is 24-36 months "
             "and $5M+ before savings materialize.")
        ))
    if ctx.shared_services_count < 2:
        warnings.append(ArchetypeWarning(
            "back_office_consolidation", "medium",
            ("Fewer than 2 shared-services functions centralized — "
             "consolidation thesis is early.")
        ))
    note = ("Back-office consolidation is a reliable lever but "
            "slow — avoid modeling full run-rate savings in year 1.")
    return ArchetypeReport("back_office_consolidation", warnings, note)


def cost_basis_compression_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    if ctx.labor_cost_pct_revenue < 0.40:
        warnings.append(ArchetypeWarning(
            "cost_basis_compression", "medium",
            (f"Labor cost {ctx.labor_cost_pct_revenue*100:.0f}% of "
             "revenue — already lean; further cuts compromise quality.")
        ))
    note = ("Cost-basis compression works once; beware assuming "
            "it works twice. Model year-1 gains, not run-rate.")
    return ArchetypeReport("cost_basis_compression", warnings, note)


def capacity_expansion_review(ctx: ArchetypeContext) -> ArchetypeReport:
    warnings: List[ArchetypeWarning] = []
    if ctx.utilization_pct < 0.65:
        warnings.append(ArchetypeWarning(
            "capacity_expansion", "high",
            (f"Existing utilization {ctx.utilization_pct*100:.0f}% — "
             "adding capacity before filling current is value-destructive.")
        ))
    if ctx.new_sites_planned >= 5:
        warnings.append(ArchetypeWarning(
            "capacity_expansion", "medium",
            (f"{ctx.new_sites_planned} new sites planned — ramp time "
             "is 12-24 months per site; EBITDA drag in years 1-2.")
        ))
    note = ("Capacity expansion: haircut the ramp curve. Assume "
            "sites underperform vintage run-rate by 30% year-1.")
    return ArchetypeReport("capacity_expansion", warnings, note)


ARCHETYPE_RUNNERS: Dict[str, Any] = {
    "payer_mix_shift": payer_mix_shift_review,
    "roll_up": roll_up_review,
    "cmi_uplift": cmi_uplift_review,
    "outpatient_migration": outpatient_migration_review,
    "back_office_consolidation": back_office_consolidation_review,
    "cost_basis_compression": cost_basis_compression_review,
    "capacity_expansion": capacity_expansion_review,
}


def run_archetype(archetype: str,
                  ctx: ArchetypeContext) -> ArchetypeReport:
    runner = ARCHETYPE_RUNNERS.get(archetype)
    if runner is None:
        return ArchetypeReport(
            archetype=archetype,
            warnings=[],
            partner_note=f"Unknown archetype: {archetype!r}.",
        )
    return runner(ctx)


def render_archetype_markdown(r: ArchetypeReport) -> str:
    lines = [
        f"# Archetype review — {r.archetype}",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    if r.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in r.warnings:
            lines.append(f"- **{w.severity.upper()}**: {w.message}")
    else:
        lines.append("_No warnings for this archetype._")
    return "\n".join(lines)
