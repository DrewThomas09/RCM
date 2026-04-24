"""Compact peer-comparison snapshot — the shape any target-aware
page can drop in to show "your target vs public comps."

The snapshot computes:

    - Target's implied EV/EBITDA (when EV + revenue supplied,
      assuming a 12% EBITDA margin if EBITDA isn't passed)
    - Peer median, p25, p75 EV/EBITDA for the category
    - Delta in turns (positive = target priced at premium)
    - Top-3 named peer constituents (sorted by revenue proximity
      when target revenue supplied)
    - Sector sentiment + latest transaction band for the specialty
    - An ``assessment`` label: DISCOUNT / IN-LINE / PREMIUM

Consumers:
    - Deal Profile "Market Context" block (live JS-fetched)
    - Thesis Pipeline page (headline band)
    - IC Packet Market Context section (already uses the underlying
      primitives; this adds the compact delta view)

The snapshot never hits a live API — it reads the same curated
YAML content the rest of market_intel uses. A Seeking Alpha /
Bloomberg adapter can replace the data source via
:mod:`rcm_mc.market_intel.adapters` without changing this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .public_comps import (
    CategoryBand, PublicComp, category_bands, list_companies,
)
from .news_feed import sector_sentiment as _sector_sentiment
from .transaction_multiples import transaction_multiple


# Assumed EBITDA margin when only revenue is available — acute
# hospital system median.  Partner-visible in the provenance sub-line.
_ASSUMED_MARGIN: float = 0.12


@dataclass
class PeerSnapshot:
    """Compact peer-context envelope for drop-in UI usage."""
    category: str
    target_revenue_usd: Optional[float] = None
    target_ev_usd: Optional[float] = None
    target_ebitda_usd: Optional[float] = None
    target_implied_multiple: Optional[float] = None

    peer_median_ev_ebitda: Optional[float] = None
    peer_p25_ev_ebitda: Optional[float] = None
    peer_p75_ev_ebitda: Optional[float] = None
    delta_vs_median_turns: Optional[float] = None   # target - median

    peers: List[Dict[str, Any]] = field(default_factory=list)

    sector_sentiment: Optional[str] = None
    transaction_band: Optional[Dict[str, Any]] = None

    # Partner-readable verdict
    assessment: str = "NO_DATA"        # DISCOUNT / IN-LINE / PREMIUM / NO_DATA
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "target_revenue_usd": self.target_revenue_usd,
            "target_ev_usd": self.target_ev_usd,
            "target_ebitda_usd": self.target_ebitda_usd,
            "target_implied_multiple": self.target_implied_multiple,
            "peer_median_ev_ebitda": self.peer_median_ev_ebitda,
            "peer_p25_ev_ebitda": self.peer_p25_ev_ebitda,
            "peer_p75_ev_ebitda": self.peer_p75_ev_ebitda,
            "delta_vs_median_turns": self.delta_vs_median_turns,
            "peers": list(self.peers),
            "sector_sentiment": self.sector_sentiment,
            "transaction_band": self.transaction_band,
            "assessment": self.assessment,
            "summary": self.summary,
        }


def _assess(
    target_mult: Optional[float],
    p25: Optional[float], median: Optional[float], p75: Optional[float],
) -> str:
    """Map target multiple into peer bucket."""
    if target_mult is None or median is None:
        return "NO_DATA"
    if p25 is not None and target_mult < p25:
        return "DISCOUNT"
    if p75 is not None and target_mult > p75:
        return "PREMIUM"
    return "IN-LINE"


def _summary(
    category: str, target_mult: Optional[float],
    median: Optional[float], assessment: str,
    delta_turns: Optional[float],
) -> str:
    """Partner-readable one-sentence summary."""
    if assessment == "NO_DATA":
        return (
            "Insufficient data to place target against peer range — "
            "supply enterprise value, revenue, and category."
        )
    if target_mult is None or median is None:
        return ""
    turns = delta_turns or 0.0
    direction = "above" if turns > 0 else "below" if turns < 0 else "at"
    if assessment == "PREMIUM":
        return (
            f"Target implied EV/EBITDA {target_mult:.1f}x "
            f"is {abs(turns):.1f} turns {direction} the peer median "
            f"({median:.1f}x) for {category.replace('_', ' ').title()} — "
            f"entering at a premium that the thesis must justify "
            f"through operational uplift or sector rotation."
        )
    if assessment == "DISCOUNT":
        return (
            f"Target implied EV/EBITDA {target_mult:.1f}x is "
            f"{abs(turns):.1f} turns {direction} the peer median "
            f"({median:.1f}x) — discount could reflect genuine alpha "
            f"or hidden distress. Cross-reference with Deal Autopsy."
        )
    return (
        f"Target implied EV/EBITDA {target_mult:.1f}x is within peer "
        f"range (median {median:.1f}x). Valuation is defensible "
        f"without additional story."
    )


def _top_peers(
    category: str, target_revenue_usd: Optional[float],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """Return the top-N same-category peers, sorted by revenue
    proximity when target revenue is available."""
    target_cat = (category or "").upper()
    matches = [
        c for c in list_companies() if c.category == target_cat
    ]
    if not matches:
        return []
    if target_revenue_usd and target_revenue_usd > 0:
        target_bn = target_revenue_usd / 1_000_000_000
        matches.sort(
            key=lambda c: abs(c.revenue_ttm_usd_bn - target_bn),
        )
    return [
        {
            "ticker": c.ticker,
            "name": c.name,
            "revenue_ttm_usd_bn": c.revenue_ttm_usd_bn,
            "ev_ebitda_multiple": c.ev_ebitda_multiple,
            "analyst_consensus": (
                c.analyst_coverage.consensus
                if c.analyst_coverage else None
            ),
        }
        for c in matches[:top_n]
    ]


def compute_peer_snapshot(
    *,
    category: str,
    target_revenue_usd: Optional[float] = None,
    target_ev_usd: Optional[float] = None,
    target_ebitda_usd: Optional[float] = None,
    specialty: Optional[str] = None,
) -> PeerSnapshot:
    """Build a compact peer-comparison envelope for a target."""
    cat = (category or "").upper()
    if not cat:
        return PeerSnapshot(
            category="",
            summary="Supply a market category to compute peer context.",
        )

    bands = category_bands()
    band = bands.get(cat)

    # Implied multiple: prefer EV/EBITDA when both supplied, else
    # EV / (revenue × 12%).
    implied_mult: Optional[float] = None
    if target_ev_usd and target_ebitda_usd and target_ebitda_usd > 0:
        implied_mult = target_ev_usd / target_ebitda_usd
    elif target_ev_usd and target_revenue_usd and target_revenue_usd > 0:
        implied_ebitda = target_revenue_usd * _ASSUMED_MARGIN
        implied_mult = (
            target_ev_usd / implied_ebitda if implied_ebitda > 0 else None
        )

    peer_median = band.median_ev_ebitda if band else None
    peer_p25 = band.p25_ev_ebitda if band else None
    peer_p75 = band.p75_ev_ebitda if band else None
    delta = (
        implied_mult - peer_median
        if implied_mult is not None and peer_median is not None else None
    )

    assessment = _assess(implied_mult, peer_p25, peer_median, peer_p75)
    summary = _summary(cat, implied_mult, peer_median, assessment, delta)
    peers = _top_peers(cat, target_revenue_usd, top_n=3)

    # Sector sentiment
    sentiment = _sector_sentiment(specialty) if specialty else None

    # Transaction band
    tb_obj = None
    if specialty:
        tb = transaction_multiple(
            specialty=specialty, ev_usd=target_ev_usd,
        )
        if tb is not None:
            # Defensive duck-type to avoid circular import pain.
            try:
                tb_obj = tb.to_dict() if hasattr(tb, "to_dict") else dict(
                    tb
                )
            except Exception:  # noqa: BLE001
                tb_obj = None

    return PeerSnapshot(
        category=cat,
        target_revenue_usd=target_revenue_usd,
        target_ev_usd=target_ev_usd,
        target_ebitda_usd=target_ebitda_usd,
        target_implied_multiple=implied_mult,
        peer_median_ev_ebitda=peer_median,
        peer_p25_ev_ebitda=peer_p25,
        peer_p75_ev_ebitda=peer_p75,
        delta_vs_median_turns=delta,
        peers=peers,
        sector_sentiment=sentiment,
        transaction_band=tb_obj,
        assessment=assessment,
        summary=summary,
    )
