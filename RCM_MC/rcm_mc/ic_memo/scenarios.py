"""Bull / Base / Bear scenario construction.

Builds a 3-scenario MOIC + IRR table off:
  • The QoE-adjusted EBITDA (from the QoE flagger), or the
    raw EBITDA when no QoE result is supplied.
  • The comparable-deal MOIC distribution (p25 = bear, p50 =
    base, p75 = bull).
  • A 5-year hold default.

Each scenario reports entry equity, exit equity, MOIC, and
implied IRR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import List, Optional


@dataclass
class Scenario:
    name: str           # bull / base / bear
    moic: float
    irr: float          # decimal
    entry_equity_mm: float
    exit_equity_mm: float
    notes: str = ""


@dataclass
class ScenarioSet:
    bull: Scenario
    base: Scenario
    bear: Scenario


def _irr_from_moic(moic: float, hold_years: float) -> float:
    """Solve (1 + IRR)^hold = MOIC for IRR. Closed form."""
    if moic <= 0 or hold_years <= 0:
        return 0.0
    return moic ** (1.0 / hold_years) - 1.0


def build_scenarios(
    *,
    entry_ebitda_mm: float,
    entry_multiple: float = 10.0,
    leverage_pct: float = 0.50,
    hold_years: float = 5.0,
    moic_p25: Optional[float] = None,
    moic_p50: Optional[float] = None,
    moic_p75: Optional[float] = None,
) -> ScenarioSet:
    """Build the 3-scenario set.

    Inputs:
      entry_ebitda_mm: post-QoE-adjustment entry EBITDA.
      entry_multiple: EV / EBITDA at entry (default 10x).
      leverage_pct: debt at close as % of EV (default 50%).
      hold_years: hold-period assumption (default 5).
      moic_p25 / p50 / p75: from the comparable-deal output.
        Defaults: p25=1.6×, p50=2.4×, p75=3.4× (typical
        healthcare-PE distribution).
    """
    p25 = moic_p25 if moic_p25 is not None else 1.6
    p50 = moic_p50 if moic_p50 is not None else 2.4
    p75 = moic_p75 if moic_p75 is not None else 3.4

    entry_ev = entry_ebitda_mm * entry_multiple
    entry_equity = entry_ev * (1.0 - leverage_pct)

    def _scenario(name: str, moic: float,
                  notes: str) -> Scenario:
        exit_equity = entry_equity * moic
        return Scenario(
            name=name,
            moic=round(moic, 2),
            irr=round(_irr_from_moic(moic, hold_years), 4),
            entry_equity_mm=round(entry_equity, 2),
            exit_equity_mm=round(exit_equity, 2),
            notes=notes,
        )

    return ScenarioSet(
        bull=_scenario(
            "bull", p75,
            "p75 of comparable-deal MOIC distribution; "
            "operational lift + multiple-expansion tailwind."),
        base=_scenario(
            "base", p50,
            "Median of the comparable-deal MOIC distribution."),
        bear=_scenario(
            "bear", p25,
            "p25 of the comparable-deal MOIC distribution; "
            "regulatory headwind + flat-multiple exit."),
    )
