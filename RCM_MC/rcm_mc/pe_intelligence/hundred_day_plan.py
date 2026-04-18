"""100-day post-close action plan generator.

A 100-day plan is the single most important document on day 1 of
ownership. It is a dated, owned checklist of actions that need to
happen in the first ~100 days of sponsor control, usually divided
into four workstreams:

1. **Operational** — RCM fixes, service-line review, capacity check.
2. **Financial** — monthly close, cash management, covenant tracking.
3. **People** — KPI cascade, incentive redesign, retention plan.
4. **Systems & data** — EHR, billing, data rooms, dashboards.

This module takes a :class:`PartnerReview` and generates a 100-day
plan tailored to the deal's issues: high AR days → accelerate AR
aging diagnosis; high denial rate → front-end eligibility work;
carve-out → TSA cutover plan; Medicare-heavy → regulatory-watch
build.

It does NOT replace the operating team's plan — it's a first draft
the team edits on day 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .partner_review import PartnerReview


# ── Model ────────────────────────────────────────────────────────────

@dataclass
class PlanAction:
    workstream: str                   # "operational" | "financial" | "people" | "systems"
    title: str
    due_day: int                      # days post-close
    owner_role: str                   # "CEO" | "CFO" | "COO" | "CIO" | "RCM lead"
    priority: str                     # "P0" | "P1" | "P2"
    detail: str = ""
    trigger: str = ""                 # why this action is in the plan

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workstream": self.workstream,
            "title": self.title,
            "due_day": self.due_day,
            "owner_role": self.owner_role,
            "priority": self.priority,
            "detail": self.detail,
            "trigger": self.trigger,
        }


@dataclass
class HundredDayPlan:
    deal_id: str
    deal_name: str = ""
    actions: List[PlanAction] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "actions": [a.to_dict() for a in self.actions],
            "summary": self.summary,
        }

    def by_workstream(self) -> Dict[str, List[PlanAction]]:
        out: Dict[str, List[PlanAction]] = {}
        for a in self.actions:
            out.setdefault(a.workstream, []).append(a)
        for ws in out:
            out[ws].sort(key=lambda x: (x.due_day, x.priority))
        return out


# ── Action library ──────────────────────────────────────────────────

def _baseline_actions() -> List[PlanAction]:
    """Actions applied to every deal."""
    return [
        PlanAction(
            workstream="financial", title="Standup monthly close process",
            due_day=30, owner_role="CFO", priority="P0",
            detail="Monthly-close discipline, board-pack cadence, covenant tracking.",
            trigger="Standard post-close.",
        ),
        PlanAction(
            workstream="financial", title="Covenant-tracking dashboard",
            due_day=45, owner_role="CFO", priority="P0",
            detail="Live view of leverage, coverage, headroom vs. lender covenants.",
            trigger="Standard post-close.",
        ),
        PlanAction(
            workstream="operational", title="Operating KPI cascade (top 10)",
            due_day=30, owner_role="COO", priority="P0",
            detail="Define, wire, and publish the top 10 operating KPIs.",
            trigger="Standard post-close.",
        ),
        PlanAction(
            workstream="people", title="Retention plan for top 20 employees",
            due_day=45, owner_role="CEO", priority="P1",
            detail="Identify top-20 critical staff; stand up retention agreements.",
            trigger="Standard post-close.",
        ),
        PlanAction(
            workstream="people", title="Incentive redesign for operating leaders",
            due_day=75, owner_role="CEO", priority="P1",
            detail="Align comp to the operating thesis — RCM / EBITDA / margin KPIs.",
            trigger="Standard post-close.",
        ),
        PlanAction(
            workstream="systems", title="Data room → operating data warehouse",
            due_day=60, owner_role="CIO", priority="P1",
            detail="Move diligence data to an ongoing operating warehouse.",
            trigger="Standard post-close.",
        ),
    ]


# ── Triggered actions ────────────────────────────────────────────────

def _ar_days_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="operational", title="AR-aging diagnosis + remediation plan",
        due_day=45, owner_role="RCM lead", priority="P0",
        detail=(
            "Segment AR by payer, age bucket, and denial reason. "
            "Identify top-10 aging customer accounts. Cash acceleration "
            "is the fastest lever in the plan."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _denial_rate_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="operational", title="Denial reason-code concentration review",
        due_day=30, owner_role="RCM lead", priority="P0",
        detail=(
            "Pull top 25 denial reason codes by volume and dollars. "
            "Identify the 3-5 codes that drive >50% of denials. "
            "Front-end edits for these codes are the fastest win."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _writeoff_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="operational", title="Write-off bucket diagnosis",
        due_day=60, owner_role="RCM lead", priority="P1",
        detail=(
            "Segment write-offs by reason (eligibility, timely filing, "
            "coding, documentation). Size the addressable portion."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _data_coverage_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="systems", title="Close data-coverage gaps",
        due_day=45, owner_role="CIO", priority="P0",
        detail=(
            "Identify the missing data elements flagged in diligence. "
            "Stand up reporting for each. Target: > 80% observed/extracted."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _case_mix_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="systems", title="CMI + acuity reporting build",
        due_day=45, owner_role="CIO", priority="P1",
        detail=(
            "Build monthly CMI and DRG-mix reporting from HCRIS and "
            "internal claims. Required for payer contract negotiations."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _covenant_headroom_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="financial", title="Covenant-cushion review + lender engagement",
        due_day=15, owner_role="CFO", priority="P0",
        detail=(
            "Within 2 weeks, run a conservative EBITDA forecast and "
            "identify quarters at risk. Open a lender conversation "
            "pre-emptively — do not wait for the first miss."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _contract_labor_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="people", title="Contract/agency labor reduction plan",
        due_day=60, owner_role="COO", priority="P1",
        detail=(
            "Replace top-5 agency roles with permanent hires. Rate reset "
            "exposure is the largest single margin risk."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _carveout_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="systems", title="TSA cutover tracker",
        due_day=90, owner_role="CIO", priority="P0",
        detail=(
            "Build a dated cutover plan for every TSA service. Every "
            "week of TSA overrun is real cost — track it weekly."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _ehr_migration_action(hit: HeuristicHit) -> PlanAction:
    return PlanAction(
        workstream="systems", title="EHR cutover risk plan",
        due_day=90, owner_role="CIO", priority="P0",
        detail=(
            "Pre-negotiate covenant relief for the cutover quarter. "
            "Model revenue drag 9-12 months around go-live."
        ),
        trigger=f"Heuristic fired: {hit.title}",
    )


def _medicare_regulatory_action() -> PlanAction:
    return PlanAction(
        workstream="financial", title="CMS / IPPS rate-update monitoring",
        due_day=30, owner_role="CFO", priority="P1",
        detail=(
            "Subscribe to CMS rule-making feeds; build a simple "
            "rate-sensitivity monitor into the monthly board pack."
        ),
        trigger="Medicare-heavy payer mix.",
    )


def _rollup_action() -> PlanAction:
    return PlanAction(
        workstream="operational", title="Integration playbook + integration officer",
        due_day=30, owner_role="COO", priority="P0",
        detail=(
            "Named integration officer, 180-day systems consolidation "
            "plan, synergy tracker. Don't wait for the first tuck-in."
        ),
        trigger="Platform rollup thesis.",
    )


# ── Trigger mapping ─────────────────────────────────────────────────

_HIT_TO_ACTION = {
    "ar_days_above_peer": _ar_days_action,
    "denial_rate_elevated": _denial_rate_action,
    "aggressive_denial_improvement": _denial_rate_action,
    "writeoff_rate_high": _writeoff_action,
    "insufficient_data_coverage": _data_coverage_action,
    "case_mix_missing": _case_mix_action,
    "covenant_headroom_tight": _covenant_headroom_action,
    "contract_labor_dependency": _contract_labor_action,
    "carveout_tsa_sprawl": _carveout_action,
    "ehr_migration_planned": _ehr_migration_action,
}


# ── Generator ────────────────────────────────────────────────────────

def generate_plan(review: PartnerReview) -> HundredDayPlan:
    """Generate a 100-day plan from a PartnerReview.

    Combines baseline actions, heuristic-triggered actions, and
    payer-mix-driven actions. Deduplicates by title.
    """
    plan = HundredDayPlan(
        deal_id=review.deal_id,
        deal_name=review.deal_name,
    )

    actions: List[PlanAction] = list(_baseline_actions())

    # Heuristic-triggered actions
    seen_triggers: set = set()
    for hit in review.heuristic_hits:
        fn = _HIT_TO_ACTION.get(hit.id)
        if fn is None:
            continue
        action = fn(hit)
        key = (action.workstream, action.title)
        if key in seen_triggers:
            continue
        seen_triggers.add(key)
        actions.append(action)

    # Payer-mix-driven action
    mix = review.context_summary.get("payer_mix") or {}
    medicare = float(mix.get("medicare", 0.0) or 0.0)
    if medicare > 1.5:
        medicare /= 100.0
    if medicare >= 0.45:
        actions.append(_medicare_regulatory_action())

    # Archetype signal — rollup thesis
    # We don't have direct archetype access, but we do have
    # heuristic_hits; integration-related hits signal rollup.
    for hit in review.heuristic_hits:
        if "rollup" in hit.id or "rollup" in hit.title.lower():
            action = _rollup_action()
            key = (action.workstream, action.title)
            if key not in seen_triggers:
                seen_triggers.add(key)
                actions.append(action)
            break

    # Dedup by (workstream, title).
    seen: set = set()
    dedup: List[PlanAction] = []
    for a in actions:
        k = (a.workstream, a.title)
        if k in seen:
            continue
        seen.add(k)
        dedup.append(a)

    dedup.sort(key=lambda a: (a.due_day, {"P0": 0, "P1": 1, "P2": 2}.get(a.priority, 3)))
    plan.actions = dedup

    p0_count = sum(1 for a in dedup if a.priority == "P0")
    plan.summary = (
        f"{len(dedup)} actions across 4 workstreams; {p0_count} P0 items "
        f"due inside the first 45 days."
    )
    return plan


def render_plan_markdown(plan: HundredDayPlan) -> str:
    """Render a HundredDayPlan as a partner-ready Markdown document."""
    name = plan.deal_name or plan.deal_id or "Deal"
    lines: List[str] = [
        f"# 100-Day Plan — {name}",
        "",
        f"_{plan.summary}_",
        "",
    ]
    workstreams = plan.by_workstream()
    for ws_name in ("operational", "financial", "people", "systems"):
        actions = workstreams.get(ws_name, [])
        if not actions:
            continue
        lines.append(f"## {ws_name.title()}")
        lines.append("")
        lines.append("| Day | Priority | Owner | Action | Why |")
        lines.append("|----:|:--------:|:------|:-------|:----|")
        for a in actions:
            lines.append(
                f"| D+{a.due_day} | {a.priority} | {a.owner_role} | "
                f"**{a.title}** — {a.detail} | {a.trigger} |"
            )
        lines.append("")
    return "\n".join(lines)
