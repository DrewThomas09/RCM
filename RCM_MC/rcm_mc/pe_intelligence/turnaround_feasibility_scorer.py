"""Turnaround feasibility — can this team actually fix it?

Partner statement: "Every turnaround thesis starts with
hope. The ones that work have a specific operator, a
placement budget, and the CEO who caused the problem
already on the exit path. If any of those is missing,
you're underwriting on faith."

### Why this module exists

`failure_archetype_library` flags
`turnaround_without_operator` as a shape-level failure
pattern. But turnaround theses are common and sometimes
work — the question is *which ones*. This module is the
partner's gate: turn the turnaround claim into a
feasibility score.

### 7 dimensions scored

1. **external_operator_identified** — named CEO / COO
   candidate pre-close.
2. **operator_placement_budget_reserved** — $5M+
   earmarked for executive hiring + transition.
3. **ceo_on_exit_path** — incumbent CEO has a defined
   transition timeline (not staying indefinitely).
4. **sponsor_has_turnaround_track_record** — sponsor's
   prior deals in the sector include successful
   operational turnarounds.
5. **hundred_day_plan_has_operator_milestones** — 100-
   day plan specifies named operator hires and their
   owned outcomes.
6. **labor_or_union_constraints_manageable** — no
   binding union contract or licensure constraint that
   blocks the turnaround plan.
7. **turnaround_duration_le_36_months** — realistic
   timeline; long turnarounds compound integration cost.

### Feasibility ladder

- **6-7/7** = `feasible` — proceed on turnaround thesis.
- **4-5/7** = `qualified` — turnaround plausible with
  named mitigation.
- **2-3/7** = `high_risk` — re-price or walk.
- **0-1/7** = `infeasible` — this turnaround doesn't work.

### Operator-placement dollar sizing

If `operator_placement_budget_reserved` is False AND the
turnaround is large ($20M+ EBITDA), partner flags the
$5M+ reservation requirement specifically in the note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TurnaroundInputs:
    thesis_requires_turnaround: bool = True
    external_operator_identified: bool = False
    operator_placement_budget_reserved: bool = False
    operator_placement_budget_m: float = 0.0
    ceo_on_exit_path: bool = False
    sponsor_has_turnaround_track_record: bool = False
    hundred_day_plan_has_operator_milestones: bool = False
    labor_or_union_constraints_manageable: bool = True
    turnaround_duration_months: int = 24
    current_ebitda_m: float = 0.0


@dataclass
class TurnaroundDimension:
    name: str
    passed: bool
    partner_comment: str


@dataclass
class TurnaroundFeasibilityReport:
    score: int                             # 0-7
    tier: str                              # feasible / qualified / high_risk / infeasible
    dimensions: List[TurnaroundDimension] = field(default_factory=list)
    operator_placement_flag: bool = False
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "tier": self.tier,
            "dimensions": [
                {"name": d.name, "passed": d.passed,
                 "partner_comment": d.partner_comment}
                for d in self.dimensions
            ],
            "operator_placement_flag":
                self.operator_placement_flag,
            "partner_note": self.partner_note,
        }


def score_turnaround_feasibility(
    inputs: TurnaroundInputs,
) -> TurnaroundFeasibilityReport:
    dims: List[TurnaroundDimension] = []

    # 1. External operator identified.
    dims.append(TurnaroundDimension(
        name="external_operator_identified",
        passed=inputs.external_operator_identified,
        partner_comment=(
            "External operator candidate named pre-close."
            if inputs.external_operator_identified else
            "No external operator identified — turnaround "
            "on faith."
        ),
    ))

    # 2. Budget reserved.
    budget_ok = (
        inputs.operator_placement_budget_reserved
        and inputs.operator_placement_budget_m >= 5.0
    )
    dims.append(TurnaroundDimension(
        name="operator_placement_budget_reserved",
        passed=budget_ok,
        partner_comment=(
            f"${inputs.operator_placement_budget_m:.1f}M "
            "reserved for placement + transition."
            if budget_ok else
            "No operator-placement budget reserved. "
            "Partner: $5M+ minimum for healthcare "
            "operator search + transition cost."
        ),
    ))

    # 3. CEO on exit path.
    dims.append(TurnaroundDimension(
        name="ceo_on_exit_path",
        passed=inputs.ceo_on_exit_path,
        partner_comment=(
            "Current CEO has defined transition timeline."
            if inputs.ceo_on_exit_path else
            "Incumbent CEO has no exit path. Asking the "
            "creator of the problem to lead the fix."
        ),
    ))

    # 4. Sponsor track record.
    dims.append(TurnaroundDimension(
        name="sponsor_has_turnaround_track_record",
        passed=inputs.sponsor_has_turnaround_track_record,
        partner_comment=(
            "Sponsor has prior successful turnarounds in "
            "sector."
            if inputs.sponsor_has_turnaround_track_record else
            "No sponsor track record on turnarounds in "
            "this sector — we're learning on this deal."
        ),
    ))

    # 5. 100-day operator milestones.
    dims.append(TurnaroundDimension(
        name="hundred_day_plan_has_operator_milestones",
        passed=inputs.hundred_day_plan_has_operator_milestones,
        partner_comment=(
            "100-day plan names operator hires and their "
            "owned outcomes."
            if inputs.hundred_day_plan_has_operator_milestones
            else
            "100-day plan silent on operator milestones. "
            "Build it before IC."
        ),
    ))

    # 6. Labor / union.
    dims.append(TurnaroundDimension(
        name="labor_or_union_constraints_manageable",
        passed=inputs.labor_or_union_constraints_manageable,
        partner_comment=(
            "No binding labor / union constraint on the "
            "turnaround plan."
            if inputs.labor_or_union_constraints_manageable
            else
            "Labor / union / licensure constraint blocks "
            "key parts of the plan."
        ),
    ))

    # 7. Duration ≤ 36 months.
    duration_ok = inputs.turnaround_duration_months <= 36
    dims.append(TurnaroundDimension(
        name="turnaround_duration_le_36_months",
        passed=duration_ok,
        partner_comment=(
            f"Turnaround estimated "
            f"{inputs.turnaround_duration_months} months."
            if duration_ok else
            f"Turnaround estimated "
            f"{inputs.turnaround_duration_months} months — "
            "36+ compounds integration cost."
        ),
    ))

    score = sum(1 for d in dims if d.passed)
    if score >= 6:
        tier = "feasible"
        note = (
            "Turnaround feasible. Partner: proceed; the "
            "ops plan has the inputs to succeed."
        )
    elif score >= 4:
        tier = "qualified"
        missing = [d.name for d in dims if not d.passed]
        note = (
            f"Turnaround qualified ({score}/7). Partner: "
            "proceed only with named mitigation on "
            f"{', '.join(missing[:3])}."
        )
    elif score >= 2:
        tier = "high_risk"
        note = (
            f"Turnaround high-risk ({score}/7). Partner: "
            "re-price down or walk. Current shape is "
            "turnaround-without-operator in "
            "disguise."
        )
    else:
        tier = "infeasible"
        note = (
            f"Turnaround infeasible ({score}/7). Partner: "
            "walk. No input this thesis relies on is in "
            "place."
        )

    # Budget flag specifically on larger deals.
    placement_flag = (
        not budget_ok
        and inputs.current_ebitda_m >= 20.0
        and inputs.thesis_requires_turnaround
    )
    if placement_flag:
        note += (
            f" On a ${inputs.current_ebitda_m:.0f}M EBITDA "
            "target, $5M+ operator-placement budget is a "
            "closing-condition item, not a nice-to-have."
        )

    return TurnaroundFeasibilityReport(
        score=score,
        tier=tier,
        dimensions=dims,
        operator_placement_flag=placement_flag,
        partner_note=note,
    )


def render_turnaround_feasibility_markdown(
    r: TurnaroundFeasibilityReport,
) -> str:
    lines = [
        "# Turnaround feasibility",
        "",
        f"**Tier:** `{r.tier}` ({r.score}/7)",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    if r.operator_placement_flag:
        lines.append(
            "> **Flag:** operator-placement budget required "
            "as a closing condition."
        )
        lines.append("")
    lines.append("| Dimension | Passed | Partner comment |")
    lines.append("|---|---|---|")
    for d in r.dimensions:
        check = "✓" if d.passed else "✗"
        lines.append(
            f"| {d.name} | {check} | {d.partner_comment} |"
        )
    return "\n".join(lines)
