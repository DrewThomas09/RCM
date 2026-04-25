"""Team-optimization recommendations.

Synthesises the scorecard, personality, org-design, and
succession outputs into a ranked list of actions:

  PROMOTE        executive whose composite scores high but is
                 in a sub-scope role
  HIRE           bench gap or anti-pattern requires net-new
                 senior hire (e.g., add a CMO at an MSO platform
                 that doesn't have one)
  RESTRUCTURE    span-of-control / layers / dual-hat fix
  COACH          executive scoring above 'concerning' but with
                 specific weakness identified
  SUNSET         executive scoring 'concerning' with no plausible
                 remediation path

Recommendations carry a priority + estimated time-to-impact
so the partner can assemble the 100-day plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .executive import ManagementTeam
from .org_design import OrgDesignScore
from .scorecard import CompetencyScorecard
from .succession import SuccessionRegister


@dataclass
class TeamAction:
    """One recommended action."""
    action_type: str           # PROMOTE / HIRE / RESTRUCTURE /
                               # COACH / SUNSET
    target_person_id: Optional[str]    # None for HIRE/RESTRUCTURE
    role: str
    rationale: str
    priority: str              # high / medium / low
    months_to_impact: int


@dataclass
class TeamRecommendations:
    """Ranked action list."""
    company_name: str
    actions: List[TeamAction] = field(default_factory=list)
    high_priority_count: int = 0


def recommend_team_actions(
    team: ManagementTeam,
    scorecard: Optional[CompetencyScorecard] = None,
    org_design: Optional[OrgDesignScore] = None,
    succession: Optional[SuccessionRegister] = None,
) -> TeamRecommendations:
    """Synthesise inputs into a ranked action list."""
    actions: List[TeamAction] = []
    exec_by_id = {e.person_id: e for e in team.executives}

    # ── From the scorecard: SUNSET / COACH ──────────────────
    if scorecard:
        for cs in scorecard.per_executive:
            if cs.band == "concerning":
                ex = exec_by_id.get(cs.person_id)
                actions.append(TeamAction(
                    action_type="SUNSET",
                    target_person_id=cs.person_id,
                    role=cs.role,
                    rationale=(
                        f"{cs.role} composite {cs.composite:.2f} "
                        f"in concerning band; no clear path to "
                        f"remediation within hold."),
                    priority="high",
                    months_to_impact=6,
                ))
            elif cs.band == "below_avg":
                actions.append(TeamAction(
                    action_type="COACH",
                    target_person_id=cs.person_id,
                    role=cs.role,
                    rationale=(
                        f"{cs.role} composite {cs.composite:.2f} "
                        f"below average; specific competency gaps "
                        f"in {scorecard.weakest_dimension}."),
                    priority="medium",
                    months_to_impact=12,
                ))

    # ── From org-design: HIRE / RESTRUCTURE ─────────────────
    if org_design:
        for ap in org_design.anti_patterns:
            if "No CMO" in ap or "missing" in ap.lower():
                actions.append(TeamAction(
                    action_type="HIRE",
                    target_person_id=None,
                    role="CMO",
                    rationale=ap,
                    priority="high",
                    months_to_impact=9,
                ))
            elif "Dual-hat" in ap:
                actions.append(TeamAction(
                    action_type="RESTRUCTURE",
                    target_person_id=None,
                    role="CFO/CRO split",
                    rationale=ap,
                    priority="high",
                    months_to_impact=6,
                ))
            else:
                actions.append(TeamAction(
                    action_type="RESTRUCTURE",
                    target_person_id=None,
                    role="org structure",
                    rationale=ap,
                    priority="medium",
                    months_to_impact=9,
                ))
        if org_design.span_of_control < 3.0:
            actions.append(TeamAction(
                action_type="RESTRUCTURE",
                target_person_id=None,
                role="span of control",
                rationale=(
                    f"Average span {org_design.avg_span:.1f} "
                    f"outside the healthy 6-8 band — manager "
                    f"layer needs adjustment."),
                priority="medium",
                months_to_impact=12,
            ))

    # ── From succession: HIRE / RESTRUCTURE for high-risk ───
    if succession:
        for risk in succession.risks:
            if risk.severity == "high":
                actions.append(TeamAction(
                    action_type="HIRE",
                    target_person_id=None,
                    role=f"{risk.role} bench",
                    rationale=(
                        f"{risk.role} key-person risk "
                        f"${risk.departure_impact_mm:.1f}M "
                        f"with bench {risk.bench_strength:.1f} — "
                        f"recruit a deputy in year 1."),
                    priority="high",
                    months_to_impact=9,
                ))

    high_priority = sum(1 for a in actions if a.priority == "high")
    return TeamRecommendations(
        company_name=team.company_name,
        actions=actions,
        high_priority_count=high_priority,
    )
