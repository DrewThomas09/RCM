"""IRR decay curve — when does extending the hold stop paying?

Partner reflex when someone suggests extending the hold: "OK, but
does IRR still clear my hurdle next year?" MOIC at the higher
EBITDA may be bigger, but the longer-year divisor crushes IRR.

This module takes projected EBITDA by year, a static exit multiple
assumption, and entry terms and returns per-year exit MOIC / IRR
plus the year at which IRR crosses a specified hurdle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IRRDecayInputs:
    ebitda_by_year_m: List[float]         # y1, y2, ...
    exit_multiple: float = 11.0
    entry_equity_net_fees_m: float = 0.0
    debt_m: float = 0.0
    hurdle_irr: float = 0.20


@dataclass
class IRRYearPoint:
    year: int
    exit_ev_m: float
    exit_equity_m: float
    moic: float
    irr: Optional[float]
    clears_hurdle: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "exit_ev_m": self.exit_ev_m,
            "exit_equity_m": self.exit_equity_m,
            "moic": self.moic,
            "irr": self.irr,
            "clears_hurdle": self.clears_hurdle,
        }


@dataclass
class IRRDecayReport:
    points: List[IRRYearPoint] = field(default_factory=list)
    irr_peak_year: int = 0
    irr_peak_value: float = 0.0
    moic_peak_year: int = 0
    moic_peak_value: float = 0.0
    last_year_above_hurdle: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "irr_peak_year": self.irr_peak_year,
            "irr_peak_value": self.irr_peak_value,
            "moic_peak_year": self.moic_peak_year,
            "moic_peak_value": self.moic_peak_value,
            "last_year_above_hurdle": self.last_year_above_hurdle,
            "partner_note": self.partner_note,
        }


def _irr(moic: float, years: int) -> Optional[float]:
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def trace_irr_decay(inputs: IRRDecayInputs) -> IRRDecayReport:
    points: List[IRRYearPoint] = []
    entry_equity = max(0.01, inputs.entry_equity_net_fees_m)
    for i, ebitda in enumerate(inputs.ebitda_by_year_m):
        year = i + 1
        exit_ev = ebitda * inputs.exit_multiple
        exit_equity = max(0.0, exit_ev - inputs.debt_m)
        moic = exit_equity / entry_equity
        irr = _irr(moic, year)
        clears = (irr is not None and irr >= inputs.hurdle_irr)
        points.append(IRRYearPoint(
            year=year,
            exit_ev_m=round(exit_ev, 2),
            exit_equity_m=round(exit_equity, 2),
            moic=round(moic, 4),
            irr=round(irr, 6) if irr is not None else None,
            clears_hurdle=clears,
        ))

    with_irr = [p for p in points if p.irr is not None]
    if with_irr:
        irr_peak = max(with_irr, key=lambda p: p.irr)
        moic_peak = max(points, key=lambda p: p.moic)
        above = [p for p in points if p.clears_hurdle]
        last_above = above[-1].year if above else 0
    else:
        irr_peak = IRRYearPoint(0, 0.0, 0.0, 0.0, 0.0, False)
        moic_peak = IRRYearPoint(0, 0.0, 0.0, 0.0, 0.0, False)
        last_above = 0

    if last_above == 0:
        note = (f"IRR never clears {inputs.hurdle_irr*100:.0f}% hurdle "
                "under this trajectory. Thesis needs multiple "
                "expansion or better EBITDA growth, not longer hold.")
    elif last_above == len(points):
        note = (f"IRR clears hurdle through year {last_above} — the "
                "trajectory supports extending if needed. MOIC peak "
                f"at year {moic_peak.year}.")
    else:
        note = (f"IRR clears hurdle through year {last_above}. "
                "Extending past that destroys IRR even if MOIC "
                f"continues growing to year {moic_peak.year}. Exit "
                f"at year {last_above} unless DPI timing dictates "
                "earlier.")

    return IRRDecayReport(
        points=points,
        irr_peak_year=irr_peak.year,
        irr_peak_value=round(irr_peak.irr, 6)
            if irr_peak.irr is not None else 0.0,
        moic_peak_year=moic_peak.year,
        moic_peak_value=moic_peak.moic,
        last_year_above_hurdle=last_above,
        partner_note=note,
    )


def render_decay_markdown(r: IRRDecayReport) -> str:
    lines = [
        "# IRR decay curve",
        "",
        f"_{r.partner_note}_",
        "",
        f"- IRR peak year: {r.irr_peak_year} "
        f"({r.irr_peak_value*100:.1f}%)",
        f"- MOIC peak year: {r.moic_peak_year} "
        f"({r.moic_peak_value:.2f}x)",
        f"- Last year above hurdle: {r.last_year_above_hurdle}",
        "",
        "| Year | Exit EV | Exit Equity | MOIC | IRR | Clears |",
        "|---:|---:|---:|---:|---:|:-:|",
    ]
    for p in r.points:
        irr_s = f"{p.irr*100:.1f}%" if p.irr is not None else "—"
        mark = "✓" if p.clears_hurdle else "✗"
        lines.append(
            f"| {p.year} | ${p.exit_ev_m:,.0f}M | "
            f"${p.exit_equity_m:,.0f}M | {p.moic:.2f}x | "
            f"{irr_s} | {mark} |"
        )
    return "\n".join(lines)
