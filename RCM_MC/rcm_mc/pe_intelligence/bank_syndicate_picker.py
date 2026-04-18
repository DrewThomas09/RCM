"""Bank syndicate picker — choose lenders for a deal.

Different deal sizes and sectors match different bank profiles:

- **Mega-deal (>$1B debt)** — bulge-bracket syndicate leadership
  (BAML, JPM, MS, GS, Citi).
- **Middle-market ($100M-$1B)** — commercial banks + BDCs + private
  credit (Wells, PNC, Truist, Antares, Owl Rock, Golub, Ares).
- **Lower-MM (<$100M)** — single-lender / club (Twin Brook, Monroe,
  NXT, Churchill, Madison Capital).
- **Healthcare specialist** — Capital One Healthcare, Siemens
  Financial (renamed Signature), Live Oak (for practice acquisitions).

This module takes deal size + sector + partner preferences and
returns a ranked shortlist + rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Lender:
    name: str
    type: str                             # "bulge" / "commercial" / "bdc" /
                                          # "direct_lender" / "specialist"
    min_hold_m: float
    max_hold_m: float
    healthcare_specialist: bool = False
    covenant_posture: str = "normal"      # "normal" / "looser" / "tighter"
    rate_competitive: bool = True         # pricing vs market
    notes: str = ""


LENDER_UNIVERSE: List[Lender] = [
    # Bulge bracket.
    Lender("JPMorgan", "bulge", 100.0, 5000.0, False,
           notes="Full capabilities; prefers platform deals."),
    Lender("Bank of America / BAML", "bulge", 100.0, 5000.0, False,
           notes="Strong leveraged finance franchise."),
    Lender("Goldman Sachs", "bulge", 150.0, 5000.0, False,
           notes="Prefers sponsor relationships; pricing on the wider side."),
    Lender("Morgan Stanley", "bulge", 150.0, 5000.0, False,
           notes="Broad leveraged finance; execution edge on complex."),
    Lender("Citi", "bulge", 100.0, 5000.0, False,
           notes="Global distribution; strong in syndication."),
    # Commercial / regional.
    Lender("Wells Fargo", "commercial", 25.0, 500.0, False,
           notes="Deep cash-flow capabilities; relationship-driven."),
    Lender("PNC", "commercial", 25.0, 400.0, False,
           notes="Strong middle-market; conservative covenants."),
    Lender("Truist", "commercial", 25.0, 400.0, False,
           notes="Healthcare vertical has depth."),
    Lender("US Bank", "commercial", 25.0, 350.0, False,
           notes="Conservative; good for sponsor relationship deals."),
    # Specialist — healthcare.
    Lender("Capital One Healthcare", "specialist", 25.0, 500.0, True,
           notes="Leading healthcare-services specialist."),
    Lender("Live Oak Bank", "specialist", 5.0, 50.0, True,
           notes="SBA-friendly for physician-practice acquisitions."),
    Lender("Siemens / Signature Healthcare", "specialist", 25.0, 300.0, True,
           notes="Equipment finance + working capital for hospitals/systems."),
    # Direct lenders / private credit.
    Lender("Antares", "direct_lender", 25.0, 400.0, False,
           notes="Unitranche; fast execution; looser covenants."),
    Lender("Owl Rock / Blue Owl Capital", "direct_lender", 75.0, 750.0, False,
           notes="Large direct lending; sophisticated."),
    Lender("Ares Direct Lending", "direct_lender", 50.0, 750.0, False,
           notes="Broad credit franchise; healthcare-capable."),
    Lender("Golub Capital", "direct_lender", 25.0, 500.0, False,
           notes="Sponsor-friendly; unitranche specialist."),
    Lender("Churchill", "direct_lender", 25.0, 350.0, False,
           notes="Sponsor-friendly mid-market."),
    Lender("Monroe Capital", "direct_lender", 20.0, 200.0, False,
           notes="Healthcare coverage; lower-MM focus."),
    Lender("Twin Brook", "direct_lender", 20.0, 300.0, False,
           notes="Unitranche; mid-market healthcare experience."),
    Lender("NXT Capital", "direct_lender", 10.0, 150.0, False,
           notes="Lower-MM focus; covenanted deals."),
    Lender("Madison Capital", "direct_lender", 15.0, 200.0, False,
           notes="Middle market direct lending."),
]


@dataclass
class SyndicateInputs:
    total_debt_m: float
    subsector: str = "specialty_practice"
    sponsor_needs_healthcare_specialist: bool = False
    prefers_looser_covenants: bool = False
    prioritize_rate: bool = False
    minimum_lenders: int = 2              # for syndication resilience
    maximum_lenders: int = 5


@dataclass
class LenderPick:
    lender: str
    rationale: str
    tier: str                             # "lead" / "joint" / "participant"


@dataclass
class SyndicateRecommendation:
    debt_m: float
    picks: List[LenderPick] = field(default_factory=list)
    fallback_picks: List[LenderPick] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debt_m": self.debt_m,
            "picks": [{"lender": p.lender, "rationale": p.rationale,
                        "tier": p.tier} for p in self.picks],
            "fallback_picks": [{"lender": p.lender, "rationale": p.rationale,
                                 "tier": p.tier} for p in self.fallback_picks],
            "partner_note": self.partner_note,
        }


def _tier_for_position(i: int) -> str:
    if i == 0:
        return "lead"
    if i < 3:
        return "joint"
    return "participant"


def pick_syndicate(inputs: SyndicateInputs) -> SyndicateRecommendation:
    # Filter candidates by deal size fit.
    candidates = [
        l for l in LENDER_UNIVERSE
        if l.min_hold_m <= inputs.total_debt_m <= l.max_hold_m * 2.5
    ]
    if not candidates:
        return SyndicateRecommendation(
            debt_m=inputs.total_debt_m,
            partner_note=("No lenders in library fit this deal size. "
                          "Consider club with overlapping holds."),
        )

    # Score each lender.
    def score(l: Lender) -> float:
        s = 0.0
        if inputs.sponsor_needs_healthcare_specialist and l.healthcare_specialist:
            s += 30.0
        if inputs.prefers_looser_covenants and l.covenant_posture == "looser":
            s += 15.0
        if (inputs.prefers_looser_covenants
                and l.type == "direct_lender"):
            s += 25.0
        if inputs.prioritize_rate and l.rate_competitive:
            s += 10.0
        # Fit for deal size.
        if l.min_hold_m <= inputs.total_debt_m <= l.max_hold_m:
            s += 20.0
        # Prefer bulge/commercial for very large deals.
        if inputs.total_debt_m > 1000 and l.type == "bulge":
            s += 15.0
        if inputs.total_debt_m <= 100 and l.type == "direct_lender":
            s += 10.0
        if 100 < inputs.total_debt_m <= 500 and l.type == "commercial":
            s += 10.0
        return s

    scored = sorted(candidates, key=score, reverse=True)

    picks: List[LenderPick] = []
    min_n = max(1, inputs.minimum_lenders)
    max_n = max(min_n, inputs.maximum_lenders)
    selected = scored[:max_n]
    for i, l in enumerate(selected):
        rationale_bits: List[str] = []
        if l.healthcare_specialist and inputs.sponsor_needs_healthcare_specialist:
            rationale_bits.append("healthcare specialist")
        if inputs.prefers_looser_covenants and l.type == "direct_lender":
            rationale_bits.append("direct lender / unitranche")
        if l.min_hold_m <= inputs.total_debt_m <= l.max_hold_m:
            rationale_bits.append("deal size match")
        if not rationale_bits:
            rationale_bits.append("deal-size compatible")
        picks.append(LenderPick(
            lender=l.name,
            rationale=f"{'; '.join(rationale_bits)}. {l.notes}",
            tier=_tier_for_position(i),
        ))

    # Fallback list: next 3 behind.
    fallback = [
        LenderPick(lender=l.name,
                   rationale=(f"Backup; {l.notes}"),
                   tier="participant")
        for l in scored[max_n:max_n + 3]
    ]

    if len(picks) < min_n:
        note = (f"Only {len(picks)} lender(s) fit — widen criteria or "
                "reduce debt size.")
    elif inputs.total_debt_m > 1000:
        note = (f"Large deal (${inputs.total_debt_m:,.0f}M) — use bulge-"
                "led syndicate with 4-6 joint arrangers.")
    elif inputs.total_debt_m > 250:
        note = (f"Middle-market deal (${inputs.total_debt_m:,.0f}M) — "
                "commercial or direct-lender club with 2-4 participants.")
    else:
        note = (f"Smaller deal (${inputs.total_debt_m:,.0f}M) — single "
                "direct lender or 2-lender club.")

    return SyndicateRecommendation(
        debt_m=inputs.total_debt_m,
        picks=picks,
        fallback_picks=fallback,
        partner_note=note,
    )


def render_syndicate_markdown(r: SyndicateRecommendation) -> str:
    lines = [
        "# Bank syndicate recommendation",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total debt: ${r.debt_m:,.1f}M",
        "",
        "## Primary picks",
        "",
    ]
    for p in r.picks:
        lines.append(f"- **{p.lender}** ({p.tier}): {p.rationale}")
    if r.fallback_picks:
        lines.extend(["", "## Fallback list", ""])
        for p in r.fallback_picks:
            lines.append(f"- {p.lender}: {p.rationale}")
    return "\n".join(lines)
