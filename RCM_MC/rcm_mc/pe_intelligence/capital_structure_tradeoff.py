"""Capital structure trade-off — debt / equity mix sweep.

For a given deal, more leverage boosts equity MOIC/IRR but raises
default risk via interest coverage erosion. This module sweeps
leverage multiples and returns:

- **Equity MOIC / IRR** at each leverage level (winner case).
- **Interest coverage** (EBITDA / annual interest) at entry.
- **Default risk score** — heuristic 0-100 based on coverage.
- **Partner recommendation** — prudent leverage level.

Healthcare PE rules of thumb (2024-2026):

- EBITDA / interest < 2.0x → high default risk (red zone).
- 2.0x-3.0x → cautious (yellow).
- ≥ 3.0x → comfortable (green).
- Absolute leverage ≥ 7.0x → regulatory scrutiny (FDIC SNC flags).

This gives partners a one-page view: "going from 5x to 6x lifts
MOIC by 0.3x but drops coverage from 3.1x to 2.4x — is it worth it?"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapStructureInputs:
    ebitda_m: float                       # LTM EBITDA
    entry_multiple: float = 11.0
    exit_multiple: float = 11.0
    ebitda_growth: float = 0.10           # annual CAGR
    hold_years: int = 5
    interest_rate: float = 0.095          # all-in rate on debt
    fees_and_trans_pct: float = 0.03


@dataclass
class CapStructurePoint:
    leverage_multiple: float
    debt_m: float
    equity_m: float
    interest_expense_m: float
    interest_coverage: float              # EBITDA / interest
    equity_moic: float
    equity_irr: Optional[float]
    default_risk_score: int               # 0-100
    status: str                           # "green" / "yellow" / "red"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leverage_multiple": self.leverage_multiple,
            "debt_m": self.debt_m,
            "equity_m": self.equity_m,
            "interest_expense_m": self.interest_expense_m,
            "interest_coverage": self.interest_coverage,
            "equity_moic": self.equity_moic,
            "equity_irr": self.equity_irr,
            "default_risk_score": self.default_risk_score,
            "status": self.status,
        }


@dataclass
class CapStructureResult:
    points: List[CapStructurePoint] = field(default_factory=list)
    recommended_leverage: float = 0.0
    recommended_moic: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "recommended_leverage": self.recommended_leverage,
            "recommended_moic": self.recommended_moic,
            "partner_note": self.partner_note,
        }


def _irr(moic: float, years: int) -> Optional[float]:
    if moic <= 0 or years <= 0:
        return None
    return moic ** (1.0 / years) - 1.0


def _default_risk(coverage: float, leverage: float) -> int:
    """Heuristic 0-100 risk score; higher is worse."""
    score = 0
    if coverage < 1.0:
        score += 80
    elif coverage < 1.5:
        score += 60
    elif coverage < 2.0:
        score += 45
    elif coverage < 3.0:
        score += 25
    elif coverage < 4.0:
        score += 10
    # Absolute leverage kicker.
    if leverage >= 7.0:
        score += 20
    elif leverage >= 6.0:
        score += 10
    return min(100, score)


def _status_from_coverage(coverage: float, leverage: float) -> str:
    if coverage < 2.0 or leverage >= 7.0:
        return "red"
    if coverage < 3.0 or leverage >= 6.0:
        return "yellow"
    return "green"


def sweep_cap_structure(inputs: CapStructureInputs,
                        leverage_range: List[float]) -> CapStructureResult:
    """Sweep leverage and return one point per level."""
    ebitda = inputs.ebitda_m
    entry_ev = ebitda * inputs.entry_multiple
    exit_ebitda = ebitda * ((1 + inputs.ebitda_growth) ** max(1, inputs.hold_years))
    exit_ev = exit_ebitda * inputs.exit_multiple

    points: List[CapStructurePoint] = []
    for lev in leverage_range:
        debt = ebitda * lev
        equity = max(0.01, entry_ev - debt)
        equity_net = equity * (1 + inputs.fees_and_trans_pct)
        interest = debt * inputs.interest_rate
        coverage = (ebitda / interest) if interest > 0 else 99.0
        exit_equity = max(0.0, exit_ev - debt)
        moic = exit_equity / equity_net
        irr = _irr(moic, inputs.hold_years)
        score = _default_risk(coverage, lev)
        status = _status_from_coverage(coverage, lev)
        points.append(CapStructurePoint(
            leverage_multiple=round(lev, 2),
            debt_m=round(debt, 2),
            equity_m=round(equity, 2),
            interest_expense_m=round(interest, 2),
            interest_coverage=round(coverage, 2),
            equity_moic=round(moic, 4),
            equity_irr=round(irr, 6) if irr is not None else None,
            default_risk_score=score,
            status=status,
        ))

    # Recommend the highest MOIC point that is still green or yellow.
    safe_points = [p for p in points if p.status != "red"]
    if safe_points:
        rec = max(safe_points, key=lambda p: p.equity_moic)
    elif points:
        # No safe point — pick the least risky.
        rec = min(points, key=lambda p: p.default_risk_score)
    else:
        rec = None

    if rec is not None:
        note = (
            f"Recommended leverage: {rec.leverage_multiple:.1f}x "
            f"(MOIC {rec.equity_moic:.2f}x, coverage "
            f"{rec.interest_coverage:.1f}x, status {rec.status}). "
            "Going higher boosts MOIC but erodes coverage."
        )
        return CapStructureResult(
            points=points,
            recommended_leverage=rec.leverage_multiple,
            recommended_moic=rec.equity_moic,
            partner_note=note,
        )
    return CapStructureResult(points=points, partner_note="No leverage points swept.")


def render_cap_structure_markdown(result: CapStructureResult) -> str:
    lines = [
        "# Capital structure trade-off",
        "",
        f"_{result.partner_note}_",
        "",
        "| Lev | Debt | Equity | Int | Cov | MOIC | IRR | Risk | Status |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for p in result.points:
        irr_s = f"{p.equity_irr*100:.1f}%" if p.equity_irr is not None else "—"
        lines.append(
            f"| {p.leverage_multiple:.1f}x | ${p.debt_m:,.0f}M | "
            f"${p.equity_m:,.0f}M | ${p.interest_expense_m:,.1f}M | "
            f"{p.interest_coverage:.1f}x | {p.equity_moic:.2f}x | "
            f"{irr_s} | {p.default_risk_score} | {p.status} |"
        )
    return "\n".join(lines)
