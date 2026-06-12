"""Pricing-power analysis — elasticity-based price-move modeling for CDD.

The CDD survey's remaining pricing gap: VoC gives willingness-to-pay
*bands* (stated tolerance), but nothing modeled what a price move does
to volume, revenue, and EBITDA — the question a pricing thesis lives
or dies on. This module runs a constant-elasticity demand model per
customer segment: volume response = (1 + Δp)^ε, revenue and
contribution flow through segment economics, and the EBITDA-optimal
price move is found by grid search over a realistic ±15% window.

Segments are curated and deterministic (the page flags illustrative);
the schema — segment, revenue, contribution margin, elasticity,
churn-floor — matches what a pricing study or transaction-data
analysis produces, so real estimates drop in without code changes.

Elasticity convention: ε < 0 (a +5% price move with ε = -0.8 loses
~3.9% of volume). |ε| < 1 is inelastic — price raises revenue; the
contribution margin then decides whether EBITDA follows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# Price-move grid: ±15% in 0.5% steps. Beyond ±15% the constant-
# elasticity assumption (and any payer contract) stops being credible.
_GRID = [round(-15 + 0.5 * i, 1) for i in range(61)]


@dataclass
class SegmentPricing:
    segment: str
    revenue_usd: float
    contribution_margin_pct: float   # variable margin on marginal volume
    elasticity: float                # < 0; demand response to price
    note: str
    price_locked: bool = False       # administered/capitated — no lever


@dataclass
class PricePoint:
    price_change_pct: float
    volume_change_pct: float
    revenue_change_usd: float
    ebitda_change_usd: float


@dataclass
class SegmentCurve:
    segment: str
    elasticity: float
    price_locked: bool
    optimal_price_change_pct: float
    optimal_ebitda_gain_usd: float
    revenue_at_optimal_usd: float
    curve: List[PricePoint]
    note: str


@dataclass
class PricingPowerResult:
    sector: str
    total_revenue_usd: float
    blended_elasticity: float
    segments: List[SegmentCurve]
    portfolio_optimal_ebitda_gain_usd: float
    headline: str


_BOOKS: Dict[str, List[SegmentPricing]] = {
    "Physician Services": [
        SegmentPricing("Commercial — out-of-network / direct", 9_000_000,
                       62.0, -1.4,
                       "Price-shoppable; reference-priced employers cap it"),
        SegmentPricing("Commercial — in-network contracted", 26_000_000,
                       58.0, -0.4,
                       "Renegotiation-cycle pricing; volume sticky in-cycle"),
        SegmentPricing("Self-pay / elective lines", 7_000_000,
                       70.0, -1.8,
                       "True consumer demand — most elastic book segment"),
        SegmentPricing("Value-based / capitated", 12_000_000,
                       45.0, -0.1,
                       "PMPM-locked for the contract term — no in-term lever",
                       price_locked=True),
    ],
    "HCIT / SaaS": [
        SegmentPricing("Enterprise (multi-year contracts)", 22_000_000,
                       80.0, -0.3,
                       "Switching costs dominate; renewal uplifts stick"),
        SegmentPricing("Mid-market (annual renewals)", 14_000_000,
                       75.0, -0.9,
                       "Benchmarked against entrants at renewal"),
        SegmentPricing("SMB / self-serve", 5_000_000,
                       68.0, -1.6,
                       "List-price sensitive; churns on increases"),
    ],
    "Home Health": [
        SegmentPricing("Commercial / private-duty", 8_000_000,
                       40.0, -1.1,
                       "Families comparison-shop hourly rates"),
        SegmentPricing("MA plan contracted episodes", 14_000_000,
                       32.0, -0.5,
                       "Plan-negotiated; volume steered by network status"),
        SegmentPricing("Traditional Medicare episodes", 18_000_000,
                       35.0, 0.0,
                       "CMS-administered pricing — no price lever at all",
                       price_locked=True),
    ],
}

SECTORS = list(_BOOKS)


def _curve(seg: SegmentPricing) -> SegmentCurve:
    if seg.price_locked:
        # Administered or in-term capitated pricing: the curve is a
        # single point at zero — modeling a move would be fiction.
        return SegmentCurve(
            segment=seg.segment, elasticity=seg.elasticity,
            price_locked=True, optimal_price_change_pct=0.0,
            optimal_ebitda_gain_usd=0.0,
            revenue_at_optimal_usd=seg.revenue_usd,
            curve=[PricePoint(0.0, 0.0, 0.0, 0.0)], note=seg.note,
        )
    pts: List[PricePoint] = []
    best = PricePoint(0.0, 0.0, 0.0, 0.0)
    base_contrib = seg.revenue_usd * seg.contribution_margin_pct / 100.0
    for dp in _GRID:
        p = dp / 100.0
        vol = (1 + p) ** seg.elasticity - 1 if seg.elasticity != 0 else 0.0
        new_rev = seg.revenue_usd * (1 + p) * (1 + vol)
        d_rev = new_rev - seg.revenue_usd
        # Contribution scales with volume; the price component of the
        # revenue change is pure margin (no marginal cost on price).
        new_contrib = (base_contrib * (1 + vol)
                       + seg.revenue_usd * (1 + vol) * p)
        d_ebitda = new_contrib - base_contrib
        pt = PricePoint(dp, round(vol * 100, 1), round(d_rev, 2),
                        round(d_ebitda, 2))
        pts.append(pt)
        if pt.ebitda_change_usd > best.ebitda_change_usd:
            best = pt
    return SegmentCurve(
        segment=seg.segment, elasticity=seg.elasticity,
        price_locked=False,
        optimal_price_change_pct=best.price_change_pct,
        optimal_ebitda_gain_usd=best.ebitda_change_usd,
        revenue_at_optimal_usd=round(
            seg.revenue_usd + best.revenue_change_usd, 2),
        curve=pts, note=seg.note,
    )


def compute_pricing_power(sector: str = "Physician Services") -> PricingPowerResult:
    book = _BOOKS.get(sector) or _BOOKS[SECTORS[0]]
    if sector not in _BOOKS:
        sector = SECTORS[0]

    total_rev = sum(s.revenue_usd for s in book)
    blended = sum(s.elasticity * s.revenue_usd for s in book) / total_rev
    curves = [_curve(s) for s in book]
    portfolio_gain = sum(c.optimal_ebitda_gain_usd for c in curves)

    movable = [c for c in curves if c.optimal_price_change_pct > 0]
    locked = [c for c in curves if c.price_locked]
    headline = (
        f"Segment-optimal price moves add "
        f"${portfolio_gain / 1e6:,.2f}M EBITDA: "
        f"{len(movable)} of {len(curves)} segments take a price increase"
        + (f"; {len(locked)} segment(s) are rate-locked "
           f"(administered / capitated) with no lever" if locked else "")
        + f". Blended elasticity {blended:.2f}."
    )
    return PricingPowerResult(
        sector=sector, total_revenue_usd=total_rev,
        blended_elasticity=round(blended, 2),
        segments=curves,
        portfolio_optimal_ebitda_gain_usd=round(portfolio_gain, 2),
        headline=headline,
    )
