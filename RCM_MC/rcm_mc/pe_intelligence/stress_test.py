"""Stress test — scenario-grid robustness scoring.

`scenario_stress.py` already models individual mechanical shocks
(rate cuts, volume declines, multiple compression, lever slip,
labor shocks). This module is different: it runs a *grid* of
downside/base/upside scenarios and scores the deal's robustness
across the grid, producing:

- Per-scenario outcome (pass / fail / breach).
- Downside-pass rate — % of downside scenarios the deal still clears.
- Upside-capture rate — % of upside scenarios that lift returns.
- A single robustness grade (A/B/C/D/F).

This is the input the operating-posture classifier uses to decide
between scenario_leader / resilient_core / etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .scenario_stress import (
    StressInputs,
    StressResult,
    stress_labor_shock,
    stress_lever_slip,
    stress_multiple_compression,
    stress_rate_down,
    stress_volume_down,
)


@dataclass
class ScenarioOutcome:
    name: str
    severity: str                       # "downside" | "base" | "upside"
    passes: Optional[bool]              # None = can't evaluate
    ebitda_delta_pct: Optional[float]
    covenant_breach: Optional[bool]
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "passes": self.passes,
            "ebitda_delta_pct": self.ebitda_delta_pct,
            "covenant_breach": self.covenant_breach,
            "partner_note": self.partner_note,
        }


@dataclass
class StressGridResult:
    outcomes: List[ScenarioOutcome] = field(default_factory=list)
    downside_pass_rate: float = 0.0    # 0..1 fraction of downsides that clear
    upside_capture_rate: float = 0.0   # 0..1 fraction of upsides that lift
    worst_case_delta_pct: Optional[float] = None
    best_case_delta_pct: Optional[float] = None
    n_covenant_breaches: int = 0
    robustness_grade: str = "F"        # A..F
    partner_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcomes": [o.to_dict() for o in self.outcomes],
            "downside_pass_rate": self.downside_pass_rate,
            "upside_capture_rate": self.upside_capture_rate,
            "worst_case_delta_pct": self.worst_case_delta_pct,
            "best_case_delta_pct": self.best_case_delta_pct,
            "n_covenant_breaches": self.n_covenant_breaches,
            "robustness_grade": self.robustness_grade,
            "partner_summary": self.partner_summary,
        }


# ── Scenario grid builders ──────────────────────────────────────────

def _downside_scenarios(inputs: StressInputs) -> List[ScenarioOutcome]:
    outcomes: List[ScenarioOutcome] = []
    for (label, shock) in (
        ("rate_down_100bps", stress_rate_down(inputs, bps=100)),
        ("rate_down_200bps", stress_rate_down(inputs, bps=200)),
        ("rate_down_300bps", stress_rate_down(inputs, bps=300)),
        ("volume_down_5pct", stress_volume_down(inputs, pct=0.05)),
        ("volume_down_10pct", stress_volume_down(inputs, pct=0.10)),
        ("multiple_compression_flat", stress_multiple_compression(inputs, flat_multiple=True)),
        ("lever_slip_60pct", stress_lever_slip(inputs, realization=0.60)),
        ("lever_slip_40pct", stress_lever_slip(inputs, realization=0.40)),
        ("labor_shock_10pct", stress_labor_shock(inputs, pct=0.10)),
        ("labor_shock_20pct", stress_labor_shock(inputs, pct=0.20)),
    ):
        outcomes.append(_stress_to_outcome(label, "downside", shock))
    return outcomes


def _upside_scenarios(inputs: StressInputs) -> List[ScenarioOutcome]:
    """Upside is simpler: multiple expansion + full lever realization."""
    outcomes: List[ScenarioOutcome] = []

    # Full lever realization = `realization=1.0` → full plan reaches target EBITDA.
    full_lever = stress_lever_slip(inputs, realization=1.0)
    outcomes.append(_stress_to_outcome("lever_full_realization", "upside", full_lever))

    # Multiple expansion: compare MOIC at exit multiple + 1.0 turn.
    from .scenario_stress import StressResult
    if (inputs.exit_multiple is not None and inputs.entry_multiple is not None
            and inputs.base_moic is not None and inputs.target_ebitda is not None):
        try:
            scale = ((inputs.exit_multiple + 1.0) / inputs.exit_multiple)
            shocked_moic = inputs.base_moic * scale
            outcomes.append(ScenarioOutcome(
                name="multiple_expansion_+1x",
                severity="upside",
                passes=shocked_moic > inputs.base_moic,
                ebitda_delta_pct=None,
                covenant_breach=False,
                partner_note=(
                    f"MOIC rises to {shocked_moic:.2f}x at +1.0 turn on exit."
                    if shocked_moic > inputs.base_moic else "No lift modeled."
                ),
            ))
        except Exception:
            pass
    return outcomes


def _stress_to_outcome(name: str, severity: str,
                       result: StressResult) -> ScenarioOutcome:
    return ScenarioOutcome(
        name=name,
        severity=severity,
        passes=result.passes,
        ebitda_delta_pct=result.ebitda_delta_pct,
        covenant_breach=result.covenant_breach,
        partner_note=result.partner_note,
    )


# ── Grader ──────────────────────────────────────────────────────────

def _robustness_grade(
    downside_pass_rate: float,
    n_breaches: int,
    n_downsides: int,
) -> str:
    """Translate pass rate + breach count into an A..F letter grade."""
    if n_downsides == 0:
        return "?"
    if downside_pass_rate >= 0.90 and n_breaches == 0:
        return "A"
    if downside_pass_rate >= 0.80 and n_breaches <= 1:
        return "B"
    if downside_pass_rate >= 0.60:
        return "C"
    if downside_pass_rate >= 0.40:
        return "D"
    return "F"


def _partner_summary(grade: str, pass_rate: float, n_breaches: int) -> str:
    if grade == "A":
        return ("Deal is robust across the downside grid — structurally sound "
                "for most rate and volume shocks.")
    if grade == "B":
        return (f"{pass_rate*100:.0f}% of downsides clear; "
                f"{n_breaches} covenant breach(es). Serviceable with tight monitoring.")
    if grade == "C":
        return (f"Downside pass rate {pass_rate*100:.0f}% — the deal is fragile "
                "to shocks. Re-size debt or move to caveats.")
    if grade == "D":
        return (f"Majority of downsides fail ({pass_rate*100:.0f}% pass). "
                "Re-underwrite the thesis before IC.")
    return ("Deal fails under most downside scenarios — do not bring to IC "
            "as modeled.")


# ── Orchestrator ────────────────────────────────────────────────────

def run_stress_grid(inputs: StressInputs) -> StressGridResult:
    """Run the downside + upside grid and score robustness."""
    downsides = _downside_scenarios(inputs)
    upsides = _upside_scenarios(inputs)
    outcomes = downsides + upsides

    # Pass/fail arithmetic.
    d_eval = [o for o in downsides if o.passes is not None]
    d_pass = [o for o in d_eval if o.passes]
    down_pass_rate = (len(d_pass) / len(d_eval)) if d_eval else 0.0

    u_eval = [o for o in upsides if o.passes is not None]
    u_pass = [o for o in u_eval if o.passes]
    up_capture = (len(u_pass) / len(u_eval)) if u_eval else 0.0

    # Worst- and best-case deltas.
    deltas = [o.ebitda_delta_pct for o in outcomes if o.ebitda_delta_pct is not None]
    worst = min(deltas) if deltas else None
    best = max(deltas) if deltas else None

    n_breaches = sum(1 for o in outcomes if o.covenant_breach)
    grade = _robustness_grade(down_pass_rate, n_breaches, len(d_eval))

    return StressGridResult(
        outcomes=outcomes,
        downside_pass_rate=round(down_pass_rate, 4),
        upside_capture_rate=round(up_capture, 4),
        worst_case_delta_pct=worst,
        best_case_delta_pct=best,
        n_covenant_breaches=n_breaches,
        robustness_grade=grade,
        partner_summary=_partner_summary(grade, down_pass_rate, n_breaches),
    )
