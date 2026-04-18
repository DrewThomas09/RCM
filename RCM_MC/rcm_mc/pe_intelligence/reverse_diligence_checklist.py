"""Reverse diligence — what would we disclose if we were the seller?

Partners run reverse diligence 12-18 months before sale. The
question is: "If a buyer's QofE team arrived tomorrow, what would
come out in the wash?" Finding and fixing issues 12 months before
they surface in a buyer's process is worth multiples of the fix
cost.

This module takes the current portfolio-company state and
produces a checklist of items the partner knows a buyer will find,
grouped by severity and fix-by date. It's deliberately built
around buyer-side patterns, not standard seller-side tidiness.

Output categories:

- **kill-deal** items — items that would cause a buyer to walk
  (open FCA, material litigation, false GAAP). Fix NOW or plan
  the exit around them.
- **price-haircut** items — items that let a buyer reprice
  (pro-forma overstatement, concentration, thin DAR controls).
  Fix 6-12 months pre-sale.
- **discovery-risk** items — items that might come out and
  might not (minor billing variances, softer CMS surveys). Fix
  if possible but don't over-engineer.
- **pure-housekeeping** items — things to tidy up in the last
  6 months.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReverseContext:
    months_to_planned_sale: int = 18
    has_pending_fca: bool = False
    material_litigation: bool = False
    pro_forma_addbacks_pct: float = 0.0
    days_in_ar: int = 45
    denial_rate: float = 0.08
    cms_survey_issues: bool = False
    aggressive_coding_history: bool = False
    concentration_top_payer: float = 0.25
    concentration_top_customer: float = 0.25
    key_contract_renewals_in_next_12mo: int = 0
    incomplete_integration_pct: float = 0.0
    mip_not_yet_vested_pct: float = 0.5


@dataclass
class DisclosureItem:
    category: str                             # kill_deal / price_haircut /
                                              # discovery_risk / housekeeping
    name: str
    description: str
    fix_by_months: int                        # months before sale
    fix_difficulty: str                       # easy / medium / hard


@dataclass
class ReverseDiligenceReport:
    items: List[DisclosureItem] = field(default_factory=list)
    kill_deal_count: int = 0
    price_haircut_count: int = 0
    discovery_risk_count: int = 0
    housekeeping_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [
                {"category": i.category, "name": i.name,
                 "description": i.description,
                 "fix_by_months": i.fix_by_months,
                 "fix_difficulty": i.fix_difficulty}
                for i in self.items
            ],
            "kill_deal_count": self.kill_deal_count,
            "price_haircut_count": self.price_haircut_count,
            "discovery_risk_count": self.discovery_risk_count,
            "housekeeping_count": self.housekeeping_count,
            "partner_note": self.partner_note,
        }


def build_reverse_diligence(
    ctx: ReverseContext,
) -> ReverseDiligenceReport:
    items: List[DisclosureItem] = []

    if ctx.has_pending_fca:
        items.append(DisclosureItem(
            category="kill_deal", name="pending_fca",
            description=("Open FCA exposure — buyers walk. Close it "
                         "via settlement or clear the docket before "
                         "announcing sale."),
            fix_by_months=12, fix_difficulty="hard",
        ))
    if ctx.material_litigation:
        items.append(DisclosureItem(
            category="kill_deal", name="material_litigation",
            description=("Material litigation — buyer's QoL will "
                         "flag; reserves and indemnity get brutal."),
            fix_by_months=9, fix_difficulty="hard",
        ))
    if ctx.cms_survey_issues:
        items.append(DisclosureItem(
            category="price_haircut", name="cms_survey_issues",
            description=("CMS survey issues on the record — price "
                         "haircut; remediate + get clean re-survey "
                         "before data room opens."),
            fix_by_months=12, fix_difficulty="medium",
        ))
    if ctx.pro_forma_addbacks_pct >= 0.15:
        items.append(DisclosureItem(
            category="price_haircut", name="pro_forma_overstatement",
            description=(f"Pro-forma add-backs "
                         f"{ctx.pro_forma_addbacks_pct*100:.0f}% — "
                         "buyers haircut; document realized "
                         "synergies before sale."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.days_in_ar >= 55:
        items.append(DisclosureItem(
            category="price_haircut", name="dar_controls",
            description=(f"DAR {ctx.days_in_ar} days — buyers read "
                         "this as weak RCM; tighten 6-9 months "
                         "pre-sale."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.denial_rate >= 0.10:
        items.append(DisclosureItem(
            category="price_haircut", name="denial_rate",
            description=(f"Denial rate "
                         f"{ctx.denial_rate*100:.1f}% — remediate "
                         "before data room."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.aggressive_coding_history:
        items.append(DisclosureItem(
            category="discovery_risk",
            name="aggressive_coding_pattern",
            description=("History of aggressive coding will surface in "
                         "forensic billing review. Remediate + "
                         "document CDI / RAC-defense processes."),
            fix_by_months=9, fix_difficulty="hard",
        ))
    if ctx.concentration_top_payer >= 0.40:
        items.append(DisclosureItem(
            category="price_haircut", name="top_payer_concentration",
            description=(f"Top payer "
                         f"{ctx.concentration_top_payer*100:.0f}% — "
                         "document renewal terms + diversification "
                         "plan; concentrated books get discounted."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.concentration_top_customer >= 0.40:
        items.append(DisclosureItem(
            category="price_haircut", name="top_customer_concentration",
            description=(f"Top customer "
                         f"{ctx.concentration_top_customer*100:.0f}% — "
                         "diversify or lock multi-year term before "
                         "sale."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.key_contract_renewals_in_next_12mo >= 2:
        items.append(DisclosureItem(
            category="discovery_risk",
            name="contract_renewal_overhang",
            description=(f"{ctx.key_contract_renewals_in_next_12mo} "
                         "major contract renewals — close pre-LOI so "
                         "buyer doesn't own the risk."),
            fix_by_months=6, fix_difficulty="medium",
        ))
    if ctx.incomplete_integration_pct >= 0.20:
        items.append(DisclosureItem(
            category="price_haircut",
            name="incomplete_integration",
            description=(f"{ctx.incomplete_integration_pct*100:.0f}% "
                         "of acquisitions not integrated — buyers "
                         "discount pro-forma. Finish the integration "
                         "PMO work 9 months pre-sale."),
            fix_by_months=9, fix_difficulty="medium",
        ))
    if ctx.mip_not_yet_vested_pct >= 0.40:
        items.append(DisclosureItem(
            category="housekeeping",
            name="mip_vesting_cleanup",
            description=(f"{ctx.mip_not_yet_vested_pct*100:.0f}% of "
                         "MIP unvested — align vesting with exit "
                         "timeline 6 months pre-sale."),
            fix_by_months=6, fix_difficulty="easy",
        ))

    # Always-on housekeeping.
    items.append(DisclosureItem(
        category="housekeeping",
        name="data_room_audit",
        description=("Dry-run data room audit 3-4 months pre-sale; "
                     "catch inconsistencies before banker does."),
        fix_by_months=4, fix_difficulty="easy",
    ))

    kill = sum(1 for i in items if i.category == "kill_deal")
    hair = sum(1 for i in items if i.category == "price_haircut")
    disc = sum(1 for i in items if i.category == "discovery_risk")
    hk = sum(1 for i in items if i.category == "housekeeping")

    if kill >= 1:
        note = (f"{kill} kill-deal item(s). Sale cannot proceed "
                "without clearing these first. Push sale date back "
                "or close them now.")
    elif hair >= 3:
        note = (f"{hair} price-haircut items — buyer will compound "
                "these into the bid. Invest in fixing them; each "
                "fix is 2-3x ROI vs the bid reduction.")
    elif hair + disc >= 3:
        note = (f"Standard pre-sale book: {hair} price-haircut + "
                f"{disc} discovery-risk items. Address in the "
                f"{ctx.months_to_planned_sale}-month runway.")
    else:
        note = ("Clean book — only housekeeping to do in the last 6 "
                "months pre-sale.")

    return ReverseDiligenceReport(
        items=items,
        kill_deal_count=kill,
        price_haircut_count=hair,
        discovery_risk_count=disc,
        housekeeping_count=hk,
        partner_note=note,
    )


def render_reverse_diligence_markdown(
    r: ReverseDiligenceReport,
) -> str:
    lines = [
        "# Reverse diligence checklist",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Kill-deal: {r.kill_deal_count}",
        f"- Price-haircut: {r.price_haircut_count}",
        f"- Discovery-risk: {r.discovery_risk_count}",
        f"- Housekeeping: {r.housekeeping_count}",
        "",
        "| Category | Item | Description | Fix by (mo) | Difficulty |",
        "|---|---|---|---:|---|",
    ]
    # Sort by category priority then fix-by-months.
    order = {"kill_deal": 0, "price_haircut": 1,
              "discovery_risk": 2, "housekeeping": 3}
    for i in sorted(r.items, key=lambda x: (order.get(x.category, 9),
                                              x.fix_by_months)):
        lines.append(
            f"| {i.category} | {i.name} | {i.description} | "
            f"{i.fix_by_months} | {i.fix_difficulty} |"
        )
    return "\n".join(lines)
