"""Bidder landscape reader — who else is at the table.

Partner statement: "I don't just need to know the asset
— I need to know who else wants it. A payer-backed
strategic sets a different clearing price than four
generalist sponsors."

The process is half-decided by **who else is bidding**.
Different bidder profiles behave differently:

- Strategics (payer-adjacent / same-sector) bring lower
  cost of capital and hunt for synergies.
- Healthcare-specialist sponsors are disciplined and
  pricing-rational.
- Generalist sponsors often overpay early, walk late.
- Family offices accept lower IRR for longer hold.
- Continuation vehicles recap themselves at a premium.

The partner's read on the bidder landscape affects:

- **Likely clearing price** — does the comp field bring
  strategic buyers willing to overpay?
- **Our posture** — reach vs. hold vs. drop.
- **Concessions we need to make** — structure vs. price.
- **Process posture** — accelerate or slow-play.

### 10 bidder profiles modeled

1. **strategic_payer_adjacent** — payers buying providers
   (Optum-style).
2. **strategic_same_sector** — consolidator in same sub-
   sector.
3. **strategic_crossover** — retail / tech / consumer
   buyer entering healthcare.
4. **sponsor_healthcare_specialist** — committed PE
   healthcare shop.
5. **sponsor_generalist** — cross-sector PE.
6. **sponsor_vintage_end** — fund at end-of-life.
7. **sponsor_first_fund** — new shop with capital to prove.
8. **family_office** — patient capital; lower IRR
   threshold.
9. **continuation_vehicle** — current sponsor recapping.
10. **foreign_buyer** — non-US strategic or sovereign-
    adjacent.

Each profile carries:
- `typical_behavior` — what they do in process.
- `expected_price_premium_pct` — rough over/under vs.
  market.
- `concession_posture` — price vs. structure.
- `partner_posture` — stay / drop / reach / hold.
- `partner_counter` — what to do when this profile is in
  the room.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BidderProfile:
    name: str
    typical_behavior: str
    expected_price_premium_pct: float      # e.g., +0.05 = 5% over
    concession_posture: str                # "price" / "structure" /
                                            # "balanced"
    partner_posture: str                   # "stay"/"drop"/"reach"/"hold"
    partner_counter: str = ""


PROFILE_LIBRARY: List[BidderProfile] = [
    BidderProfile(
        name="strategic_payer_adjacent",
        typical_behavior=(
            "Pays up for vertical-integration thesis. Cost of "
            "capital 300-500 bps below PE. Has regulatory-"
            "adjacency diligence team."
        ),
        expected_price_premium_pct=0.15,
        concession_posture="price",
        partner_posture="drop",
        partner_counter=(
            "Payer-adjacent strategic will pay 15% over. "
            "Drop the process unless we have a cost-of-"
            "capital answer; otherwise we're wasting "
            "diligence budget."
        ),
    ),
    BidderProfile(
        name="strategic_same_sector",
        typical_behavior=(
            "Already owns adjacent platform. Sees synergies "
            "we don't. Often does pre-emptive bid."
        ),
        expected_price_premium_pct=0.10,
        concession_posture="price",
        partner_posture="drop",
        partner_counter=(
            "Same-sector strategic with synergy angle will "
            "clear at 10% over our number. Drop unless this "
            "is a scarce asset we *must* own."
        ),
    ),
    BidderProfile(
        name="strategic_crossover",
        typical_behavior=(
            "Retail / tech / consumer operator new to "
            "healthcare. Tends to overpay early, walk at "
            "reg-diligence, or make structural errors."
        ),
        expected_price_premium_pct=0.05,
        concession_posture="balanced",
        partner_posture="stay",
        partner_counter=(
            "Crossover often fails diligence. Stay in the "
            "process; we become the backup bid at the "
            "crossover's walk."
        ),
    ),
    BidderProfile(
        name="sponsor_healthcare_specialist",
        typical_behavior=(
            "Disciplined pricing, shape-aware. Walks on "
            "fundamentals. Knows the sector traps."
        ),
        expected_price_premium_pct=0.0,
        concession_posture="structure",
        partner_posture="hold",
        partner_counter=(
            "Specialist competitor prices like us. Process "
            "will clear in the range. Hold our posture and "
            "win on structure."
        ),
    ),
    BidderProfile(
        name="sponsor_generalist",
        typical_behavior=(
            "Less sector context. Overpays on premium "
            "narrative, discovers issues in diligence, "
            "walks or re-prices late."
        ),
        expected_price_premium_pct=0.08,
        concession_posture="price",
        partner_posture="stay",
        partner_counter=(
            "Generalist will clear at premium in first "
            "round then walk. Stay disciplined; we're the "
            "backup bid at re-price."
        ),
    ),
    BidderProfile(
        name="sponsor_vintage_end",
        typical_behavior=(
            "Fund-life pressure. Aggressive in early "
            "rounds. May accept weak structure to close "
            "by quarter-end."
        ),
        expected_price_premium_pct=0.10,
        concession_posture="price",
        partner_posture="drop",
        partner_counter=(
            "Vintage-end sponsor outpays us on LP-clock "
            "logic. Drop unless we have a structural "
            "angle (reg / ops) they can't match."
        ),
    ),
    BidderProfile(
        name="sponsor_first_fund",
        typical_behavior=(
            "New shop with capital to prove. Willing to "
            "reach on marquee asset. Unpredictable in "
            "final rounds."
        ),
        expected_price_premium_pct=0.07,
        concession_posture="balanced",
        partner_posture="stay",
        partner_counter=(
            "First-fund sponsor overreaches early; comes "
            "back to earth in diligence. Stay; be the "
            "pricing-rational bid."
        ),
    ),
    BidderProfile(
        name="family_office",
        typical_behavior=(
            "Lower IRR threshold (15-18% OK). Longer hold "
            "(7-10 years). Price up to 7% over PE on "
            "stable cash-flow assets."
        ),
        expected_price_premium_pct=0.07,
        concession_posture="balanced",
        partner_posture="hold",
        partner_counter=(
            "Family office pays up on stable assets but "
            "walks on volatility. If asset has recurring-"
            "EBITDA profile, we're competing on process "
            "speed."
        ),
    ),
    BidderProfile(
        name="continuation_vehicle",
        typical_behavior=(
            "Current sponsor recapping their own asset via "
            "secondaries. Price set by GP-led fairness "
            "opinion."
        ),
        expected_price_premium_pct=0.00,
        concession_posture="structure",
        partner_posture="stay",
        partner_counter=(
            "Continuation vehicle sets an inside price. "
            "Outside bidders rarely win unless materially "
            "above CV mark. Don't chase; let CV close."
        ),
    ),
    BidderProfile(
        name="foreign_buyer",
        typical_behavior=(
            "Non-US strategic or sovereign-adjacent. Pays "
            "up but faces CFIUS / FCC / reg scrutiny."
        ),
        expected_price_premium_pct=0.12,
        concession_posture="price",
        partner_posture="stay",
        partner_counter=(
            "Foreign buyer clears high but regulatory "
            "delays / walk rights common. Stay — we're "
            "the backup if CFIUS blocks."
        ),
    ),
]


@dataclass
class BidderLandscapeInputs:
    bidders_present: List[str] = field(default_factory=list)
    our_base_price_m: float = 0.0


@dataclass
class BidderObservation:
    profile: BidderProfile
    expected_clearing_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": {
                "name": self.profile.name,
                "typical_behavior": self.profile.typical_behavior,
                "expected_price_premium_pct":
                    self.profile.expected_price_premium_pct,
                "concession_posture":
                    self.profile.concession_posture,
                "partner_posture": self.profile.partner_posture,
                "partner_counter": self.profile.partner_counter,
            },
            "expected_clearing_m": self.expected_clearing_m,
        }


@dataclass
class BidderLandscapeReport:
    observations: List[BidderObservation] = field(default_factory=list)
    likely_clearing_price_m: Optional[float] = None
    recommended_partner_posture: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observations": [o.to_dict()
                             for o in self.observations],
            "likely_clearing_price_m":
                self.likely_clearing_price_m,
            "recommended_partner_posture":
                self.recommended_partner_posture,
            "partner_note": self.partner_note,
        }


_PROFILE_BY_NAME: Dict[str, BidderProfile] = {
    p.name: p for p in PROFILE_LIBRARY
}


def read_bidder_landscape(
    inputs: BidderLandscapeInputs,
) -> BidderLandscapeReport:
    observations: List[BidderObservation] = []
    clearing_prices: List[float] = []
    for name in inputs.bidders_present:
        profile = _PROFILE_BY_NAME.get(name)
        if profile is None:
            continue
        expected_m = (
            inputs.our_base_price_m *
            (1.0 + profile.expected_price_premium_pct)
            if inputs.our_base_price_m > 0 else None
        )
        observations.append(BidderObservation(
            profile=profile,
            expected_clearing_m=(round(expected_m, 2)
                                   if expected_m else None),
        ))
        if expected_m is not None:
            clearing_prices.append(expected_m)

    # Clearing price = max(expected) — because highest-premium
    # bidder sets the market.
    likely_clearing = (max(clearing_prices)
                        if clearing_prices else None)

    # Recommended partner posture = plurality of individual
    # postures, weighted toward "drop" when high-premium
    # strategics present.
    postures = [o.profile.partner_posture for o in observations]
    if not postures:
        posture = ""
    elif any(o.profile.expected_price_premium_pct >= 0.10
              and o.profile.concession_posture == "price"
              for o in observations):
        posture = "drop"
    elif "stay" in postures:
        posture = "stay"
    elif "hold" in postures:
        posture = "hold"
    else:
        posture = postures[0]

    # Partner note.
    if not observations:
        note = ("No recognized bidder profiles provided. Partner: "
                "ask the banker directly who else is in the "
                "process. Information asymmetry costs us.")
    elif posture == "drop":
        note = (
            f"Landscape includes a high-premium strategic "
            f"(expected clearing "
            f"${likely_clearing:,.0f}M "
            f"vs. base ${inputs.our_base_price_m:,.0f}M). "
            "Partner: drop unless we have a structural answer."
        )
    elif posture == "stay":
        note = (
            f"Competing bidders likely to walk in diligence "
            f"(expected clearing ${likely_clearing:,.0f}M). "
            "Partner: stay disciplined; we are the backup bid."
        )
    else:
        note = (
            f"Clearing price expected ${likely_clearing:,.0f}M. "
            f"Partner posture: {posture}. Win on structure, not "
            "price."
        )

    return BidderLandscapeReport(
        observations=observations,
        likely_clearing_price_m=(round(likely_clearing, 2)
                                   if likely_clearing else None),
        recommended_partner_posture=posture,
        partner_note=note,
    )


def list_bidder_profiles() -> List[str]:
    return [p.name for p in PROFILE_LIBRARY]


def render_bidder_landscape_markdown(
    r: BidderLandscapeReport,
) -> str:
    lines = [
        "# Bidder landscape read",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Likely clearing price: "
        f"{'$'+format(r.likely_clearing_price_m, ',.1f')+'M' if r.likely_clearing_price_m else '—'}",
        f"- Recommended partner posture: "
        f"`{r.recommended_partner_posture or '—'}`",
        "",
        "| Profile | Premium | Clearing | Posture | "
        "Partner counter |",
        "|---|---|---|---|---|",
    ]
    for o in r.observations:
        p = o.profile
        lines.append(
            f"| {p.name} | "
            f"{p.expected_price_premium_pct*100:+.0f}% | "
            f"${o.expected_clearing_m:,.0f}M | "
            f"{p.partner_posture} | {p.partner_counter} |"
        )
    return "\n".join(lines)
