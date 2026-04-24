"""Cohort-liquidation censoring rule, as a structured integrity check.

The math lives in
:mod:`rcm_mc.diligence.benchmarks.cohort_liquidation` —
``compute_cohort_liquidation`` already refuses to emit a number for
any cohort × window where the cohort is younger than the window.
This module wraps that math as a :class:`GuardrailResult`-returning
check so the packet builder's pre-flight can gate CCD-derived
cohort values behind a single, uniform surface.

Rule (restated from the spec):

    For a cohort of claims with date-of-service ``D`` and a window
    ``T`` days, liquidation at T is computable only when
    ``(as_of_date - D) >= T``. Otherwise the statistic is reported
    as ``INSUFFICIENT_DATA`` with the exact shortfall in days.

What this module does:

- Given a list of canonical claims + ``as_of_date`` + windows, scan
  for cohorts whose age at as_of is less than any window in the set.
- Return PASS when every cohort × window pair is fully mature.
- Return WARN when *some* cohort × window pairs are censored
  (normal — a recent deal always has young cohorts).
- Return FAIL only when the caller asks to compute a specific
  (cohort, window) pair that IS censored — the "you tried to
  fabricate a number" case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..benchmarks.cohort_liquidation import (
    CohortStatus,
    DEFAULT_WINDOWS,
    compute_cohort_liquidation,
)
from .split_enforcer import GuardrailResult


@dataclass
class CensoringCheck:
    """Input bundle for :func:`check_cohort_censoring`."""
    claims: Sequence[Any]
    as_of_date: date
    windows: Sequence[int] = tuple(DEFAULT_WINDOWS)
    # When the caller is about to extract a specific (cohort, window)
    # cell, pass it here. If that cell is censored, we FAIL instead
    # of merely WARNing.
    requested_cells: Optional[Sequence[Tuple[str, int]]] = None


def check_cohort_censoring(req: CensoringCheck) -> GuardrailResult:
    """Run the censoring rule and return a structured verdict."""
    rep = compute_cohort_liquidation(
        req.claims, as_of_date=req.as_of_date, windows=req.windows,
        by_payer_class=False,
    )
    censored = [
        (c.cohort_month, c.days_since_dos)
        for c in rep.cells if c.status == CohortStatus.INSUFFICIENT_DATA
    ]
    mature = [
        (c.cohort_month, c.days_since_dos)
        for c in rep.cells if c.status == CohortStatus.MATURE
    ]

    # FAIL path: the caller asked for cells we can't compute.
    if req.requested_cells:
        censored_set = set(censored)
        requested = [(str(c), int(w)) for c, w in req.requested_cells]
        offending = [r for r in requested if r in censored_set]
        if offending:
            shortfalls = {
                (c, w): _shortfall_days(c, req.as_of_date, w)
                for c, w in offending
            }
            return GuardrailResult(
                guardrail="cohort_censoring", ok=False, status="FAIL",
                reason=(
                    f"{len(offending)} requested (cohort, window) cell(s) are "
                    f"censored; the caller would have fabricated a number. "
                    f"Refuse."
                ),
                details={
                    "censored_requested": [
                        {"cohort": c, "window_days": w,
                         "shortfall_days": d}
                        for (c, w), d in shortfalls.items()
                    ],
                },
            )

    # Everything mature: PASS. At least one censored cell, nothing
    # requested: WARN (normal — recent months).
    if not censored:
        return GuardrailResult(
            guardrail="cohort_censoring", ok=True, status="PASS",
            reason=(
                f"{len(mature)} mature cohort×window cell(s); no cohort "
                f"is younger than the largest window ({max(req.windows)}d)."
            ),
        )
    return GuardrailResult(
        guardrail="cohort_censoring", ok=True, status="WARN",
        reason=(
            f"{len(censored)} cohort×window cell(s) in-flight (as_of - DOS < "
            f"window); reported as INSUFFICIENT_DATA, no number fabricated."
        ),
        details={
            "censored_cells": [
                {"cohort": c, "window_days": w} for c, w in censored
            ],
            "mature_cell_count": len(mature),
        },
    )


def _shortfall_days(
    cohort_month: str, as_of: date, window: int,
) -> int:
    """Days remaining before the (cohort_month, window) pair becomes
    mature. ``cohort_month`` is ``YYYY-MM``; we take the first of the
    month as the cohort-start anchor (matches
    ``compute_cohort_liquidation``)."""
    y, m = cohort_month.split("-")
    cohort_start = date(int(y), int(m), 1)
    age = (as_of - cohort_start).days
    return max(0, window - age)
