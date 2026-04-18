"""Partner traps library — named thesis traps partners have seen before.

These are the specific fallacies that show up in pitch decks and
IC discussions. Each trap has a name, the argument sellers make,
why partners know the argument is thin, and packet fields that
surface the trap.

The user named three canonical traps:

- "We can fix denials in 12 months."
- "Payer renegotiation is coming."
- "Medicare Advantage will make it up."

This module formalizes those and adds more from partner experience:
"back-office synergies in year 1," "the bolt-on pipeline is
robust," "the CEO will stay through exit."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PartnerTrap:
    name: str
    seller_pitch: str
    partner_rebuttal: str
    packet_triggers: List[str] = field(default_factory=list)


TRAPS_LIBRARY: List[PartnerTrap] = [
    PartnerTrap(
        name="fix_denials_in_12_months",
        seller_pitch=("We can get initial-denial rate from 12% down "
                       "to 5% in 12 months with RCM investment."),
        partner_rebuttal=(
            "Denial-rate reductions of 700 bps in 12 months require "
            "coding, contracting, front-end, and technology changes "
            "simultaneously. Partner experience: 200-300 bps/yr is "
            "the realistic ceiling under a focused program. "
            "Model 200 bps/yr with 50% realization."
        ),
        packet_triggers=[
            "current_denial_rate > 0.10",
            "target_denial_rate < 0.06",
            "months_to_target <= 12",
        ],
    ),
    PartnerTrap(
        name="payer_renegotiation_is_coming",
        seller_pitch=("We're up for renegotiation with our top payers "
                       "next year; scale gives us leverage."),
        partner_rebuttal=(
            "Payer renegotiation timelines slip by 6-12 months routinely. "
            "Rate increases rarely exceed 3%/yr in contract language; "
            "headline 5%+ wins come from mix shifts (codes, services), "
            "not rate cards. Underwrite at 2.5% and stress-test at 0%."
        ),
        packet_triggers=[
            "payer_contracts_renewing_next_12mo >= 2",
            "claimed_rate_growth_pct > 0.04",
        ],
    ),
    PartnerTrap(
        name="ma_will_make_it_up",
        seller_pitch=("Medicare Advantage enrollment growth will offset "
                       "Medicare FFS rate risk."),
        partner_rebuttal=(
            "MA plans pass through CMS rate changes with 12-18 month "
            "lag; MA margins on your book are set by the plan's "
            "benchmark, not your cost structure. MA does not cushion "
            "regulatory risk — it absorbs it slightly slower. "
            "Assume MA rate growth matches FFS less 1-2%."
        ),
        packet_triggers=[
            "medicare_advantage_pct >= 0.20",
            "regulatory_risk_material",
        ],
    ),
    PartnerTrap(
        name="back_office_synergies_year_1",
        seller_pitch=("Back-office synergies across bolt-ons will "
                       "deliver $X of EBITDA lift in year 1."),
        partner_rebuttal=(
            "Back-office consolidation timelines are 24-36 months for "
            "ERP consolidation, 12-18 months for HR/payroll, 18-24 "
            "months for RCM. Year 1 synergies are typically 25-30% of "
            "run-rate. Model 25% year-1 realization, 70% year-2."
        ),
        packet_triggers=[
            "claimed_year_1_synergies_m > 0",
            "num_erps > 1",
        ],
    ),
    PartnerTrap(
        name="robust_bolt_on_pipeline",
        seller_pitch=("Robust bolt-on pipeline of 15+ targets at "
                       "attractive multiples."),
        partner_rebuttal=(
            "Pipelines at entry look full; close rates on named "
            "targets are 10-15%. By month 6 post-close, most 'pipeline' "
            "targets have gone to other sponsors or cooled. Model "
            "15% conversion and spread across 24 months."
        ),
        packet_triggers=[
            "claimed_pipeline_count >= 10",
            "platform_first_year",
        ],
    ),
    PartnerTrap(
        name="ceo_stays_through_exit",
        seller_pitch=("Founder-CEO is committed to the business "
                       "through our hold period."),
        partner_rebuttal=(
            "Founder-CEO retention past the 3-year mark runs ~40%. "
            "Exit multiples compress materially when the founder "
            "leaves pre-exit. Negotiate a retention package tied to "
            "exit-year performance, not post-close milestones."
        ),
        packet_triggers=[
            "founder_ceo_in_place",
            "no_retention_agreement",
        ],
    ),
    PartnerTrap(
        name="we_are_underpenetrated",
        seller_pitch=("We capture only X% of our addressable market; "
                       "reaching Y% drives the thesis."),
        partner_rebuttal=(
            "\"Underpenetrated\" in healthcare usually means limited "
            "payer contracts or provider capacity, not weak demand. "
            "Verify the bottleneck is not structural before modeling "
            "share gains."
        ),
        packet_triggers=[
            "claimed_market_share_growth > 0.10",
            "existing_market_share < 0.10",
        ],
    ),
    PartnerTrap(
        name="quality_and_growth_together",
        seller_pitch=("We can grow faster while improving quality metrics."),
        partner_rebuttal=(
            "Rapid growth typically depresses quality metrics for 18-24 "
            "months — onboarding clinicians, new-site ramps, training "
            "gaps. The only way growth + quality coexist is deliberate "
            "pacing and investment. Haircut the growth rate or the "
            "quality improvement, not both."
        ),
        packet_triggers=[
            "claimed_volume_growth > 0.15",
            "claimed_quality_improvement_in_hold",
        ],
    ),
    PartnerTrap(
        name="multiple_will_re_rate",
        seller_pitch=("At exit, the market will re-rate our multiple "
                       "given our scale / recurring mix / growth."),
        partner_rebuttal=(
            "Multiple re-rating is the weakest leg in any MOIC bridge. "
            "Exit multiples compress more often than expand. Underwrite "
            "with exit multiple ≤ entry and make the math work. If the "
            "math needs expansion, the math does not work."
        ),
        packet_triggers=[
            "exit_multiple_assumption > entry_multiple",
            "moic_dependent_on_multiple_expansion",
        ],
    ),
    PartnerTrap(
        name="technology_platform_lift",
        seller_pitch=("Our technology platform will lift productivity "
                       "15%+ post-close."),
        partner_rebuttal=(
            "Technology productivity gains in healthcare require "
            "workflow redesign, training, and change management — "
            "12-24 months of effort before measurable lift. First-year "
            "gains are typically 3-5%. If the seller claims 10%+ in "
            "year 1, ask for the workflow-redesign plan."
        ),
        packet_triggers=[
            "claimed_year_1_productivity_lift > 0.10",
        ],
    ),
]


@dataclass
class TrapHit:
    trap: PartnerTrap
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.trap.name,
            "seller_pitch": self.trap.seller_pitch,
            "partner_rebuttal": self.trap.partner_rebuttal,
            "partner_note": self.partner_note,
        }


# Matcher functions — read a packet-like context and return trap names
# that fire.

def _match_fix_denials(ctx: Dict[str, Any]) -> bool:
    return (
        float(ctx.get("current_denial_rate", 0)) > 0.10
        and float(ctx.get("target_denial_rate", 1)) < 0.06
        and int(ctx.get("months_to_target", 99)) <= 12
    )


def _match_payer_reneg(ctx: Dict[str, Any]) -> bool:
    return (
        int(ctx.get("payer_contracts_renewing_next_12mo", 0)) >= 2
        and float(ctx.get("claimed_rate_growth_pct", 0)) > 0.04
    )


def _match_ma_will_make_it_up(ctx: Dict[str, Any]) -> bool:
    return (
        float(ctx.get("medicare_advantage_pct", 0)) >= 0.20
        and bool(ctx.get("regulatory_risk_material", False))
    )


def _match_back_office_year_1(ctx: Dict[str, Any]) -> bool:
    return (
        float(ctx.get("claimed_year_1_synergies_m", 0)) > 0
        and int(ctx.get("num_erps", 0)) > 1
    )


def _match_robust_pipeline(ctx: Dict[str, Any]) -> bool:
    return (
        int(ctx.get("claimed_pipeline_count", 0)) >= 10
        and bool(ctx.get("platform_first_year", False))
    )


def _match_ceo_stays(ctx: Dict[str, Any]) -> bool:
    return (
        bool(ctx.get("founder_ceo_in_place", False))
        and bool(ctx.get("no_retention_agreement", False))
    )


def _match_underpenetrated(ctx: Dict[str, Any]) -> bool:
    return (
        float(ctx.get("claimed_market_share_growth", 0)) > 0.10
        and float(ctx.get("existing_market_share", 1.0)) < 0.10
    )


def _match_quality_and_growth(ctx: Dict[str, Any]) -> bool:
    return (
        float(ctx.get("claimed_volume_growth", 0)) > 0.15
        and bool(ctx.get("claimed_quality_improvement_in_hold", False))
    )


def _match_multiple_rerate(ctx: Dict[str, Any]) -> bool:
    entry = float(ctx.get("entry_multiple", 0))
    exit_m = float(ctx.get("exit_multiple_assumption", 0))
    return exit_m > entry > 0


def _match_tech_platform(ctx: Dict[str, Any]) -> bool:
    return float(ctx.get("claimed_year_1_productivity_lift", 0)) > 0.10


MATCHERS: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    "fix_denials_in_12_months": _match_fix_denials,
    "payer_renegotiation_is_coming": _match_payer_reneg,
    "ma_will_make_it_up": _match_ma_will_make_it_up,
    "back_office_synergies_year_1": _match_back_office_year_1,
    "robust_bolt_on_pipeline": _match_robust_pipeline,
    "ceo_stays_through_exit": _match_ceo_stays,
    "we_are_underpenetrated": _match_underpenetrated,
    "quality_and_growth_together": _match_quality_and_growth,
    "multiple_will_re_rate": _match_multiple_rerate,
    "technology_platform_lift": _match_tech_platform,
}


def match_traps(ctx: Dict[str, Any]) -> List[TrapHit]:
    hits: List[TrapHit] = []
    for trap in TRAPS_LIBRARY:
        matcher = MATCHERS.get(trap.name)
        if matcher is None:
            continue
        try:
            if matcher(ctx):
                hits.append(TrapHit(
                    trap=trap,
                    partner_note=(f"Pitch: '{trap.seller_pitch}' — "
                                   f"rebuttal: {trap.partner_rebuttal}"),
                ))
        except Exception:
            continue
    return hits


def render_traps_markdown(hits: List[TrapHit]) -> str:
    if not hits:
        return ("# Partner traps\n\n"
                "_No named partner traps fire against this pitch._")
    lines = ["# Partner traps — thesis claims that look familiar",
              ""]
    for h in hits:
        lines.append(f"## {h.trap.name}")
        lines.append(f"**Seller pitch:** {h.trap.seller_pitch}")
        lines.append("")
        lines.append(f"**Partner rebuttal:** {h.trap.partner_rebuttal}")
        lines.append("")
    return "\n".join(lines)


def list_all_traps() -> List[PartnerTrap]:
    return list(TRAPS_LIBRARY)
