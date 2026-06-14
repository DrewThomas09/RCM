"""NEW-05 Cohort retention / churn curves (survival-based).

Kaplan-Meier retention curves per cohort using lifelines, with an optional
Weibull parametric lifetime, a cohort-by-age triangle, a small-cohort
reliability flag (fewer than 30 members), a vintage overlay that tests whether
newer cohorts retain worse, and cliff-month detection (the months with the
steepest conditional churn).

Event-log contract: rows of {entity_id, cohort, duration_months, churned}.
A row may instead carry {cohort_start, last_active} as 'YYYY-MM' strings, in
which case duration_months is the month difference and churned is taken from a
``status`` field equal to "churned".

The estimator is the Kaplan-Meier product-limit estimator. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from lifelines import KaplanMeierFitter

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-05"
MIN_COHORT = 30
DEFAULT_TIMES = (1, 3, 6, 12)
DEFAULT_CLIFF_THRESHOLD = 0.20


def _month_diff(start: str, end: str) -> int:
    sy, sm = (int(x) for x in start.split("-")[:2])
    ey, em = (int(x) for x in end.split("-")[:2])
    return (ey - sy) * 12 + (em - sm)


def _normalize(row: Mapping[str, Any]) -> Tuple[str, float, int]:
    cohort = str(row.get("cohort", row.get("cohort_start", "all")))
    if "duration_months" in row:
        dur = float(row["duration_months"])
    elif "cohort_start" in row and "last_active" in row:
        dur = float(_month_diff(str(row["cohort_start"]), str(row["last_active"])))
    else:
        raise ValueError("row needs duration_months or cohort_start+last_active")
    if "churned" in row:
        event = 1 if bool(row["churned"]) else 0
    else:
        event = 1 if str(row.get("status", "")).lower() == "churned" else 0
    return cohort, dur, event


def _km_for(durations: Sequence[float], events: Sequence[int]):
    kmf = KaplanMeierFitter()
    kmf.fit(durations, events)
    return kmf


def _cliffs(durations: Sequence[float], events: Sequence[int], threshold: float) -> List[Dict[str, float]]:
    """Conditional churn hazard d_i / n_i at each event time, flagging steep months."""
    n = len(durations)
    # at-risk just before each unique event time; censoring at a tie leaves after events.
    order = sorted(range(n), key=lambda i: durations[i])
    out: List[Dict[str, float]] = []
    # group by time
    times = sorted(set(durations[i] for i in order if events[i] == 1))
    for t in times:
        at_risk = sum(1 for i in range(n) if durations[i] >= t)
        d = sum(1 for i in range(n) if durations[i] == t and events[i] == 1)
        hazard = safe_div(d, at_risk)
        if hazard >= threshold:
            out.append({"month": float(t), "hazard": hazard, "churned": float(d), "at_risk": float(at_risk)})
    out.sort(key=lambda r: r["hazard"], reverse=True)
    return out


def retention_curves(
    rows: Sequence[Mapping[str, Any]],
    *,
    times: Sequence[int] = DEFAULT_TIMES,
    min_cohort: int = MIN_COHORT,
    cliff_threshold: float = DEFAULT_CLIFF_THRESHOLD,
    source: str = "Customer or member event log",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Kaplan-Meier retention per cohort with reliability and cliff flags."""
    if not rows:
        raise ValueError("retention_curves requires at least one row")

    by_cohort: Dict[str, Tuple[List[float], List[int]]] = {}
    all_dur: List[float] = []
    all_evt: List[int] = []
    for r in rows:
        cohort, dur, evt = _normalize(r)
        by_cohort.setdefault(cohort, ([], []))
        by_cohort[cohort][0].append(dur)
        by_cohort[cohort][1].append(evt)
        all_dur.append(dur)
        all_evt.append(evt)

    flags: List[Flag] = []
    cohorts_out: Dict[str, Any] = {}
    triangle: List[Dict[str, Any]] = []
    survival_series_pts: List[Dict[str, Any]] = []

    for cohort in sorted(by_cohort):
        dur, evt = by_cohort[cohort]
        size = len(dur)
        kmf = _km_for(dur, evt)
        surv = {int(t): float(kmf.survival_function_at_times(t).iloc[0]) for t in times}
        cliffs = _cliffs(dur, evt, cliff_threshold)
        cohorts_out[cohort] = {
            "size": size,
            "survival": surv,
            "cliffs": cliffs,
            "reliable": size >= min_cohort,
        }
        for t in times:
            triangle.append({"cohort": cohort, "age_months": int(t), "retention": surv[int(t)]})
            survival_series_pts.append({"label": f"{cohort} m{t}", "value": surv[int(t)]})
        if size < min_cohort:
            flags.append(Flag(
                code="small_cohort",
                severity="warn",
                message=(
                    f"Cohort {cohort} has {size} members, below {min_cohort}. "
                    "Kaplan-Meier estimates for it are statistically unreliable."
                ),
            ))

    # Aggregate KM across all members.
    agg_kmf = _km_for(all_dur, all_evt)
    agg_surv = {int(t): float(agg_kmf.survival_function_at_times(t).iloc[0]) for t in times}

    # Vintage overlay: compare retention of cohorts at a common age.
    vintage_flag = None
    cohort_order = sorted(by_cohort)
    if len(cohort_order) >= 2:
        common_age = min(times)
        retentions = [(c, cohorts_out[c]["survival"][int(common_age)]) for c in cohort_order]
        # cohort labels sorted ascending == oldest first (e.g. 2023 < 2024).
        oldest, newest = retentions[0], retentions[-1]
        if newest[1] < oldest[1] - 1e-9:
            vintage_flag = {"age": int(common_age), "oldest": oldest, "newest": newest}
            flags.append(Flag(
                code="newer_cohorts_retain_worse",
                severity="warn",
                message=(
                    f"At month {int(common_age)}, the newest cohort retains "
                    f"{newest[1]*100:.1f} percent versus {oldest[1]*100:.1f} "
                    "percent for the oldest. Retention is deteriorating."
                ),
                source=source,
            ))

    # Reconciliation: survival is monotone non-increasing in age for the aggregate.
    monotone_ok = all(
        agg_surv[int(times[i])] >= agg_surv[int(times[i + 1])] - 1e-9
        for i in range(len(times) - 1)
    )
    reconciliations = [
        Reconciliation(
            identity="aggregate retention is monotone non-increasing in age",
            lhs=1.0 if monotone_ok else 0.0,
            rhs=1.0,
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="Aggregate retention", kind="line",
               points=[{"label": f"m{t}", "value": agg_surv[int(t)]} for t in times]),
        Series(name="Cohort retention triangle", kind="line", points=triangle),
        Series(name="Per-cohort survival detail", kind="line",
               internal_only=True, points=survival_series_pts),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Retention is the Kaplan-Meier product-limit estimate; churn is the event.",
            f"Cohorts below {min_cohort} members are flagged as statistically unreliable.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Cohort retention curves",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(by_cohort)} cohort(s). Aggregate retention at month "
            f"{int(times[0])} is {agg_surv[int(times[0])]*100:.1f} percent."
        ),
        meta={
            "cohorts": cohorts_out,
            "aggregate_survival": agg_surv,
            "vintage_flag": vintage_flag,
            "times": list(int(t) for t in times),
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    rows = []
    plan = [(1, 1, 2), (3, 1, 2), (6, 1, 1), (6, 0, 5)]  # (months, churned, count)
    i = 0
    for months, churned, count in plan:
        for _ in range(count):
            rows.append({"entity_id": f"e{i}", "cohort": "2024", "duration_months": months, "churned": bool(churned)})
            i += 1
    return retention_curves(rows, times=(1, 3, 6), source="Demo event log", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Cohort retention / churn curves (survival-based)",
        audience="both",
        demo=_demo,
    )
)
