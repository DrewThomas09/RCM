"""Counterfactual deal-structuring advisor.

Every risk module in this platform has severity bands driven by
thresholds. Given a current RED/CRITICAL finding, this package
back-solves the minimum input change that flips the band — the
answer to "what would change our mind about this deal?"

Use cases:
    - Walk a partner from "this is CRITICAL" to "here's the
      specific offer modification that flips it."
    - Produce the walkaway-condition section of the IC memo.
    - Feed the partner-voice synthesis: "structure RED reverts to
      YELLOW if X; price RED stays RED regardless of structure."

Solvers:
    for_cpom(report)         → restructure / drop-state counterfactual
    for_nsa(exposure)        → OON share / QPA reduction counterfactual
    for_steward(result)      → factor-removal counterfactual
    for_team(exposure)       → track-selection counterfactual
    for_antitrust(exposure)  → divestiture counterfactual
    for_cyber(score)         → BA replacement / EHR migration
    for_site_neutral(exp)    → HOPD revenue recategorization

Each solver returns a :class:`Counterfactual` with the smallest-
change-that-flips-the-band recommendation, the estimated dollar
impact, and the narrative a partner can drop into an IC memo.

Design invariant: NEVER recommend a change that isn't lawful /
feasible. A counterfactual is always actionable advice (divest,
restructure, negotiate), not a hypothetical ("what if the FTC
didn't exist").
"""
from __future__ import annotations

from .advisor import (
    Counterfactual, CounterfactualSet, advise_all, for_antitrust,
    for_cpom, for_cyber, for_nsa, for_physician_attrition,
    for_site_neutral, for_steward, for_team,
)
from .bridge_integration import (
    CounterfactualLever, counterfactual_bridge_lever,
)
from .ccd_runner import (
    run_counterfactuals_from_ccd, summarize_ccd_inputs,
)

__all__ = [
    "Counterfactual",
    "CounterfactualLever",
    "CounterfactualSet",
    "advise_all",
    "counterfactual_bridge_lever",
    "for_antitrust",
    "for_cpom",
    "for_cyber",
    "for_nsa",
    "for_physician_attrition",
    "for_site_neutral",
    "for_steward",
    "for_team",
    "run_counterfactuals_from_ccd",
    "summarize_ccd_inputs",
]
