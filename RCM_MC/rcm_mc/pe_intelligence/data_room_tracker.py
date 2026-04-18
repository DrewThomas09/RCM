"""Data-room tracker — seller data-room completeness checker.

Healthcare-PE diligence has a canonical data-room checklist. This
module scores a seller-provided data-room against the expected
document set:

- **Financial** — 3yr audited, monthly P&L, AR aging, bad-debt
  history.
- **Payer** — contracts, fee schedules, denial reports by payer.
- **Operational** — KPI dashboards, service-line P&L, census.
- **Clinical** — quality metrics, CMS reports, inspection records.
- **Regulatory** — licensure, certifications, CIA / OIG history.
- **Legal** — litigation, contracts, employment agreements.
- **IT** — EHR documentation, data security / HIPAA compliance.
- **HR** — org chart, comp / retention schedules, union contracts.

Output: 0-100 completeness score + gap list prioritized by partner
impact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class DataRoomItem:
    category: str
    name: str
    status: str = "missing"          # "present" | "partial" | "missing" | "na"
    priority: str = "P1"             # "P0" | "P1" | "P2"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "status": self.status,
            "priority": self.priority,
            "notes": self.notes,
        }


CANONICAL_CHECKLIST: List[DataRoomItem] = [
    # Financial
    DataRoomItem(category="financial", name="3yr audited financials", priority="P0"),
    DataRoomItem(category="financial", name="monthly P&L (TTM)", priority="P0"),
    DataRoomItem(category="financial", name="AR aging report", priority="P0"),
    DataRoomItem(category="financial", name="bad-debt history 24mo", priority="P1"),
    DataRoomItem(category="financial", name="capex schedule 3yr", priority="P1"),
    DataRoomItem(category="financial", name="working capital schedule", priority="P1"),
    # Payer
    DataRoomItem(category="payer", name="top-10 payer contracts", priority="P0"),
    DataRoomItem(category="payer", name="payer fee schedules", priority="P1"),
    DataRoomItem(category="payer", name="denial reports by payer 24mo", priority="P0"),
    DataRoomItem(category="payer", name="collections by payer 24mo", priority="P1"),
    # Operational
    DataRoomItem(category="operational", name="KPI dashboard (TTM)", priority="P1"),
    DataRoomItem(category="operational", name="service-line P&L", priority="P1"),
    DataRoomItem(category="operational", name="census / volume history", priority="P1"),
    DataRoomItem(category="operational", name="labor hours / productivity", priority="P1"),
    # Clinical
    DataRoomItem(category="clinical", name="CMS quality reports", priority="P1"),
    DataRoomItem(category="clinical", name="readmission rates", priority="P1"),
    DataRoomItem(category="clinical", name="HCAHPS results", priority="P2"),
    DataRoomItem(category="clinical", name="inspection reports 3yr", priority="P0"),
    # Regulatory
    DataRoomItem(category="regulatory", name="state licenses", priority="P0"),
    DataRoomItem(category="regulatory", name="accreditation (TJC / DNV)", priority="P0"),
    DataRoomItem(category="regulatory", name="CMS provider agreements", priority="P0"),
    DataRoomItem(category="regulatory", name="CIA / OIG history", priority="P0"),
    # Legal
    DataRoomItem(category="legal", name="litigation schedule", priority="P0"),
    DataRoomItem(category="legal", name="material contracts", priority="P0"),
    DataRoomItem(category="legal", name="employment agreements (top-20)", priority="P1"),
    DataRoomItem(category="legal", name="IP / license schedule", priority="P2"),
    # IT
    DataRoomItem(category="it", name="EHR documentation", priority="P1"),
    DataRoomItem(category="it", name="HIPAA compliance records", priority="P0"),
    DataRoomItem(category="it", name="IT asset register", priority="P2"),
    DataRoomItem(category="it", name="cybersecurity incident log", priority="P1"),
    # HR
    DataRoomItem(category="hr", name="org chart", priority="P1"),
    DataRoomItem(category="hr", name="comp / retention schedule top-20", priority="P1"),
    DataRoomItem(category="hr", name="union contracts", priority="P1"),
    DataRoomItem(category="hr", name="benefits plan documents", priority="P2"),
]


@dataclass
class DataRoomReport:
    items: List[DataRoomItem] = field(default_factory=list)
    score: int = 0                                # 0..100
    completeness_by_category: Dict[str, float] = field(default_factory=dict)
    p0_missing: List[str] = field(default_factory=list)
    p1_missing: List[str] = field(default_factory=list)
    status: str = ""                              # "ready" | "partial" | "insufficient"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "score": self.score,
            "completeness_by_category": dict(self.completeness_by_category),
            "p0_missing": list(self.p0_missing),
            "p1_missing": list(self.p1_missing),
            "status": self.status,
            "partner_note": self.partner_note,
        }


def _status_score(status: str) -> float:
    return {"present": 1.0, "partial": 0.5, "missing": 0.0, "na": None}.get(status, 0.0)


def analyze_data_room(
    provided_items: List[DataRoomItem],
    *,
    checklist: Optional[List[DataRoomItem]] = None,
) -> DataRoomReport:
    """Score the data room against the canonical checklist."""
    checklist = list(checklist or CANONICAL_CHECKLIST)
    # Map provided items by (category, name).
    provided_map = {(i.category, i.name): i for i in provided_items}

    merged: List[DataRoomItem] = []
    for item in checklist:
        found = provided_map.get((item.category, item.name))
        if found:
            merged.append(DataRoomItem(
                category=item.category, name=item.name,
                status=found.status, priority=item.priority,
                notes=found.notes,
            ))
        else:
            merged.append(DataRoomItem(
                category=item.category, name=item.name,
                status="missing", priority=item.priority,
            ))

    # Weighted score: P0 = 3, P1 = 2, P2 = 1.
    weight = {"P0": 3, "P1": 2, "P2": 1}
    total_weight = 0
    achieved = 0
    cat_weights: Dict[str, float] = {}
    cat_achieved: Dict[str, float] = {}
    for item in merged:
        if item.status == "na":
            continue
        w = weight.get(item.priority, 1)
        total_weight += w
        s = _status_score(item.status) or 0.0
        achieved += w * s
        cat_weights[item.category] = cat_weights.get(item.category, 0.0) + w
        cat_achieved[item.category] = cat_achieved.get(item.category, 0.0) + (w * s)

    score = int(round((achieved / max(total_weight, 1e-9)) * 100))
    completeness_by_category = {
        k: round(cat_achieved.get(k, 0.0) / cat_weights.get(k, 1e-9), 4)
        for k in cat_weights
    }

    p0_missing = [f"{i.category}: {i.name}" for i in merged
                  if i.priority == "P0" and i.status in ("missing", "partial")]
    p1_missing = [f"{i.category}: {i.name}" for i in merged
                  if i.priority == "P1" and i.status in ("missing", "partial")]

    if score >= 90:
        status = "ready"
        note = "Data room is IC-ready."
    elif score >= 70:
        status = "partial"
        note = (f"Data room partial ({len(p0_missing)} P0 gap(s)). "
                "Close P0 gaps before IC.")
    else:
        status = "insufficient"
        note = ("Data room insufficient — escalate seller requests "
                "before continuing diligence.")

    return DataRoomReport(
        items=merged,
        score=score,
        completeness_by_category=completeness_by_category,
        p0_missing=p0_missing,
        p1_missing=p1_missing,
        status=status,
        partner_note=note,
    )


def render_data_room_markdown(report: DataRoomReport) -> str:
    lines = [
        "# Data-room readiness",
        "",
        f"**Score:** {report.score}/100  ",
        f"**Status:** {report.status}",
        "",
        f"_{report.partner_note}_",
        "",
        "## Category completeness",
        "",
    ]
    for cat, pct in sorted(report.completeness_by_category.items()):
        lines.append(f"- {cat}: {pct*100:.0f}%")
    if report.p0_missing:
        lines.extend(["", "## P0 gaps", ""])
        for m in report.p0_missing:
            lines.append(f"- {m}")
    if report.p1_missing:
        lines.extend(["", "## P1 gaps", ""])
        for m in report.p1_missing:
            lines.append(f"- {m}")
    return "\n".join(lines)
