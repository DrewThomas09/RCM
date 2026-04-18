"""Sponsor reputation tracker — who are we dealing with across the table?

Partners keep a mental file on other sponsors. When a deal hits
market and you see Sponsor X is also bidding, you want to know:

- Are they disciplined or known to over-pay?
- Do they add operating value or strip-mine?
- Are they a natural buyer at our exit?
- Are they a good co-investor if we want to share risk?

This module maintains a partner-approximated reputation map with
five dimensions scored 0-100:

- **pricing_discipline** — do they pay rational multiples?
- **operating_value_add** — do they improve companies?
- **exit_track_record** — do they generate clean returns for LPs?
- **reputational_profile** — how are they regarded externally?
- **cultural_fit_with_management** — do CEOs like working with them?

Partners use this to pressure-test bids, pick co-investors, and
target the right sponsor-to-sponsor exit buyer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SponsorProfile:
    name: str
    pricing_discipline: int = 70
    operating_value_add: int = 70
    exit_track_record: int = 70
    reputational_profile: int = 70
    cultural_fit_with_management: int = 70
    known_archetypes: List[str] = field(default_factory=list)
    notes: str = ""


# Partner-approximated cross-sponsor book. Illustrative only; real
# partners refresh against direct observation and LP intel.
SPONSOR_BOOK: Dict[str, SponsorProfile] = {
    # Mega-funds.
    "KKR": SponsorProfile(
        name="KKR",
        pricing_discipline=72, operating_value_add=80,
        exit_track_record=82, reputational_profile=85,
        cultural_fit_with_management=75,
        known_archetypes=["platform_buyer", "international_capable"],
        notes=("Premium brand; selective at auction. Operating "
               "partner bench is deep."),
    ),
    "Blackstone": SponsorProfile(
        name="Blackstone",
        pricing_discipline=68, operating_value_add=82,
        exit_track_record=84, reputational_profile=85,
        cultural_fit_with_management=72,
        known_archetypes=["platform_buyer", "real_assets_capable"],
        notes="Price-leader in auctions; strong post-close playbook.",
    ),
    "Bain Capital": SponsorProfile(
        name="Bain Capital",
        pricing_discipline=75, operating_value_add=85,
        exit_track_record=80, reputational_profile=82,
        cultural_fit_with_management=78,
        known_archetypes=["platform_buyer", "healthcare_deep"],
        notes=("Consulting-heritage operating value-add; sophisticated "
               "healthcare book."),
    ),
    "Carlyle": SponsorProfile(
        name="Carlyle",
        pricing_discipline=70, operating_value_add=72,
        exit_track_record=72, reputational_profile=78,
        cultural_fit_with_management=70,
        known_archetypes=["platform_buyer"],
        notes="Mixed track record in healthcare; watch integration.",
    ),
    "TPG": SponsorProfile(
        name="TPG",
        pricing_discipline=70, operating_value_add=75,
        exit_track_record=76, reputational_profile=80,
        cultural_fit_with_management=72,
        known_archetypes=["platform_buyer", "growth_capable"],
        notes="Strong in growth equity and tech-enabled healthcare.",
    ),
    # Upper-MM healthcare specialists.
    "New Mountain Capital": SponsorProfile(
        name="New Mountain Capital",
        pricing_discipline=80, operating_value_add=85,
        exit_track_record=88, reputational_profile=85,
        cultural_fit_with_management=82,
        known_archetypes=["healthcare_specialist",
                           "consolidator_capable"],
        notes="Sector specialist; typically disciplined.",
    ),
    "Welsh Carson": SponsorProfile(
        name="Welsh Carson Anderson & Stowe",
        pricing_discipline=82, operating_value_add=88,
        exit_track_record=85, reputational_profile=87,
        cultural_fit_with_management=85,
        known_archetypes=["healthcare_specialist", "ppm_capable",
                           "platform_buyer"],
        notes=("Deep physician-practice playbook; disciplined bidder."),
    ),
    "Silversmith": SponsorProfile(
        name="Silversmith",
        pricing_discipline=78, operating_value_add=80,
        exit_track_record=80, reputational_profile=78,
        cultural_fit_with_management=80,
        known_archetypes=["growth_equity", "founder_friendly"],
        notes="Growth-focused; good founder-CEO fit.",
    ),
    "Leonard Green": SponsorProfile(
        name="Leonard Green & Partners",
        pricing_discipline=72, operating_value_add=70,
        exit_track_record=70, reputational_profile=72,
        cultural_fit_with_management=65,
        known_archetypes=["buyout", "consumer_healthcare"],
        notes=("Mixed healthcare book historically; Prospect Medical "
               "is a cautionary tale."),
    ),
    "Cerberus": SponsorProfile(
        name="Cerberus",
        pricing_discipline=65, operating_value_add=55,
        exit_track_record=55, reputational_profile=55,
        cultural_fit_with_management=50,
        known_archetypes=["distressed", "opportunistic"],
        notes=("Steward legacy looms; distressed approach can strip-"
               "mine operating assets."),
    ),
    "Apollo": SponsorProfile(
        name="Apollo",
        pricing_discipline=68, operating_value_add=70,
        exit_track_record=75, reputational_profile=70,
        cultural_fit_with_management=65,
        known_archetypes=["structured", "credit_capable"],
        notes=("Credit-flavored structures; complicated cap tables "
               "common."),
    ),
}


@dataclass
class SponsorAssessment:
    name: str
    overall_score_0_100: int
    strongest_dim: str
    weakest_dim: str
    profile: SponsorProfile
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "overall_score_0_100": self.overall_score_0_100,
            "strongest_dim": self.strongest_dim,
            "weakest_dim": self.weakest_dim,
            "notes": self.profile.notes,
            "known_archetypes": list(self.profile.known_archetypes),
            "partner_commentary": self.partner_commentary,
        }


def _commentary(profile: SponsorProfile, context: str) -> str:
    score_avg = (profile.pricing_discipline + profile.operating_value_add
                 + profile.exit_track_record + profile.reputational_profile
                 + profile.cultural_fit_with_management) / 5
    if context == "competing_bidder":
        if profile.pricing_discipline < 65:
            return ("Expect aggressive bidding; this sponsor stretches "
                    "price. Don't anchor to their bid level.")
        if profile.pricing_discipline >= 80:
            return ("Disciplined bidder — if they pass, listen. If they "
                    "chase the auction, the math really works.")
        return "Bids in the middle of the pack; informative but not authoritative."
    if context == "co_investor":
        if profile.operating_value_add >= 80 and profile.cultural_fit_with_management >= 75:
            return ("Strong co-investor partner — adds operating value "
                    "and plays well with CEOs.")
        if profile.operating_value_add < 60:
            return ("Co-invest reluctantly; passive-capital posture "
                    "doesn't add to the operating agenda.")
        return "Workable co-investor; use if relationship is valuable."
    if context == "exit_buyer":
        if profile.reputational_profile >= 80 and score_avg >= 75:
            return ("Natural exit-buyer candidate; quality counterparty "
                    "for the sell-side process.")
        return "Acceptable exit candidate; no premium over generic sponsor."
    return (f"Average reputation {int(score_avg)}/100.")


def assess_sponsor(
    name: str, context: str = "competing_bidder",
) -> Optional[SponsorAssessment]:
    profile = SPONSOR_BOOK.get(name)
    if profile is None:
        return None
    dims = {
        "pricing_discipline": profile.pricing_discipline,
        "operating_value_add": profile.operating_value_add,
        "exit_track_record": profile.exit_track_record,
        "reputational_profile": profile.reputational_profile,
        "cultural_fit_with_management":
            profile.cultural_fit_with_management,
    }
    overall = int(round(sum(dims.values()) / len(dims)))
    strongest = max(dims, key=dims.get)
    weakest = min(dims, key=dims.get)
    return SponsorAssessment(
        name=name,
        overall_score_0_100=overall,
        strongest_dim=strongest,
        weakest_dim=weakest,
        profile=profile,
        partner_commentary=_commentary(profile, context),
    )


def list_sponsors() -> List[str]:
    return sorted(SPONSOR_BOOK.keys())


def render_sponsor_assessment_markdown(
    a: SponsorAssessment,
) -> str:
    lines = [
        f"# {a.name} — Sponsor reputation",
        "",
        f"- Overall: **{a.overall_score_0_100}/100**",
        f"- Strongest dimension: {a.strongest_dim} "
        f"({getattr(a.profile, a.strongest_dim)})",
        f"- Weakest dimension: {a.weakest_dim} "
        f"({getattr(a.profile, a.weakest_dim)})",
        f"- Notes: {a.profile.notes}",
        f"- Known archetypes: "
        f"{', '.join(a.profile.known_archetypes) or '—'}",
        "",
        f"**Partner commentary:** {a.partner_commentary}",
    ]
    return "\n".join(lines)
