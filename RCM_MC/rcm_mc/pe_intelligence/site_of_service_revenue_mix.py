"""Site-of-service revenue mix — where the revenue is and where it can move.

Partner statement: "Show me revenue split across
inpatient / HOPD / ASC / physician office. The mix
tells you the regulatory exposure (HOPD heavy =
site-neutral risk), the margin profile (ASC =
better margin per case), and the migration
opportunity (IP procedures eligible for OP
migration). The current mix is one number; the
mix you can engineer over the hold is the lever."

Distinct from:
- `site_neutral_specific_impact_calculator` — reg
  $-impact only.
- `outpatient_migration` archetype — narrative shape.

This module operates on **the actual current mix**
across 4 site-of-service categories and outputs:
- mix concentration
- regulatory exposure (HOPD share)
- margin profile (weighted contribution margin)
- migration opportunity (IP procedures with OP path)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SITE_TYPES = (
    "inpatient",
    "hopd",
    "asc",
    "physician_office",
)

# Typical contribution margins by site-of-service.
TYPICAL_MARGIN_BY_SITE: Dict[str, float] = {
    "inpatient": 0.10,
    "hopd": 0.18,
    "asc": 0.30,
    "physician_office": 0.22,
}

# Site-neutral / OBBBA exposure proxy by site.
REG_EXPOSURE_BY_SITE: Dict[str, str] = {
    "inpatient": "low",
    "hopd": "high",
    "asc": "medium",
    "physician_office": "low",
}


@dataclass
class SiteRevenueLine:
    site_type: str
    npr_m: float
    eligible_for_op_migration: bool = False
    """For inpatient: True if this revenue could shift
    to outpatient setting if not already."""


@dataclass
class SiteOfServiceMixInputs:
    lines: List[SiteRevenueLine] = field(
        default_factory=list)


@dataclass
class SiteShare:
    site_type: str
    npr_m: float
    share_pct: float
    typical_margin_pct: float
    contribution_m: float
    reg_exposure: str


@dataclass
class SiteOfServiceMixReport:
    shares: List[SiteShare] = field(default_factory=list)
    total_npr_m: float = 0.0
    weighted_contribution_margin_pct: float = 0.0
    weighted_contribution_m: float = 0.0
    hopd_share_pct: float = 0.0
    asc_share_pct: float = 0.0
    op_migration_opportunity_m: float = 0.0
    reg_exposure_verdict: str = "balanced"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shares": [
                {"site_type": s.site_type,
                 "npr_m": s.npr_m,
                 "share_pct": s.share_pct,
                 "typical_margin_pct":
                     s.typical_margin_pct,
                 "contribution_m": s.contribution_m,
                 "reg_exposure": s.reg_exposure}
                for s in self.shares
            ],
            "total_npr_m": self.total_npr_m,
            "weighted_contribution_margin_pct":
                self.weighted_contribution_margin_pct,
            "weighted_contribution_m":
                self.weighted_contribution_m,
            "hopd_share_pct": self.hopd_share_pct,
            "asc_share_pct": self.asc_share_pct,
            "op_migration_opportunity_m":
                self.op_migration_opportunity_m,
            "reg_exposure_verdict":
                self.reg_exposure_verdict,
            "partner_note": self.partner_note,
        }


def analyze_site_of_service_mix(
    inputs: SiteOfServiceMixInputs,
) -> SiteOfServiceMixReport:
    if not inputs.lines:
        return SiteOfServiceMixReport(
            partner_note=(
                "No site-of-service revenue lines — "
                "verify revenue cut by site is "
                "available in the data room."
            ),
        )

    total = sum(l.npr_m for l in inputs.lines)
    if total == 0:
        return SiteOfServiceMixReport(
            partner_note=(
                "Total NPR is zero — check inputs."
            ),
        )

    # Aggregate by site type
    site_buckets: Dict[str, float] = {}
    op_migration_m = 0.0
    for l in inputs.lines:
        site_buckets[l.site_type] = (
            site_buckets.get(l.site_type, 0.0) +
            l.npr_m
        )
        if (l.site_type == "inpatient" and
                l.eligible_for_op_migration):
            op_migration_m += l.npr_m

    shares: List[SiteShare] = []
    weighted_contribution = 0.0
    for site_type, npr in site_buckets.items():
        share = npr / total
        margin = TYPICAL_MARGIN_BY_SITE.get(site_type, 0.15)
        contribution = npr * margin
        weighted_contribution += contribution
        shares.append(SiteShare(
            site_type=site_type,
            npr_m=round(npr, 2),
            share_pct=round(share, 4),
            typical_margin_pct=round(margin, 4),
            contribution_m=round(contribution, 2),
            reg_exposure=REG_EXPOSURE_BY_SITE.get(
                site_type, "unknown"),
        ))

    shares.sort(
        key=lambda s: s.npr_m, reverse=True)

    weighted_margin = weighted_contribution / total

    hopd_share = next(
        (s.share_pct for s in shares
         if s.site_type == "hopd"), 0.0)
    asc_share = next(
        (s.share_pct for s in shares
         if s.site_type == "asc"), 0.0)

    if hopd_share >= 0.50:
        verdict = "high_reg_exposure"
        note = (
            f"HOPD share {hopd_share:.0%} — high site-"
            "neutral exposure. Run "
            "site_neutral_specific_impact_calculator on "
            "the service-line cuts; bake into bridge."
        )
    elif hopd_share >= 0.30:
        verdict = "moderate_reg_exposure"
        note = (
            f"HOPD share {hopd_share:.0%} — moderate "
            "site-neutral exposure. Track CMS rule "
            "cycle and keep service-line schedule "
            "current."
        )
    else:
        verdict = "balanced"
        note = (
            f"HOPD share {hopd_share:.0%} — low site-"
            "neutral exposure. Reg risk is not the "
            "binding constraint on multiple."
        )

    if op_migration_m > 0:
        note += (
            f" Migration opportunity: "
            f"${op_migration_m:.1f}M of inpatient "
            "revenue eligible for OP shift — model the "
            "margin uplift if executed."
        )
    if asc_share >= 0.30:
        note += (
            f" ASC share {asc_share:.0%} drives margin "
            "premium — protect physician retention; "
            "ASC economics depend on owner alignment."
        )

    return SiteOfServiceMixReport(
        shares=shares,
        total_npr_m=round(total, 2),
        weighted_contribution_margin_pct=round(
            weighted_margin, 4),
        weighted_contribution_m=round(
            weighted_contribution, 2),
        hopd_share_pct=round(hopd_share, 4),
        asc_share_pct=round(asc_share, 4),
        op_migration_opportunity_m=round(
            op_migration_m, 2),
        reg_exposure_verdict=verdict,
        partner_note=note,
    )


def render_site_of_service_mix_markdown(
    r: SiteOfServiceMixReport,
) -> str:
    lines = [
        "# Site-of-service revenue mix",
        "",
        f"_Verdict: **{r.reg_exposure_verdict}**_ — "
        f"{r.partner_note}",
        "",
        f"- Total NPR: ${r.total_npr_m:.1f}M",
        f"- Weighted margin: "
        f"{r.weighted_contribution_margin_pct:.1%} "
        f"(${r.weighted_contribution_m:.1f}M contribution)",
        f"- HOPD share: {r.hopd_share_pct:.0%}",
        f"- ASC share: {r.asc_share_pct:.0%}",
        f"- IP→OP migration opportunity: "
        f"${r.op_migration_opportunity_m:.1f}M",
        "",
        "| Site | NPR $M | Share | Margin | "
        "Contribution | Reg exposure |",
        "|---|---|---|---|---|---|",
    ]
    for s in r.shares:
        lines.append(
            f"| {s.site_type} | "
            f"${s.npr_m:.1f}M | "
            f"{s.share_pct:.0%} | "
            f"{s.typical_margin_pct:.0%} | "
            f"${s.contribution_m:.1f}M | "
            f"{s.reg_exposure} |"
        )
    return "\n".join(lines)
