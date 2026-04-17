"""Quality-of-diligence scorer — is our OWN team's work IC-ready?

Partner reflex: before recommending invest/pass, a senior partner
audits their own team's diligence. "Have we done enough work?"
The failure mode is NOT missing the deal — it's going to IC with
a thin book and learning in the room.

This module scores the diligence package across six dimensions:

- **Financial** — QofE final? NWC closed? Recurring vs one-time
  split documented?
- **Commercial** — payer concentration mapped? Contract review
  done? Competitive analysis?
- **Clinical** — quality metrics pulled? CMS survey history
  reviewed? Physician interviews done?
- **Operational** — IT / systems inventoried? KPI dashboards?
  Integration plan?
- **Legal** — QoL (legal) done? FCA / Stark / litigation
  screens? Contract consents?
- **Management** — references called? MIP finalized? Succession
  mapped?

Each dimension is a set of binary items. Score = completed /
required. Overall IC-ready = all dimensions ≥ 80%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# Required items per dimension.
REQUIRED = {
    "financial": [
        "qofe_final",
        "nwc_peg_agreed",
        "recurring_vs_onetime_split",
        "capex_history_3yr",
        "debt_schedule_current",
        "capital_plan_reviewed",
    ],
    "commercial": [
        "payer_concentration_map",
        "top10_contract_review",
        "competitive_map",
        "customer_references",
        "pricing_power_assessment",
    ],
    "clinical": [
        "quality_metrics_pulled",
        "cms_survey_history",
        "physician_interviews_done",
        "coding_audit",
        "rac_audit_history",
    ],
    "operational": [
        "it_systems_inventory",
        "kpi_dashboard_review",
        "integration_playbook_received",
        "labor_cost_review",
        "staffing_pipeline_audit",
    ],
    "legal": [
        "qol_report_final",
        "fca_screen",
        "stark_kickback_screen",
        "material_litigation_review",
        "coc_contract_consents_mapped",
        "environmental_review",
    ],
    "management": [
        "ceo_references_called",
        "cfo_references_called",
        "mip_finalized",
        "succession_plan_mapped",
        "board_charter",
    ],
}


@dataclass
class DiligenceCompleted:
    financial: Set[str] = field(default_factory=set)
    commercial: Set[str] = field(default_factory=set)
    clinical: Set[str] = field(default_factory=set)
    operational: Set[str] = field(default_factory=set)
    legal: Set[str] = field(default_factory=set)
    management: Set[str] = field(default_factory=set)


@dataclass
class DimensionScore:
    dimension: str
    completed: int
    required: int
    completion_pct: float
    missing_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "completed": self.completed,
            "required": self.required,
            "completion_pct": self.completion_pct,
            "missing_items": list(self.missing_items),
        }


@dataclass
class QoDReport:
    dimensions: List[DimensionScore] = field(default_factory=list)
    overall_pct: float = 0.0
    ic_ready: bool = False
    weakest_dimension: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "overall_pct": self.overall_pct,
            "ic_ready": self.ic_ready,
            "weakest_dimension": self.weakest_dimension,
            "partner_note": self.partner_note,
        }


def score_diligence(completed: DiligenceCompleted) -> QoDReport:
    scores: List[DimensionScore] = []
    for dim_name, items in REQUIRED.items():
        done = getattr(completed, dim_name, set())
        required = set(items)
        missing = sorted(required - done)
        pct = (len(required - set(missing)) / len(required)
               if required else 1.0)
        scores.append(DimensionScore(
            dimension=dim_name,
            completed=len(required) - len(missing),
            required=len(required),
            completion_pct=round(pct, 4),
            missing_items=missing,
        ))

    total_req = sum(s.required for s in scores)
    total_done = sum(s.completed for s in scores)
    overall = total_done / total_req if total_req else 0.0
    ic_ready = all(s.completion_pct >= 0.80 for s in scores)
    weakest = min(scores, key=lambda s: s.completion_pct)

    if ic_ready:
        note = (f"Diligence is IC-ready ({overall*100:.0f}% overall). "
                f"Weakest dimension is still {weakest.dimension} at "
                f"{weakest.completion_pct*100:.0f}%.")
    elif weakest.completion_pct < 0.50:
        note = (f"Diligence is NOT IC-ready. {weakest.dimension} is "
                f"at {weakest.completion_pct*100:.0f}% — thin enough "
                "that the partner should decline to recommend "
                "without more work. Pull IC back 2-3 weeks.")
    else:
        note = (f"Diligence is near-ready ({overall*100:.0f}%). Close "
                f"gaps on {weakest.dimension} (missing: "
                f"{', '.join(weakest.missing_items[:3])}) before IC.")

    return QoDReport(
        dimensions=scores,
        overall_pct=round(overall, 4),
        ic_ready=ic_ready,
        weakest_dimension=weakest.dimension,
        partner_note=note,
    )


def render_qod_markdown(r: QoDReport) -> str:
    lines = [
        "# Quality-of-diligence scorecard",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Overall completion: {r.overall_pct*100:.0f}%",
        f"- IC-ready: **{'yes' if r.ic_ready else 'no'}**",
        f"- Weakest dimension: {r.weakest_dimension}",
        "",
        "| Dimension | Completed | Required | % | Missing |",
        "|---|---:|---:|---:|---|",
    ]
    for d in r.dimensions:
        missing_str = (", ".join(d.missing_items[:3])
                        + ("..." if len(d.missing_items) > 3 else "")
                        if d.missing_items else "—")
        lines.append(
            f"| {d.dimension} | {d.completed} | {d.required} | "
            f"{d.completion_pct*100:.0f}% | {missing_str} |"
        )
    return "\n".join(lines)
