"""Hold period optimizer — how long should we hold this deal?

Most healthcare-PE funds target a 5-year hold, but optimal hold
varies by deal:

- **EBITDA growth plateau** — if growth is decelerating, exit sooner.
- **Exit window timing** — strategic buyer M&A wave / rate cycle.
- **Covenant expiration** — refi windows.
- **IRR vs MOIC trade-off** — another year may boost MOIC but dilute
  IRR.

This module takes a base case EBITDA trajectory + exit multiples
by year and returns the IRR-maximizing hold year, the
MOIC-maximizing hold year, and a partner note on trade-offs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HoldInputs:
    ebitda_by_year_m: List[float]         # ebitda[0] = year 1, etc.
    entry_ev_m: float                     # entry enterprise value
    entry_debt_m: float                   # constant debt (simplified)
    exit_multiples_by_year: List[float]   # exit multiple each year
    entry_equity_m: float                 # partner's equity at entry
    fees_pct: float = 0.03


@dataclass
class HoldYearOutcome:
    year: int
    exit_ev_m: float
    exit_equity_m: float
    moic: float
    irr: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year, "exit_ev_m": self.exit_ev_m,
            "exit_equity_m": self.exit_equity_m, "moic": self.moic,
            "irr": self.irr,
        }


@dataclass
class HoldOptimizerResult:
    outcomes: List[HoldYearOutcome] = field(default_factory=list)
    max_irr_year: int = 0
    max_moic_year: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcomes": [o.to_dict() for o in self.outcomes],
            "max_irr_year": self.max_irr_year,
            "max_moic_year": self.max_moic_year,
            "partner_note": self.partner_note,
        }


def _irr(moic: float, years: int) -> Optional[float]:
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def optimize_hold(inputs: HoldInputs) -> HoldOptimizerResult:
    if not inputs.ebitda_by_year_m or not inputs.exit_multiples_by_year:
        return HoldOptimizerResult(partner_note="Insufficient inputs.")
    horizon = min(len(inputs.ebitda_by_year_m),
                   len(inputs.exit_multiples_by_year))
    entry_equity_net = inputs.entry_equity_m * (1 + inputs.fees_pct)
    outcomes: List[HoldYearOutcome] = []
    for i in range(horizon):
        y = i + 1
        exit_ev = inputs.ebitda_by_year_m[i] * inputs.exit_multiples_by_year[i]
        exit_equity = max(0.0, exit_ev - inputs.entry_debt_m)
        moic = exit_equity / max(0.01, entry_equity_net)
        irr = _irr(moic, y)
        outcomes.append(HoldYearOutcome(
            year=y, exit_ev_m=round(exit_ev, 2),
            exit_equity_m=round(exit_equity, 2),
            moic=round(moic, 4),
            irr=round(irr, 6) if irr is not None else None,
        ))

    max_moic_year = max(outcomes, key=lambda o: o.moic).year
    with_irr = [o for o in outcomes if o.irr is not None]
    max_irr_year = max(with_irr, key=lambda o: o.irr).year if with_irr else 0

    if max_irr_year < max_moic_year:
        irr_pt = next(o for o in outcomes if o.year == max_irr_year)
        moic_pt = next(o for o in outcomes if o.year == max_moic_year)
        note = (f"IRR peaks in year {max_irr_year} at "
                f"{irr_pt.irr*100:.1f}% (MOIC {irr_pt.moic:.2f}x). "
                f"MOIC peaks year {max_moic_year} at "
                f"{moic_pt.moic:.2f}x. Classic tension — exit at "
                f"year {max_irr_year} if IRR is the LP scoring metric; "
                f"hold to {max_moic_year} if MOIC narrative matters.")
    elif max_irr_year == max_moic_year:
        pt = next(o for o in outcomes if o.year == max_irr_year)
        note = (f"Both IRR and MOIC peak in year {max_irr_year} "
                f"(MOIC {pt.moic:.2f}x, "
                f"IRR {pt.irr*100 if pt.irr else 0:.1f}%). "
                "No ambiguity on hold year.")
    else:
        note = (f"MOIC peaks year {max_moic_year}, IRR year "
                f"{max_irr_year} — unusual shape, review exit multiple "
                "curve assumptions.")

    return HoldOptimizerResult(
        outcomes=outcomes,
        max_irr_year=max_irr_year,
        max_moic_year=max_moic_year,
        partner_note=note,
    )


def render_hold_markdown(r: HoldOptimizerResult) -> str:
    lines = [
        "# Hold period optimizer",
        "",
        f"_{r.partner_note}_",
        "",
        f"- IRR-max year: {r.max_irr_year}",
        f"- MOIC-max year: {r.max_moic_year}",
        "",
        "| Year | Exit EV | Equity | MOIC | IRR |",
        "|---:|---:|---:|---:|---:|",
    ]
    for o in r.outcomes:
        irr_s = f"{o.irr*100:.1f}%" if o.irr is not None else "—"
        lines.append(
            f"| {o.year} | ${o.exit_ev_m:,.0f}M | "
            f"${o.exit_equity_m:,.0f}M | {o.moic:.2f}x | {irr_s} |"
        )
    return "\n".join(lines)
