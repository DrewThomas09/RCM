"""Buyer-type fit analyzer — which buyer is right for this asset?

Different from `exit_channel_selector` (strategic / sponsor /
IPO / continuation generic ranking). This module asks a more
specific partner question: "Given THIS asset's profile, which
SPECIFIC buyer type is the right fit for the banker to target?"

Buyer types:

- **Strategic health system** — for assets that extend clinical
  capabilities geographically.
- **Strategic payer-led (UHG / Elevance / Humana)** — for
  assets that close the value chain for a national payer.
- **Specialty consolidator** — for roll-up-ready assets in a
  specialty (dermatology, dental, vet, PT, etc.).
- **Larger sponsor** — for platform-ready growth assets.
- **Peer sponsor (lateral)** — for modest asset with a clean
  thesis.
- **IPO** — for category leaders with public-ready scale.
- **Continuation vehicle** — if the asset has material runway
  and the GP has conviction.
- **Industry passive (REIT / infra)** — for real-estate-heavy
  asset mixes.

The module scores each buyer type against the asset's profile
and returns the top 3 with rationale and the specific named
buyers a banker should pitch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BuyerFitContext:
    subsector: str = ""
    ebitda_m: float = 0.0
    revenue_m: float = 0.0
    recurring_ebitda_pct: float = 0.90
    is_category_leader: bool = False
    has_national_scale: bool = False
    has_clean_geography: bool = True
    has_real_estate_heavy: bool = False
    has_mna_pipeline: bool = False
    commercial_payer_pct: float = 0.50
    vbc_revenue_pct: float = 0.0
    organic_growth_pct: float = 0.08
    cycle_phase: str = "mid_expansion"


@dataclass
class BuyerTypeFit:
    buyer_type: str
    score_0_100: int
    named_targets: List[str]
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_type": self.buyer_type,
            "score_0_100": self.score_0_100,
            "named_targets": list(self.named_targets),
            "rationale": self.rationale,
        }


@dataclass
class BuyerFitReport:
    fits: List[BuyerTypeFit] = field(default_factory=list)
    top_pick: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fits": [f.to_dict() for f in self.fits],
            "top_pick": self.top_pick,
            "partner_note": self.partner_note,
        }


def _strategic_health_system(
    ctx: BuyerFitContext,
) -> BuyerTypeFit:
    score = 40
    if ctx.subsector in ("hospital", "outpatient_asc",
                          "home_health"):
        score += 20
    if ctx.has_clean_geography:
        score += 10
    if ctx.ebitda_m >= 50:
        score += 10
    if ctx.is_category_leader:
        score += 15
    return BuyerTypeFit(
        buyer_type="strategic_health_system",
        score_0_100=min(100, score),
        named_targets=["HCA", "Tenet", "CommonSpirit",
                        "Ascension", "AdventHealth"],
        rationale=(
            "Health systems buy outpatient / home-health / ASC "
            "assets for geographic fill-in. Cleaner when the asset "
            "has a defensible geography and scale."),
    )


def _strategic_payer_led(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 30
    if ctx.vbc_revenue_pct >= 0.10:
        score += 25
    if ctx.subsector in ("home_health", "specialty_practice"):
        score += 15
    if ctx.has_national_scale:
        score += 15
    if ctx.commercial_payer_pct >= 0.50:
        score += 10
    return BuyerTypeFit(
        buyer_type="strategic_payer_led",
        score_0_100=min(100, score),
        named_targets=["UnitedHealth/Optum", "Elevance/Carelon",
                        "Humana/CenterWell", "CVS/Aetna",
                        "Cigna/Evernorth"],
        rationale=(
            "National payers are acquiring care-delivery assets to "
            "close the value chain. Premium for VBC-ready books and "
            "national footprint."),
    )


def _specialty_consolidator(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 25
    if ctx.subsector in ("specialty_practice", "outpatient_asc",
                          "dermatology", "dental", "vet"):
        score += 30
    if ctx.has_mna_pipeline:
        score += 15
    if ctx.ebitda_m <= 75 and ctx.ebitda_m >= 10:
        score += 10
    if ctx.is_category_leader:
        score += 10
    return BuyerTypeFit(
        buyer_type="specialty_consolidator",
        score_0_100=min(100, score),
        named_targets=["USOC (ortho)", "US Dermatology Partners",
                        "Heartland Dental", "Shore Capital",
                        "Madison Dearborn ASC platforms"],
        rationale=(
            "Specialty consolidators pay premium for roll-up-ready "
            "scale; they see acquired assets as accretion fuel."),
    )


def _larger_sponsor(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 40
    if ctx.ebitda_m >= 75:
        score += 15
    if ctx.organic_growth_pct >= 0.10:
        score += 15
    if ctx.recurring_ebitda_pct >= 0.90:
        score += 10
    if ctx.cycle_phase in ("mid_expansion", "peak"):
        score += 10
    return BuyerTypeFit(
        buyer_type="larger_sponsor",
        score_0_100=min(100, score),
        named_targets=["KKR", "Blackstone", "Bain Capital",
                        "Carlyle", "TPG"],
        rationale=(
            "Upper-MM and mega sponsors pay for platform-ready "
            "growth assets with clean recurring EBITDA and organic "
            "momentum."),
    )


def _peer_sponsor(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 55
    if ctx.ebitda_m <= 50:
        score += 15
    if ctx.recurring_ebitda_pct >= 0.80:
        score += 10
    return BuyerTypeFit(
        buyer_type="peer_sponsor",
        score_0_100=min(100, score),
        named_targets=["New Mountain", "Silversmith", "Nordic Capital",
                        "Welsh Carson", "General Atlantic"],
        rationale=(
            "Peer sponsors are the fallback — reliable if the asset "
            "doesn't attract strategics and isn't big enough for the "
            "mega-fund list."),
    )


def _ipo(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 15
    if ctx.revenue_m >= 400 and ctx.ebitda_m >= 80:
        score += 30
    if ctx.is_category_leader:
        score += 20
    if ctx.organic_growth_pct >= 0.15:
        score += 15
    if ctx.cycle_phase == "peak":
        score += 10
    return BuyerTypeFit(
        buyer_type="ipo",
        score_0_100=min(100, score),
        named_targets=["Goldman / Morgan Stanley / JPM equity desks"],
        rationale=(
            "IPO path needs scale + growth + leadership. Typical "
            "minimum: ~$400M revenue and ~$80M EBITDA; >15% organic."),
    )


def _continuation(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 20
    if ctx.organic_growth_pct >= 0.10:
        score += 15
    if ctx.has_mna_pipeline:
        score += 10
    if ctx.recurring_ebitda_pct >= 0.90:
        score += 10
    return BuyerTypeFit(
        buyer_type="continuation_vehicle",
        score_0_100=min(100, score),
        named_targets=["ICG / Pantheon / Lexington / Coller Capital"],
        rationale=(
            "Continuation vehicles work when the GP has high "
            "conviction and the asset has named runway — 2-3 more "
            "years of thesis execution ahead."),
    )


def _industry_passive(ctx: BuyerFitContext) -> BuyerTypeFit:
    score = 15
    if ctx.has_real_estate_heavy:
        score += 40
    if ctx.subsector in ("hospital", "home_health", "behavioral"):
        score += 10
    return BuyerTypeFit(
        buyer_type="industry_passive",
        score_0_100=min(100, score),
        named_targets=["MPT", "Sabra", "Omega", "Welltower",
                        "Ventas"],
        rationale=(
            "Healthcare REITs want the real estate; operating "
            "company stays with management. Useful when the real-"
            "estate value is meaningful vs operating-co value."),
    )


BUILDERS = (
    _strategic_health_system,
    _strategic_payer_led,
    _specialty_consolidator,
    _larger_sponsor,
    _peer_sponsor,
    _ipo,
    _continuation,
    _industry_passive,
)


def analyze_buyer_fit(ctx: BuyerFitContext) -> BuyerFitReport:
    fits = [b(ctx) for b in BUILDERS]
    fits.sort(key=lambda f: f.score_0_100, reverse=True)
    top = fits[0]
    runner_up = fits[1]

    note = (f"Top buyer type: **{top.buyer_type}** "
            f"({top.score_0_100}/100). Runner-up: "
            f"{runner_up.buyer_type} ({runner_up.score_0_100}/100). "
            "Banker should lead with the top; keep runner-up in the "
            "buyer book for round 2 depth.")

    return BuyerFitReport(
        fits=fits,
        top_pick=top.buyer_type,
        partner_note=note,
    )


def render_buyer_fit_markdown(r: BuyerFitReport) -> str:
    lines = [
        "# Buyer-type fit analyzer",
        "",
        f"_{r.partner_note}_",
        "",
        "| Buyer type | Score | Named targets |",
        "|---|---:|---|",
    ]
    for f in r.fits:
        targets = ", ".join(f.named_targets[:3])
        lines.append(
            f"| {f.buyer_type} | {f.score_0_100} | {targets}{'...' if len(f.named_targets) > 3 else ''} |"
        )
    lines.extend(["", "## Rationale per type", ""])
    for f in r.fits:
        lines.append(f"- **{f.buyer_type}** ({f.score_0_100}): "
                     f"{f.rationale}")
    return "\n".join(lines)
