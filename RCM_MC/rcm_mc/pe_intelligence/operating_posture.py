"""Operating posture — classify a deal's strategic stance.

Given the stress-grid outcome + regime + concentration signals,
classify a deal into one of:

- **scenario_leader** — robust across the downside grid AND captures
  the upside grid; durable / emerging-growth regime; not over-concentrated.
- **resilient_core** — robust downside but limited upside — a
  cash-cow / steady deal.
- **balanced** — moderate downside pass rate, modest upside.
- **growth_optional** — weak downside but strong upside (high beta).
  Only underwrite if you're comfortable owning volatility.
- **concentration_risk** — downside AND upside both weakened by
  payer / state / service-line concentration.

This is a post-hoc label, not a recommendation. It helps partners
explain the deal shape in one word.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


POSTURE_SCENARIO_LEADER = "scenario_leader"
POSTURE_RESILIENT_CORE = "resilient_core"
POSTURE_BALANCED = "balanced"
POSTURE_GROWTH_OPTIONAL = "growth_optional"
POSTURE_CONCENTRATION_RISK = "concentration_risk"

ALL_POSTURES = (
    POSTURE_SCENARIO_LEADER,
    POSTURE_RESILIENT_CORE,
    POSTURE_BALANCED,
    POSTURE_GROWTH_OPTIONAL,
    POSTURE_CONCENTRATION_RISK,
)


@dataclass
class PostureInputs:
    downside_pass_rate: Optional[float] = None    # 0..1
    upside_capture_rate: Optional[float] = None   # 0..1
    n_covenant_breaches: int = 0
    robustness_grade: str = ""                    # A..F (optional)
    regime: Optional[str] = None                  # from regime_classifier
    concentration_flags: List[str] = field(default_factory=list)
    # e.g. ["payer_concentration_risk", "service_line_concentration",
    #       "state_medicaid_volatility"]


@dataclass
class PostureResult:
    posture: str
    confidence: float                              # 0..1
    signals: List[str] = field(default_factory=list)
    partner_note: str = ""
    playbook: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "posture": self.posture,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "partner_note": self.partner_note,
            "playbook": self.playbook,
        }


# ── Classifier ──────────────────────────────────────────────────────

def _flag(posture: str, confidence: float, signals: List[str]) -> PostureResult:
    return PostureResult(
        posture=posture,
        confidence=confidence,
        signals=list(signals),
        partner_note=_PARTNER_NOTE[posture],
        playbook=_PLAYBOOK[posture],
    )


_PARTNER_NOTE = {
    POSTURE_SCENARIO_LEADER: (
        "Robust across downsides and captures upside — the kind of deal you "
        "want to write a check on."),
    POSTURE_RESILIENT_CORE: (
        "Deal is stress-resistant but upside is capped. Think cash-cow: use "
        "leverage to amplify distributions, not to chase growth."),
    POSTURE_BALANCED: (
        "Neither stress-resistant nor strongly asymmetric. Operating levers "
        "need to carry the return."),
    POSTURE_GROWTH_OPTIONAL: (
        "Strong upside, weak downside. Only underwrite at equity sizes the "
        "fund can tolerate losing."),
    POSTURE_CONCENTRATION_RISK: (
        "Concentration risk dominates both tails. Diversify exposure before "
        "IC or re-size the check."),
}

_PLAYBOOK = {
    POSTURE_SCENARIO_LEADER: (
        "Go offensive — size up, accelerate the value-creation plan, "
        "consider dividend recap mid-hold."),
    POSTURE_RESILIENT_CORE: (
        "Run for cash: distributions first, then reinvestment. Exit when "
        "multiples ripen."),
    POSTURE_BALANCED: (
        "Operating discipline carries the return. Build the KPI cadence "
        "post-close and hold management accountable."),
    POSTURE_GROWTH_OPTIONAL: (
        "Hedge downside via covenant structure + escrow. Keep optionality "
        "open for a quick exit if the upside materializes early."),
    POSTURE_CONCENTRATION_RISK: (
        "Address concentration pre-IC: contract re-negotiation, payer "
        "diversification, or geographic expansion."),
}


def classify_posture(inputs: PostureInputs) -> PostureResult:
    """Pick a posture based on stress + regime + concentration signals."""
    signals: List[str] = []

    # Concentration takes precedence when flagged — classification order matters.
    n_conc = len([c for c in inputs.concentration_flags if c])
    if n_conc >= 2:
        signals.append(f"{n_conc} concentration flag(s): {', '.join(inputs.concentration_flags[:3])}")
        return _flag(POSTURE_CONCENTRATION_RISK, 0.85, signals)
    if n_conc == 1:
        signals.append(f"One concentration flag: {inputs.concentration_flags[0]}")
        # Fall through to normal classification but note the flag.

    dp = inputs.downside_pass_rate
    uc = inputs.upside_capture_rate
    if dp is None:
        signals.append("Downside data unavailable; defaulting to balanced.")
        return _flag(POSTURE_BALANCED, 0.30, signals)

    # Scenario leader: high downside pass + high upside capture.
    if dp >= 0.85 and (uc is None or uc >= 0.60):
        signals.append(f"Downside pass rate {dp*100:.0f}%")
        if uc is not None:
            signals.append(f"Upside capture {uc*100:.0f}%")
        return _flag(POSTURE_SCENARIO_LEADER, 0.90, signals)

    # Resilient core: high downside, low upside.
    if dp >= 0.85 and uc is not None and uc < 0.50:
        signals.append(f"Downside pass {dp*100:.0f}%, upside {uc*100:.0f}%")
        return _flag(POSTURE_RESILIENT_CORE, 0.80, signals)

    # Growth optional: low downside, high upside.
    if dp < 0.60 and uc is not None and uc >= 0.70:
        signals.append(f"Downside pass {dp*100:.0f}%, upside {uc*100:.0f}%")
        return _flag(POSTURE_GROWTH_OPTIONAL, 0.75, signals)

    # Default: balanced
    signals.append(f"Downside pass {dp*100:.0f}%"
                   + (f", upside {uc*100:.0f}%" if uc is not None else ""))
    return _flag(POSTURE_BALANCED, 0.60, signals)


def posture_from_stress_and_heuristics(
    stress_grid_dict: Dict[str, Any],
    heuristic_hits: List[Any],
    *,
    regime: Optional[str] = None,
) -> PostureResult:
    """Convenience wrapper that pulls the inputs out of a stress-grid
    result dict and a list of heuristic hits (objects with
    ``.id`` / ``.category`` attrs or dicts)."""
    # Concentration-flag ids we recognize as structurally relevant.
    flagged_ids = {"payer_concentration_risk", "service_line_concentration",
                   "state_medicaid_volatility", "340b_margin_dependency",
                   "medicare_heavy_multiple_ceiling"}
    concentration_flags: List[str] = []
    for h in heuristic_hits or []:
        hid = getattr(h, "id", None) or (h.get("id") if isinstance(h, dict) else None)
        if hid in flagged_ids:
            concentration_flags.append(hid)

    dp = stress_grid_dict.get("downside_pass_rate")
    uc = stress_grid_dict.get("upside_capture_rate")
    n_breaches = int(stress_grid_dict.get("n_covenant_breaches") or 0)
    grade = stress_grid_dict.get("robustness_grade", "")

    return classify_posture(PostureInputs(
        downside_pass_rate=dp,
        upside_capture_rate=uc,
        n_covenant_breaches=n_breaches,
        robustness_grade=grade,
        regime=regime,
        concentration_flags=concentration_flags,
    ))
