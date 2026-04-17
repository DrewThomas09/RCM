"""Value creation tracker — post-close lever-vs-plan reporting.

Once the deal is in the portfolio, the partner tracks progress
against the underwriting plan on a monthly cadence. Each lever has:

- An underwriting target for year N.
- An actual observed value for the current period.
- A trend: on pace / behind / ahead.

This module provides the arithmetic and partner-voice commentary for
a monthly review. It's not a full OLAP cube — it takes a list of
lever observations and the original plan, and returns a status list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


# ── Inputs ──────────────────────────────────────────────────────────

@dataclass
class LeverPlan:
    name: str
    unit: str                       # "bps" | "days" | "pct" | "usd_m"
    baseline: float                 # value at close
    year1_target: Optional[float] = None
    year2_target: Optional[float] = None
    year3_target: Optional[float] = None
    year4_target: Optional[float] = None
    year5_target: Optional[float] = None
    lower_is_better: bool = False


@dataclass
class LeverActual:
    lever_name: str
    as_of: date
    observed_value: float
    period_label: str = ""          # "Q1 2027" etc.


# ── Outputs ─────────────────────────────────────────────────────────

@dataclass
class LeverStatus:
    lever_name: str
    unit: str
    baseline: float
    target_current: Optional[float]
    observed: Optional[float]
    delta_vs_plan: Optional[float]     # observed - target (or inverse sign)
    pct_of_plan: Optional[float]       # [observed - baseline] / [target - baseline]
    status: str                        # "ahead" | "on_track" | "behind" | "off_track" | "unknown"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever_name": self.lever_name,
            "unit": self.unit,
            "baseline": self.baseline,
            "target_current": self.target_current,
            "observed": self.observed,
            "delta_vs_plan": self.delta_vs_plan,
            "pct_of_plan": self.pct_of_plan,
            "status": self.status,
            "partner_note": self.partner_note,
        }


# ── Evaluator ───────────────────────────────────────────────────────

def _target_for_year(plan: LeverPlan, year: int) -> Optional[float]:
    if year <= 1:
        return plan.year1_target
    if year == 2:
        return plan.year2_target
    if year == 3:
        return plan.year3_target
    if year == 4:
        return plan.year4_target
    if year >= 5:
        return plan.year5_target
    return None


def _status_from_pct(pct: Optional[float]) -> str:
    if pct is None:
        return "unknown"
    if pct >= 1.10:
        return "ahead"
    if pct >= 0.85:
        return "on_track"
    if pct >= 0.60:
        return "behind"
    return "off_track"


def _partner_note_for_status(status: str, lever: str, pct: Optional[float]) -> str:
    if status == "ahead":
        return f"{lever}: pulling forward plan value. Don't celebrate yet — check sustainability."
    if status == "on_track":
        return f"{lever}: tracking plan. No action."
    if status == "behind":
        return (f"{lever}: at ~{(pct or 0)*100:.0f}% of plan. Diagnose root cause this month, "
                "don't wait for the quarter.")
    if status == "off_track":
        return (f"{lever}: materially behind. Escalate to operating partner; "
                "consider re-baselining.")
    return f"{lever}: insufficient data to evaluate."


def evaluate_lever(
    plan: LeverPlan,
    actual: LeverActual,
    *,
    year_in_hold: int,
) -> LeverStatus:
    """Compute lever status against the plan."""
    target = _target_for_year(plan, year_in_hold)
    observed = actual.observed_value
    pct: Optional[float]
    delta: Optional[float]
    if target is None:
        pct = None
        delta = None
    else:
        expected_delta = target - plan.baseline
        actual_delta = observed - plan.baseline
        # For lower_is_better, flip signs so pct is positive when improvement.
        if plan.lower_is_better:
            expected_delta = -expected_delta
            actual_delta = -actual_delta
        if expected_delta == 0:
            pct = 1.0 if actual_delta == 0 else None
        else:
            pct = actual_delta / expected_delta
        delta = (observed - target) * (-1.0 if plan.lower_is_better else 1.0)
    status = _status_from_pct(pct)
    note = _partner_note_for_status(status, plan.name, pct)
    return LeverStatus(
        lever_name=plan.name,
        unit=plan.unit,
        baseline=plan.baseline,
        target_current=target,
        observed=observed,
        delta_vs_plan=delta,
        pct_of_plan=pct,
        status=status,
        partner_note=note,
    )


def evaluate_plan(
    plans: List[LeverPlan],
    actuals: List[LeverActual],
    *,
    year_in_hold: int,
) -> List[LeverStatus]:
    """Evaluate every lever in the plan against observed actuals.

    Levers without an actual observation get a ``unknown`` status
    with no partner note.
    """
    by_lever = {a.lever_name: a for a in actuals}
    out: List[LeverStatus] = []
    for plan in plans:
        actual = by_lever.get(plan.name)
        if actual is None:
            out.append(LeverStatus(
                lever_name=plan.name,
                unit=plan.unit,
                baseline=plan.baseline,
                target_current=_target_for_year(plan, year_in_hold),
                observed=None,
                delta_vs_plan=None,
                pct_of_plan=None,
                status="unknown",
                partner_note=f"{plan.name}: no observation reported.",
            ))
            continue
        out.append(evaluate_lever(plan, actual, year_in_hold=year_in_hold))
    return out


# ── Overall health ──────────────────────────────────────────────────

def rollup_status(statuses: List[LeverStatus]) -> Dict[str, Any]:
    """Portfolio-level rollup of lever statuses.

    Partner-facing: what fraction of levers are on track? Any
    off-track? One-sentence headline.
    """
    total = len(statuses)
    if total == 0:
        return {"total": 0, "headline": "No levers tracked."}
    counts = {"ahead": 0, "on_track": 0, "behind": 0, "off_track": 0, "unknown": 0}
    for s in statuses:
        counts[s.status] = counts.get(s.status, 0) + 1
    ok = counts["on_track"] + counts["ahead"]
    if counts["off_track"] > 0:
        headline = (f"{counts['off_track']} lever(s) off-track — materially behind plan. "
                    "Escalate.")
    elif counts["behind"] >= 2:
        headline = (f"{counts['behind']} levers behind plan — workstream re-prioritization "
                    "needed this month.")
    elif ok == total - counts["unknown"]:
        headline = f"All tracked levers on pace ({ok} on track, {counts['ahead']} ahead)."
    else:
        headline = (f"{ok}/{total - counts['unknown']} levers on or above plan; "
                    f"{counts['behind']} behind.")
    return {
        "total": total,
        "counts": counts,
        "headline": headline,
    }
