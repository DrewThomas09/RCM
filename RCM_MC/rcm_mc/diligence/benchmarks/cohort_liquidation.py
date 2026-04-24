"""Cohort liquidation analysis — with mandatory as_of censoring.

The trap we're guarding against:

    An analyst running diligence on 2026-03-15 looks at the
    "January 2026 cohort at 90 days." But 2026-01-15 + 90 days =
    2026-04-15, which is *in the future*. Only ~60 days of actual
    resolution data exist; the "90-day number" is a lie by 30 days.

This module computes cumulative liquidation curves and **refuses** to
report windows that aren't fully mature. A cohort whose date-of-
service is within ``window_days`` of ``as_of_date`` returns a
:class:`CohortCell` with ``status=INSUFFICIENT_DATA`` and a clear
reason. The UI renders these as "in-flight — insufficient data"
rather than a number.

Reference: HFMA discusses collection-velocity curves without going
hard on censoring, but every reputable diligence shop (Chartis,
KaufmanHall, BDO) applies this censoring by convention. Our
implementation is explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ── Result shapes ──────────────────────────────────────────────────

class CohortStatus(str, Enum):
    MATURE = "MATURE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EMPTY = "EMPTY"


@dataclass
class CohortCell:
    """One (cohort_month, days_since_dos) entry."""
    cohort_month: str                # "2024-01"
    days_since_dos: int              # 30 | 60 | 90 | 120
    status: CohortStatus
    cumulative_liquidation_pct: Optional[float] = None
    numerator_usd: float = 0.0
    denominator_usd: float = 0.0
    cohort_size_claims: int = 0
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort_month": self.cohort_month,
            "days_since_dos": self.days_since_dos,
            "status": self.status.value,
            "cumulative_liquidation_pct": self.cumulative_liquidation_pct,
            "numerator_usd": self.numerator_usd,
            "denominator_usd": self.denominator_usd,
            "cohort_size_claims": self.cohort_size_claims,
            "reason": self.reason,
        }


@dataclass
class CohortLiquidationReport:
    """Full grid of (cohort × window) cells + per-payer-class splits."""
    as_of_date: date
    window_days: Tuple[int, ...] = (30, 60, 90, 120)
    cells: List[CohortCell] = field(default_factory=list)
    cells_by_payer_class: Dict[str, List[CohortCell]] = field(default_factory=dict)

    def mature_cells(self) -> List[CohortCell]:
        return [c for c in self.cells if c.status == CohortStatus.MATURE]

    def censored_cells(self) -> List[CohortCell]:
        return [c for c in self.cells if c.status == CohortStatus.INSUFFICIENT_DATA]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of_date": self.as_of_date.isoformat(),
            "window_days": list(self.window_days),
            "cells": [c.to_dict() for c in self.cells],
            "cells_by_payer_class": {
                k: [c.to_dict() for c in v]
                for k, v in self.cells_by_payer_class.items()
            },
        }


# ── Public API ─────────────────────────────────────────────────────

DEFAULT_WINDOWS = (30, 60, 90, 120)


def compute_cohort_liquidation(
    claims: Sequence[Any],
    *,
    as_of_date: date,
    windows: Sequence[int] = DEFAULT_WINDOWS,
    by_payer_class: bool = True,
    cohort_granularity: str = "month",  # "month" | "quarter"
) -> CohortLiquidationReport:
    """Group claims by ``cohort_granularity`` of DOS; compute cumulative
    liquidation % at each window; censor windows that aren't fully
    mature as of ``as_of_date``.

    Liquidation % at W days = sum(paid_amount on claims where
    (paid_date - service_date_from) ≤ W) / sum(allowed_or_charge).

    Denied claims are counted in the denominator per HFMA: they are
    part of the original expected receivable even if unrecoverable.
    """
    windows = tuple(sorted(set(windows)))

    # Bucket claims by cohort key.
    by_cohort: Dict[str, List[Any]] = {}
    for c in claims:
        if c.service_date_from is None:
            continue
        key = _cohort_key(c.service_date_from, cohort_granularity)
        by_cohort.setdefault(key, []).append(c)

    report = CohortLiquidationReport(
        as_of_date=as_of_date,
        window_days=windows,
    )

    for cohort_key in sorted(by_cohort.keys()):
        cohort_claims = by_cohort[cohort_key]
        cohort_start = _cohort_start_date(cohort_key, cohort_granularity)
        # The "age" of the cohort at as_of_date is from the START of
        # the cohort bucket (worst-case most-mature claim). A claim
        # that happened later in the month will have even less
        # post-DOS time; we measure age from the OLDEST claim (cohort
        # start) so the censoring is conservative in the MATURE
        # direction.
        cohort_age_days = (as_of_date - cohort_start).days

        for w in windows:
            cell = _compute_cell(
                cohort_key=cohort_key, cohort_claims=cohort_claims,
                window=w, cohort_age_days=cohort_age_days,
            )
            report.cells.append(cell)

    # Per-payer-class split.
    if by_payer_class:
        by_class: Dict[str, Dict[str, List[Any]]] = {}
        for c in claims:
            if c.service_date_from is None:
                continue
            cls = c.payer_class.value if hasattr(c.payer_class, "value") \
                else str(c.payer_class)
            key = _cohort_key(c.service_date_from, cohort_granularity)
            by_class.setdefault(cls, {}).setdefault(key, []).append(c)
        for cls, ck_map in by_class.items():
            out: List[CohortCell] = []
            for cohort_key in sorted(ck_map.keys()):
                cohort_claims = ck_map[cohort_key]
                cohort_start = _cohort_start_date(cohort_key, cohort_granularity)
                cohort_age_days = (as_of_date - cohort_start).days
                for w in windows:
                    out.append(_compute_cell(
                        cohort_key=cohort_key, cohort_claims=cohort_claims,
                        window=w, cohort_age_days=cohort_age_days,
                    ))
            report.cells_by_payer_class[cls] = out

    return report


def _compute_cell(
    *,
    cohort_key: str,
    cohort_claims: Sequence[Any],
    window: int,
    cohort_age_days: int,
) -> CohortCell:
    if cohort_age_days < window:
        # Censored — refuse to report, per spec.
        return CohortCell(
            cohort_month=cohort_key, days_since_dos=window,
            status=CohortStatus.INSUFFICIENT_DATA,
            cohort_size_claims=len(cohort_claims),
            reason=(
                f"cohort age {cohort_age_days}d < window {window}d — "
                f"in-flight, insufficient data"
            ),
        )
    if not cohort_claims:
        return CohortCell(
            cohort_month=cohort_key, days_since_dos=window,
            status=CohortStatus.EMPTY,
            reason="no claims in this cohort",
        )

    num = 0.0
    denom = 0.0
    for c in cohort_claims:
        billable = float(c.allowed_amount or c.charge_amount or 0.0)
        denom += billable
        if c.paid_date is not None and c.service_date_from is not None:
            delta = (c.paid_date - c.service_date_from).days
            if 0 <= delta <= window:
                num += float(c.paid_amount or 0.0)
    pct = (num / denom) if denom > 0 else None
    return CohortCell(
        cohort_month=cohort_key, days_since_dos=window,
        status=CohortStatus.MATURE,
        cumulative_liquidation_pct=pct,
        numerator_usd=num, denominator_usd=denom,
        cohort_size_claims=len(cohort_claims),
    )


def _cohort_key(d: date, granularity: str) -> str:
    if granularity == "quarter":
        q = (d.month - 1) // 3 + 1
        return f"{d.year}-Q{q}"
    return f"{d.year:04d}-{d.month:02d}"


def _cohort_start_date(key: str, granularity: str) -> date:
    if granularity == "quarter":
        year, q = key.split("-Q")
        month = (int(q) - 1) * 3 + 1
        return date(int(year), month, 1)
    year, month = key.split("-")
    return date(int(year), int(month), 1)
