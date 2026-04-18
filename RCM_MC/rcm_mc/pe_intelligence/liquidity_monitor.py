"""Liquidity monitor — cash runway + 13-week cash forecast.

When a deal gets tight, the Ops partner runs a 13-week cash. This
module tracks:

- **Cash runway** — weeks of cash given burn rate.
- **Minimum cash threshold** — below this, operating discipline breaks.
- **Covenant-driven cash floor** — lender-mandated minimum.
- **Weekly projection** — cash balance week-by-week given planned
  inflows/outflows.

Used in distressed and near-covenant situations alongside
`covenant_monitor.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CashWeek:
    week_number: int                  # 1-indexed
    opening_balance: float
    collections: float
    operating_outflows: float
    debt_service: float
    ending_balance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_number": self.week_number,
            "opening_balance": self.opening_balance,
            "collections": self.collections,
            "operating_outflows": self.operating_outflows,
            "debt_service": self.debt_service,
            "ending_balance": self.ending_balance,
        }


@dataclass
class LiquidityReport:
    current_cash: float
    weeks: List[CashWeek] = field(default_factory=list)
    weeks_of_runway: Optional[float] = None
    minimum_cash: float = 0.0
    covenant_floor: float = 0.0
    breach_week: Optional[int] = None        # first week cash < floor
    status: str = "green"                    # green / amber / red
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_cash": self.current_cash,
            "weeks": [w.to_dict() for w in self.weeks],
            "weeks_of_runway": self.weeks_of_runway,
            "minimum_cash": self.minimum_cash,
            "covenant_floor": self.covenant_floor,
            "breach_week": self.breach_week,
            "status": self.status,
            "partner_note": self.partner_note,
        }


def project_cash_runway(
    *,
    current_cash: float,
    weekly_collections: float,
    weekly_operating_outflows: float,
    weekly_debt_service: float = 0.0,
    weeks_to_project: int = 13,
    minimum_cash: float = 0.0,
    covenant_floor: float = 0.0,
) -> LiquidityReport:
    """Project 13 weeks (default) of cash given flat weekly values.

    Callers with detail should instead call :func:`project_cash_detail`
    with a list of (collections, outflows, debt_service) per week.
    """
    weekly_detail = [
        (weekly_collections, weekly_operating_outflows, weekly_debt_service)
        for _ in range(weeks_to_project)
    ]
    return project_cash_detail(
        current_cash=current_cash,
        weekly_detail=weekly_detail,
        minimum_cash=minimum_cash,
        covenant_floor=covenant_floor,
    )


def project_cash_detail(
    *,
    current_cash: float,
    weekly_detail: List[tuple],           # [(collections, outflows, debt_service), ...]
    minimum_cash: float = 0.0,
    covenant_floor: float = 0.0,
) -> LiquidityReport:
    weeks: List[CashWeek] = []
    cash = float(current_cash)
    breach_week: Optional[int] = None
    burn_rates: List[float] = []
    for i, (coll, out, dsv) in enumerate(weekly_detail, start=1):
        opening = cash
        cash = cash + float(coll) - float(out) - float(dsv)
        weeks.append(CashWeek(
            week_number=i,
            opening_balance=round(opening, 2),
            collections=float(coll),
            operating_outflows=float(out),
            debt_service=float(dsv),
            ending_balance=round(cash, 2),
        ))
        # Track weekly burn (outflow - collection) for runway calc.
        burn_rates.append(float(out) + float(dsv) - float(coll))
        if breach_week is None and cash < covenant_floor:
            breach_week = i

    # Runway: how many weeks until cash hits minimum_cash at average burn.
    runway: Optional[float] = None
    if burn_rates:
        avg_burn = sum(burn_rates) / len(burn_rates)
        if avg_burn > 0:
            runway = max(0.0, (current_cash - minimum_cash) / avg_burn)
        else:
            # Net positive cash flow, infinite runway.
            runway = float("inf")

    # Status
    floor = max(minimum_cash, covenant_floor)
    if breach_week is not None:
        status = "red"
        note = (f"Cash breaches floor in week {breach_week}. "
                "Line up a liquidity intervention now.")
    elif runway is not None and runway != float("inf") and runway < 26:
        status = "amber"
        note = (f"Runway ~{runway:.0f} weeks — tight. Tighten collections "
                "cadence and defer non-essential outflows.")
    else:
        status = "green"
        note = "Liquidity comfortable — no near-term intervention required."

    return LiquidityReport(
        current_cash=round(float(current_cash), 2),
        weeks=weeks,
        weeks_of_runway=(None if runway is None
                         else (round(runway, 2)
                               if runway != float("inf") else None)),
        minimum_cash=float(minimum_cash),
        covenant_floor=float(covenant_floor),
        breach_week=breach_week,
        status=status,
        partner_note=note,
    )


def render_liquidity_markdown(report: LiquidityReport) -> str:
    lines = [
        "# Liquidity monitor",
        "",
        f"**Status:** {report.status.upper()}  ",
        f"**Current cash:** ${report.current_cash:,.0f}  ",
        f"**Minimum cash:** ${report.minimum_cash:,.0f}  ",
        f"**Covenant floor:** ${report.covenant_floor:,.0f}  ",
        f"**Weeks of runway:** {report.weeks_of_runway or '∞'}",
        "",
        f"_{report.partner_note}_",
        "",
        "| Week | Opening | Collections | Operating | Debt service | Ending |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for w in report.weeks:
        lines.append(
            f"| {w.week_number} | ${w.opening_balance:,.0f} | "
            f"${w.collections:,.0f} | ${w.operating_outflows:,.0f} | "
            f"${w.debt_service:,.0f} | ${w.ending_balance:,.0f} |"
        )
    if report.breach_week is not None:
        lines.extend([
            "",
            f"**Breach week:** {report.breach_week} — cash falls below covenant floor.",
        ])
    return "\n".join(lines)
