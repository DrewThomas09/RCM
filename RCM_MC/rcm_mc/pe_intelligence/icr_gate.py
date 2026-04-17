"""Investment-Committee-Ready gate.

A deal is "IC-ready" when every must-have diligence item is green.
This module is the consolidator: it takes a :class:`PartnerReview`,
diligence board, and optional supplemental inputs, then returns a
single yes/no verdict + a checklist of blockers.

Gates checked:

1. **No critical heuristic / red-flag hits** — any CRITICAL severity
   blocks IC.
2. **No implausible band verdicts** — IRR, multiple, margin must not
   be IMPLAUSIBLE.
3. **Data coverage ≥ 60%** — below that we don't pencil.
4. **P0 diligence items complete** — if a diligence board is
   provided.
5. **No LP side-letter breach** — if a side-letter set is provided.
6. **Management score ≥ 50** — team must at minimum be "concerns"
   not "replace" (if score provided).

Returns an :class:`ICReadinessResult` with a boolean, ordered
blocker list, and a partner-voice summary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .diligence_tracker import DiligenceBoard, STATUS_COMPLETE
from .heuristics import SEV_CRITICAL
from .lp_side_letter_flags import ConformanceFinding, has_breach
from .management_assessment import ManagementScore
from .partner_review import PartnerReview
from .reasonableness import VERDICT_IMPLAUSIBLE


@dataclass
class ICReadinessResult:
    ic_ready: bool
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ic_ready": self.ic_ready,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "partner_note": self.partner_note,
        }


def evaluate_ic_readiness(
    review: PartnerReview,
    *,
    diligence_board: Optional[DiligenceBoard] = None,
    side_letter_findings: Optional[List[ConformanceFinding]] = None,
    management: Optional[ManagementScore] = None,
    minimum_data_coverage: float = 0.60,
) -> ICReadinessResult:
    """Return the IC-ready gate result."""
    blockers: List[str] = []
    warnings: List[str] = []

    # 1. Critical heuristics
    critical_hits = [h for h in review.heuristic_hits
                     if h.severity == SEV_CRITICAL]
    if critical_hits:
        blockers.append(
            f"{len(critical_hits)} critical heuristic hit(s): "
            + ", ".join(h.title for h in critical_hits)
        )

    # 2. Implausible bands
    impl_bands = [b for b in review.reasonableness_checks
                  if b.verdict == VERDICT_IMPLAUSIBLE]
    if impl_bands:
        blockers.append(
            f"{len(impl_bands)} implausible band(s): "
            + ", ".join(b.metric for b in impl_bands)
        )

    # 3. Data coverage
    data_cov = review.context_summary.get("data_coverage_pct")
    if data_cov is not None and data_cov < minimum_data_coverage:
        blockers.append(
            f"Data coverage {data_cov*100:.0f}% < required {minimum_data_coverage*100:.0f}%."
        )

    # 4. P0 diligence items
    if diligence_board is not None:
        if not diligence_board.is_ic_ready():
            open_p0 = [i for i in diligence_board.items.values()
                       if i.priority == "P0" and i.status != STATUS_COMPLETE]
            blockers.append(
                f"{len(open_p0)} P0 diligence item(s) incomplete: "
                + ", ".join(i.title for i in open_p0[:3])
            )

    # 5. LP side-letter breach
    if side_letter_findings is not None and has_breach(side_letter_findings):
        breach_items = [f for f in side_letter_findings if f.severity == "breach"]
        blockers.append(
            f"LP side-letter breach: {', '.join(f.rule_id for f in breach_items)}"
        )

    # 6. Management
    if management is not None:
        if management.status == "replace" or management.overall < 50:
            blockers.append(
                f"Management inadequate (overall {management.overall})."
            )
        elif management.status == "concerns":
            warnings.append("Material team concerns; seat-adds planned.")

    # Warnings (non-blocking)
    high_hits = [h for h in review.heuristic_hits if h.severity == "HIGH"]
    if len(high_hits) >= 3:
        warnings.append(f"{len(high_hits)} HIGH-severity findings — review at IC.")

    ic_ready = len(blockers) == 0
    if ic_ready:
        if warnings:
            note = "IC-ready with stated warnings."
        else:
            note = "IC-ready. No blockers identified."
    else:
        note = f"Not IC-ready — {len(blockers)} blocker(s) to resolve."

    return ICReadinessResult(
        ic_ready=ic_ready,
        blockers=blockers,
        warnings=warnings,
        partner_note=note,
    )
