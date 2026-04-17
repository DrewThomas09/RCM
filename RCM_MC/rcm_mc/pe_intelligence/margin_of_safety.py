"""Margin-of-safety analyzer — how wrong can we be and still win?

Partners ask this first, not last. "If I'm 20% wrong on EBITDA
growth, do I still clear my hurdle? What if I'm 20% wrong on exit
multiple? What if I'm wrong on BOTH at once?"

This module takes a base case (EBITDA, entry multiple, exit
multiple, growth, hold, leverage) and the partner's hurdle rate
and computes **breakeven deltas** on each lever — how far each
can move before MOIC falls below the hurdle.

A partner reads the output as: "we have 25% headroom on growth
but only 8% on exit multiple. Where is the pressure point?"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SafetyInputs:
    ebitda_m: float
    entry_multiple: float = 11.0
    exit_multiple: float = 11.0
    ebitda_growth: float = 0.10
    leverage_multiple: float = 5.5
    hold_years: int = 5
    fees_and_trans_pct: float = 0.03
    hurdle_moic: float = 2.0              # partner's breakeven MOIC


@dataclass
class LeverSafety:
    lever: str
    base_value: float
    breakeven_value: float                # value at which MOIC = hurdle
    breakeven_delta_pct: float            # % change from base to breakeven
    safety_grade: str                     # "thin" / "moderate" / "ample"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever": self.lever,
            "base_value": self.base_value,
            "breakeven_value": self.breakeven_value,
            "breakeven_delta_pct": self.breakeven_delta_pct,
            "safety_grade": self.safety_grade,
        }


@dataclass
class SafetyReport:
    base_moic: float
    base_irr: Optional[float]
    hurdle_moic: float
    levers: List[LeverSafety] = field(default_factory=list)
    combined_shock_moic: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_moic": self.base_moic,
            "base_irr": self.base_irr,
            "hurdle_moic": self.hurdle_moic,
            "levers": [l.to_dict() for l in self.levers],
            "combined_shock_moic": self.combined_shock_moic,
            "partner_note": self.partner_note,
        }


def _moic(inputs: SafetyInputs, **overrides) -> float:
    ebitda = overrides.get("ebitda_m", inputs.ebitda_m)
    em = overrides.get("entry_multiple", inputs.entry_multiple)
    xm = overrides.get("exit_multiple", inputs.exit_multiple)
    g = overrides.get("ebitda_growth", inputs.ebitda_growth)
    lev = overrides.get("leverage_multiple", inputs.leverage_multiple)
    h = overrides.get("hold_years", inputs.hold_years)

    entry_ev = ebitda * em
    debt = ebitda * lev
    entry_equity = max(0.01, entry_ev - debt)
    entry_equity_net = entry_equity * (1 + inputs.fees_and_trans_pct)
    exit_ebitda = ebitda * ((1 + g) ** max(1, h))
    exit_ev = exit_ebitda * xm
    exit_equity = max(0.0, exit_ev - debt)
    return exit_equity / entry_equity_net


def _find_breakeven(
    inputs: SafetyInputs,
    lever: str,
    lower: float,
    upper: float,
) -> Tuple[float, float]:
    """Binary search for value where MOIC == hurdle. Returns (val, delta_pct)."""
    base = getattr(inputs, lever)
    hurdle = inputs.hurdle_moic

    # Determine direction (does MOIC rise or fall with lever)?
    base_moic = _moic(inputs)
    hi_val = upper if upper != base else base + abs(base) * 0.5 + 0.001
    hi_moic = _moic(inputs, **{lever: hi_val})
    direction_up = hi_moic > base_moic

    # Search lower-direction if MOIC rises with lever, upper if falls.
    if base_moic <= hurdle:
        return (base, 0.0)

    # Binary search — pick bracket based on which direction hurts.
    if direction_up:
        # MOIC rises with lever; breakeven is below base.
        lo, hi = lower, base
    else:
        # MOIC falls as lever rises; breakeven is above base.
        lo, hi = base, upper
    for _ in range(60):
        mid = (lo + hi) / 2.0
        moic = _moic(inputs, **{lever: mid})
        if direction_up:
            if moic < hurdle:
                lo = mid
            else:
                hi = mid
        else:
            if moic < hurdle:
                hi = mid
            else:
                lo = mid
        if abs(moic - hurdle) < 0.001:
            break
    breakeven = (lo + hi) / 2.0
    delta_pct = (breakeven - base) / max(abs(base), 0.001)
    return (breakeven, delta_pct)


def _grade(delta_pct: float, direction_harmful_sign: int) -> str:
    """Grade safety headroom.

    direction_harmful_sign:
      -1 if reducing lever hurts (so we want breakeven_delta < 0; harmful direction is negative)
      +1 if increasing lever hurts
    """
    harmful_distance = abs(delta_pct) if (
        (delta_pct < 0 and direction_harmful_sign < 0)
        or (delta_pct > 0 and direction_harmful_sign > 0)
    ) else 0.0
    # harmful_distance = % move required in the harmful direction to break even.
    if harmful_distance < 0.10:
        return "thin"
    if harmful_distance < 0.25:
        return "moderate"
    return "ample"


def analyze_safety(inputs: SafetyInputs) -> SafetyReport:
    base_moic = _moic(inputs)
    base_irr = (base_moic ** (1.0 / inputs.hold_years) - 1.0
                if base_moic > 0 and inputs.hold_years > 0 else None)
    levers: List[LeverSafety] = []

    # EBITDA growth — harmful direction is down.
    g_break, g_delta = _find_breakeven(
        inputs, "ebitda_growth", lower=-0.50, upper=0.50,
    )
    levers.append(LeverSafety(
        lever="ebitda_growth",
        base_value=inputs.ebitda_growth,
        breakeven_value=round(g_break, 4),
        breakeven_delta_pct=round(g_delta, 4),
        safety_grade=_grade(g_delta, -1),
    ))

    # Exit multiple — harmful direction is down.
    xm_break, xm_delta = _find_breakeven(
        inputs, "exit_multiple", lower=3.0, upper=25.0,
    )
    levers.append(LeverSafety(
        lever="exit_multiple",
        base_value=inputs.exit_multiple,
        breakeven_value=round(xm_break, 4),
        breakeven_delta_pct=round(xm_delta, 4),
        safety_grade=_grade(xm_delta, -1),
    ))

    # Entry multiple — harmful direction is up (more expensive entry).
    em_break, em_delta = _find_breakeven(
        inputs, "entry_multiple", lower=3.0, upper=25.0,
    )
    levers.append(LeverSafety(
        lever="entry_multiple",
        base_value=inputs.entry_multiple,
        breakeven_value=round(em_break, 4),
        breakeven_delta_pct=round(em_delta, 4),
        safety_grade=_grade(em_delta, 1),
    ))

    # Leverage — harmful direction is down (less leverage → lower MOIC
    # on winner; true for this simplified model since we treat debt as
    # constant cash shield).
    lev_break, lev_delta = _find_breakeven(
        inputs, "leverage_multiple", lower=0.0, upper=inputs.entry_multiple,
    )
    levers.append(LeverSafety(
        lever="leverage_multiple",
        base_value=inputs.leverage_multiple,
        breakeven_value=round(lev_break, 4),
        breakeven_delta_pct=round(lev_delta, 4),
        safety_grade=_grade(lev_delta, -1),
    ))

    # Combined shock: -25% growth AND -1x exit multiple.
    combined = _moic(
        inputs,
        ebitda_growth=inputs.ebitda_growth - 0.05,
        exit_multiple=max(1.0, inputs.exit_multiple - 1.0),
    )

    thin_count = sum(1 for l in levers if l.safety_grade == "thin")
    if base_moic < inputs.hurdle_moic:
        note = (f"Base MOIC {base_moic:.2f}x is already below hurdle "
                f"{inputs.hurdle_moic:.2f}x. No margin of safety — pass.")
    elif thin_count >= 2:
        note = (f"{thin_count} lever(s) with thin safety margins. "
                "The thesis is load-bearing on aggressive "
                "assumptions; minor shocks compound.")
    elif thin_count == 1:
        thin = next(l for l in levers if l.safety_grade == "thin")
        note = (f"Thin margin on {thin.lever}. Deal works, but "
                "pressure-test that lever specifically.")
    else:
        note = ("Margin of safety is ample across levers. The deal "
                "can absorb reasonable downside scenarios without "
                "dropping below hurdle.")

    return SafetyReport(
        base_moic=round(base_moic, 4),
        base_irr=round(base_irr, 6) if base_irr is not None else None,
        hurdle_moic=inputs.hurdle_moic,
        levers=levers,
        combined_shock_moic=round(combined, 4),
        partner_note=note,
    )


def render_safety_markdown(r: SafetyReport) -> str:
    lines = [
        "# Margin of safety",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Base MOIC: {r.base_moic:.2f}x (hurdle "
        f"{r.hurdle_moic:.2f}x)",
    ]
    if r.base_irr is not None:
        lines.append(f"- Base IRR: {r.base_irr*100:.1f}%")
    lines.extend([
        f"- Combined shock MOIC: {r.combined_shock_moic:.2f}x",
        "",
        "| Lever | Base | Breakeven | Δ% | Safety |",
        "|---|---:|---:|---:|---|",
    ])
    for l in r.levers:
        lines.append(
            f"| {l.lever} | {l.base_value:.3f} | "
            f"{l.breakeven_value:.3f} | {l.breakeven_delta_pct*100:+.1f}% | "
            f"{l.safety_grade} |"
        )
    return "\n".join(lines)
