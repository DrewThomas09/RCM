"""Quality of Earnings (QofE) tracker — diligence progress.

QofE is a non-negotiable pre-close deliverable. This module tracks:

- **Status** — in-progress, draft, final.
- **Net working capital (NWC) true-up** — target + actual + peg.
- **Adjustments schedule** — quality / non-recurring / pro-forma.
- **Red findings** — cash-basis revenue, accruals, related-party
  transactions, customer concentration surprises.
- **Auditor + timeline** — who's doing it, days to final.

Partners use the tracker to (a) know if the deal is on critical
path and (b) spot issues before final QofE lands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


QOFE_STATUSES = ("not_started", "in_progress", "draft", "final")


@dataclass
class QofEAdjustment:
    label: str
    category: str                         # "quality" / "non_recurring" /
                                          # "pro_forma"
    amount_m: float
    supported: bool = False               # evidence attached


@dataclass
class QofEFinding:
    severity: str                         # "low" / "medium" / "high"
    area: str
    description: str


@dataclass
class QofEInputs:
    status: str = "in_progress"
    auditor: str = ""
    target_completion_date: str = ""      # ISO date
    days_until_target: int = 30
    nwc_target_m: float = 0.0
    nwc_actual_m: float = 0.0
    nwc_peg_m: float = 0.0
    adjustments: List[QofEAdjustment] = field(default_factory=list)
    findings: List[QofEFinding] = field(default_factory=list)


@dataclass
class QofETracker:
    status: str
    total_adjustments_m: float
    supported_adjustments_m: float
    unsupported_adjustments_m: float
    nwc_vs_peg_m: float
    high_severity_findings: int
    is_on_critical_path: bool
    days_until_target: int
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "total_adjustments_m": self.total_adjustments_m,
            "supported_adjustments_m": self.supported_adjustments_m,
            "unsupported_adjustments_m": self.unsupported_adjustments_m,
            "nwc_vs_peg_m": self.nwc_vs_peg_m,
            "high_severity_findings": self.high_severity_findings,
            "is_on_critical_path": self.is_on_critical_path,
            "days_until_target": self.days_until_target,
            "partner_note": self.partner_note,
        }


def track_qofe(inputs: QofEInputs) -> QofETracker:
    if inputs.status not in QOFE_STATUSES:
        status = "in_progress"
    else:
        status = inputs.status

    total_adj = sum(a.amount_m for a in inputs.adjustments)
    supported = sum(a.amount_m for a in inputs.adjustments if a.supported)
    unsupported = total_adj - supported

    nwc_vs_peg = inputs.nwc_actual_m - inputs.nwc_peg_m
    high_sev = sum(1 for f in inputs.findings if f.severity == "high")

    # Critical path: status not final, or days < 10, or high findings ≥ 2.
    is_critical = (
        status != "final"
        and (inputs.days_until_target < 10 or high_sev >= 2)
    )

    if status == "final" and high_sev == 0:
        note = "QofE final with no high findings — clean."
    elif status == "final" and high_sev > 0:
        note = (f"QofE final but {high_sev} high-severity finding(s) — "
                "reflect in purchase-price mechanism.")
    elif is_critical:
        note = (f"QofE NOT on track: status {status}, "
                f"{inputs.days_until_target}d to target, "
                f"{high_sev} high finding(s). Escalate to deal team lead.")
    elif status == "draft":
        note = (f"QofE draft received — review adjustments "
                f"(${total_adj:,.1f}M, ${unsupported:,.1f}M unsupported).")
    else:
        note = (f"QofE in progress ({inputs.days_until_target}d to target). "
                "Monitor progress daily as deadline approaches.")

    return QofETracker(
        status=status,
        total_adjustments_m=round(total_adj, 2),
        supported_adjustments_m=round(supported, 2),
        unsupported_adjustments_m=round(unsupported, 2),
        nwc_vs_peg_m=round(nwc_vs_peg, 2),
        high_severity_findings=high_sev,
        is_on_critical_path=is_critical,
        days_until_target=inputs.days_until_target,
        partner_note=note,
    )


def render_qofe_markdown(t: QofETracker) -> str:
    lines = [
        "# Quality of Earnings tracker",
        "",
        f"_{t.partner_note}_",
        "",
        f"- Status: **{t.status}**",
        f"- Days until target: {t.days_until_target}",
        f"- Total adjustments: ${t.total_adjustments_m:,.1f}M "
        f"(${t.unsupported_adjustments_m:,.1f}M unsupported)",
        f"- NWC vs peg: ${t.nwc_vs_peg_m:+,.1f}M",
        f"- High-severity findings: {t.high_severity_findings}",
        f"- Critical path: **{'YES' if t.is_on_critical_path else 'no'}**",
    ]
    return "\n".join(lines)
