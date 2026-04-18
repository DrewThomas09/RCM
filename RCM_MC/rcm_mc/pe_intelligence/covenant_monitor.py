"""Covenant monitor — live covenant tracking + waiver scenario math.

Partners track leverage / coverage / fixed-charge covenants monthly.
This module takes a deal's covenant definitions + latest metrics and
returns:

- Per-covenant status (green / amber / red) with headroom.
- Projected status at end of next quarter given a trend.
- Waiver math — what EBITDA level triggers a technical default.

Used in the Ops partner's monthly review cadence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CovenantDefinition:
    name: str                              # "net_leverage" | "interest_coverage" | "fcf_coverage"
    direction: str                         # "max" | "min"
    threshold: float                        # covenant level
    headroom_amber_pct: float = 0.15       # headroom % below which = amber
    headroom_red_pct: float = 0.05         # headroom % below which = red


@dataclass
class CovenantObservation:
    covenant_name: str
    observed_value: float
    period_label: str = ""
    trend_per_quarter: Optional[float] = None   # change per quarter


@dataclass
class CovenantStatus:
    definition: CovenantDefinition
    observed: float
    headroom_abs: float                    # absolute distance to threshold
    headroom_pct: float                    # fraction of threshold
    status: str                            # "green" | "amber" | "red"
    projected_next_q: Optional[float] = None
    projected_status: Optional[str] = None
    break_ebitda: Optional[float] = None   # EBITDA level that triggers breach
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definition": {
                "name": self.definition.name,
                "direction": self.definition.direction,
                "threshold": self.definition.threshold,
            },
            "observed": self.observed,
            "headroom_abs": self.headroom_abs,
            "headroom_pct": self.headroom_pct,
            "status": self.status,
            "projected_next_q": self.projected_next_q,
            "projected_status": self.projected_status,
            "break_ebitda": self.break_ebitda,
            "partner_note": self.partner_note,
        }


@dataclass
class CovenantReport:
    statuses: List[CovenantStatus] = field(default_factory=list)
    worst_status: str = "green"
    red_count: int = 0
    amber_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statuses": [s.to_dict() for s in self.statuses],
            "worst_status": self.worst_status,
            "red_count": self.red_count,
            "amber_count": self.amber_count,
            "partner_note": self.partner_note,
        }


# ── Evaluator ──────────────────────────────────────────────────────

def _status_for(
    definition: CovenantDefinition,
    observed: float,
) -> tuple:
    """Return (status, headroom_abs, headroom_pct)."""
    if definition.threshold == 0:
        return "amber", 0.0, 0.0
    if definition.direction == "max":
        headroom_abs = definition.threshold - observed
        headroom_pct = headroom_abs / abs(definition.threshold)
    else:   # "min"
        headroom_abs = observed - definition.threshold
        headroom_pct = headroom_abs / abs(definition.threshold)
    if headroom_pct < definition.headroom_red_pct:
        status = "red"
    elif headroom_pct < definition.headroom_amber_pct:
        status = "amber"
    else:
        status = "green"
    return status, headroom_abs, headroom_pct


def _break_ebitda(
    definition: CovenantDefinition,
    observed: float,
    *,
    debt: Optional[float],
    interest: Optional[float],
) -> Optional[float]:
    """For leverage / coverage covenants, compute the EBITDA level
    that pushes the metric to the threshold."""
    name = definition.name
    if name in ("net_leverage", "leverage_multiple", "debt_to_ebitda"):
        # Breach when debt / EBITDA = threshold → EBITDA = debt / threshold.
        if debt is None or debt <= 0:
            return None
        return debt / max(definition.threshold, 1e-9)
    if name in ("interest_coverage", "ebitda_to_interest"):
        if interest is None or interest <= 0:
            return None
        return definition.threshold * interest
    if name in ("fcf_coverage",):
        # Simplified: assume FCF/interest mapping via a 70% conversion.
        if interest is None or interest <= 0:
            return None
        # FCF / interest >= threshold → FCF = threshold*interest → EBITDA = FCF / 0.70
        return (definition.threshold * interest) / 0.70
    return None


def evaluate_covenant(
    definition: CovenantDefinition,
    observed: float,
    *,
    trend_per_quarter: Optional[float] = None,
    debt: Optional[float] = None,
    interest: Optional[float] = None,
) -> CovenantStatus:
    status, abs_h, pct_h = _status_for(definition, observed)

    projected_next = None
    projected_status = None
    if trend_per_quarter is not None:
        projected_next = observed + trend_per_quarter
        p_status, _, _ = _status_for(definition, projected_next)
        projected_status = p_status

    break_ebitda = _break_ebitda(definition, observed,
                                 debt=debt, interest=interest)

    # Partner note
    if status == "green":
        note = "Green — meaningful headroom to covenant."
    elif status == "amber":
        note = (f"Amber — {pct_h*100:.1f}% headroom below amber threshold; "
                "watch the next quarter.")
    else:
        note = (f"Red — {pct_h*100:.1f}% headroom below red threshold. "
                "Open a lender conversation now.")

    return CovenantStatus(
        definition=definition,
        observed=observed,
        headroom_abs=round(abs_h, 4),
        headroom_pct=round(pct_h, 4),
        status=status,
        projected_next_q=projected_next,
        projected_status=projected_status,
        break_ebitda=break_ebitda,
        partner_note=note,
    )


# ── Orchestrator ───────────────────────────────────────────────────

def monitor_covenants(
    definitions: List[CovenantDefinition],
    observations: List[CovenantObservation],
    *,
    debt: Optional[float] = None,
    interest: Optional[float] = None,
) -> CovenantReport:
    """Evaluate every covenant that has an observation."""
    obs_map = {o.covenant_name: o for o in observations}
    statuses: List[CovenantStatus] = []
    for d in definitions:
        obs = obs_map.get(d.name)
        if obs is None:
            continue
        statuses.append(evaluate_covenant(
            d, obs.observed_value,
            trend_per_quarter=obs.trend_per_quarter,
            debt=debt, interest=interest,
        ))
    red = sum(1 for s in statuses if s.status == "red")
    amber = sum(1 for s in statuses if s.status == "amber")
    if red > 0:
        worst = "red"
        note = (f"{red} covenant(s) in red — engage lender now; avoid "
                "surprise at the next quarterly compliance certificate.")
    elif amber > 0:
        worst = "amber"
        note = (f"{amber} covenant(s) in amber — trend toward breach; "
                "tighten forecast cadence.")
    else:
        worst = "green"
        note = "All covenants green — no lender engagement needed."

    return CovenantReport(
        statuses=statuses,
        worst_status=worst,
        red_count=red,
        amber_count=amber,
        partner_note=note,
    )


def render_covenant_report_markdown(report: CovenantReport) -> str:
    lines = [
        "# Covenant monitor",
        "",
        f"**Worst status:** {report.worst_status.upper()}  ",
        f"**Red count:** {report.red_count}  ",
        f"**Amber count:** {report.amber_count}",
        "",
        f"_{report.partner_note}_",
        "",
        "| Covenant | Observed | Threshold | Headroom | Status | Break-EBITDA | Note |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    for s in report.statuses:
        be = (f"${s.break_ebitda:,.0f}" if s.break_ebitda is not None
              else "—")
        lines.append(
            f"| {s.definition.name} | {s.observed:.2f} | "
            f"{s.definition.threshold:.2f} | "
            f"{s.headroom_pct*100:.1f}% | {s.status} | "
            f"{be} | {s.partner_note} |"
        )
    return "\n".join(lines)
