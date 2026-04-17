"""First thirty minutes — the targeted questions a partner opens with.

A senior partner walking into a management interview has 30 minutes
to get the answers that will make or break their diligence
convictions. They do NOT ask generic questions. They ask three to
five questions that the packet already hinted at, with enough
specificity to force a non-rehearsed answer.

This module reads a packet-like context and produces a partner's
opening questions, each tied to the packet signal that motivated it.

Questions are tiered:

- **Opening** — the question that sets the tone; always about the
  thing the deck tried hardest to downplay.
- **Probe** — follow-up questions that test whether the answer is
  genuine or canned.
- **Landmine** — the specific risk that would kill the deal if true.

Each question carries the packet trigger that generated it so the
associate can reference the data if management deflects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FirstThirtyContext:
    """Packet-derived signals the partner has already absorbed."""
    # Financial signals:
    current_denial_rate: float = 0.05
    prior_year_denial_rate: float = 0.05
    days_in_ar: int = 45
    recurring_ebitda_pct: float = 1.0
    one_time_pct_of_ebitda: float = 0.0
    # Payer / regulatory:
    medicare_ffs_pct: float = 0.25
    medicaid_pct: float = 0.15
    commercial_pct: float = 0.55
    top_payer_share: float = 0.25
    oon_revenue_share: float = 0.0
    # Management / team:
    founder_ceo_in_place: bool = False
    c_suite_tenure_avg_years: float = 4.0
    physician_attrition_pct: float = 0.08
    # Historical pattern match:
    historical_failure_matches: List[str] = field(default_factory=list)
    # Thesis:
    claimed_rate_growth_pct: float = 0.03
    claimed_volume_growth_pct: float = 0.04
    claimed_synergies_year_1_m: float = 0.0
    pro_forma_addbacks_pct: float = 0.0
    # Regulatory / structural:
    has_pending_fca: bool = False
    has_material_litigation: bool = False
    sale_leaseback_in_thesis: bool = False


@dataclass
class PartnerQuestion:
    tier: str                              # "opening" / "probe" / "landmine"
    text: str
    packet_trigger: str                    # the signal that motivated it

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier, "text": self.text,
            "packet_trigger": self.packet_trigger,
        }


@dataclass
class FirstThirtyPlan:
    questions: List[PartnerQuestion] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "questions": [q.to_dict() for q in self.questions],
            "partner_note": self.partner_note,
        }


def _denial_question(ctx: FirstThirtyContext) -> Optional[PartnerQuestion]:
    if ctx.current_denial_rate >= 0.10:
        return PartnerQuestion(
            tier="opening",
            text=(f"Your denial rate is "
                  f"{ctx.current_denial_rate*100:.1f}%. Walk me "
                  "through the three biggest denial reasons by payer, "
                  "and tell me which ones you can fix in 2026 vs "
                  "which ones are structural."),
            packet_trigger=(f"current_denial_rate="
                             f"{ctx.current_denial_rate:.3f}"),
        )
    return None


def _dar_question(ctx: FirstThirtyContext) -> Optional[PartnerQuestion]:
    if ctx.days_in_ar >= 55:
        return PartnerQuestion(
            tier="probe",
            text=(f"DAR of {ctx.days_in_ar} days. Is this a billing "
                  "timing issue, a payer-mix issue, or a first-pass "
                  "clean-claim issue? How do you know?"),
            packet_trigger=f"days_in_ar={ctx.days_in_ar}",
        )
    return None


def _recurring_ebitda_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.one_time_pct_of_ebitda >= 0.15:
        return PartnerQuestion(
            tier="opening",
            text=(f"Your reported EBITDA is "
                  f"{ctx.one_time_pct_of_ebitda*100:.0f}% one-time. "
                  "The exit multiple only applies to recurring. What "
                  "is your recurring EBITDA at this exact moment, and "
                  "what is the trajectory over the next 6 quarters?"),
            packet_trigger=(f"one_time_pct_of_ebitda="
                             f"{ctx.one_time_pct_of_ebitda:.2f}"),
        )
    return None


def _oon_question(ctx: FirstThirtyContext) -> Optional[PartnerQuestion]:
    if ctx.oon_revenue_share >= 0.20:
        return PartnerQuestion(
            tier="landmine",
            text=(f"OON revenue is {ctx.oon_revenue_share*100:.0f}% of "
                  "the book. Under the No Surprises Act framework, how "
                  "much of this revenue is at risk in 2026-2027, and "
                  "what is the in-network conversion pipeline?"),
            packet_trigger=(f"oon_revenue_share="
                             f"{ctx.oon_revenue_share:.2f}"),
        )
    return None


def _denial_trend_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    delta = ctx.current_denial_rate - ctx.prior_year_denial_rate
    if delta >= 0.015:
        return PartnerQuestion(
            tier="probe",
            text=(f"Denial rate moved from "
                  f"{ctx.prior_year_denial_rate*100:.1f}% to "
                  f"{ctx.current_denial_rate*100:.1f}% in one year. "
                  "What broke? Who owns it and what is the specific "
                  "remediation timeline?"),
            packet_trigger=(f"denial_trend_delta=+{delta*100:.1f}pp"),
        )
    return None


def _management_tenure_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.c_suite_tenure_avg_years < 2.5:
        return PartnerQuestion(
            tier="probe",
            text=(f"Average C-suite tenure is "
                  f"{ctx.c_suite_tenure_avg_years:.1f} years. Who "
                  "has been here more than 3 years, and what retention "
                  "packages are in place through exit?"),
            packet_trigger=(f"c_suite_tenure_avg_years="
                             f"{ctx.c_suite_tenure_avg_years:.1f}"),
        )
    return None


def _fca_question(ctx: FirstThirtyContext) -> Optional[PartnerQuestion]:
    if ctx.has_pending_fca:
        return PartnerQuestion(
            tier="landmine",
            text=("Walk me through every open FCA matter or CID. Who "
                  "is representing you, what is the exposure, and "
                  "what is the settlement timeline? If this is "
                  "material, I need to know now, not in week 6."),
            packet_trigger="has_pending_fca=True",
        )
    return None


def _leverage_on_rate_growth(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.claimed_rate_growth_pct > 0.05:
        return PartnerQuestion(
            tier="probe",
            text=(f"Model assumes {ctx.claimed_rate_growth_pct*100:.1f}% "
                  "annual rate growth. Show me the signed or in-process "
                  "contract wins that support that. If the number is "
                  "mostly mix-shift, tell me; a 5%+ rate-card number "
                  "does not exist in your payer book."),
            packet_trigger=(f"claimed_rate_growth_pct="
                             f"{ctx.claimed_rate_growth_pct:.2f}"),
        )
    return None


def _top_payer_concentration_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.top_payer_share >= 0.35:
        return PartnerQuestion(
            tier="landmine",
            text=(f"Top payer is {ctx.top_payer_share*100:.0f}% of "
                  "revenue. When does that contract renew, what are "
                  "the rate escalators, and what is your contingency "
                  "if they walk or cut rates 5%?"),
            packet_trigger=f"top_payer_share={ctx.top_payer_share:.2f}",
        )
    return None


def _historical_pattern_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.historical_failure_matches:
        pattern = ctx.historical_failure_matches[0]
        return PartnerQuestion(
            tier="opening",
            text=(f"This deal pattern-matches {pattern}. In my head "
                  "I'm asking: what makes this different? Walk me "
                  "through the three structural mitigations that "
                  "prevent the same outcome."),
            packet_trigger=f"historical_match={pattern}",
        )
    return None


def _synergy_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.claimed_synergies_year_1_m > 5.0:
        return PartnerQuestion(
            tier="probe",
            text=(f"You are claiming ${ctx.claimed_synergies_year_1_m:.1f}M "
                  "of year-1 synergies. Partner experience: 25-30% of "
                  "run-rate in year 1 is realistic. Which specific "
                  "actions close in months 1-6 vs 7-12, with named "
                  "owners?"),
            packet_trigger=(f"claimed_synergies_year_1_m="
                             f"{ctx.claimed_synergies_year_1_m:.1f}"),
        )
    return None


def _sale_leaseback_question(
    ctx: FirstThirtyContext,
) -> Optional[PartnerQuestion]:
    if ctx.sale_leaseback_in_thesis:
        return PartnerQuestion(
            tier="landmine",
            text=("Sale-leaseback structure in the thesis. What is "
                  "rent-to-EBITDA post-close, and does it stay below "
                  "0.50x at -10% EBITDA? Steward told us what happens "
                  "when rent consumes the operating margin."),
            packet_trigger="sale_leaseback_in_thesis=True",
        )
    return None


DETECTORS = (
    _denial_question,
    _dar_question,
    _recurring_ebitda_question,
    _oon_question,
    _denial_trend_question,
    _management_tenure_question,
    _fca_question,
    _leverage_on_rate_growth,
    _top_payer_concentration_question,
    _historical_pattern_question,
    _synergy_question,
    _sale_leaseback_question,
)


def build_first_thirty(ctx: FirstThirtyContext,
                        max_questions: int = 5) -> FirstThirtyPlan:
    raw = [d(ctx) for d in DETECTORS]
    questions = [q for q in raw if q is not None]

    # Ordering: landmines first, then openings, then probes.
    order = {"landmine": 0, "opening": 1, "probe": 2}
    questions.sort(key=lambda q: order.get(q.tier, 99))
    questions = questions[:max_questions]

    if not questions:
        note = ("No packet-derived questions fire — the deal looks "
                "clean on paper. Use the generic opening list.")
    else:
        by_tier = {"landmine": 0, "opening": 0, "probe": 0}
        for q in questions:
            by_tier[q.tier] = by_tier.get(q.tier, 0) + 1
        note = (f"Open with {by_tier.get('landmine', 0)} landmine "
                f"question(s), {by_tier.get('opening', 0)} opening, "
                f"{by_tier.get('probe', 0)} probe. Partner discipline: "
                "do not let management deflect the landmine to week-6 "
                "diligence — it goes first.")

    return FirstThirtyPlan(questions=questions, partner_note=note)


def render_first_thirty_markdown(plan: FirstThirtyPlan) -> str:
    lines = [
        "# First thirty minutes — partner questions",
        "",
        f"_{plan.partner_note}_",
        "",
    ]
    for q in plan.questions:
        lines.append(f"## ({q.tier.upper()}) {q.text}")
        lines.append(f"- Packet trigger: `{q.packet_trigger}`")
        lines.append("")
    return "\n".join(lines)
