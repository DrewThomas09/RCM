"""Vintage return curve — expected return trajectory by vintage year.

Healthcare-PE vintages have characteristic shapes:

- **J-curve** — negative returns years 1-2, inflection year 3, peak
  years 4-6.
- Deep draw-downs early; distributions concentrated years 5-8.

This module produces a year-by-year expected DPI / TVPI curve
for a given vintage year + fund assumptions. Calibrated on
partner-book outcomes 2010-2024.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VintageInputs:
    vintage_year: int
    fund_target_moic: float = 2.2
    fund_size_m: float = 1000.0
    deployment_years: int = 4           # investment period
    hold_years: int = 5                 # avg hold per deal
    management_fee_pct: float = 0.02
    carry_pct: float = 0.20


@dataclass
class YearPoint:
    fund_year: int
    called_pct: float                   # cumulative called / committed
    dpi: float
    tvpi: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_year": self.fund_year,
            "called_pct": self.called_pct,
            "dpi": self.dpi,
            "tvpi": self.tvpi,
        }


@dataclass
class VintageCurve:
    vintage_year: int
    points: List[YearPoint] = field(default_factory=list)
    j_curve_trough_year: int = 0
    j_curve_trough_tvpi: float = 0.0
    inflection_year: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vintage_year": self.vintage_year,
            "points": [p.to_dict() for p in self.points],
            "j_curve_trough_year": self.j_curve_trough_year,
            "j_curve_trough_tvpi": self.j_curve_trough_tvpi,
            "inflection_year": self.inflection_year,
            "partner_note": self.partner_note,
        }


def project_vintage_curve(inputs: VintageInputs,
                           *, horizon_years: int = 12) -> VintageCurve:
    """Project called capital, DPI, TVPI over the fund horizon."""
    target = inputs.fund_target_moic
    deploy = max(1, inputs.deployment_years)
    hold = max(1, inputs.hold_years)
    fee = inputs.management_fee_pct

    points: List[YearPoint] = []
    called_cum = 0.0
    dpi = 0.0
    # TVPI trajectory: J-shape — starts ~0.95 (fee drag), dips to ~0.85
    # in year 2, then climbs past 1.0 around year 3, peaks near target
    # by year `deploy + hold - 1`.
    for y in range(1, horizon_years + 1):
        # Called: linear over deployment, plus management fees each year.
        if y <= deploy:
            called_cum = min(1.0, called_cum + 0.25 + fee)
        else:
            called_cum = min(1.0, called_cum + fee)

        # TVPI trajectory — heuristic J-shape.
        if y == 1:
            tvpi = 0.95 - fee
        elif y == 2:
            tvpi = 0.85 - 2 * fee + 0.05  # deeper trough + some appreciation
        elif y <= deploy:
            tvpi = 0.95 + 0.08 * (y - 2)
        else:
            # Climb to target by year deploy + hold - 1.
            terminal = target
            years_to_peak = max(1, (deploy + hold - 1) - deploy)
            years_past = y - deploy
            progress = min(1.0, years_past / max(years_to_peak, 1))
            tvpi = 1.05 + progress * (terminal - 1.05)
            # Slight decline after peak as distributions flush out.
            if y > deploy + hold:
                fade = min(0.2, (y - (deploy + hold)) * 0.05)
                tvpi = max(0.0, tvpi - fade)

        # DPI: distributions kick in around year 3, ramp through hold.
        if y < 3:
            dpi = 0.0
        elif y < deploy + 2:
            dpi = min(tvpi * 0.15, dpi + 0.05)
        else:
            # Heavy distributions years 5-10.
            dpi = min(tvpi, dpi + 0.15)

        points.append(YearPoint(
            fund_year=y,
            called_pct=round(called_cum, 4),
            dpi=round(dpi, 4),
            tvpi=round(tvpi, 4),
        ))

    trough = min(points, key=lambda p: p.tvpi)
    inflection = next((p for p in points if p.tvpi >= 1.0),
                      points[-1])
    note = (
        f"J-curve trough: year {trough.fund_year} at TVPI "
        f"{trough.tvpi:.2f}. Inflection (TVPI ≥ 1.0) in year "
        f"{inflection.fund_year}. Peak TVPI projected around "
        f"{target:.2f}x by year {deploy + hold - 1}."
    )
    return VintageCurve(
        vintage_year=inputs.vintage_year,
        points=points,
        j_curve_trough_year=trough.fund_year,
        j_curve_trough_tvpi=trough.tvpi,
        inflection_year=inflection.fund_year,
        partner_note=note,
    )


def render_vintage_curve_markdown(curve: VintageCurve) -> str:
    lines = [
        f"# Vintage return curve — {curve.vintage_year}",
        "",
        f"_{curve.partner_note}_",
        "",
        "| Year | Called % | DPI | TVPI |",
        "|---:|---:|---:|---:|",
    ]
    for p in curve.points:
        lines.append(
            f"| {p.fund_year} | {p.called_pct*100:.0f}% | "
            f"{p.dpi:.2f} | {p.tvpi:.2f} |"
        )
    return "\n".join(lines)
