"""Post-mortem — structured lessons-learned template for exited deals.

Partners look back at every deal after exit (or after a kill). The
post-mortem captures:

- Actual vs planned outcomes (IRR, MOIC, hold, exit multiple).
- Attribution: what drove the gap (good or bad)?
- Counterfactuals: what should we have done differently?
- Lessons: patterns to propagate to the playbook.

Structured so partners can compare across deals and update the
partner-voice heuristics in `heuristics.py` / `extra_heuristics.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PostMortemInputs:
    deal_id: str
    deal_name: str = ""
    close_year: Optional[int] = None
    exit_year: Optional[int] = None
    planned_irr: Optional[float] = None
    actual_irr: Optional[float] = None
    planned_moic: Optional[float] = None
    actual_moic: Optional[float] = None
    planned_exit_multiple: Optional[float] = None
    actual_exit_multiple: Optional[float] = None
    planned_ebitda_at_exit_m: Optional[float] = None
    actual_ebitda_at_exit_m: Optional[float] = None
    exit_outcome: Optional[str] = None         # "strategic_exit" | "sponsor_exit" | "ipo" | "continuation" | "write_off"
    thesis_executed: Optional[bool] = None
    management_retained: Optional[bool] = None
    external_tailwinds: Optional[str] = None   # narrative
    external_headwinds: Optional[str] = None
    lesson_tags: List[str] = field(default_factory=list)


@dataclass
class PostMortemFinding:
    dimension: str                      # "returns" | "operating" | "structure" | "exit"
    gap: str                            # "beat" | "met" | "missed"
    detail: str
    attribution: str = ""               # "internal" | "external" | "mixed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "gap": self.gap,
            "detail": self.detail,
            "attribution": self.attribution,
        }


@dataclass
class PostMortemReport:
    deal_id: str
    deal_name: str
    findings: List[PostMortemFinding] = field(default_factory=list)
    net_vs_plan: str = ""                # "outperform" | "on_plan" | "underperform"
    top_lessons: List[str] = field(default_factory=list)
    playbook_updates: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "findings": [f.to_dict() for f in self.findings],
            "net_vs_plan": self.net_vs_plan,
            "top_lessons": list(self.top_lessons),
            "playbook_updates": list(self.playbook_updates),
            "partner_note": self.partner_note,
        }


def _gap(actual: Optional[float], planned: Optional[float],
         tolerance: float = 0.05) -> str:
    if actual is None or planned is None:
        return "unknown"
    if planned == 0:
        return "unknown"
    delta = (actual - planned) / abs(planned)
    if delta >= tolerance:
        return "beat"
    if delta <= -tolerance:
        return "missed"
    return "met"


def _irr_finding(inputs: PostMortemInputs) -> Optional[PostMortemFinding]:
    if inputs.actual_irr is None and inputs.planned_irr is None:
        return None
    g = _gap(inputs.actual_irr, inputs.planned_irr)
    if inputs.actual_irr is not None and inputs.planned_irr is not None:
        detail = (f"Actual IRR {inputs.actual_irr*100:.1f}% vs planned "
                  f"{inputs.planned_irr*100:.1f}%.")
    else:
        detail = "IRR comparison incomplete."
    return PostMortemFinding(dimension="returns", gap=g, detail=detail,
                              attribution="mixed")


def _moic_finding(inputs: PostMortemInputs) -> Optional[PostMortemFinding]:
    if inputs.actual_moic is None and inputs.planned_moic is None:
        return None
    g = _gap(inputs.actual_moic, inputs.planned_moic)
    if inputs.actual_moic is not None and inputs.planned_moic is not None:
        detail = (f"Actual MOIC {inputs.actual_moic:.2f}x vs planned "
                  f"{inputs.planned_moic:.2f}x.")
    else:
        detail = "MOIC comparison incomplete."
    return PostMortemFinding(dimension="returns", gap=g, detail=detail,
                              attribution="mixed")


def _exit_multiple_finding(inputs: PostMortemInputs) -> Optional[PostMortemFinding]:
    if (inputs.actual_exit_multiple is None
            and inputs.planned_exit_multiple is None):
        return None
    g = _gap(inputs.actual_exit_multiple, inputs.planned_exit_multiple)
    if (inputs.actual_exit_multiple is not None
            and inputs.planned_exit_multiple is not None):
        detail = (f"Actual exit {inputs.actual_exit_multiple:.2f}x vs "
                  f"planned {inputs.planned_exit_multiple:.2f}x.")
    else:
        detail = "Exit multiple comparison incomplete."
    attribution = "external" if g == "missed" else "mixed"
    return PostMortemFinding(dimension="exit", gap=g, detail=detail,
                              attribution=attribution)


def _ebitda_finding(inputs: PostMortemInputs) -> Optional[PostMortemFinding]:
    if (inputs.actual_ebitda_at_exit_m is None
            and inputs.planned_ebitda_at_exit_m is None):
        return None
    g = _gap(inputs.actual_ebitda_at_exit_m,
             inputs.planned_ebitda_at_exit_m)
    if (inputs.actual_ebitda_at_exit_m is not None
            and inputs.planned_ebitda_at_exit_m is not None):
        detail = (f"Actual exit EBITDA ${inputs.actual_ebitda_at_exit_m:.1f}M "
                  f"vs planned ${inputs.planned_ebitda_at_exit_m:.1f}M.")
    else:
        detail = "Exit EBITDA comparison incomplete."
    attribution = "internal" if g == "missed" else "mixed"
    return PostMortemFinding(dimension="operating", gap=g, detail=detail,
                              attribution=attribution)


def _top_lessons(inputs: PostMortemInputs,
                 findings: List[PostMortemFinding]) -> List[str]:
    out: List[str] = []
    exit_miss = any(f.dimension == "exit" and f.gap == "missed"
                    for f in findings)
    op_miss = any(f.dimension == "operating" and f.gap == "missed"
                  for f in findings)
    if exit_miss and op_miss:
        out.append("Both EBITDA ramp and exit multiple missed — thesis "
                   "was too ambitious on both axes.")
    elif exit_miss:
        out.append("Exit multiple compressed — revisit multiple-expansion "
                   "assumptions for similar deals.")
    elif op_miss:
        out.append("Operating ramp slipped — tighten lever-realization "
                   "discount in forward underwrites.")
    if inputs.management_retained is False:
        out.append("Management departed during hold — tighten retention "
                   "and succession planning pre-close.")
    if inputs.thesis_executed is False:
        out.append("Thesis was not executed — diligence the operating "
                   "partner allocation more carefully.")
    if inputs.exit_outcome == "write_off":
        out.append("Deal was written off — review pre-close red flags; "
                   "update heuristics.")
    return out[:5]


def _playbook_updates(findings: List[PostMortemFinding]) -> List[str]:
    updates: List[str] = []
    for f in findings:
        if f.gap == "missed" and f.dimension == "exit":
            updates.append("Add heuristic: when exit comps compressed, "
                           "haircut modeled exit multiple by 0.75-1.0 turn.")
        if f.gap == "missed" and f.dimension == "operating":
            updates.append("Add heuristic: haircut lever-program ramp by 30%.")
    # Dedup preserving order.
    seen: set = set()
    uniq: List[str] = []
    for u in updates:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq


def _net_vs_plan(findings: List[PostMortemFinding]) -> str:
    returns_findings = [f for f in findings if f.dimension == "returns"]
    if not returns_findings:
        return "unknown"
    misses = sum(1 for f in returns_findings if f.gap == "missed")
    beats = sum(1 for f in returns_findings if f.gap == "beat")
    if beats > misses:
        return "outperform"
    if misses > beats:
        return "underperform"
    return "on_plan"


def run_post_mortem(inputs: PostMortemInputs) -> PostMortemReport:
    findings: List[PostMortemFinding] = []
    for fn in (_irr_finding, _moic_finding,
               _exit_multiple_finding, _ebitda_finding):
        f = fn(inputs)
        if f is not None:
            findings.append(f)

    net = _net_vs_plan(findings)
    lessons = _top_lessons(inputs, findings)
    updates = _playbook_updates(findings)

    if net == "outperform":
        note = "Outperformed plan — capture what worked in the playbook."
    elif net == "underperform":
        note = ("Underperformed plan — propagate lessons to heuristics and "
                "update forward-deal assumptions.")
    else:
        note = "Met plan — document execution but no major playbook change."

    return PostMortemReport(
        deal_id=inputs.deal_id,
        deal_name=inputs.deal_name,
        findings=findings,
        net_vs_plan=net,
        top_lessons=lessons,
        playbook_updates=updates,
        partner_note=note,
    )


def render_post_mortem_markdown(report: PostMortemReport) -> str:
    name = report.deal_name or report.deal_id
    lines = [
        f"# Post-mortem — {name}",
        "",
        f"**Net vs plan:** {report.net_vs_plan}",
        "",
        f"_{report.partner_note}_",
        "",
        "## Findings",
        "",
        "| Dimension | Gap | Attribution | Detail |",
        "|---|---|---|---|",
    ]
    for f in report.findings:
        lines.append(
            f"| {f.dimension} | {f.gap} | {f.attribution} | {f.detail} |"
        )
    if report.top_lessons:
        lines.extend(["", "## Top lessons", ""])
        for l in report.top_lessons:
            lines.append(f"- {l}")
    if report.playbook_updates:
        lines.extend(["", "## Playbook updates", ""])
        for u in report.playbook_updates:
            lines.append(f"- {u}")
    return "\n".join(lines)
