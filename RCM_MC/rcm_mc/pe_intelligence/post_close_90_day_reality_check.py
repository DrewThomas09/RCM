"""90-day post-close reality check — did the underwriting hold up?

Partner statement: "First board meeting post-close
is 90 days in. By then I want to know: did the
underwriting hold up? Are the leading indicators
moving the way the model assumed? Is the operator
delivering on the day-1 actions, or are they still
'getting their arms around it'? Three things have to
be true at 90 days for me to feel good: the financial
trajectory is on or ahead of underwrite, the operator
has named what's stuck and what's moving, and the
flagged risks haven't materialized in a way we
weren't expecting. If any of those three is off, the
post-close diary writes itself."

Distinct from:
- `quarterly_operating_review` — 4-block QoR agenda.
- `post_close_surprises_log` — running surprises log
  across the hold.
- `value_creation_tracker` — long-term VCP execution.
- `hundred_day_plan` — the plan itself.
- `day_one_action_plan` — day-1 specifics.

This module is the **first-quarter reality test**:
each underwriting assumption + 90-day actual; flag
where reality diverges from underwrite.

### 6 reality-check categories

1. **revenue_trajectory** — same-store growth vs.
   underwrite annualized.
2. **ebitda_margin** — actual margin vs. underwrite
   margin at this point in the curve.
3. **denial_rate** — KPI moving the right direction
   at right pace?
4. **physician_retention** — top producers all in
   chair after close?
5. **management_team_intact** — CEO/CFO/COO all in
   seat?
6. **named_day1_actions_delivered** — day-1 plan
   complete?

### Three-bucket verdict per item

- **on_track** — actual matches underwrite or better.
- **at_risk** — within tolerance but trending off.
- **off_track** — divergence > tolerance; needs
  intervention.

### Aggregate verdict

- 5+ on_track → **healthy_first_quarter**
- 1+ off_track → **diary_warranted** (board write-up)
- 2+ off_track → **acceleration_warranted**
  (intervention)
- 3+ off_track → **thesis_at_risk** (escalate to IC)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


STATUS_ON_TRACK = "on_track"
STATUS_AT_RISK = "at_risk"
STATUS_OFF_TRACK = "off_track"


@dataclass
class NinetyDayInputs:
    deal_name: str = "PortCo"
    # Revenue trajectory
    underwritten_annual_growth_pct: float = 0.08
    actual_q1_annualized_growth_pct: float = 0.07
    # EBITDA margin
    underwritten_ebitda_margin_pct: float = 0.18
    actual_q1_ebitda_margin_pct: float = 0.17
    # Denial rate
    underwritten_q1_denial_drop_bps: float = 25.0
    actual_q1_denial_drop_bps: float = 22.0
    # Physician retention
    top_5_physicians_at_close: int = 5
    top_5_physicians_active_q1: int = 5
    # Management team
    expected_c_suite_count: int = 3
    actual_c_suite_count_at_q1: int = 3
    # Day-1 actions
    day1_actions_committed: int = 8
    day1_actions_delivered: int = 7
    # Material surprises (count of new risk items beyond
    # what was flagged at IC)
    material_surprises_count: int = 0


@dataclass
class CategoryCheck:
    name: str
    status: str
    actual: str
    underwritten: str
    delta_summary: str
    partner_read: str


@dataclass
class NinetyDayReport:
    deal_name: str = ""
    categories: List[CategoryCheck] = field(
        default_factory=list)
    on_track_count: int = 0
    at_risk_count: int = 0
    off_track_count: int = 0
    aggregate_verdict: str = "healthy_first_quarter"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "categories": [
                {"name": c.name,
                 "status": c.status,
                 "actual": c.actual,
                 "underwritten": c.underwritten,
                 "delta_summary": c.delta_summary,
                 "partner_read": c.partner_read}
                for c in self.categories
            ],
            "on_track_count": self.on_track_count,
            "at_risk_count": self.at_risk_count,
            "off_track_count": self.off_track_count,
            "aggregate_verdict":
                self.aggregate_verdict,
            "partner_note": self.partner_note,
        }


def _check_revenue(
    i: NinetyDayInputs,
) -> CategoryCheck:
    delta = (
        i.actual_q1_annualized_growth_pct -
        i.underwritten_annual_growth_pct
    )
    if delta >= -0.005:
        status = STATUS_ON_TRACK
        read = (
            "Revenue trajectory on or ahead of "
            "underwrite. Maintain reporting cadence; "
            "no intervention."
        )
    elif delta >= -0.020:
        status = STATUS_AT_RISK
        read = (
            "Revenue softening within tolerance — flag "
            "in board package as monitor item; not yet "
            "intervention-warranting."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            "Revenue materially below underwrite; "
            "operator owes a 'what changed and what's "
            "the response' note for next board."
        )
    return CategoryCheck(
        name="revenue_trajectory",
        status=status,
        actual=f"{i.actual_q1_annualized_growth_pct:+.1%}",
        underwritten=f"{i.underwritten_annual_growth_pct:+.1%}",
        delta_summary=f"{delta:+.1%}",
        partner_read=read,
    )


def _check_ebitda_margin(
    i: NinetyDayInputs,
) -> CategoryCheck:
    delta_bps = (
        i.actual_q1_ebitda_margin_pct -
        i.underwritten_ebitda_margin_pct
    ) * 10000
    if delta_bps >= -50:
        status = STATUS_ON_TRACK
        read = (
            "EBITDA margin holds vs. underwrite. "
            "Continue lever execution."
        )
    elif delta_bps >= -150:
        status = STATUS_AT_RISK
        read = (
            "EBITDA margin slipping within tolerance "
            "(within 150 bps). Diagnose now before "
            "Q2 entrenches."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            "EBITDA margin off underwrite — likely "
            "labor or supply cost pressure. Operator "
            "owes a cost-bridge for Q2 board package."
        )
    return CategoryCheck(
        name="ebitda_margin",
        status=status,
        actual=f"{i.actual_q1_ebitda_margin_pct:.1%}",
        underwritten=f"{i.underwritten_ebitda_margin_pct:.1%}",
        delta_summary=f"{delta_bps:+.0f} bps",
        partner_read=read,
    )


def _check_denial_rate(
    i: NinetyDayInputs,
) -> CategoryCheck:
    delta_bps = (
        i.actual_q1_denial_drop_bps -
        i.underwritten_q1_denial_drop_bps
    )
    if delta_bps >= -5:
        status = STATUS_ON_TRACK
        read = (
            "Denial-rate work tracking — Q1 pace as "
            "modeled; the eligibility/format wins came "
            "in on schedule."
        )
    elif delta_bps >= -15:
        status = STATUS_AT_RISK
        read = (
            "Denial work behind plan; check whether "
            "the front-end automation / staffing hire "
            "shipped as planned."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            "Denial-rate work materially behind — "
            "either RCM platform conversion stalled "
            "or front-end staffing didn't land. Board "
            "needs explicit recovery plan."
        )
    return CategoryCheck(
        name="denial_rate_movement",
        status=status,
        actual=f"-{i.actual_q1_denial_drop_bps:.0f} bps",
        underwritten=f"-{i.underwritten_q1_denial_drop_bps:.0f} bps",
        delta_summary=f"{delta_bps:+.0f} bps",
        partner_read=read,
    )


def _check_physician_retention(
    i: NinetyDayInputs,
) -> CategoryCheck:
    lost = (
        i.top_5_physicians_at_close -
        i.top_5_physicians_active_q1
    )
    if lost == 0:
        status = STATUS_ON_TRACK
        read = (
            "Top-5 physicians intact at Q1. Retention "
            "package and onboarding worked."
        )
    elif lost == 1:
        status = STATUS_AT_RISK
        read = (
            "1 top-5 physician departure in Q1 — "
            "retention package design is being tested. "
            "Get the exit-interview note now."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            f"{lost} top-5 physicians departed in Q1 — "
            "this is the named risk materializing. "
            "Re-run physician_retention_stress and "
            "escalate immediately."
        )
    return CategoryCheck(
        name="physician_retention",
        status=status,
        actual=f"{i.top_5_physicians_active_q1}/5 active",
        underwritten=f"{i.top_5_physicians_at_close}/5 at close",
        delta_summary=f"{-lost:+d} top-5 departures",
        partner_read=read,
    )


def _check_management(
    i: NinetyDayInputs,
) -> CategoryCheck:
    missing = (
        i.expected_c_suite_count -
        i.actual_c_suite_count_at_q1
    )
    if missing == 0:
        status = STATUS_ON_TRACK
        read = (
            "C-suite intact. No transition risk firing "
            "in Q1."
        )
    elif missing == 1:
        status = STATUS_AT_RISK
        read = (
            "1 C-suite seat open or transitional. "
            "Identify search timeline and interim plan "
            "for next board."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            f"{missing} C-suite seats unfilled — the "
            "operator has lost team capacity to deliver "
            "the day-1 plan. Escalate."
        )
    return CategoryCheck(
        name="management_team_intact",
        status=status,
        actual=f"{i.actual_c_suite_count_at_q1} active",
        underwritten=f"{i.expected_c_suite_count} expected",
        delta_summary=f"{-missing:+d} seats",
        partner_read=read,
    )


def _check_day1_actions(
    i: NinetyDayInputs,
) -> CategoryCheck:
    if i.day1_actions_committed == 0:
        ratio = 1.0
    else:
        ratio = (
            i.day1_actions_delivered /
            i.day1_actions_committed
        )
    delta = (
        i.day1_actions_delivered -
        i.day1_actions_committed
    )
    if ratio >= 0.85:
        status = STATUS_ON_TRACK
        read = (
            "Day-1 plan substantially delivered. "
            "Operator earns trust; expand the runway "
            "for Q2."
        )
    elif ratio >= 0.65:
        status = STATUS_AT_RISK
        read = (
            "Day-1 plan partially delivered. Ask the "
            "operator which items got reprioritized "
            "and why; that's the diagnostic."
        )
    else:
        status = STATUS_OFF_TRACK
        read = (
            "Day-1 plan not delivered. Operator is "
            "still 'getting their arms around it' — "
            "that's a 30-day window, not 90. "
            "Escalate."
        )
    return CategoryCheck(
        name="day1_actions_delivered",
        status=status,
        actual=f"{i.day1_actions_delivered}/{i.day1_actions_committed}",
        underwritten="100% by Q1",
        delta_summary=f"{delta:+d} actions",
        partner_read=read,
    )


_CHECKERS = [
    _check_revenue,
    _check_ebitda_margin,
    _check_denial_rate,
    _check_physician_retention,
    _check_management,
    _check_day1_actions,
]


def run_90_day_reality_check(
    inputs: NinetyDayInputs,
) -> NinetyDayReport:
    cats = [fn(inputs) for fn in _CHECKERS]

    on_track = sum(
        1 for c in cats if c.status == STATUS_ON_TRACK)
    at_risk = sum(
        1 for c in cats if c.status == STATUS_AT_RISK)
    off_track = sum(
        1 for c in cats if c.status == STATUS_OFF_TRACK)

    if off_track >= 3:
        verdict = "thesis_at_risk"
        note = (
            f"{off_track} categories off track — thesis "
            "is at risk. Escalate to IC; redo bear case "
            "with Q1 actuals in the model. The 90-day "
            "diary is the partner's call to action."
        )
    elif off_track >= 2:
        verdict = "acceleration_warranted"
        note = (
            f"{off_track} categories off track — "
            "operator intervention warranted before "
            "Q2 board. Time to add bench or re-prioritize "
            "explicitly."
        )
    elif off_track >= 1 or at_risk >= 2:
        verdict = "diary_warranted"
        note = (
            f"{off_track} off-track + {at_risk} at-risk "
            "— write the 90-day diary entry; flag in "
            "next board package; no intervention yet."
        )
    elif on_track >= 5:
        verdict = "healthy_first_quarter"
        note = (
            f"{on_track} categories on track. Healthy "
            "first quarter — operator earned trust; "
            "Q2 cadence can be standard."
        )
    else:
        verdict = "diary_warranted"
        note = (
            "Mixed first quarter — no off-tracks but "
            "several at-risk; document for next board."
        )

    return NinetyDayReport(
        deal_name=inputs.deal_name,
        categories=cats,
        on_track_count=on_track,
        at_risk_count=at_risk,
        off_track_count=off_track,
        aggregate_verdict=verdict,
        partner_note=note,
    )


def render_90_day_markdown(
    r: NinetyDayReport,
) -> str:
    lines = [
        "# 90-day post-close reality check",
        "",
        f"_{r.deal_name} — verdict: **{r.aggregate_verdict}**_",
        "",
        f"_{r.partner_note}_",
        "",
        f"- on track: {r.on_track_count}",
        f"- at risk: {r.at_risk_count}",
        f"- off track: {r.off_track_count}",
        "",
        "| Category | Status | Actual | Underwritten | Δ | Partner read |",
        "|---|---|---|---|---|---|",
    ]
    for c in r.categories:
        lines.append(
            f"| {c.name} | {c.status} | {c.actual} | "
            f"{c.underwritten} | {c.delta_summary} | "
            f"{c.partner_read} |"
        )
    return "\n".join(lines)
