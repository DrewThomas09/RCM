"""KPI alert rules — threshold-based alerts for monthly ops reviews.

Operating partners run a monthly review where each portfolio KPI is
compared to a target + upper/lower guardrails. When a KPI crosses a
guardrail, an alert fires. Alerts have a severity (low/medium/high)
and a recommended next action.

This module is the alerting engine: given current KPI values +
targets + guardrails, it returns a list of fired alerts, each with
partner-voice commentary and escalation guidance.

Paired with `value_creation_tracker.py` — that module tracks progress
against plan; this one fires alerts when individual KPIs drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class KPIRule:
    kpi: str
    direction: str             # "higher_is_better" | "lower_is_better"
    guardrail_low: float       # below this fires an alert
    guardrail_high: float      # above this fires an alert
    hard_floor: Optional[float] = None
    hard_ceiling: Optional[float] = None
    unit: str = ""             # "bps" | "days" | "pct"


@dataclass
class KPIObservation:
    kpi: str
    value: float
    period: str = ""


@dataclass
class KPIAlert:
    kpi: str
    severity: str              # "low" | "medium" | "high"
    direction: str             # "below" | "above"
    observed: float
    guardrail: float
    unit: str = ""
    partner_note: str = ""
    escalation: str = ""       # who to page

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi": self.kpi,
            "severity": self.severity,
            "direction": self.direction,
            "observed": self.observed,
            "guardrail": self.guardrail,
            "unit": self.unit,
            "partner_note": self.partner_note,
            "escalation": self.escalation,
        }


# ── Default rule set ────────────────────────────────────────────────

DEFAULT_RULES: List[KPIRule] = [
    KPIRule(kpi="initial_denial_rate", direction="lower_is_better",
            guardrail_low=0.06, guardrail_high=0.14, hard_ceiling=0.20,
            unit="pct"),
    KPIRule(kpi="final_writeoff_rate", direction="lower_is_better",
            guardrail_low=0.025, guardrail_high=0.07, hard_ceiling=0.10,
            unit="pct"),
    KPIRule(kpi="days_in_ar", direction="lower_is_better",
            guardrail_low=40, guardrail_high=60, hard_ceiling=80,
            unit="days"),
    KPIRule(kpi="clean_claim_rate", direction="higher_is_better",
            guardrail_low=0.88, guardrail_high=0.96, hard_floor=0.80,
            unit="pct"),
    KPIRule(kpi="ebitda_margin", direction="higher_is_better",
            guardrail_low=0.04, guardrail_high=0.25, hard_floor=-0.05,
            unit="pct"),
    KPIRule(kpi="labor_pct_of_revenue", direction="lower_is_better",
            guardrail_low=0.40, guardrail_high=0.58, hard_ceiling=0.65,
            unit="pct"),
    KPIRule(kpi="census_occupancy", direction="higher_is_better",
            guardrail_low=0.65, guardrail_high=0.92, hard_floor=0.50,
            unit="pct"),
]


# ── Evaluator ───────────────────────────────────────────────────────

def _severity_for(
    value: float, rule: KPIRule,
) -> Optional[Tuple[str, str, float]]:
    """Return (severity, direction, breached_guardrail) or None."""
    if rule.direction == "lower_is_better":
        # Below guardrail_low = great (silent).
        if (rule.hard_ceiling is not None and value > rule.hard_ceiling):
            return ("high", "above", rule.hard_ceiling)
        if value > rule.guardrail_high:
            return ("medium", "above", rule.guardrail_high)
    else:
        if (rule.hard_floor is not None and value < rule.hard_floor):
            return ("high", "below", rule.hard_floor)
        if value < rule.guardrail_low:
            return ("medium", "below", rule.guardrail_low)
    return None


_PARTNER_NOTE = {
    ("initial_denial_rate", "above"): (
        "Denial rate above guardrail — check last month's intake / eligibility "
        "edits. Which reason codes spiked?"),
    ("final_writeoff_rate", "above"): (
        "Write-offs trending above guardrail — diagnose by bucket (timely "
        "filing, medical necessity, coding)."),
    ("days_in_ar", "above"): (
        "AR days drifting up. Look at the aging bucket split — is this "
        "billing or payer?"),
    ("clean_claim_rate", "below"): (
        "Clean claim rate below guardrail. Rework cost and DSO both bite."),
    ("ebitda_margin", "below"): (
        "Margin below guardrail — is this seasonality, volume, or a new "
        "structural issue?"),
    ("labor_pct_of_revenue", "above"): (
        "Labor cost drift — contract-labor rates? Productivity loss? "
        "Investigate this month."),
    ("census_occupancy", "below"): (
        "Census below guardrail — volume softness directly compresses "
        "contribution margin. Sales team conversation."),
}

_ESCALATION = {
    "high": "Page operating partner within 24 hours.",
    "medium": "Raise in next weekly ops call.",
    "low": "Noted in monthly review.",
}


def evaluate_kpi(
    obs: KPIObservation,
    rule: KPIRule,
) -> Optional[KPIAlert]:
    """Evaluate a single observation; return an alert or None."""
    breach = _severity_for(obs.value, rule)
    if breach is None:
        return None
    severity, direction, guardrail = breach
    note = _PARTNER_NOTE.get((obs.kpi, direction), "")
    return KPIAlert(
        kpi=obs.kpi, severity=severity, direction=direction,
        observed=obs.value, guardrail=guardrail,
        unit=rule.unit, partner_note=note,
        escalation=_ESCALATION.get(severity, ""),
    )


def evaluate_all(
    observations: List[KPIObservation],
    rules: Optional[List[KPIRule]] = None,
) -> List[KPIAlert]:
    """Evaluate a set of observations against rules.

    Uses `DEFAULT_RULES` when ``rules`` is None. Observations without
    a matching rule are ignored.
    """
    rules = rules if rules is not None else DEFAULT_RULES
    by_kpi = {r.kpi: r for r in rules}
    alerts: List[KPIAlert] = []
    for obs in observations:
        rule = by_kpi.get(obs.kpi)
        if rule is None:
            continue
        alert = evaluate_kpi(obs, rule)
        if alert is not None:
            alerts.append(alert)
    # Severity order: high → medium → low
    order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: order.get(a.severity, 3))
    return alerts


def summarize_alerts(alerts: List[KPIAlert]) -> Dict[str, Any]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for a in alerts:
        counts[a.severity] = counts.get(a.severity, 0) + 1
    return {
        "total": len(alerts),
        "counts": counts,
        "headline": (
            "No KPI alerts this period."
            if not alerts else
            f"{len(alerts)} alert(s): "
            f"{counts['high']} high / {counts['medium']} medium / {counts['low']} low."
        ),
    }
