"""Payer watchlist by name — per-payer posture + partner read.

Partner statement: "Every major commercial payer has
a posture — some are rate-aggressive, some still
negotiate in good faith, some are geographically
dominant and run providers. Knowing the named payer
tells you what to expect at the renewal table. When
the deal's top-3 includes a payer known for rate-
cuts in the specialty, that's a pricing signal
before you read the contract."

Distinct from:
- `payer_renegotiation_timing_model` — calendar /
  posture *bands* only.
- `payer_mix_risk` — share concentration.
- `medicare_advantage_bridge_trap` — MA narrative.

This module is the **named payer book**: 12 top
commercial + MA-operating payers with a per-payer
posture, recent-notable-action, and exposure read
for deals where that payer appears in the top mix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Per-payer book. Postures use the same bands as
# payer_renegotiation_timing_model. "recent_stance"
# reflects partner-known behavior patterns, not
# forensic news.
PAYER_BOOK: Dict[str, Dict[str, Any]] = {
    "United Healthcare": {
        "posture": "aggressive",
        "geography": "national",
        "ma_exposure": "very_high",
        "recent_stance": (
            "Aggressive narrow-network construction; "
            "pushed rate cuts in commercial across "
            "most specialties 2023-2025."
        ),
        "partner_read": (
            "If in your top-3, expect -3 to -6% at "
            "next renewal. Pre-negotiate with named "
            "contact; UNH's posture is the market tell."
        ),
    },
    "Anthem / Elevance": {
        "posture": "firm",
        "geography": "multi-state BCBS",
        "ma_exposure": "high",
        "recent_stance": (
            "Firm but negotiates; MLR rebates and "
            "quality-bonus exposure makes them more "
            "cooperative than UNH on quality-led "
            "providers."
        ),
        "partner_read": (
            "Expect flat-to-minor-cut on commercial; "
            "push quality data to win rate upside."
        ),
    },
    "Aetna / CVS": {
        "posture": "firm",
        "geography": "national",
        "ma_exposure": "high",
        "recent_stance": (
            "Integration with CVS / MinuteClinic "
            "changes site-of-service pressure on "
            "ambulatory; MA growth pressure drives "
            "corridor negotiation."
        ),
        "partner_read": (
            "Watch for vertical-integration pressure "
            "where Aetna wants to route volume to CVS "
            "ambulatory."
        ),
    },
    "Cigna": {
        "posture": "firm",
        "geography": "national + international",
        "ma_exposure": "medium",
        "recent_stance": (
            "Strong commercial focus; Evernorth PBM "
            "arm dominant. Provider contracting "
            "relatively cooperative vs. UNH."
        ),
        "partner_read": (
            "Cigna in top-3 is generally favorable; "
            "specialty-drug exposure needs Evernorth "
            "lens."
        ),
    },
    "Humana": {
        "posture": "firm",
        "geography": "national MA",
        "ma_exposure": "very_high",
        "recent_stance": (
            "Dominant MA-first posture; aggressive "
            "risk-share contract push on primary "
            "care."
        ),
        "partner_read": (
            "MA-heavy providers should model Humana "
            "risk-contract corridors explicitly; "
            "commercial exposure limited."
        ),
    },
    "BCBS (state plan)": {
        "posture": "firm",
        "geography": "single state (varies)",
        "ma_exposure": "medium",
        "recent_stance": (
            "Varies dramatically by state. Dominant "
            "BCBS plans (IL, MI, NC, TX, NY) can "
            "drive > 50% mix → de facto price-setters."
        ),
        "partner_read": (
            "State concentration is critical — if "
            "BCBS is > 40% of mix, single-payer deal "
            "risk. Verify specific state plan's "
            "recent actions."
        ),
    },
    "Centene": {
        "posture": "aggressive",
        "geography": "national Medicaid + marketplace",
        "ma_exposure": "medium",
        "recent_stance": (
            "Medicaid-heavy; aggressive on rates. "
            "Regulatory exposure on state Medicaid "
            "cycle."
        ),
        "partner_read": (
            "Medicaid-concentrated deals with Centene "
            "exposure = state-Medicaid-cycle risk; "
            "price in state DSH/UPL changes."
        ),
    },
    "Molina": {
        "posture": "aggressive",
        "geography": "national Medicaid",
        "ma_exposure": "low",
        "recent_stance": (
            "Medicaid-focused; tight rates and strict "
            "utilization review."
        ),
        "partner_read": (
            "Expect aggressive prior-auth discipline; "
            "denial-rate modeling must account for "
            "Molina's process."
        ),
    },
    "Kaiser Permanente": {
        "posture": "closed",
        "geography": "CA + select regions",
        "ma_exposure": "high",
        "recent_stance": (
            "Closed system — contracts only specialists "
            "it can't cover internally."
        ),
        "partner_read": (
            "If Kaiser is > 20% of a non-CA provider's "
            "mix, something unusual is happening — "
            "investigate referral relationship."
        ),
    },
    "HCSC": {
        "posture": "firm",
        "geography": "IL / TX / NM / OK / MT BCBS",
        "ma_exposure": "medium",
        "recent_stance": (
            "BCBS operator across 5 states; TX and IL "
            "are concentration markets."
        ),
        "partner_read": (
            "TX/IL providers with HCSC > 30% are "
            "single-payer dependent; TX rate actions "
            "in 2024-2025 were material."
        ),
    },
    "Highmark": {
        "posture": "firm",
        "geography": "PA / DE / WV / NY",
        "ma_exposure": "medium",
        "recent_stance": (
            "PA-dominant BCBS; vertically integrated "
            "with Allegheny Health."
        ),
        "partner_read": (
            "PA provider deals with Highmark exposure: "
            "watch for AHN site-of-service routing "
            "pressure."
        ),
    },
    "Independence Blue Cross": {
        "posture": "neutral",
        "geography": "Philadelphia metro",
        "ma_exposure": "medium",
        "recent_stance": (
            "Philadelphia region dominant; "
            "relatively cooperative on contracting."
        ),
        "partner_read": (
            "Philly metro deals with IBC top-3: lower "
            "payer-side rate-cut risk than national "
            "payer comparable."
        ),
    },
}


@dataclass
class PayerInDealMix:
    payer_name: str
    mix_share_pct: float


@dataclass
class PayerWatchlistInputs:
    deal_mix: List[PayerInDealMix] = field(default_factory=list)


@dataclass
class PayerHit:
    payer_name: str
    in_book: bool
    mix_share_pct: float
    posture: str
    geography: str
    ma_exposure: str
    recent_stance: str
    partner_read: str


@dataclass
class PayerWatchlistReport:
    hits: List[PayerHit] = field(default_factory=list)
    aggressive_share_pct: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": [
                {"payer_name": h.payer_name,
                 "in_book": h.in_book,
                 "mix_share_pct": h.mix_share_pct,
                 "posture": h.posture,
                 "geography": h.geography,
                 "ma_exposure": h.ma_exposure,
                 "recent_stance": h.recent_stance,
                 "partner_read": h.partner_read}
                for h in self.hits
            ],
            "aggressive_share_pct":
                self.aggressive_share_pct,
            "partner_note": self.partner_note,
        }


def read_payer_watchlist(
    inputs: PayerWatchlistInputs,
) -> PayerWatchlistReport:
    if not inputs.deal_mix:
        return PayerWatchlistReport(
            partner_note=(
                "No payers in mix — provide top-5 "
                "named payer concentration."),
        )

    hits: List[PayerHit] = []
    aggressive_share = 0.0
    for p in inputs.deal_mix:
        book = PAYER_BOOK.get(p.payer_name)
        if book is None:
            hits.append(PayerHit(
                payer_name=p.payer_name,
                in_book=False,
                mix_share_pct=round(p.mix_share_pct, 4),
                posture="unknown",
                geography="unknown",
                ma_exposure="unknown",
                recent_stance=(
                    "Payer not in catalog — partner "
                    "should research specific stance."),
                partner_read=(
                    "Unknown payer; get management "
                    "to walk through the relationship "
                    "and recent rate history."),
            ))
            continue
        hits.append(PayerHit(
            payer_name=p.payer_name,
            in_book=True,
            mix_share_pct=round(p.mix_share_pct, 4),
            posture=book["posture"],
            geography=book["geography"],
            ma_exposure=book["ma_exposure"],
            recent_stance=book["recent_stance"],
            partner_read=book["partner_read"],
        ))
        if book["posture"] == "aggressive":
            aggressive_share += p.mix_share_pct

    if aggressive_share > 0.30:
        note = (
            f"Aggressive-posture payers "
            f"{aggressive_share:.0%} of mix — expect "
            "material rate pressure at renewal. Bake "
            "-2% to -4% rate drift into exit case."
        )
    elif aggressive_share > 0.15:
        note = (
            f"{aggressive_share:.0%} mix with "
            "aggressive-posture payers — modest but "
            "non-zero rate exposure. Flag for renewal "
            "calendar."
        )
    else:
        note = (
            "Low exposure to aggressive-posture "
            "payers; payer-side rate-cut risk is not "
            "the binding constraint."
        )

    return PayerWatchlistReport(
        hits=hits,
        aggressive_share_pct=round(
            aggressive_share, 4),
        partner_note=note,
    )


def render_payer_watchlist_markdown(
    r: PayerWatchlistReport,
) -> str:
    lines = [
        "# Payer watchlist by name",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Aggressive-posture share: "
        f"{r.aggressive_share_pct:.0%}",
        "",
        "| Payer | Mix | Posture | MA exp | Geography |",
        "|---|---|---|---|---|",
    ]
    for h in r.hits:
        lines.append(
            f"| {h.payer_name} | "
            f"{h.mix_share_pct:.0%} | "
            f"{h.posture} | {h.ma_exposure} | "
            f"{h.geography} |"
        )
    for h in r.hits:
        lines.append("")
        lines.append(f"### {h.payer_name}")
        lines.append(f"- Stance: {h.recent_stance}")
        lines.append(f"- Partner read: {h.partner_read}")
    return "\n".join(lines)
