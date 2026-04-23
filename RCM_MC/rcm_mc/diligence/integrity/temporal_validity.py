"""Temporal validity stamp for every KPI.

Historical claims from 2023 don't predict 2026 payer behaviour when
OBBBA Medicaid work requirements, site-neutral payment rules, and
MA risk-adjustment revisions phase in across the diligence window.
The PE Intelligence brain's regulatory calendar knows this; the KPI
math currently doesn't.

Every computed KPI carries a :class:`TemporalValidity` stamp with:

- The date range of claims used.
- Any regulatory events that landed *inside* that range, flagged as
  coefficient risks for downstream models.

Callers are expected to attach this to the ObservedMetric's
quality_flags (as a stringified tag) and to surface any flagged
events prominently in the memo. The brain's ``regulatory_calendar``
module owns the canonical event list; we read from it lazily (by
path, not by import) so this module remains independent of the
brain's lifecycle.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import List, Optional, Sequence, Tuple


# The regulatory events we're sensitive to for RCM diligence. Kept
# local so this module is self-contained; the brain's calendar can
# override via ``check_regulatory_overlap(events=...)``.
#
# Dates are effective-date in the US. Cited where possible so a
# partner can verify. All events materially change claims behaviour
# and therefore the stability of historical KPIs as predictors.
_DEFAULT_EVENTS: Tuple[Tuple[str, date, str], ...] = (
    (
        "OBBBA: Medicaid work requirements (phase-in)",
        date(2026, 1, 1),
        "H.R. 1 §71001 — beneficiaries 19–64 must report 80h/mo "
        "'community engagement' to retain coverage. Expected churn "
        "impacts Medicaid claim volume and denial mix.",
    ),
    (
        "Site-neutral payment expansion (OPPS → PFS alignment)",
        date(2026, 1, 1),
        "CMS 2026 OPPS rule extends site-neutral payment to "
        "off-campus HOPDs. Materially reduces outpatient facility "
        "allowed amounts vs history.",
    ),
    (
        "MA risk-adjustment v28 phase-in (year 3)",
        date(2026, 1, 1),
        "Final phase of the v24→v28 transition. Removes ~2,200 HCC "
        "codes; historical MA capitation revenue is not a clean "
        "predictor of post-transition revenue.",
    ),
    (
        "No Surprises Act IDR fee increase",
        date(2025, 1, 1),
        "Administrative fee for IDR changes affect out-of-network "
        "dispute cadence and paid-to-charge ratios on emergency claims.",
    ),
    (
        "ICD-10-CM 2026 annual update",
        date(2025, 10, 1),
        "New codes, deletions, and revised guidelines. Claims coded "
        "pre-10/2025 cannot resubmit under the 2026 set without "
        "remapping.",
    ),
    (
        "OBBBA: Medicaid provider tax cap (hold harmless)",
        date(2026, 10, 1),
        "Lowers the safe harbor for provider taxes from 6% to 3.5% "
        "over five years; affects supplemental Medicaid payment "
        "streams relied on by many acute hospital acquisitions.",
    ),
)


# ── Dataclass ───────────────────────────────────────────────────────

@dataclass
class RegulatoryOverlap:
    name: str
    effective_date: str         # ISO string for JSON-safety
    detail: str


@dataclass
class TemporalValidity:
    """Range + regulatory-overlap stamp attached to a KPI."""
    claims_date_min: Optional[str] = None    # ISO
    claims_date_max: Optional[str] = None    # ISO
    overlapping_events: List[RegulatoryOverlap] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "claims_date_min": self.claims_date_min,
            "claims_date_max": self.claims_date_max,
            "overlapping_events": [asdict(e) for e in self.overlapping_events],
            "warnings": list(self.warnings),
        }


# ── API ─────────────────────────────────────────────────────────────

def check_regulatory_overlap(
    claims_dates: Sequence[date],
    *,
    events: Optional[Sequence[Tuple[str, date, str]]] = None,
) -> TemporalValidity:
    """Produce a :class:`TemporalValidity` stamp for a list of claim
    service dates.

    Empty ``claims_dates`` produces a warning rather than an error —
    the caller may legitimately be computing a KPI that didn't need a
    date range (e.g. a static payer-mix summary).
    """
    tv = TemporalValidity()
    if not claims_dates:
        tv.warnings.append("no claims dates supplied — temporal validity unknown")
        return tv

    valid_dates = [d for d in claims_dates if isinstance(d, date)]
    if not valid_dates:
        tv.warnings.append("claims_dates contained no valid date objects")
        return tv

    lo, hi = min(valid_dates), max(valid_dates)
    tv.claims_date_min = lo.isoformat()
    tv.claims_date_max = hi.isoformat()

    source = events if events is not None else _DEFAULT_EVENTS
    for name, eff_date, detail in source:
        if lo <= eff_date <= hi:
            tv.overlapping_events.append(RegulatoryOverlap(
                name=name, effective_date=eff_date.isoformat(),
                detail=detail,
            ))
    if tv.overlapping_events:
        tv.warnings.append(
            f"{len(tv.overlapping_events)} regulatory event(s) took effect "
            f"inside the claims window — historical KPIs are not a clean "
            f"predictor of forward behaviour."
        )
    return tv


def span_too_short_for_cohort(
    *,
    cohort_dos_month: date,
    as_of_date: date,
    window_days: int,
) -> bool:
    """True if a cohort whose date-of-service is ``cohort_dos_month``
    does not yet have ``window_days`` of post-service data at
    ``as_of_date``. Used by cohort-liquidation censoring.
    """
    available = (as_of_date - cohort_dos_month).days
    return available < window_days
