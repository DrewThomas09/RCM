"""100-day plan from packet — auto-generate the day-1-100 actions.

Partners don't wait until post-close to plan the 100 days. When
they read the packet they are already mentally drafting the
playbook: who gets fired, what gets instrumented, where cash gets
freed, what gets communicated.

This module takes a packet-like context and emits a concrete
100-day action list. Each action has:

- A named workstream (operations / finance / people / RCM /
  commercial / compliance / board).
- A specific owner suggestion (who on the team runs it).
- A **latest-start-by** week (weeks 1-15).
- Expected $ impact where calculable.
- A named trigger explaining why it's on the list.

Partner discipline: < 15 actions. More than that and it is not
a 100-day plan, it is a wish list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanContext:
    # Financial signals.
    current_denial_rate: float = 0.08
    days_in_ar: int = 45
    top_payer_share: float = 0.25
    has_covenant_lite: bool = False
    leverage: float = 5.5
    interest_coverage: float = 3.0
    # Operational.
    integration_pct: float = 1.0
    cdi_program_in_place: bool = False
    erps_count: int = 1
    # Team.
    management_score_0_100: int = 70
    c_suite_tenure_avg_years: float = 4.0
    key_role_gaps: List[str] = field(default_factory=list)
    # Quality / compliance.
    open_fca_exposure: bool = False
    cms_survey_issues: bool = False
    # Commercial.
    commercial_payer_pct: float = 0.50
    has_mip_finalized: bool = False


@dataclass
class PlanAction:
    week_latest: int                       # week 1-15
    workstream: str
    action: str
    owner: str
    expected_impact_m: Optional[float]
    trigger: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_latest": self.week_latest,
            "workstream": self.workstream,
            "action": self.action,
            "owner": self.owner,
            "expected_impact_m": self.expected_impact_m,
            "trigger": self.trigger,
        }


@dataclass
class Plan:
    actions: List[PlanAction] = field(default_factory=list)
    total_expected_impact_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "total_expected_impact_m": self.total_expected_impact_m,
            "partner_note": self.partner_note,
        }


# Rules: each returns a PlanAction or None.

def _mip_action(ctx: PlanContext) -> Optional[PlanAction]:
    if not ctx.has_mip_finalized:
        return PlanAction(
            week_latest=2, workstream="people",
            action=("Finalize MIP grants and communicate to C-suite. "
                    "Cannot retain what isn't granted."),
            owner="CEO + GP",
            expected_impact_m=None,
            trigger="has_mip_finalized=False",
        )
    return None


def _covenant_review(ctx: PlanContext) -> Optional[PlanAction]:
    if not ctx.has_covenant_lite and ctx.leverage >= 6.0:
        return PlanAction(
            week_latest=4, workstream="finance",
            action=("Weekly covenant headroom monitor. Build 13-week "
                    "cash with covenant stress scenarios."),
            owner="CFO + FP&A",
            expected_impact_m=None,
            trigger=(f"leverage={ctx.leverage:.1f}x, "
                     "covenant_lite=False"),
        )
    return None


def _denial_blitz(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.current_denial_rate >= 0.10:
        # Rough impact: 2pp/yr improvement = 2% of Medicare rev ≈ X.
        return PlanAction(
            week_latest=3, workstream="rcm",
            action=("RCM denial-reduction blitz. Top-3 denial reasons "
                    "by payer; weekly denial war-room."),
            owner="VP Revenue Cycle + ops partner",
            expected_impact_m=2.0,
            trigger=f"current_denial_rate={ctx.current_denial_rate:.3f}",
        )
    return None


def _dar_workstream(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.days_in_ar >= 55:
        return PlanAction(
            week_latest=6, workstream="rcm",
            action=("DAR reduction program — first-pass clean-claim, "
                    "back-end billing QA, statement cadence."),
            owner="VP Revenue Cycle",
            expected_impact_m=1.0,
            trigger=f"days_in_ar={ctx.days_in_ar}",
        )
    return None


def _cdi_standup(ctx: PlanContext) -> Optional[PlanAction]:
    if not ctx.cdi_program_in_place:
        return PlanAction(
            week_latest=8, workstream="rcm",
            action=("Stand up CDI program — 2-3 CDI specialists + "
                    "monthly scorecard; target 0.05 CMI lift in 12mo."),
            owner="CMO + VP Revenue Cycle",
            expected_impact_m=1.5,
            trigger="cdi_program_in_place=False",
        )
    return None


def _management_hires(ctx: PlanContext) -> Optional[PlanAction]:
    if (ctx.management_score_0_100 < 60
            or ctx.c_suite_tenure_avg_years < 2.0
            or ctx.key_role_gaps):
        gaps = (", ".join(ctx.key_role_gaps)
                if ctx.key_role_gaps else "CFO or COO")
        return PlanAction(
            week_latest=4, workstream="people",
            action=(f"Named-search for {gaps}. Not a posting — a "
                    "retained search with a named firm and 60-day "
                    "short-list target."),
            owner="CEO + GP",
            expected_impact_m=None,
            trigger=(f"management_score={ctx.management_score_0_100}, "
                     f"tenure_avg={ctx.c_suite_tenure_avg_years}, "
                     f"gaps={ctx.key_role_gaps}"),
        )
    return None


def _erp_consolidation(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.erps_count >= 3:
        return PlanAction(
            week_latest=10, workstream="operations",
            action=(f"ERP consolidation charter — {ctx.erps_count} "
                    "systems to 1; 24-36 month program. Select target "
                    "ERP and name program owner."),
            owner="CFO + CIO",
            expected_impact_m=None,
            trigger=f"erps_count={ctx.erps_count}",
        )
    return None


def _integration_sprint(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.integration_pct < 0.80:
        return PlanAction(
            week_latest=6, workstream="operations",
            action=(f"Integration sprint to close the remaining "
                    f"{(1 - ctx.integration_pct)*100:.0f}% of bolt-on "
                    "systems, chart-of-accounts, KPI reporting."),
            owner="COO + integration PMO",
            expected_impact_m=None,
            trigger=f"integration_pct={ctx.integration_pct:.2f}",
        )
    return None


def _commercial_contracts(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.commercial_payer_pct < 0.50:
        return PlanAction(
            week_latest=12, workstream="commercial",
            action=("Commercial payer strategy review — target 3-5 "
                    "in-network wins in the next 6-9 months; rate-"
                    "escalator language in renewals."),
            owner="Chief Commercial Officer",
            expected_impact_m=None,
            trigger=(f"commercial_payer_pct="
                     f"{ctx.commercial_payer_pct:.2f}"),
        )
    return None


def _fca_counsel(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.open_fca_exposure:
        return PlanAction(
            week_latest=1, workstream="compliance",
            action=("Engage specialized healthcare FCA counsel. "
                    "Weekly status to GP until resolved."),
            owner="GP + outside counsel",
            expected_impact_m=None,
            trigger="open_fca_exposure=True",
        )
    return None


def _cms_survey_remediation(ctx: PlanContext) -> Optional[PlanAction]:
    if ctx.cms_survey_issues:
        return PlanAction(
            week_latest=5, workstream="compliance",
            action=("CMS-survey remediation plan by site; 90-day "
                    "re-audit against named gaps."),
            owner="CMO + CNO",
            expected_impact_m=None,
            trigger="cms_survey_issues=True",
        )
    return None


def _top_payer_contingency(
    ctx: PlanContext,
) -> Optional[PlanAction]:
    if ctx.top_payer_share >= 0.40:
        return PlanAction(
            week_latest=9, workstream="commercial",
            action=(f"Top-payer contingency plan. {ctx.top_payer_share*100:.0f}% "
                    "concentration is an operational risk — map a 12-"
                    "month diversification plan."),
            owner="Chief Commercial Officer",
            expected_impact_m=None,
            trigger=f"top_payer_share={ctx.top_payer_share:.2f}",
        )
    return None


def _board_cadence(ctx: PlanContext) -> PlanAction:
    # Always included.
    return PlanAction(
        week_latest=2, workstream="board",
        action=("Board cadence + committee charter. Monthly operating "
                "review + quarterly strategic; audit, comp, and "
                "compliance committees chartered."),
        owner="GP + board chair",
        expected_impact_m=None,
        trigger="day-1 governance standard",
    )


def _kpi_instrumentation(ctx: PlanContext) -> PlanAction:
    return PlanAction(
        week_latest=4, workstream="finance",
        action=("KPI dashboard instrumented — denials, DAR, volume by "
                "payer, labor, capex. Monthly cadence to GP by week 8."),
        owner="CFO + FP&A",
        expected_impact_m=None,
        trigger="day-1 instrumentation standard",
    )


RULES = (
    _fca_counsel,
    _mip_action,
    _board_cadence,
    _denial_blitz,
    _management_hires,
    _covenant_review,
    _kpi_instrumentation,
    _cms_survey_remediation,
    _integration_sprint,
    _dar_workstream,
    _cdi_standup,
    _top_payer_contingency,
    _erp_consolidation,
    _commercial_contracts,
)


def generate_plan(ctx: PlanContext) -> Plan:
    actions: List[PlanAction] = []
    for rule in RULES:
        a = rule(ctx)
        if a is not None:
            actions.append(a)
    actions.sort(key=lambda a: a.week_latest)
    # Cap at 15 — partner discipline.
    actions = actions[:15]
    total = sum(a.expected_impact_m for a in actions
                 if a.expected_impact_m is not None)

    if len(actions) < 6:
        note = (f"{len(actions)} actions — thin plan, which usually "
                "means the diligence flagged few specific issues. "
                "Partner watch: confirm the packet is complete "
                "before accepting a thin plan.")
    elif len(actions) >= 12:
        note = (f"{len(actions)} actions — aggressive plan. Partner "
                "discipline: ensure owners are named and the CEO can "
                "actually execute on 12+ simultaneous workstreams.")
    else:
        note = (f"{len(actions)} actions — standard 100-day plan. "
                f"~${total:,.1f}M of quantified EBITDA impact from "
                "named items; more from retention / hiring / "
                "governance work.")

    return Plan(
        actions=actions,
        total_expected_impact_m=round(total, 2),
        partner_note=note,
    )


def render_plan_markdown(plan: Plan) -> str:
    lines = [
        "# 100-day plan (auto-derived from packet)",
        "",
        f"_{plan.partner_note}_",
        "",
        f"- Total quantified EBITDA impact: "
        f"${plan.total_expected_impact_m:,.1f}M",
        "",
        "| Wk | Workstream | Action | Owner | $M impact | Trigger |",
        "|---:|---|---|---|---:|---|",
    ]
    for a in plan.actions:
        impact = (f"${a.expected_impact_m:.1f}"
                   if a.expected_impact_m is not None else "—")
        lines.append(
            f"| {a.week_latest} | {a.workstream} | {a.action} | "
            f"{a.owner} | {impact} | {a.trigger} |"
        )
    return "\n".join(lines)
