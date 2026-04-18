"""Sensitivity grid — one-variable-at-a-time MOIC / IRR sweeps.

Partners want to know: "if the exit multiple comes in at 9x instead
of 11x, what's the damage?" And: "if EBITDA grows 8% not 12%, where
does MOIC land?"

This module produces a grid of MOIC + IRR outcomes across a user-
specified variable range, holding everything else at base. It's a
tornado-chart precursor: the widest MOIC swing wins.

Variables supported:

- ``entry_multiple`` — entry EV / EBITDA.
- ``exit_multiple`` — exit EV / EBITDA.
- ``ebitda_growth`` — annual EBITDA CAGR over hold.
- ``leverage_multiple`` — debt / EBITDA at entry.
- ``hold_years`` — years to exit.

Outputs: a grid of ``SensitivityPoint`` rows (value, MOIC, IRR,
delta vs base) and a ``SensitivityGrid`` with summary stats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_VARIABLES = (
    "entry_multiple",
    "exit_multiple",
    "ebitda_growth",
    "leverage_multiple",
    "hold_years",
)


@dataclass
class SensitivityBase:
    """Base-case inputs for the sensitivity model."""
    ebitda_m: float                       # LTM EBITDA at entry
    entry_multiple: float = 11.0
    exit_multiple: float = 11.0
    ebitda_growth: float = 0.10           # annual CAGR
    leverage_multiple: float = 5.5        # debt / EBITDA at entry
    hold_years: int = 5
    fees_and_trans_pct: float = 0.03      # fees drag on entry equity


@dataclass
class SensitivityPoint:
    value: float                          # the swept variable's value
    moic: float
    irr: Optional[float]
    delta_moic: float                     # vs base
    delta_irr: Optional[float]            # vs base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "moic": self.moic,
            "irr": self.irr,
            "delta_moic": self.delta_moic,
            "delta_irr": self.delta_irr,
        }


@dataclass
class SensitivityGrid:
    variable: str
    base_moic: float
    base_irr: Optional[float]
    points: List[SensitivityPoint] = field(default_factory=list)
    swing_moic: float = 0.0               # max - min across sweep
    swing_irr: Optional[float] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "base_moic": self.base_moic,
            "base_irr": self.base_irr,
            "points": [p.to_dict() for p in self.points],
            "swing_moic": self.swing_moic,
            "swing_irr": self.swing_irr,
            "partner_note": self.partner_note,
        }


def _irr_from_moic(moic: float, years: int) -> Optional[float]:
    """CAGR IRR given MOIC + hold — None if moic ≤ 0."""
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def _compute_moic(base: SensitivityBase,
                  *,
                  entry_multiple: Optional[float] = None,
                  exit_multiple: Optional[float] = None,
                  ebitda_growth: Optional[float] = None,
                  leverage_multiple: Optional[float] = None,
                  hold_years: Optional[int] = None) -> Tuple[float, int]:
    """Return (moic, hold_years) for one parameter combination."""
    em = entry_multiple if entry_multiple is not None else base.entry_multiple
    xm = exit_multiple if exit_multiple is not None else base.exit_multiple
    g = ebitda_growth if ebitda_growth is not None else base.ebitda_growth
    lev = (leverage_multiple if leverage_multiple is not None
           else base.leverage_multiple)
    h = hold_years if hold_years is not None else base.hold_years

    entry_ev = base.ebitda_m * em
    debt = base.ebitda_m * lev
    entry_equity = max(0.01, entry_ev - debt)
    entry_equity_net_fees = entry_equity * (1 + base.fees_and_trans_pct)

    exit_ebitda = base.ebitda_m * ((1 + g) ** max(1, h))
    exit_ev = exit_ebitda * xm
    # Simplified: debt stays flat (no amortization / recap).
    exit_equity = max(0.0, exit_ev - debt)
    moic = exit_equity / entry_equity_net_fees
    return moic, max(1, h)


def run_sensitivity(base: SensitivityBase, variable: str,
                    values: List[float]) -> SensitivityGrid:
    """Sweep ``variable`` across ``values``; hold other inputs at base."""
    if variable not in SUPPORTED_VARIABLES:
        raise ValueError(
            f"Unsupported variable: {variable!r}. "
            f"Supported: {SUPPORTED_VARIABLES}"
        )
    base_moic, base_h = _compute_moic(base)
    base_irr = _irr_from_moic(base_moic, base_h)

    points: List[SensitivityPoint] = []
    for v in values:
        kwargs: Dict[str, Any] = {}
        if variable == "hold_years":
            kwargs[variable] = int(v)
        else:
            kwargs[variable] = float(v)
        moic, h = _compute_moic(base, **kwargs)
        irr = _irr_from_moic(moic, h)
        d_moic = round(moic - base_moic, 4)
        d_irr = (round(irr - base_irr, 6)
                 if irr is not None and base_irr is not None else None)
        points.append(SensitivityPoint(
            value=v,
            moic=round(moic, 4),
            irr=round(irr, 6) if irr is not None else None,
            delta_moic=d_moic,
            delta_irr=d_irr,
        ))

    if points:
        swing_moic = max(p.moic for p in points) - min(p.moic for p in points)
        irrs = [p.irr for p in points if p.irr is not None]
        swing_irr = (round(max(irrs) - min(irrs), 6)
                     if len(irrs) >= 2 else None)
    else:
        swing_moic = 0.0
        swing_irr = None

    note = _compose_note(variable, base_moic, points)
    return SensitivityGrid(
        variable=variable,
        base_moic=round(base_moic, 4),
        base_irr=round(base_irr, 6) if base_irr is not None else None,
        points=points,
        swing_moic=round(swing_moic, 4),
        swing_irr=swing_irr,
        partner_note=note,
    )


def _compose_note(variable: str, base_moic: float,
                  points: List[SensitivityPoint]) -> str:
    if not points:
        return f"No sweep values provided for {variable}."
    low = min(points, key=lambda p: p.moic)
    high = max(points, key=lambda p: p.moic)
    return (
        f"{variable}: sweep spans MOIC {low.moic:.2f}x (at "
        f"{low.value}) to {high.moic:.2f}x (at {high.value}). "
        f"Base case MOIC {base_moic:.2f}x."
    )


def tornado(base: SensitivityBase,
            sweeps: Dict[str, List[float]]) -> List[SensitivityGrid]:
    """Run multiple single-variable sweeps — returns grids sorted by swing."""
    grids: List[SensitivityGrid] = []
    for var, values in sweeps.items():
        try:
            grids.append(run_sensitivity(base, var, values))
        except ValueError:
            continue
    grids.sort(key=lambda g: g.swing_moic, reverse=True)
    return grids


def render_sensitivity_markdown(grid: SensitivityGrid) -> str:
    lines = [
        f"# Sensitivity — {grid.variable}",
        "",
        f"_{grid.partner_note}_",
        "",
        f"- Base MOIC: {grid.base_moic:.2f}x",
    ]
    if grid.base_irr is not None:
        lines.append(f"- Base IRR: {grid.base_irr*100:.1f}%")
    lines.extend([
        f"- MOIC swing: {grid.swing_moic:.2f}x",
        "",
        "| Value | MOIC | IRR | Δ MOIC |",
        "|---:|---:|---:|---:|",
    ])
    for p in grid.points:
        irr_s = f"{p.irr*100:.1f}%" if p.irr is not None else "—"
        lines.append(
            f"| {p.value} | {p.moic:.2f}x | {irr_s} | "
            f"{p.delta_moic:+.2f} |"
        )
    return "\n".join(lines)


def render_tornado_markdown(grids: List[SensitivityGrid]) -> str:
    lines = ["# Tornado — variable importance", ""]
    if not grids:
        lines.append("_No grids._")
        return "\n".join(lines)
    lines.extend([
        "| Variable | MOIC swing |",
        "|---|---:|",
    ])
    for g in grids:
        lines.append(f"| {g.variable} | {g.swing_moic:.2f}x |")
    return "\n".join(lines)
