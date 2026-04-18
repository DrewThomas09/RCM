"""Seller motivation decoder — why are they selling now?

Partner statement: "Before I counter-price I want to know
why they're at the table. A founder who needs liquidity
negotiates differently from a sponsor at vintage end.
Same price, different leverage."

Healthcare-services sellers come to market for a finite set
of reasons. Each carries a distinct **leverage profile**:
the partner's negotiation position depends on why the seller
is motivated to close by a specific date.

### Motivations modeled

1. **founder_liquidity** — age/succession. Time-sensitive;
   buyer has pricing leverage if seller has no alternative.
2. **tax_timing** — capital-gains sunset, state tax cliff.
   Hard deadline; partner reads the calendar.
3. **family_liquidity** — divorce, estate, sibling buyout.
   Sometimes very price-insensitive.
4. **sponsor_vintage_end** — PE sponsor at fund life end
   (yr 7-10). Must exit; LP pressure.
5. **covenant_trip_imminent** — private-credit lender
   forcing exit. Distressed framing is leverage.
6. **failed_prior_process** — market-tested, failed,
   repricing down. Read carefully — previous buyers
   walked for a reason.
7. **management_exit_wanted** — CEO wants out, equity
   rolling isn't workable. Operator-risk question.
8. **strategic_fatigue** — subscale, can't compete.
   Partner's ops-value is real.
9. **industry_trough_fear** — sell before reg cuts or
   reimbursement compression. Seller has info asymmetry.
10. **activist_pressure** — public parent spinning off.
    Partner negotiates with the parent, not the target.

### Leverage profile

Each motivation is tagged with:
- `seller_urgency`: low / medium / high.
- `buyer_leverage`: low / medium / high.
- `price_sensitivity`: low / medium / high (seller's).
- `negotiation_counter`: partner's recommended counter.
- `common_seller_position`: what they open with.
- `packet_signals`: fields / facts that suggest this
  motivation is in play.

### Entry point

`decode_seller_motivation(context)` scans signals and
returns ranked motivation matches. `render_motivation_markdown`
produces a partner-voice read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SellerMotivation:
    name: str
    description: str
    seller_urgency: str       # "low" / "medium" / "high"
    buyer_leverage: str       # "low" / "medium" / "high"
    price_sensitivity: str    # "low" / "medium" / "high"
    negotiation_counter: str
    common_seller_position: str
    packet_signals: List[str] = field(default_factory=list)


MOTIVATION_LIBRARY: List[SellerMotivation] = [
    SellerMotivation(
        name="founder_liquidity",
        description=("Founder age 65+ / succession event. "
                      "Typically owns > 30% directly; no heir "
                      "in operating seat."),
        seller_urgency="high",
        buyer_leverage="high",
        price_sensitivity="medium",
        negotiation_counter=(
            "Partner play: propose rollover equity "
            "sized to founder's liquidity goal + earn-out "
            "to bridge price gap. Founder keeps upside."
        ),
        common_seller_position=(
            "Maximum cash at close; resists rollover."
        ),
        packet_signals=[
            "founder_age_65_plus",
            "no_family_heir_in_ops",
            "founder_equity_gt_30pct",
        ],
    ),
    SellerMotivation(
        name="tax_timing",
        description=("Capital-gains rate cliff, estate "
                      "planning deadline, or state tax "
                      "window closing."),
        seller_urgency="high",
        buyer_leverage="medium",
        price_sensitivity="medium",
        negotiation_counter=(
            "Partner play: structure mix of "
            "installment / earn-out to seller's tax "
            "calendar. Small price concession for "
            "structure often works."
        ),
        common_seller_position=(
            "Push for close-by-date; price slightly "
            "flexible."
        ),
        packet_signals=[
            "proposed_close_before_year_end",
            "state_tax_cliff_known",
            "federal_cap_gains_sunset_year",
        ],
    ),
    SellerMotivation(
        name="family_liquidity",
        description=("Divorce, estate partition, or sibling "
                      "buyout driving sale."),
        seller_urgency="high",
        buyer_leverage="high",
        price_sensitivity="low",
        negotiation_counter=(
            "Partner play: move fast with clean cash "
            "terms. Avoid tax-sensitive structures — the "
            "family needs dollar amounts."
        ),
        common_seller_position=(
            "Fixed cash at close; resists contingent "
            "consideration."
        ),
        packet_signals=[
            "family_litigation_public",
            "estate_partition_filed",
            "sibling_dispute_documented",
        ],
    ),
    SellerMotivation(
        name="sponsor_vintage_end",
        description=("PE sponsor at yr 7-10 of fund life. "
                      "LPs pressing for exit."),
        seller_urgency="high",
        buyer_leverage="medium",
        price_sensitivity="low",    # LP-return focused
        negotiation_counter=(
            "Partner play: LP-scorecard sellers often hold "
            "price hard but accept aggressive reps + "
            "indemnity. Use R&W insurance to bridge. "
            "Deadline pressure rises in Q4."
        ),
        common_seller_position=(
            "Price-hard; deadline-flexible on structure."
        ),
        packet_signals=[
            "sponsor_fund_vintage_2016_or_earlier",
            "sponsor_exit_list_public",
            "management_fee_waiver_expired",
        ],
    ),
    SellerMotivation(
        name="covenant_trip_imminent",
        description=("Lender pressure / covenant trip in "
                      "next 1-2 measurement dates."),
        seller_urgency="high",
        buyer_leverage="high",
        price_sensitivity="high",
        negotiation_counter=(
            "Partner play: distressed framing. Offer "
            "meaningfully below sticker with fast close. "
            "Watch for unannounced liabilities."
        ),
        common_seller_position=(
            "Public line: 'strategic review'. Private line: "
            "'close by Q3 or we're in default'."
        ),
        packet_signals=[
            "net_debt_gt_7x_ebitda",
            "covenant_waiver_in_past_12_months",
            "private_credit_lender_on_record",
        ],
    ),
    SellerMotivation(
        name="failed_prior_process",
        description=("Seller ran a process that broke; back "
                      "to market at lower price."),
        seller_urgency="medium",
        buyer_leverage="high",
        price_sensitivity="high",
        negotiation_counter=(
            "Partner play: understand why prior buyers "
            "walked. If diligence surfaced something, it "
            "will surface again for us. Aggressive re-price."
        ),
        common_seller_position=(
            "New advisor, reframed thesis; hoping for "
            "different buyer pool."
        ),
        packet_signals=[
            "prior_process_within_24_months",
            "process_broke_before_loi",
            "new_banker_replacing_prior",
        ],
    ),
    SellerMotivation(
        name="management_exit_wanted",
        description=("CEO wants liquidity + exit; not "
                      "willing to roll equity."),
        seller_urgency="medium",
        buyer_leverage="medium",
        price_sensitivity="medium",
        negotiation_counter=(
            "Partner play: operator risk is real. Line up "
            "a CEO search pre-close; do not underwrite on "
            "the current CEO's post-close commitment."
        ),
        common_seller_position=(
            "CEO quotes 'transition role'; no specifics."
        ),
        packet_signals=[
            "ceo_declined_rollover",
            "ceo_unsigned_post_close_agreement",
            "ceo_age_60_plus_succession_unplanned",
        ],
    ),
    SellerMotivation(
        name="strategic_fatigue",
        description=("Sub-scale operator; can't compete "
                      "without platform capital."),
        seller_urgency="medium",
        buyer_leverage="medium",
        price_sensitivity="medium",
        negotiation_counter=(
            "Partner play: ops value is real; sell "
            "the partnership story, not just the price. "
            "Rollover + 100-day plan."
        ),
        common_seller_position=(
            "Believer in the partnership but wants full "
            "market price for the platform."
        ),
        packet_signals=[
            "revenue_under_100m_in_scale_market",
            "ceo_public_mentions_scale_challenge",
            "subscale_vs_top_5_peers",
        ],
    ),
    SellerMotivation(
        name="industry_trough_fear",
        description=("Seller expects regulatory or "
                      "reimbursement compression; selling "
                      "ahead of cut."),
        seller_urgency="high",
        buyer_leverage="low",
        price_sensitivity="low",
        negotiation_counter=(
            "Partner play: seller knows something. Do "
            "regulatory diligence cold. If OBBBA / site-"
            "neutral / state Medicaid exposure is "
            "material, we're re-pricing or passing."
        ),
        common_seller_position=(
            "Bull thesis + 'market is strong' — "
            "information asymmetry flag."
        ),
        packet_signals=[
            "medicare_ffs_gt_40pct",
            "hopd_exposure_material",
            "state_medicaid_vulnerability_public",
        ],
    ),
    SellerMotivation(
        name="activist_pressure",
        description=("Public parent spinning off segment "
                      "under activist pressure."),
        seller_urgency="medium",
        buyer_leverage="medium",
        price_sensitivity="medium",
        negotiation_counter=(
            "Partner play: negotiate with parent IR team, "
            "not target mgmt. Parent's public messaging is "
            "the real constraint."
        ),
        common_seller_position=(
            "Clean break; limited indemnity; rely on R&W."
        ),
        packet_signals=[
            "public_parent_activist_filing",
            "segment_announced_as_non_core",
            "board_sale_mandate_dated",
        ],
    ),
]


@dataclass
class MotivationMatch:
    motivation: SellerMotivation
    signals_matched: List[str] = field(default_factory=list)
    match_score: float = 0.0           # fraction of signals hit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motivation": {
                "name": self.motivation.name,
                "description": self.motivation.description,
                "seller_urgency": self.motivation.seller_urgency,
                "buyer_leverage": self.motivation.buyer_leverage,
                "price_sensitivity":
                    self.motivation.price_sensitivity,
                "negotiation_counter":
                    self.motivation.negotiation_counter,
                "common_seller_position":
                    self.motivation.common_seller_position,
            },
            "signals_matched": list(self.signals_matched),
            "match_score": self.match_score,
        }


@dataclass
class SellerMotivationReport:
    matches: List[MotivationMatch] = field(default_factory=list)
    dominant_motivation: Optional[str] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "dominant_motivation": self.dominant_motivation,
            "partner_note": self.partner_note,
        }


def decode_seller_motivation(
    signals: Dict[str, Any],
) -> SellerMotivationReport:
    """Given a dict of signal-name → bool/truthy values,
    rank the motivation library by fraction of signals
    matched."""
    matches: List[MotivationMatch] = []
    for mot in MOTIVATION_LIBRARY:
        hit = [s for s in mot.packet_signals
               if bool(signals.get(s, False))]
        if not hit:
            continue
        score = len(hit) / max(1, len(mot.packet_signals))
        matches.append(MotivationMatch(
            motivation=mot,
            signals_matched=hit,
            match_score=round(score, 3),
        ))
    matches.sort(key=lambda m: -m.match_score)

    dominant = matches[0].motivation.name if matches else None

    if not matches:
        note = ("No motivation signals detected. Partner: "
                "ask the banker directly — 'why are they "
                "selling now?' — before pricing.")
    elif len(matches) >= 3:
        note = (f"Multiple motivations: "
                f"{', '.join(m.motivation.name for m in matches[:3])}. "
                "Partner: seller's story is layered. Negotiate "
                "against the highest-urgency motivation; verify "
                "the others in diligence.")
    elif matches[0].motivation.buyer_leverage == "high":
        note = (f"Dominant motivation: {dominant}. Partner has "
                "high leverage — counter below sticker + "
                "structural asks.")
    else:
        note = (f"Dominant motivation: {dominant}. Partner "
                "leverage is "
                f"{matches[0].motivation.buyer_leverage}; "
                "price negotiation proceeds on merits.")

    return SellerMotivationReport(
        matches=matches,
        dominant_motivation=dominant,
        partner_note=note,
    )


def render_seller_motivation_markdown(
    r: SellerMotivationReport,
) -> str:
    lines = [
        "# Seller motivation decoder",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Dominant motivation: "
        f"{r.dominant_motivation or '—'}",
        f"- Matches: {len(r.matches)}",
        "",
    ]
    for m in r.matches:
        mot = m.motivation
        lines.append(f"## {mot.name} (score {m.match_score:.2f})")
        lines.append(f"- **Description:** {mot.description}")
        lines.append(
            f"- **Urgency:** {mot.seller_urgency} / "
            f"**Leverage:** {mot.buyer_leverage} / "
            f"**Price sensitivity:** {mot.price_sensitivity}"
        )
        lines.append(f"- **Seller opens with:** "
                     f"{mot.common_seller_position}")
        lines.append(f"- **Partner counter:** "
                     f"{mot.negotiation_counter}")
        lines.append(f"- **Signals matched:** "
                     f"{', '.join(m.signals_matched)}")
        lines.append("")
    return "\n".join(lines)


def list_all_motivations() -> List[str]:
    return [m.name for m in MOTIVATION_LIBRARY]
