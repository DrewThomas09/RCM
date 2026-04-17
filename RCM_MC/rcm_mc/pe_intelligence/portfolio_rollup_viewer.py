"""Portfolio rollup viewer — fund-level aggregation across deals.

Partners and LPs want a one-page view of the fund's book. This
module rolls up per-deal metrics into fund-wide aggregates:

- **Total NAV, cost basis, unrealized vs realized.**
- **Weighted gross MOIC / IRR.**
- **Distribution bucket counts** — holds, exits, write-offs.
- **Sub-sector exposure.**
- **Vintage exposure.**
- **Deal stage distribution** — platform vs add-on.
- **Top movers** in the period (up and down).

Takes a list of per-deal snapshots and returns the aggregated
dashboard plus partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PortfolioDeal:
    name: str
    sector: str = "healthcare"
    subsector: str = "specialty_practice"
    vintage_year: int = 2022
    stage: str = "platform"               # "platform" / "add_on"
    status: str = "held"                  # "held" / "exited" / "written_off"
    cost_basis_m: float = 0.0
    current_nav_m: float = 0.0
    realized_m: float = 0.0
    current_irr: Optional[float] = None
    prior_nav_m: Optional[float] = None   # optional previous-period NAV


@dataclass
class SectorSummary:
    subsector: str
    deal_count: int
    nav_m: float
    cost_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "deal_count": self.deal_count,
            "nav_m": self.nav_m,
            "cost_m": self.cost_m,
        }


@dataclass
class TopMover:
    name: str
    delta_m: float                        # NAV change

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "delta_m": self.delta_m}


@dataclass
class PortfolioRollup:
    total_deals: int
    total_cost_m: float
    total_nav_m: float
    total_realized_m: float
    total_unrealized_m: float
    weighted_moic: float
    weighted_irr: Optional[float]
    hold_count: int
    exit_count: int
    write_off_count: int
    top_gainers: List[TopMover] = field(default_factory=list)
    top_losers: List[TopMover] = field(default_factory=list)
    by_subsector: List[SectorSummary] = field(default_factory=list)
    by_vintage: Dict[int, int] = field(default_factory=dict)
    by_stage: Dict[str, int] = field(default_factory=dict)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_deals": self.total_deals,
            "total_cost_m": self.total_cost_m,
            "total_nav_m": self.total_nav_m,
            "total_realized_m": self.total_realized_m,
            "total_unrealized_m": self.total_unrealized_m,
            "weighted_moic": self.weighted_moic,
            "weighted_irr": self.weighted_irr,
            "hold_count": self.hold_count,
            "exit_count": self.exit_count,
            "write_off_count": self.write_off_count,
            "top_gainers": [t.to_dict() for t in self.top_gainers],
            "top_losers": [t.to_dict() for t in self.top_losers],
            "by_subsector": [s.to_dict() for s in self.by_subsector],
            "by_vintage": dict(self.by_vintage),
            "by_stage": dict(self.by_stage),
            "partner_note": self.partner_note,
        }


def build_portfolio_rollup(deals: List[PortfolioDeal]) -> PortfolioRollup:
    if not deals:
        return PortfolioRollup(
            total_deals=0, total_cost_m=0.0, total_nav_m=0.0,
            total_realized_m=0.0, total_unrealized_m=0.0,
            weighted_moic=0.0, weighted_irr=None,
            hold_count=0, exit_count=0, write_off_count=0,
            partner_note="Empty book.",
        )

    total_cost = sum(d.cost_basis_m for d in deals)
    total_nav = sum(d.current_nav_m for d in deals)
    total_realized = sum(d.realized_m for d in deals)
    total_unrealized = total_nav

    value = total_realized + total_nav
    weighted_moic = (value / total_cost) if total_cost > 0 else 0.0

    # Cost-weighted IRR (skip deals with no IRR).
    irr_deals = [d for d in deals if d.current_irr is not None]
    if irr_deals:
        w = sum(d.cost_basis_m for d in irr_deals)
        weighted_irr = (sum(d.current_irr * d.cost_basis_m
                             for d in irr_deals) / w) if w > 0 else None
    else:
        weighted_irr = None

    hold_count = sum(1 for d in deals if d.status == "held")
    exit_count = sum(1 for d in deals if d.status == "exited")
    write_off_count = sum(1 for d in deals if d.status == "written_off")

    # Movers (period-over-period NAV change).
    movers = []
    for d in deals:
        if d.prior_nav_m is not None:
            delta = d.current_nav_m - d.prior_nav_m
            movers.append(TopMover(name=d.name, delta_m=round(delta, 2)))
    movers.sort(key=lambda m: m.delta_m, reverse=True)
    gainers = [m for m in movers if m.delta_m > 0][:5]
    losers = [m for m in movers if m.delta_m < 0][-5:]
    losers.sort(key=lambda m: m.delta_m)  # most-negative first

    # Sub-sector rollup.
    by_sub: Dict[str, Dict[str, float]] = {}
    for d in deals:
        agg = by_sub.setdefault(d.subsector, {"count": 0, "nav": 0.0,
                                                "cost": 0.0})
        agg["count"] += 1
        agg["nav"] += d.current_nav_m
        agg["cost"] += d.cost_basis_m
    by_subsector = [
        SectorSummary(subsector=s, deal_count=int(v["count"]),
                        nav_m=round(v["nav"], 2), cost_m=round(v["cost"], 2))
        for s, v in sorted(by_sub.items(),
                            key=lambda kv: kv[1]["nav"],
                            reverse=True)
    ]

    by_vintage: Dict[int, int] = {}
    for d in deals:
        by_vintage[d.vintage_year] = by_vintage.get(d.vintage_year, 0) + 1

    by_stage: Dict[str, int] = {}
    for d in deals:
        by_stage[d.stage] = by_stage.get(d.stage, 0) + 1

    if weighted_moic >= 2.5:
        note = (f"Book performing strongly (weighted MOIC "
                f"{weighted_moic:.2f}x). {write_off_count} write-off(s).")
    elif weighted_moic >= 1.8:
        note = (f"Book on track (weighted MOIC {weighted_moic:.2f}x). "
                f"{len(gainers)} top-5 gainers offset "
                f"{len(losers)} laggards.")
    elif weighted_moic >= 1.2:
        note = (f"Book is pedestrian (MOIC {weighted_moic:.2f}x). "
                "Need outperformance from later vintages.")
    else:
        note = (f"Book is under water (MOIC {weighted_moic:.2f}x). "
                "GP intervention required across multiple holds.")

    return PortfolioRollup(
        total_deals=len(deals),
        total_cost_m=round(total_cost, 2),
        total_nav_m=round(total_nav, 2),
        total_realized_m=round(total_realized, 2),
        total_unrealized_m=round(total_unrealized, 2),
        weighted_moic=round(weighted_moic, 4),
        weighted_irr=round(weighted_irr, 6) if weighted_irr is not None else None,
        hold_count=hold_count,
        exit_count=exit_count,
        write_off_count=write_off_count,
        top_gainers=gainers,
        top_losers=losers,
        by_subsector=by_subsector,
        by_vintage=by_vintage,
        by_stage=by_stage,
        partner_note=note,
    )


def render_rollup_markdown(r: PortfolioRollup) -> str:
    lines = [
        "# Portfolio rollup",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Deals: {r.total_deals} "
        f"({r.hold_count} held / {r.exit_count} exited / "
        f"{r.write_off_count} written off)",
        f"- Cost: ${r.total_cost_m:,.1f}M",
        f"- NAV: ${r.total_nav_m:,.1f}M",
        f"- Realized: ${r.total_realized_m:,.1f}M",
        f"- Weighted MOIC: {r.weighted_moic:.2f}x",
    ]
    if r.weighted_irr is not None:
        lines.append(f"- Weighted IRR: {r.weighted_irr*100:.1f}%")
    if r.top_gainers:
        lines.extend(["", "## Top gainers", ""])
        for m in r.top_gainers:
            lines.append(f"- {m.name}: ${m.delta_m:+,.1f}M")
    if r.top_losers:
        lines.extend(["", "## Top losers", ""])
        for m in r.top_losers:
            lines.append(f"- {m.name}: ${m.delta_m:+,.1f}M")
    if r.by_subsector:
        lines.extend(["", "## By sub-sector", "",
                       "| Sub-sector | Deals | NAV | Cost |",
                       "|---|---:|---:|---:|"])
        for s in r.by_subsector:
            lines.append(f"| {s.subsector} | {s.deal_count} | "
                         f"${s.nav_m:,.1f}M | ${s.cost_m:,.1f}M |")
    return "\n".join(lines)
