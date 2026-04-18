"""Working capital peg negotiator — the $ driver most deals under-negotiate.

At close, purchase price is adjusted dollar-for-dollar by the
delta between delivered NWC and the negotiated peg. A $5M peg
misalignment is $5M of purchase price the partner just moved.

Partners have strong views on NWC peg methodology:

- **Trailing 12-month average** — the industry standard; but
  seasonality can game this.
- **Normalized trailing 12** — strip out one-time working-capital
  movements (contract timing, tax receivables).
- **Median-of-quarterly** — when seasonality is heavy, use
  quarter-ends to smooth.

This module takes NWC history + seller's proposed peg and returns
the partner's counter-peg + rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NWCObservation:
    month: str                                # "2025-01"
    nwc_m: float


@dataclass
class WCPegContext:
    history: List[NWCObservation] = field(default_factory=list)
    seller_proposed_peg_m: float = 0.0
    has_material_one_time: bool = False
    one_time_items_m: float = 0.0             # strip out if present
    is_seasonal_business: bool = False
    days_to_close_estimated: int = 60


@dataclass
class WCPegReport:
    seller_peg_m: float
    partner_peg_m: float
    peg_delta_m: float                        # partner - seller
    methodology: str
    trailing_12m_avg: float
    normalized_trailing_12m: float
    median_of_quarterly: float
    partner_note: str
    negotiation_lever_m: float                # expected negotiation shift

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seller_peg_m": self.seller_peg_m,
            "partner_peg_m": self.partner_peg_m,
            "peg_delta_m": self.peg_delta_m,
            "methodology": self.methodology,
            "trailing_12m_avg": self.trailing_12m_avg,
            "normalized_trailing_12m":
                self.normalized_trailing_12m,
            "median_of_quarterly": self.median_of_quarterly,
            "partner_note": self.partner_note,
            "negotiation_lever_m": self.negotiation_lever_m,
        }


def _median(values: List[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def negotiate_wc_peg(ctx: WCPegContext) -> WCPegReport:
    if not ctx.history:
        return WCPegReport(
            seller_peg_m=ctx.seller_proposed_peg_m,
            partner_peg_m=ctx.seller_proposed_peg_m,
            peg_delta_m=0.0, methodology="no_history",
            trailing_12m_avg=0.0,
            normalized_trailing_12m=0.0,
            median_of_quarterly=0.0,
            partner_note="No NWC history provided.",
            negotiation_lever_m=0.0,
        )

    # Use last 12 observations if more provided.
    recent = sorted(ctx.history, key=lambda o: o.month)[-12:]
    values = [o.nwc_m for o in recent]
    t12_avg = sum(values) / len(values)
    normalized = t12_avg - (ctx.one_time_items_m / 12.0
                              if ctx.has_material_one_time else 0.0)

    # Quarter-end approximation: take every 3rd observation.
    quarter_ends = values[2::3] or values
    median_q = _median(quarter_ends)

    # Methodology selection:
    if ctx.has_material_one_time:
        partner_peg = normalized
        methodology = "normalized_trailing_12m"
    elif ctx.is_seasonal_business:
        partner_peg = median_q
        methodology = "median_of_quarterly"
    else:
        partner_peg = t12_avg
        methodology = "trailing_12m_avg"

    # Partner always pushes 2-3% more conservative (higher peg) than
    # the raw number to account for the closing-period build.
    closing_period_buffer = partner_peg * 0.02
    partner_peg += closing_period_buffer

    delta = partner_peg - ctx.seller_proposed_peg_m

    if delta > 0.10 * ctx.seller_proposed_peg_m:
        note = (f"Partner peg {partner_peg:,.2f}M vs seller's "
                f"{ctx.seller_proposed_peg_m:,.2f}M — partner is "
                f"${delta:,.2f}M higher. Seller has under-weighted "
                "normalized working capital; this is real "
                "price-paid money.")
    elif delta > 0:
        note = (f"Partner peg {partner_peg:,.2f}M vs seller's "
                f"{ctx.seller_proposed_peg_m:,.2f}M — modest "
                f"${delta:,.2f}M gap. Standard NWC-peg negotiation.")
    elif delta < -0.05 * ctx.seller_proposed_peg_m:
        note = (f"Seller's peg exceeds partner's "
                f"(${abs(delta):,.2f}M higher). Unusual — seller may "
                "be building cushion to increase adjustment at "
                "close. Verify methodology.")
    else:
        note = (f"Partner and seller pegs within a rounding band "
                f"(${delta:+,.2f}M). Not a material negotiation "
                "item.")

    return WCPegReport(
        seller_peg_m=round(ctx.seller_proposed_peg_m, 2),
        partner_peg_m=round(partner_peg, 2),
        peg_delta_m=round(delta, 2),
        methodology=methodology,
        trailing_12m_avg=round(t12_avg, 2),
        normalized_trailing_12m=round(normalized, 2),
        median_of_quarterly=round(median_q, 2),
        partner_note=note,
        negotiation_lever_m=round(abs(delta), 2),
    )


def render_wc_peg_markdown(r: WCPegReport) -> str:
    lines = [
        "# Working capital peg negotiator",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Seller proposed: ${r.seller_peg_m:,.2f}M",
        f"- Partner peg: ${r.partner_peg_m:,.2f}M",
        f"- Delta: ${r.peg_delta_m:+,.2f}M",
        f"- Methodology: {r.methodology}",
        f"- Trailing 12m avg: ${r.trailing_12m_avg:,.2f}M",
        f"- Normalized trailing: "
        f"${r.normalized_trailing_12m:,.2f}M",
        f"- Median of quarterly: "
        f"${r.median_of_quarterly:,.2f}M",
        f"- Negotiation lever: ${r.negotiation_lever_m:,.2f}M",
    ]
    return "\n".join(lines)
