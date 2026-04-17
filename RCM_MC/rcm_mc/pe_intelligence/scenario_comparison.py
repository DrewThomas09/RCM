"""Scenario comparison — base / bull / bear side-by-side.

Produces a three-column pricing comparison: base case, bull case,
bear case. Each column has an adjusted EBITDA target, exit
multiple, and computed IRR / MOIC / equity value.

Inputs are a base case + delta sets that describe what bull /
bear mean in this context (e.g., bull = +10% EBITDA at exit,
+1 turn multiple; bear = -15% EBITDA, -1 turn multiple).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioInputs:
    deal_id: str
    base_ebitda_m: float                 # EBITDA at close (today)
    base_exit_ebitda_m: float            # modeled base-case exit EBITDA
    base_entry_multiple: float
    base_exit_multiple: float
    hold_years: float
    equity_invested_m: float
    debt_at_close_m: float = 0.0
    debt_paydown_m: float = 0.0          # total paydown over hold
    bull_ebitda_delta_pct: float = 0.15
    bull_multiple_delta: float = 1.0
    bear_ebitda_delta_pct: float = -0.20
    bear_multiple_delta: float = -1.0


@dataclass
class ScenarioOutcome:
    name: str                           # "base" | "bull" | "bear"
    exit_ebitda_m: float
    exit_multiple: float
    exit_ev_m: float
    exit_equity_m: float
    moic: float
    irr: Optional[float]
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "exit_ebitda_m": self.exit_ebitda_m,
            "exit_multiple": self.exit_multiple,
            "exit_ev_m": self.exit_ev_m,
            "exit_equity_m": self.exit_equity_m,
            "moic": self.moic,
            "irr": self.irr,
            "partner_note": self.partner_note,
        }


@dataclass
class ScenarioComparison:
    base: ScenarioOutcome
    bull: ScenarioOutcome
    bear: ScenarioOutcome
    bull_bear_spread_moic: float
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base": self.base.to_dict(),
            "bull": self.bull.to_dict(),
            "bear": self.bear.to_dict(),
            "bull_bear_spread_moic": self.bull_bear_spread_moic,
            "partner_note": self.partner_note,
        }


def _irr(moic: float, years: float) -> Optional[float]:
    if moic <= 0 or years <= 0:
        return None
    try:
        return moic ** (1.0 / years) - 1.0
    except Exception:
        return None


def _compute_outcome(
    name: str,
    inputs: ScenarioInputs,
    *,
    ebitda_delta: float,
    multiple_delta: float,
) -> ScenarioOutcome:
    exit_ebitda = inputs.base_exit_ebitda_m * (1 + ebitda_delta)
    exit_multiple = max(1.0, inputs.base_exit_multiple + multiple_delta)
    exit_ev = exit_ebitda * exit_multiple
    # Remaining debt at exit.
    remaining_debt = max(0.0, inputs.debt_at_close_m - inputs.debt_paydown_m)
    exit_equity = max(0.0, exit_ev - remaining_debt)
    moic = exit_equity / max(inputs.equity_invested_m, 1e-9)
    irr = _irr(moic, inputs.hold_years)
    if name == "base":
        note = "Base case assumes modeled ramp + market exit multiple."
    elif name == "bull":
        note = ("Bull case assumes faster EBITDA ramp + multiple expansion.")
    else:
        note = ("Bear case assumes slower ramp + multiple compression.")
    return ScenarioOutcome(
        name=name,
        exit_ebitda_m=round(exit_ebitda, 2),
        exit_multiple=round(exit_multiple, 2),
        exit_ev_m=round(exit_ev, 2),
        exit_equity_m=round(exit_equity, 2),
        moic=round(moic, 4),
        irr=round(irr, 4) if irr is not None else None,
        partner_note=note,
    )


def compare_scenarios(inputs: ScenarioInputs) -> ScenarioComparison:
    base = _compute_outcome("base", inputs, ebitda_delta=0.0,
                             multiple_delta=0.0)
    bull = _compute_outcome("bull", inputs,
                             ebitda_delta=inputs.bull_ebitda_delta_pct,
                             multiple_delta=inputs.bull_multiple_delta)
    bear = _compute_outcome("bear", inputs,
                             ebitda_delta=inputs.bear_ebitda_delta_pct,
                             multiple_delta=inputs.bear_multiple_delta)
    spread = round(bull.moic - bear.moic, 4)
    if spread > 2.0:
        note = ("Wide MOIC spread — deal is highly sensitive to execution "
                "and multiple. Tighten bear case protections.")
    elif spread > 1.0:
        note = ("Meaningful MOIC spread — typical for healthcare PE. Bull "
                "upside matters; protect the bear downside.")
    else:
        note = ("Tight MOIC spread — deal is structurally bounded; "
                "returns less sensitive to swing factors.")
    return ScenarioComparison(
        base=base, bull=bull, bear=bear,
        bull_bear_spread_moic=spread,
        partner_note=note,
    )


def render_scenario_comparison_markdown(
    comparison: ScenarioComparison,
) -> str:
    lines = [
        "# Scenario comparison",
        "",
        f"**Bull-bear MOIC spread:** {comparison.bull_bear_spread_moic:.2f}x",
        "",
        f"_{comparison.partner_note}_",
        "",
        "| Scenario | Exit EBITDA | Exit x | Exit EV | Equity | MOIC | IRR |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in (comparison.base, comparison.bull, comparison.bear):
        irr_str = f"{s.irr*100:.1f}%" if s.irr is not None else "—"
        lines.append(
            f"| {s.name} | ${s.exit_ebitda_m:,.1f}M | "
            f"{s.exit_multiple:.2f}x | ${s.exit_ev_m:,.1f}M | "
            f"${s.exit_equity_m:,.1f}M | {s.moic:.2f}x | {irr_str} |"
        )
    return "\n".join(lines)
