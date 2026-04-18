"""Deal source quality reader — how the deal arrived.

Partner statement: "A proprietary deal from a 10-year
relationship is a different animal from a 20-bidder auction.
Same asset, different process, different price, different
diligence scope. Know the source before you set the team's
mandate."

### Why source matters

The partner's posture on a deal is shaped as much by **how
it arrived** as by the asset itself. A proprietary deal off
a relationship:

- Is priced to *relationship*, not market.
- Has longer diligence windows.
- Invites deeper ops diligence.
- Rarely has other active bidders.

A 20-bidder broad auction:

- Clears near market-top.
- Compresses diligence to 3-6 weeks.
- Requires pre-commit on structure.
- Rewards speed over depth.

This module encodes 8 source profiles each with:
- Typical price premium / discount vs market
- Implication for diligence scope
- Process-duration expectation
- Partner counter / posture

### 8 source profiles

1. **proprietary_from_relationship** — direct, off-market.
2. **limited_auction_invited** — banker-run, 3-5 bidders.
3. **broad_auction** — banker-run, 15+ bidders.
4. **second_look_after_broken_process** — prior process
   failed.
5. **distressed_forced_sale** — lender-driven.
6. **continuation_vehicle_inside** — current sponsor
   offering secondaries.
7. **reverse_inquiry** — target reached out.
8. **management_led_carveout** — MBO-style.

### Partner-note escalation

- `distressed_forced_sale` / `second_look` → "meaningful
  price discount possible; watch for hidden issue."
- `broad_auction` → "accept competitive clearing; win on
  structure or don't swing."
- `proprietary_from_relationship` → "you already have
  priced-in the relationship; diligence deeply, walk if
  math fails."
- `reverse_inquiry` → "ask why now — sometimes gem,
  sometimes strategic misfit."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DealSourceProfile:
    name: str
    description: str
    typical_price_premium_pct: float     # negative = discount
    diligence_scope_note: str
    process_duration_weeks: int
    partner_posture: str                 # "lean_in"/"balanced"/"caution"
    partner_counter: str = ""


SOURCE_LIBRARY: Dict[str, DealSourceProfile] = {
    "proprietary_from_relationship": DealSourceProfile(
        name="proprietary_from_relationship",
        description=(
            "Off-market; direct relationship with seller or "
            "operating partner. No banker."
        ),
        typical_price_premium_pct=-0.05,   # 5% below market
        diligence_scope_note=(
            "Extended diligence window. Deeper ops / clinical "
            "diligence possible. Build in 12-week plan."
        ),
        process_duration_weeks=12,
        partner_posture="lean_in",
        partner_counter=(
            "You already have priced-in the relationship. "
            "Diligence deeply, walk if math fails. Don't let "
            "relationship pressure override discipline."
        ),
    ),
    "limited_auction_invited": DealSourceProfile(
        name="limited_auction_invited",
        description=(
            "Banker-run process with 3-5 pre-qualified "
            "bidders. Selective invite."
        ),
        typical_price_premium_pct=0.03,
        diligence_scope_note=(
            "Standard data-room scope. 6-8 week IOI-to-LOI "
            "window."
        ),
        process_duration_weeks=8,
        partner_posture="balanced",
        partner_counter=(
            "Balanced process. Focus diligence on the 3 "
            "things that decide verdict; let banker-provided "
            "materials answer the rest."
        ),
    ),
    "broad_auction": DealSourceProfile(
        name="broad_auction",
        description=(
            "Banker-run with 15+ bidders. Seller optimizing "
            "for max price."
        ),
        typical_price_premium_pct=0.08,
        diligence_scope_note=(
            "Compressed 3-6 week window. Pre-commit on "
            "structure. Partners expect seller-friendly "
            "package."
        ),
        process_duration_weeks=5,
        partner_posture="caution",
        partner_counter=(
            "Broad auction clears near market-top. Win on "
            "structure or don't swing. If we can't price in "
            "thesis at top of range, drop in round 2."
        ),
    ),
    "second_look_after_broken_process": DealSourceProfile(
        name="second_look_after_broken_process",
        description=(
            "Prior process failed in last 24 months. Banker "
            "re-marketing."
        ),
        typical_price_premium_pct=-0.08,
        diligence_scope_note=(
            "Demand access to prior diligence notes. Every "
            "break is information — usually 1-2 specific "
            "deal-killers that prior buyers found."
        ),
        process_duration_weeks=10,
        partner_posture="caution",
        partner_counter=(
            "Meaningful discount possible but hidden issues "
            "likely. Spend diligence on prior-buyers' reason "
            "for walking before anything else."
        ),
    ),
    "distressed_forced_sale": DealSourceProfile(
        name="distressed_forced_sale",
        description=(
            "Lender or restructuring-driven. Seller under "
            "time pressure."
        ),
        typical_price_premium_pct=-0.15,
        diligence_scope_note=(
            "Fast-track diligence. Specific indemnity scope "
            "needed; seller may have unannounced liabilities. "
            "R&W insurance essential."
        ),
        process_duration_weeks=4,
        partner_posture="lean_in",
        partner_counter=(
            "Significant discount. Lean in on clear-"
            "liability assets; walk on messy ones. Speed "
            "is a real advantage here."
        ),
    ),
    "continuation_vehicle_inside": DealSourceProfile(
        name="continuation_vehicle_inside",
        description=(
            "Current sponsor recapping own portfolio company "
            "via GP-led secondary."
        ),
        typical_price_premium_pct=0.00,
        diligence_scope_note=(
            "Standard CV fairness-opinion scope. Partners "
            "can get sponsor-level detail but inside-price "
            "sets anchor."
        ),
        process_duration_weeks=16,
        partner_posture="balanced",
        partner_counter=(
            "Inside price set by fairness opinion. Outside "
            "bidders rarely win unless materially above mark. "
            "Don't chase."
        ),
    ),
    "reverse_inquiry": DealSourceProfile(
        name="reverse_inquiry",
        description=(
            "Target or target's management reached out to us "
            "directly."
        ),
        typical_price_premium_pct=-0.03,
        diligence_scope_note=(
            "Investigate why they're approaching us: (a) "
            "strategic misfit with current sponsor, (b) "
            "management wants out, (c) hidden value. All "
            "three are equally likely."
        ),
        process_duration_weeks=10,
        partner_posture="balanced",
        partner_counter=(
            "Reverse inquiry is information — ask why now. "
            "Sometimes gem, sometimes strategic misfit. "
            "Diligence the motivation first."
        ),
    ),
    "management_led_carveout": DealSourceProfile(
        name="management_led_carveout",
        description=(
            "MBO-style; incumbent mgmt leading the purchase "
            "of a division from parent."
        ),
        typical_price_premium_pct=-0.05,
        diligence_scope_note=(
            "Mgmt info-advantage is real but aligns "
            "incentives. Focus on separation costs / TSA "
            "complexity / standalone cost structure."
        ),
        process_duration_weeks=14,
        partner_posture="balanced",
        partner_counter=(
            "Mgmt alignment is a plus. TSA and carve-out "
            "separation complexity often underestimated — "
            "price that in explicitly."
        ),
    ),
}


@dataclass
class DealSourceInputs:
    source: str = ""                    # key into SOURCE_LIBRARY
    base_market_price_m: float = 0.0


@dataclass
class DealSourceReport:
    source: str
    profile: Optional[DealSourceProfile] = None
    expected_price_m: Optional[float] = None
    expected_discount_m: Optional[float] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "profile": ({
                "name": self.profile.name,
                "description": self.profile.description,
                "typical_price_premium_pct":
                    self.profile.typical_price_premium_pct,
                "diligence_scope_note":
                    self.profile.diligence_scope_note,
                "process_duration_weeks":
                    self.profile.process_duration_weeks,
                "partner_posture": self.profile.partner_posture,
                "partner_counter": self.profile.partner_counter,
            } if self.profile else None),
            "expected_price_m": self.expected_price_m,
            "expected_discount_m": self.expected_discount_m,
            "partner_note": self.partner_note,
        }


def read_deal_source(
    inputs: DealSourceInputs,
) -> DealSourceReport:
    profile = SOURCE_LIBRARY.get(inputs.source)
    if profile is None:
        return DealSourceReport(
            source=inputs.source,
            profile=None,
            partner_note=(
                f"Deal source '{inputs.source}' not modeled. "
                "Partner: ask the team how this deal arrived "
                "— sourcing shapes price and diligence scope."
            ),
        )

    expected_price = None
    expected_discount = None
    if inputs.base_market_price_m > 0:
        expected_price = round(
            inputs.base_market_price_m *
            (1.0 + profile.typical_price_premium_pct),
            2,
        )
        expected_discount = round(
            inputs.base_market_price_m - expected_price,
            2,
        )

    # Partner note keyed to posture + source.
    posture = profile.partner_posture
    if profile.name == "distressed_forced_sale":
        note = (
            f"Distressed sale — expected "
            f"{abs(profile.typical_price_premium_pct)*100:.0f}% "
            "discount. Partner: lean in on clean-liability "
            "assets; R&W essential; speed is a real edge."
        )
    elif profile.name == "second_look_after_broken_process":
        note = (
            "Second-look after broken process. Spend the "
            "first diligence week on *why prior buyers "
            "walked* — usually 1-2 named issues."
        )
    elif profile.name == "broad_auction":
        note = (
            "Broad auction. Clears near market-top. Win on "
            "structure or don't swing. If we can't price at "
            "top of range, drop round 2."
        )
    elif profile.name == "proprietary_from_relationship":
        note = (
            "Proprietary / relationship source. Extended "
            "diligence available. Do not let relationship "
            "pressure override discipline — walk if math "
            "fails."
        )
    elif posture == "lean_in":
        note = (
            f"Source '{profile.name}' posture: lean in. "
            "Clear process advantage; use it."
        )
    elif posture == "caution":
        note = (
            f"Source '{profile.name}' posture: caution. "
            "Manage expectation against clearing price."
        )
    else:
        note = (
            f"Source '{profile.name}' posture: balanced. "
            "Standard diligence and process discipline apply."
        )

    return DealSourceReport(
        source=inputs.source,
        profile=profile,
        expected_price_m=expected_price,
        expected_discount_m=expected_discount,
        partner_note=note,
    )


def list_deal_sources() -> List[str]:
    return sorted(SOURCE_LIBRARY.keys())


def render_deal_source_markdown(
    r: DealSourceReport,
) -> str:
    if r.profile is None:
        return (
            "# Deal source read\n\n"
            f"_{r.partner_note}_"
        )
    p = r.profile
    lines = [
        f"# Deal source read — {p.name}",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Description: {p.description}",
        f"- Typical premium/discount: "
        f"{p.typical_price_premium_pct*100:+.0f}%",
    ]
    if r.expected_price_m is not None:
        lines.append(
            f"- Expected price: ${r.expected_price_m:,.1f}M "
            f"(discount ${r.expected_discount_m:,.1f}M)"
        )
    lines.append(
        f"- Process duration: {p.process_duration_weeks} weeks"
    )
    lines.append(f"- Partner posture: `{p.partner_posture}`")
    lines.append(f"- Diligence scope: {p.diligence_scope_note}")
    lines.append(f"- Partner counter: {p.partner_counter}")
    return "\n".join(lines)
